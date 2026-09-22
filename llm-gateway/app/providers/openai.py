from __future__ import annotations

from app.config import JSON_OBJECT_PROFILES, settings
from app.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """Calls OpenAI Chat Completions (or any OpenAI-compatible base URL).

    Credentials come from OPENAI_* env vars (typically repo-root .env).
    Lazy-imports the openai SDK so mock mode never requires it.
    """

    def __init__(self) -> None:
        from openai import OpenAI  # local import so 'mock' mode never requires openai

        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when LLM_PROVIDER/AI_PROVIDER is 'openai'"
            )
        self._client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=float(__import__("os").getenv("OPENAI_TIMEOUT_SECONDS", "600")),
        )
        self._model = settings.openai_model
        self._temperature = settings.openai_temperature
        self._json_object = settings.llm_profile in JSON_OBJECT_PROFILES

    def complete(self, prompt: str, *, skill_id: str) -> str:
        kwargs: dict[str, object] = {
            "model": self._model,
            "temperature": self._temperature,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the QAZen LLM Gateway completion endpoint for skill "
                        f"{skill_id}. Reply with a single JSON object only — no markdown "
                        "fences, no commentary — that satisfies the schema described in "
                        "the user prompt."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
        if self._json_object:
            kwargs["response_format"] = {"type": "json_object"}
        response = self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        return content or ""
