"""Phase 0 smoke test: prove the Prompt Builder -> Provider -> Schema Validation
loop works end to end for every skill in the vertical slice, using the mock
provider (no AWS credentials required).

Run with: pytest llm-gateway/tests -q   (from repo root, with LLM_PROVIDER=mock)
"""
import os

os.environ.setdefault("LLM_PROVIDER", "mock")

import pytest

from app.gateway import invoke_skill
from app.prompt_builder import build_prompt, load_agent_instructions, load_skill_md
from app.schema_validator import validate

VERTICAL_SLICE_SKILLS = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11"]


def test_agent_instructions_loads():
    text = load_agent_instructions()
    assert "AGENT_INSTRUCTIONS.md" in text
    assert "Version:** 2.0.0" in text


@pytest.mark.parametrize("skill_id", VERTICAL_SLICE_SKILLS)
def test_skill_md_loads(skill_id):
    text = load_skill_md(skill_id)
    assert skill_id in text


@pytest.mark.parametrize("skill_id", VERTICAL_SLICE_SKILLS)
def test_prompt_builds(skill_id):
    prompt = build_prompt(skill_id, {"example": "input"})
    assert "BINDING RULEBOOK" in prompt
    assert f"SKILL DEFINITION -- {skill_id}" in prompt


@pytest.mark.parametrize("skill_id", VERTICAL_SLICE_SKILLS)
def test_invoke_skill_returns_schema_valid_output(skill_id):
    result = invoke_skill(skill_id, {"example": "input"})
    assert result.escalated is False, result.escalation_reason
    assert result.attempts == 1
    # Should not raise:
    validate(skill_id, result.output)


def test_invoke_unknown_skill_raises_for_missing_schema():
    from app.schema_validator import SchemaNotFoundError

    with pytest.raises(SchemaNotFoundError):
        invoke_skill("S99", {})
