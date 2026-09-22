from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql://qazen:qazen_local_dev@localhost:5432/qazen"
        )
    )
    orchestrator_url: str = field(
        default_factory=lambda: os.getenv("ORCHESTRATOR_URL", "http://localhost:8002")
    )
    llm_gateway_url: str = field(
        default_factory=lambda: os.getenv("LLM_GATEWAY_URL", "http://localhost:8000")
    )
    port: int = field(default_factory=lambda: int(os.getenv("REVIEW_API_PORT", "8001")))
    ci_gate_mode: str = field(default_factory=lambda: os.getenv("CI_GATE_MODE", "mock"))
    ci_gate_endpoint: str = field(default_factory=lambda: os.getenv("CI_GATE_ENDPOINT", ""))
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", ""))
    llm_profile: str = field(default_factory=lambda: os.getenv("LLM_PROFILE", "ollama"))
    s6_execution_mode: str = field(
        default_factory=lambda: os.getenv("S6_EXECUTION_MODE", "playwright")
    )
    minio_endpoint: str = field(default_factory=lambda: os.getenv("MINIO_ENDPOINT", ""))


settings = Settings()
