"""LLM Gateway configuration.

Loaded from environment (see infra/.env.example). Kept intentionally small --
the Gateway has no business logic of its own beyond assembling a prompt,
calling a provider, and validating the result.

LLM_PROFILE selects presets (ollama | gemini | mistral | groq | openai | mock).
Explicit LLM_PROVIDER=mock always wins for offline tests. Explicit OPENAI_* env
values override profile defaults. Profile-specific keys (MISTRAL_API_KEY,
GROQ_API_KEY, GEMINI_API_KEY) win over OPENAI_API_KEY for that profile.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]

# Load repo-root .env for local OpenAI / infra vars. Existing process env wins
# (override=False) so CI and explicit LLM_PROVIDER=mock for tests stay offline.
load_dotenv(REPO_ROOT / ".env", override=False)

_PROFILE_PRESETS: dict[str, dict[str, str]] = {
    "ollama": {
        "provider": "openai",
        "openai_base_url": "http://127.0.0.1:11434/v1",
        "openai_api_key": "ollama",
        "openai_model": "qwen2.5:7b",
    },
    "gemini": {
        "provider": "openai",
        "openai_base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "openai_api_key": "",
        "openai_model": "gemini-3.6-flash",
    },
    "mistral": {
        "provider": "openai",
        "openai_base_url": "https://api.mistral.ai/v1",
        "openai_api_key": "",
        "openai_model": "mistral-small-latest",
    },
    "groq": {
        "provider": "openai",
        "openai_base_url": "https://api.groq.com/openai/v1",
        "openai_api_key": "",
        "openai_model": "openai/gpt-oss-20b",
    },
    "openai": {
        "provider": "openai",
        "openai_base_url": "https://api.openai.com/v1",
        "openai_api_key": "",
        "openai_model": "gpt-4o-mini",
    },
    "mock": {
        "provider": "mock",
        "openai_base_url": "https://api.openai.com/v1",
        "openai_api_key": "",
        "openai_model": "gpt-4o-mini",
    },
}

# Cloud OpenAI-compatible profiles that accept response_format=json_object.
# Ollama is excluded: local models may reject the parameter.
JSON_OBJECT_PROFILES = frozenset({"gemini", "mistral", "openai", "groq"})

# Dedicated key env vars so Gemini and Mistral keys can both live in .env.
_PROFILE_API_KEY_ENV: dict[str, str] = {
    "gemini": "GEMINI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "groq": "GROQ_API_KEY",
}


def _env(name: str) -> Optional[str]:
    raw = os.getenv(name)
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped if stripped else None


def resolve_llm_runtime() -> dict[str, Any]:
    """Resolve profile + provider + OpenAI-compatible settings.

    Order:
      1. LLM_PROVIDER=mock (or LLM_PROFILE=mock) → mock
      2. LLM_PROFILE set → apply presets for any unset OPENAI_*
      3. Else LLM_PROVIDER / AI_PROVIDER / legacy OPENAI_* defaults
    """
    profile = (_env("LLM_PROFILE") or "").lower() or None
    explicit_provider = (_env("LLM_PROVIDER") or "").lower() or None
    ai_provider = (_env("AI_PROVIDER") or "").lower() or None

    if explicit_provider == "mock" or (profile == "mock" and explicit_provider is None):
        return {
            "llm_profile": profile or "mock",
            "provider": "mock",
            "openai_base_url": _env("OPENAI_BASE_URL") or "https://api.openai.com/v1",
            "openai_api_key": _env("OPENAI_API_KEY") or "",
            "openai_model": _env("OPENAI_MODEL") or "gpt-4o-mini",
        }

    preset = _PROFILE_PRESETS.get(profile) if profile else None

    if explicit_provider:
        provider = explicit_provider
    elif preset:
        provider = preset["provider"]
    elif ai_provider:
        provider = ai_provider
    else:
        provider = "mock"

    def pick(env_name: str, preset_key: str, fallback: str) -> str:
        explicit = _env(env_name)
        if explicit is not None:
            return explicit
        if preset and preset.get(preset_key):
            return preset[preset_key]
        return fallback

    def pick_api_key() -> str:
        if profile:
            dedicated_env = _PROFILE_API_KEY_ENV.get(profile)
            if dedicated_env:
                dedicated = _env(dedicated_env)
                if dedicated:
                    return dedicated
        return pick("OPENAI_API_KEY", "openai_api_key", "")

    return {
        "llm_profile": profile or "none",
        "provider": provider,
        "openai_base_url": pick(
            "OPENAI_BASE_URL", "openai_base_url", "https://api.openai.com/v1"
        ),
        "openai_api_key": pick_api_key(),
        "openai_model": pick("OPENAI_MODEL", "openai_model", "gpt-4o-mini"),
    }


@dataclass(frozen=True)
class Settings:
    provider: str
    llm_profile: str
    aws_region: str
    bedrock_model_id: str
    openai_model: str
    openai_api_key: str
    openai_base_url: str
    openai_temperature: float
    port: int
    agent_instructions_path: Path
    skills_dir: Path
    schemas_dir: Path
    max_schema_retries: int


def build_settings() -> Settings:
    runtime = resolve_llm_runtime()
    return Settings(
        provider=runtime["provider"],
        llm_profile=runtime["llm_profile"],
        aws_region=_env("AWS_REGION") or "us-east-1",
        bedrock_model_id=_env("BEDROCK_MODEL_ID")
        or "anthropic.claude-3-5-sonnet-20241022-v2:0",
        openai_model=runtime["openai_model"],
        openai_api_key=runtime["openai_api_key"],
        openai_base_url=runtime["openai_base_url"],
        openai_temperature=float(_env("OPENAI_TEMPERATURE") or "0"),
        port=int(_env("LLM_GATEWAY_PORT") or "8000"),
        agent_instructions_path=REPO_ROOT / "AGENT_INSTRUCTIONS.md",
        skills_dir=REPO_ROOT / "skills",
        schemas_dir=REPO_ROOT / "schemas",
        max_schema_retries=int(_env("LLM_GATEWAY_MAX_RETRIES") or "2"),
    )


settings = build_settings()
