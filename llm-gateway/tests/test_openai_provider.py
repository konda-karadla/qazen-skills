"""Unit tests for OpenAI provider wiring (no live network)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.providers.openai import OpenAIProvider


def _fake_settings(**overrides: object) -> SimpleNamespace:
    base = {
        "openai_api_key": "sk-test-not-real",
        "openai_model": "gpt-4o-mini",
        "openai_base_url": "https://api.openai.com/v1",
        "openai_temperature": 0.0,
        "provider": "openai",
        "llm_profile": "openai",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _complete_kwargs(**settings_overrides: object) -> dict:
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))]
    )
    with (
        patch("app.providers.openai.settings", _fake_settings(**settings_overrides)),
        patch("openai.OpenAI", return_value=fake_client),
    ):
        provider = OpenAIProvider()
        provider.complete("prompt body", skill_id="S1")
    return fake_client.chat.completions.create.call_args.kwargs


def test_openai_provider_requires_api_key() -> None:
    with patch("app.providers.openai.settings", _fake_settings(openai_api_key="")):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            OpenAIProvider()


def test_openai_provider_complete_returns_message_content() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))]
    )

    with (
        patch("app.providers.openai.settings", _fake_settings()),
        patch("openai.OpenAI", return_value=fake_client) as openai_cls,
    ):
        provider = OpenAIProvider()
        text = provider.complete("prompt body", skill_id="S1")

    assert text == '{"ok": true}'
    openai_cls.assert_called_once()
    kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["temperature"] == 0.0
    assert kwargs["messages"][0]["role"] == "system"
    assert "S1" in kwargs["messages"][0]["content"]
    assert kwargs["messages"][1] == {"role": "user", "content": "prompt body"}
    assert kwargs["response_format"] == {"type": "json_object"}


def test_openai_provider_json_object_for_cloud_profiles() -> None:
    for profile in ("gemini", "mistral", "openai", "groq"):
        kwargs = _complete_kwargs(llm_profile=profile)
        assert kwargs["response_format"] == {"type": "json_object"}, profile


def test_openai_provider_skips_json_object_for_ollama() -> None:
    kwargs = _complete_kwargs(llm_profile="ollama")
    assert "response_format" not in kwargs


def test_get_provider_openai_branch() -> None:
    with (
        patch("app.providers.settings", _fake_settings(provider="openai")),
        patch("app.providers.openai.settings", _fake_settings()),
        patch("openai.OpenAI", return_value=MagicMock()),
    ):
        from app.providers import get_provider
        from app.providers.openai import OpenAIProvider as OP

        assert isinstance(get_provider(), OP)
