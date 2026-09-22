from __future__ import annotations

import json
from pathlib import Path

from app.providers.base import LLMProvider

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Lowercase skill id ('s1'..'s11') -> fixture file.
_AVAILABLE = {"s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11"}


class MockProviderError(Exception):
    pass


class MockProvider(LLMProvider):
    """Returns a canned, schema-valid example response per skill.

    Used until AWS Bedrock credentials are provisioned (LLM_PROVIDER=mock is
    the default, see infra/.env.example). This lets the Orchestrator, schema
    validation/retry loop, and Automation Model Compiler all be exercised
    end-to-end without any external LLM dependency.
    """

    def complete(self, prompt: str, *, skill_id: str) -> str:
        key = skill_id.lower()
        if key not in _AVAILABLE:
            raise MockProviderError(
                f"No mock fixture available for '{skill_id}'. "
                f"Available: {sorted(_AVAILABLE)}. Add one under "
                f"llm-gateway/app/providers/fixtures/, or set LLM_PROVIDER=bedrock."
            )
        fixture_path = _FIXTURES_DIR / f"{key}.json"
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        return json.dumps(data)
