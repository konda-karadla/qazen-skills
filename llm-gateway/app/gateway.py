"""The Gateway's one job: assemble prompt -> call provider -> parse ->
validate against JSON Schema -> retry on invalid -> return.

Everything here is stateless across HTTP calls -- no skill's prior
invocation is remembered. A single HTTP call to /v1/skills/{skill_id}/invoke
may make more than one underlying LLM completion call (the retry loop), but
never carries context from a *different* skill invocation.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.config import settings
from app.prompt_builder import build_prompt
from app.providers import get_provider
from app.schema_validator import SchemaValidationError, load_schema, validate

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.DOTALL)

# Skills whose schema root is an object wrapping a top-level array the model
# sometimes emits bare (common with smaller local LLMs).
_BARE_ARRAY_WRAPPERS = {
    "S3": "test_cases",
}

# Schema source_tags allow only FACT | DECISION. Weaker models often emit INFERENCE.
_SOURCE_TAG_ALIASES = {
    "INFERENCE": "FACT",
    "INFERRED": "FACT",
    "ASSUMPTION": "FACT",
    "GUESS": "FACT",
}
_ALLOWED_SOURCE_TAGS = frozenset({"FACT", "DECISION"})


class GatewayError(Exception):
    pass


@dataclass
class GatewayResult:
    skill_id: str
    output: dict
    attempts: int
    escalated: bool = False
    escalation_reason: str | None = None
    raw_attempts: list[str] = field(default_factory=list)


def _strip_nulls(value: object) -> object:
    """Drop JSON nulls so optional schema string fields aren't invalidated by local LLMs."""
    if isinstance(value, dict):
        return {k: _strip_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_strip_nulls(v) for v in value]
    return value


def _normalize_source_tags(value: object) -> object:
    """Map off-schema source_tags (e.g. INFERENCE) onto FACT | DECISION."""
    if isinstance(value, dict):
        out: dict[str, object] = {}
        for key, child in value.items():
            if key == "source_tags" and isinstance(child, list):
                mapped: list[object] = []
                for tag in child:
                    if isinstance(tag, str):
                        upper = tag.strip().upper()
                        if upper in _ALLOWED_SOURCE_TAGS:
                            mapped.append(upper)
                        else:
                            mapped.append(_SOURCE_TAG_ALIASES.get(upper, "FACT"))
                    else:
                        mapped.append(tag)
                out[key] = mapped
            else:
                out[key] = _normalize_source_tags(child)
        return out
    if isinstance(value, list):
        return [_normalize_source_tags(v) for v in value]
    return value


def _extract_json(raw_text: str, *, skill_id: str | None = None) -> dict:
    text = raw_text.strip()
    match = _JSON_FENCE_RE.search(text)
    candidate = match.group(1).strip() if match else text
    # If fences weren't used, still try to slice from first JSON token.
    if not match:
        for i, ch in enumerate(candidate):
            if ch in "{[":
                candidate = candidate[i:]
                break
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise GatewayError(f"Provider response was not valid JSON: {exc}\nRaw: {raw_text[:2000]}") from exc

    if isinstance(parsed, list):
        wrap_key = _BARE_ARRAY_WRAPPERS.get(skill_id or "")
        if wrap_key:
            parsed = {wrap_key: parsed}
        else:
            raise GatewayError(
                f"Provider returned a JSON array; expected an object for {skill_id or 'skill'}.\n"
                f"Raw: {raw_text[:2000]}"
            )
    if not isinstance(parsed, dict):
        raise GatewayError(
            f"Provider returned JSON type {type(parsed).__name__}; expected object.\n"
            f"Raw: {raw_text[:2000]}"
        )
    return _normalize_source_tags(_strip_nulls(parsed))  # type: ignore[return-value]


def invoke_skill(skill_id: str, input_payload: dict) -> GatewayResult:
    provider = get_provider()
    output_schema = load_schema(skill_id)

    prior_output: dict | None = None
    prior_error: str | None = None
    raw_attempts: list[str] = []

    max_attempts = settings.max_schema_retries + 1
    for attempt in range(1, max_attempts + 1):
        prompt = build_prompt(
            skill_id,
            input_payload,
            output_schema=output_schema,
            prior_output=prior_output,
            prior_error=prior_error,
        )
        raw = provider.complete(prompt, skill_id=skill_id)
        raw_attempts.append(raw)

        try:
            candidate = _extract_json(raw, skill_id=skill_id)
            validate(skill_id, candidate)
        except (GatewayError, SchemaValidationError) as exc:
            prior_output = candidate if isinstance(exc, SchemaValidationError) else None
            prior_error = "; ".join(exc.errors) if isinstance(exc, SchemaValidationError) else str(exc)
            if attempt == max_attempts:
                return GatewayResult(
                    skill_id=skill_id,
                    output=prior_output or {},
                    attempts=attempt,
                    escalated=True,
                    escalation_reason=(
                        f"Schema validation failed after {attempt} attempt(s): {prior_error}"
                    ),
                    raw_attempts=raw_attempts,
                )
            continue

        return GatewayResult(skill_id=skill_id, output=candidate, attempts=attempt, raw_attempts=raw_attempts)

    raise GatewayError("unreachable")  # pragma: no cover
