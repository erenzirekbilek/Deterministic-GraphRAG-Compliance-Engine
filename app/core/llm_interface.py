from abc import ABC, abstractmethod


class LLMService(ABC):
    """
    Abstract base for all LLM providers.
    Every adapter must implement generate() and return a string.
    The string MUST be valid JSON: {"decision": "...", "reason": "..."}
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError
