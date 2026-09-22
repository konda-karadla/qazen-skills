from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql://qazen:qazen_local_dev@localhost:5432/qazen"
        )
    )
    llm_gateway_url: str = field(
        default_factory=lambda: os.getenv("LLM_GATEWAY_URL", "http://localhost:8000")
    )
    orchestrator_port: int = field(
        default_factory=lambda: int(os.getenv("ORCHESTRATOR_PORT", "8002"))
    )
    framework_version: str = field(default_factory=lambda: os.getenv("FRAMEWORK_VERSION", "0.1.0"))
    rulebook_version: str = field(default_factory=lambda: os.getenv("RULEBOOK_VERSION", "2.0.0"))
    model_version: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "mock"))
    # mock = LLM Gateway S6 fixture (unit tests). playwright = real @playwright/test + MinIO.
    s6_execution_mode: str = field(
        default_factory=lambda: os.getenv("S6_EXECUTION_MODE", "playwright").strip().lower()
    )
    # Local Ollama skill calls can exceed 60s (model load + schema retries).
    llm_gateway_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("LLM_GATEWAY_TIMEOUT_SECONDS", "600"))
    )


settings = Settings()
