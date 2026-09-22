from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.gateway import GatewayError, invoke_skill
from app.schema_validator import SchemaNotFoundError

app = FastAPI(
    title="QAZen LLM Gateway",
    description=(
        "Stateless completion service. Assembles AGENT_INSTRUCTIONS.md + the "
        "requested skill.md + caller-supplied input into one prompt per skill "
        "invocation, validates the structured output against that skill's "
        "JSON Schema, and retries on schema failure before returning."
    ),
    version="0.1.0",
)


class InvokeRequest(BaseModel):
    input: dict


class InvokeResponse(BaseModel):
    skill_id: str
    output: dict
    attempts: int
    escalated: bool
    escalation_reason: str | None = None


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "provider": settings.provider,
        "llm_profile": settings.llm_profile,
        "openai_base_url": settings.openai_base_url,
        "openai_model": settings.openai_model,
    }


@app.post("/v1/skills/{skill_id}/invoke", response_model=InvokeResponse)
def invoke(skill_id: str, request: InvokeRequest) -> InvokeResponse:
    skill_id = skill_id.upper()
    try:
        result = invoke_skill(skill_id, request.input)
    except SchemaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GatewayError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return InvokeResponse(
        skill_id=result.skill_id,
        output=result.output,
        attempts=result.attempts,
        escalated=result.escalated,
        escalation_reason=result.escalation_reason,
    )
