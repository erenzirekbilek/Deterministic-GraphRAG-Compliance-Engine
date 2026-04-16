"""
Anticorruption Layer (ACL)

This module provides a protective layer between external services (LLM providers)
and our internal domain model. It ensures that:

1. External API quirks don't leak into our domain
2. Response formats are normalized
3. Errors are transformed into domain-specific exceptions
4. API versioning is handled gracefully
"""

import logging
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class LLMRuntimeError(Exception):
    """Domain exception for LLM runtime errors."""

    def __init__(self, provider: str, message: str, original_error: Exception = None):
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"[{provider}] {message}")


class LLMQuotaExceededError(LLMRuntimeError):
    """Raised when API quota is exceeded."""

    def __init__(self, provider: str, original_error: Exception = None):
        super().__init__(
            provider, "API quota exceeded. Please try again later.", original_error
        )


class LLMServiceUnavailableError(LLMRuntimeError):
    """Raised when LLM service is unavailable."""

    def __init__(self, provider: str, original_error: Exception = None):
        super().__init__(
            provider, "LLM service temporarily unavailable.", original_error
        )


class LLMResponseParsingError(LLMRuntimeError):
    """Raised when response parsing fails."""

    def __init__(
        self, provider: str, raw_response: str, original_error: Exception = None
    ):
        self.raw_response = raw_response[:500]
        super().__init__(provider, "Failed to parse LLM response", original_error)


class ResponseFormat(str, Enum):
    """Supported response formats from LLMs."""

    JSON = "json"
    TEXT = "text"
    MARKDOWN = "markdown"


@dataclass
class NormalizedLLMResponse:
    """Domain model for normalized LLM response."""

    content: str
    format: ResponseFormat
    raw_provider: str
    model: str
    tokens_used: Optional[int] = None
    raw_response: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "format": self.format.value,
            "provider": self.raw_provider,
            "model": self.model,
            "tokens_used": self.tokens_used,
        }


class ACLTransformer(ABC):
    """Base transformer for ACL."""

    @abstractmethod
    def transform_request(self, prompt: str) -> Dict[str, Any]:
        """Transform internal prompt to provider-specific format."""
        pass

    @abstractmethod
    def transform_response(self, raw_response: Any) -> NormalizedLLMResponse:
        """Transform provider response to normalized format."""
        pass

    @abstractmethod
    def transform_error(self, error: Exception) -> LLMRuntimeError:
        """Transform provider error to domain exception."""
        pass


class GroqACLTransformer(ACLTransformer):
    """Anticorruption layer for Groq API."""

    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.model = model
        self.provider = "groq"

    def transform_request(self, prompt: str) -> Dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a strict JSON generator. Output ONLY valid JSON. No explanations, no markdown.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
        }

    def transform_response(self, raw_response: Any) -> NormalizedLLMResponse:
        try:
            content = raw_response["choices"][0]["message"]["content"]
            return NormalizedLLMResponse(
                content=self._extract_json(content),
                format=ResponseFormat.JSON,
                raw_provider=self.provider,
                model=self.model,
                raw_response=json.dumps(raw_response),
            )
        except (KeyError, IndexError) as e:
            raise LLMResponseParsingError(self.provider, str(raw_response), e)

    def transform_error(self, error: Exception) -> LLMRuntimeError:
        error_msg = str(error).lower()
        if "429" in error_msg or "rate limit" in error_msg:
            return LLMQuotaExceededError(self.provider, error)
        if "503" in error_msg or "unavailable" in error_msg:
            return LLMServiceUnavailableError(self.provider, error)
        return LLMRuntimeError(self.provider, str(error), error)

    def _extract_json(self, text: str) -> str:
        """Extract JSON from text, removing markdown."""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```", 1)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0]
        return text.strip()


class MiniMaxACLTransformer(ACLTransformer):
    """Anticorruption layer for MiniMax API."""

    def __init__(self, model: str = "MiniMax-M2.1"):
        self.model = model
        self.provider = "minimax"

    def transform_request(self, prompt: str) -> Dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a strict JSON generator. Output ONLY valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
        }

    def transform_response(self, raw_response: Any) -> NormalizedLLMResponse:
        try:
            content = raw_response["choices"][0]["message"]["content"]
            return NormalizedLLMResponse(
                content=self._extract_json(content),
                format=ResponseFormat.JSON,
                raw_provider=self.provider,
                model=self.model,
                raw_response=json.dumps(raw_response),
            )
        except (KeyError, IndexError) as e:
            raise LLMResponseParsingError(self.provider, str(raw_response), e)

    def transform_error(self, error: Exception) -> LLMRuntimeError:
        error_msg = str(error).lower()
        if "429" in error_msg or "rate limit" in error_msg:
            return LLMQuotaExceededError(self.provider, error)
        return LLMRuntimeError(self.provider, str(error), error)

    def _extract_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```", 1)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0]
        return text.strip()


class GeminiACLTransformer(ACLTransformer):
    """Anticorruption layer for Gemini API."""

    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
        self.provider = "gemini"

    def transform_request(self, prompt: str) -> Dict[str, Any]:
        return {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 4096,
                "responseModalities": ["TEXT"],
            },
        }

    def transform_response(self, raw_response: Any) -> NormalizedLLMResponse:
        try:
            content = raw_response["candidates"][0]["content"]["parts"][0]["text"]
            return NormalizedLLMResponse(
                content=self._extract_json(content),
                format=ResponseFormat.JSON,
                raw_provider=self.provider,
                model=self.model,
                raw_response=json.dumps(raw_response),
            )
        except (KeyError, IndexError) as e:
            raise LLMResponseParsingError(self.provider, str(raw_response), e)

    def transform_error(self, error: Exception) -> LLMRuntimeError:
        error_msg = str(error).lower()
        if "429" in error_msg or "quota" in error_msg:
            return LLMQuotaExceededError(self.provider, error)
        if "503" in error_msg or "unavailable" in error_msg:
            return LLMServiceUnavailableError(self.provider, error)
        return LLMRuntimeError(self.provider, str(error), error)

    def _extract_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```", 1)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0]
        return text.strip()


class HuggingFaceACLTransformer(ACLTransformer):
    """Anticorruption layer for HuggingFace API."""

    def __init__(self, model: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"):
        self.model = model
        self.provider = "huggingface"

    def transform_request(self, prompt: str) -> Dict[str, Any]:
        return {
            "inputs": f"You are a strict JSON generator. Output ONLY valid JSON.\n\n{prompt}",
            "parameters": {
                "max_new_tokens": 4096,
                "temperature": 0.1,
                "return_full_text": False,
            },
            "options": {"use_cache": True},
        }

    def transform_response(self, raw_response: Any) -> NormalizedLLMResponse:
        try:
            content = raw_response[0]["generated_text"]
            return NormalizedLLMResponse(
                content=self._extract_json(content),
                format=ResponseFormat.TEXT,
                raw_provider=self.provider,
                model=self.model,
                raw_response=json.dumps(raw_response),
            )
        except (KeyError, IndexError) as e:
            raise LLMResponseParsingError(self.provider, str(raw_response), e)

    def transform_error(self, error: Exception) -> LLMRuntimeError:
        error_msg = str(error).lower()
        if "429" in error_msg or "rate limit" in error_msg:
            return LLMQuotaExceededError(self.provider, error)
        if "503" in error_msg or "unavailable" in error_msg:
            return LLMServiceUnavailableError(self.provider, error)
        return LLMRuntimeError(self.provider, str(error), error)

    def _extract_json(self, text: str) -> str:
        import re

        text = text.strip()
        if text.startswith("```"):
            text = text.split("```", 1)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0]
        match = re.search(r"\{[\s\S]*\}", text)
        return match.group(0) if match else text


class ACLFactory:
    """Factory to create appropriate ACL transformer."""

    _transformers = {
        "groq": GroqACLTransformer,
        "minimax": MiniMaxACLTransformer,
        "gemini": GeminiACLTransformer,
        "huggingface": HuggingFaceACLTransformer,
    }

    @classmethod
    def create(cls, provider: str, model: str = None) -> ACLTransformer:
        provider = provider.lower()
        if provider not in cls._transformers:
            raise ValueError(f"Unknown provider: {provider}")

        transformer_class = cls._transformers[provider]

        if model and hasattr(transformer_class, "__init__"):
            return transformer_class(model=model)
        return transformer_class()


class LLMClientWithACL:
    """LLM client that uses Anticorruption Layer."""

    def __init__(self, adapter, transformer: ACLTransformer):
        self.adapter = adapter
        self.transformer = transformer

    def generate(self, prompt: str) -> str:
        try:
            request = self.transformer.transform_request(prompt)
            raw_response = self.adapter._make_request(request)
            normalized = self.transformer.transform_response(raw_response)
            return normalized.content
        except Exception as e:
            domain_error = self.transformer.transform_error(e)
            raise domain_error

    def generate_with_metadata(self, prompt: str) -> NormalizedLLMResponse:
        try:
            request = self.transformer.transform_request(prompt)
            raw_response = self.adapter._make_request(request)
            return self.transformer.transform_response(raw_response)
        except Exception as e:
            domain_error = self.transformer.transform_error(e)
            raise domain_error
