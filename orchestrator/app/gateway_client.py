from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import settings


class SkillEscalatedError(Exception):
    """Raised when the LLM Gateway exhausted its schema-validation retries.

    Per AGENT_INSTRUCTIONS.md Section 7, this must surface as a visible
    escalation, not be silently swallowed or defaulted around.
    """

    def __init__(self, skill_id: str, reason: str):
        super().__init__(f"{skill_id} escalated: {reason}")
        self.skill_id = skill_id
        self.reason = reason


class LlmGatewayError(Exception):
    """Gateway HTTP / transport failure with a reason safe to show in the UI."""

    def __init__(self, skill_id: str, reason: str, *, status_code: int | None = None):
        super().__init__(f"{skill_id}: {reason}")
        self.skill_id = skill_id
        self.reason = reason
        self.status_code = status_code


@dataclass
class SkillResult:
    skill_id: str
    output: dict
    attempts: int


def invoke_skill(
    skill_id: str,
    input_payload: dict,
    *,
    timeout: float | None = None,
) -> SkillResult:
    try:
        response = httpx.post(
            f"{settings.llm_gateway_url}/v1/skills/{skill_id}/invoke",
            json={"input": input_payload},
            timeout=settings.llm_gateway_timeout_seconds if timeout is None else timeout,
        )
    except httpx.TimeoutException as exc:
        raise LlmGatewayError(
            skill_id,
            "LLM Gateway timed out. Increase LLM_GATEWAY_TIMEOUT_SECONDS or switch model/profile "
            "in repo-root .env and restart :8000.",
            status_code=None,
        ) from exc
    except httpx.HTTPError as exc:
        raise LlmGatewayError(
            skill_id,
            f"LLM Gateway unreachable ({type(exc).__name__}). Confirm gateway :8000 is running.",
            status_code=None,
        ) from exc

    if response.status_code >= 400:
        body = (response.text or "")[:2000]
        lower = body.lower()
        if response.status_code == 429 or "quota" in lower or "rate limit" in lower:
            reason = (
                f"LLM quota or rate limit (HTTP {response.status_code}). "
                "Update OPENAI_API_KEY / switch LLM_PROFILE in repo-root .env, then restart "
                f"the gateway on :8000. Details: {body or 'no body'}"
            )
        elif response.status_code in (401, 403) or "api key" in lower or "unauthorized" in lower:
            reason = (
                f"LLM authentication failed (HTTP {response.status_code}). "
                "Set a valid API key for the active LLM_PROFILE in repo-root .env and restart "
                f"gateway :8000. Details: {body or 'no body'}"
            )
        else:
            reason = f"LLM Gateway HTTP {response.status_code}: {body or 'no body'}"
        raise LlmGatewayError(skill_id, reason, status_code=response.status_code)

    body = response.json()
    if body.get("escalated"):
        raise SkillEscalatedError(skill_id, body.get("escalation_reason") or "unspecified")
    return SkillResult(
        skill_id=body["skill_id"], output=body["output"], attempts=body["attempts"]
    )
