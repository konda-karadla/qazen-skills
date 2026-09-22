from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """A provider makes exactly one completion call per invocation.

    Swappable so no skill or Orchestrator code is ever coupled to a specific
    model vendor -- only this module knows what "openai", "bedrock", or "mock" means.
    """

    @abstractmethod
    def complete(self, prompt: str, *, skill_id: str) -> str:
        """Returns the raw text completion. Caller is responsible for parsing/validating."""
        raise NotImplementedError
