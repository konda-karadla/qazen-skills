"""Proves the schema-invalid -> retry -> corrected loop actually runs, using a
provider stub that returns broken JSON once, then a valid fixture on retry.
"""
import json
import os

os.environ.setdefault("LLM_PROVIDER", "mock")

from app.gateway import invoke_skill
from app.providers.mock import _FIXTURES_DIR
from app.providers import base


class FlakyThenValidProvider(base.LLMProvider):
    """First call: violates the schema (missing required field).
    Second call: returns the real S1 fixture.
    """

    def __init__(self):
        self.calls = 0

    def complete(self, prompt: str, *, skill_id: str) -> str:
        self.calls += 1
        if self.calls == 1:
            return json.dumps({"source_type": "BRD"})  # missing required fields
        return (_FIXTURES_DIR / "s1.json").read_text(encoding="utf-8")


def test_retry_recovers_from_schema_invalid_first_attempt(monkeypatch):
    stub = FlakyThenValidProvider()
    monkeypatch.setattr("app.gateway.get_provider", lambda: stub)

    result = invoke_skill("S1", {"raw": "some BRD text"})

    assert stub.calls == 2
    assert result.attempts == 2
    assert result.escalated is False
    assert result.output["source_type"] == "BRD"


def test_exhausting_retries_returns_escalation(monkeypatch):
    class AlwaysBrokenProvider(base.LLMProvider):
        def complete(self, prompt: str, *, skill_id: str) -> str:
            return json.dumps({"source_type": "BRD"})  # always missing required fields

    monkeypatch.setattr("app.gateway.get_provider", lambda: AlwaysBrokenProvider())

    result = invoke_skill("S1", {"raw": "some BRD text"})

    assert result.escalated is True
    assert "schema validation" in result.escalation_reason.lower()
