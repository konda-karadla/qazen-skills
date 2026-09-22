"""Unit tests for LLM_PROFILE resolution (no network)."""
import os

import pytest

from app.config import resolve_llm_runtime


@pytest.fixture(autouse=True)
def _clear_llm_env(monkeypatch):
    for key in (
        "LLM_PROFILE",
        "LLM_PROVIDER",
        "AI_PROVIDER",
        "OPENAI_BASE_URL",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "GEMINI_API_KEY",
        "MISTRAL_API_KEY",
        "GROQ_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_profile_ollama_defaults(monkeypatch):
    monkeypatch.setenv("LLM_PROFILE", "ollama")
    runtime = resolve_llm_runtime()
    assert runtime["llm_profile"] == "ollama"
    assert runtime["provider"] == "openai"
    assert runtime["openai_base_url"] == "http://127.0.0.1:11434/v1"
    assert runtime["openai_api_key"] == "ollama"
    assert runtime["openai_model"] == "qwen2.5:7b"


def test_profile_gemini_defaults(monkeypatch):
    monkeypatch.setenv("LLM_PROFILE", "gemini")
    runtime = resolve_llm_runtime()
    assert runtime["llm_profile"] == "gemini"
    assert runtime["provider"] == "openai"
    assert runtime["openai_base_url"] == (
        "https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    assert runtime["openai_model"] == "gemini-3.6-flash"
    assert runtime["openai_api_key"] == ""


def test_profile_mistral_defaults(monkeypatch):
    monkeypatch.setenv("LLM_PROFILE", "mistral")
    runtime = resolve_llm_runtime()
    assert runtime["llm_profile"] == "mistral"
    assert runtime["provider"] == "openai"
    assert runtime["openai_base_url"] == "https://api.mistral.ai/v1"
    assert runtime["openai_model"] == "mistral-small-latest"
    assert runtime["openai_api_key"] == ""


def test_mistral_uses_dedicated_key_not_openai_key(monkeypatch):
    monkeypatch.setenv("LLM_PROFILE", "mistral")
    monkeypatch.setenv("OPENAI_API_KEY", "gemini-should-not-be-used")
    monkeypatch.setenv("MISTRAL_API_KEY", "mistral-backup-key")
    runtime = resolve_llm_runtime()
    assert runtime["openai_api_key"] == "mistral-backup-key"
    assert runtime["openai_base_url"] == "https://api.mistral.ai/v1"


def test_profile_groq_defaults(monkeypatch):
    monkeypatch.setenv("LLM_PROFILE", "groq")
    runtime = resolve_llm_runtime()
    assert runtime["llm_profile"] == "groq"
    assert runtime["provider"] == "openai"
    assert runtime["openai_base_url"] == "https://api.groq.com/openai/v1"
    assert runtime["openai_model"] == "openai/gpt-oss-20b"
    assert runtime["openai_api_key"] == ""


def test_profile_openai_defaults(monkeypatch):
    monkeypatch.setenv("LLM_PROFILE", "openai")
    runtime = resolve_llm_runtime()
    assert runtime["llm_profile"] == "openai"
    assert runtime["provider"] == "openai"
    assert runtime["openai_base_url"] == "https://api.openai.com/v1"
    assert runtime["openai_model"] == "gpt-4o-mini"
    assert runtime["openai_api_key"] == ""


def test_profile_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROFILE", "mock")
    runtime = resolve_llm_runtime()
    assert runtime["provider"] == "mock"


def test_explicit_mock_provider_wins_over_ollama_profile(monkeypatch):
    monkeypatch.setenv("LLM_PROFILE", "ollama")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    runtime = resolve_llm_runtime()
    assert runtime["provider"] == "mock"


def test_explicit_openai_env_overrides_profile_defaults(monkeypatch):
    monkeypatch.setenv("LLM_PROFILE", "ollama")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://custom:11434/v1")
    monkeypatch.setenv("OPENAI_MODEL", "custom-model")
    monkeypatch.setenv("OPENAI_API_KEY", "custom-key")
    runtime = resolve_llm_runtime()
    assert runtime["openai_base_url"] == "http://custom:11434/v1"
    assert runtime["openai_model"] == "custom-model"
    assert runtime["openai_api_key"] == "custom-key"


def test_no_profile_falls_back_to_mock_without_provider(monkeypatch):
    runtime = resolve_llm_runtime()
    assert runtime["provider"] == "mock"
