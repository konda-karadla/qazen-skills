from app.config import settings
from app.providers.base import LLMProvider
from app.providers.bedrock import BedrockProvider
from app.providers.mock import MockProvider


def get_provider() -> LLMProvider:
    if settings.provider == "bedrock":
        return BedrockProvider()
    if settings.provider == "openai":
        from app.providers.openai import OpenAIProvider

        return OpenAIProvider()
    if settings.provider == "mock":
        return MockProvider()
    raise ValueError(
        f"Unknown LLM_PROVIDER '{settings.provider}' "
        "(expected 'bedrock', 'openai', or 'mock')"
    )
