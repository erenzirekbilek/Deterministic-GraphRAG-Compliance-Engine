import pytest
from unittest.mock import patch, MagicMock
import requests


class TestMiniMaxAdapter:
    @pytest.fixture
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
        monkeypatch.setenv("MINIMAX_MODEL", "MiniMax-M2.1")

    def test_initialization(self, mock_env):
        from app.core.minimax_adapter import MiniMaxAdapter

        adapter = MiniMaxAdapter("test-key")

        assert adapter.api_key == "test-key"
        assert adapter.model == "MiniMax-M2.1"

    def test_initialization_from_env(self, monkeypatch):
        monkeypatch.setenv("MINIMAX_API_KEY", "env-key")
        from app.core.minimax_adapter import MiniMaxAdapter

        adapter = MiniMaxAdapter()

        assert adapter.api_key == "env-key"

    def test_initialization_no_key(self):
        import os

        original_key = os.environ.get("MINIMAX_API_KEY")
        if "MINIMAX_API_KEY" in os.environ:
            del os.environ["MINIMAX_API_KEY"]

        from app.core.minimax_adapter import MiniMaxAdapter

        with pytest.raises(ValueError):
            MiniMaxAdapter()

        if original_key:
            os.environ["MINIMAX_API_KEY"] = original_key

    def test_provider_name(self, mock_env):
        from app.core.minimax_adapter import MiniMaxAdapter

        adapter = MiniMaxAdapter("test-key")

        assert adapter.provider_name == "minimax-MiniMax-M2.1"

    def test_repair_json(self, mock_env):
        from app.core.minimax_adapter import MiniMaxAdapter

        adapter = MiniMaxAdapter("test-key")

        text = '```json\n{"key": "value"}\n```'
        result = adapter._repair_json(text)

        assert result == '{"key": "value"}'

    def test_repair_json_with_prefix(self, mock_env):
        from app.core.minimax_adapter import MiniMaxAdapter

        adapter = MiniMaxAdapter("test-key")

        text = 'Here is the JSON: {"key": "value"}'
        result = adapter._repair_json(text)

        assert "key" in result


class TestGeminiAdapter:
    def test_initialization(self):
        from app.core.gemini_adapter import GeminiAdapter

        adapter = GeminiAdapter("test-key")

        assert adapter.api_key == "test-key"

    def test_initialization_no_key(self):
        from app.core.gemini_adapter import GeminiAdapter

        with pytest.raises(ValueError):
            GeminiAdapter("")

    def test_provider_name(self):
        from app.core.gemini_adapter import GeminiAdapter

        adapter = GeminiAdapter("test-key")

        assert adapter.provider_name == "google-gemini-2.0-flash"

    def test_repair_json(self):
        from app.core.gemini_adapter import GeminiAdapter

        adapter = GeminiAdapter("test-key")

        text = '```json\n{"key": "value"}\n```'
        result = adapter._repair_json(text)

        assert result == '{"key": "value"}'


class TestGroqAdapter:
    def test_initialization(self):
        from app.core.groq_adapter import GroqAdapter

        adapter = GroqAdapter("test-key")

        assert adapter.api_key == "test-key"

    def test_initialization_no_key(self):
        from app.core.groq_adapter import GroqAdapter

        with pytest.raises(ValueError):
            GroqAdapter("")

    def test_provider_name(self):
        from app.core.groq_adapter import GroqAdapter

        adapter = GroqAdapter("test-key")

        assert adapter.provider_name == "groq-llama-3.3-70b"

    def test_repair_json(self):
        from app.core.groq_adapter import GroqAdapter

        adapter = GroqAdapter("test-key")

        text = '```json\n{"key": "value"}\n```'
        result = adapter._repair_json(text)

        assert result == '{"key": "value"}'


class TestHuggingFaceAdapter:
    @pytest.fixture
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("HUGGINGFACE_API_KEY", "test-key")

    def test_initialization(self, mock_env):
        from app.core.huggingface_adapter import HuggingFaceAdapter

        adapter = HuggingFaceAdapter("test-key")

        assert adapter.api_key == "test-key"

    def test_initialization_no_key(self):
        import os

        original_key = os.environ.get("HUGGINGFACE_API_KEY")
        if "HUGGINGFACE_API_KEY" in os.environ:
            del os.environ["HUGGINGFACE_API_KEY"]

        from app.core.huggingface_adapter import HuggingFaceAdapter

        with pytest.raises(ValueError):
            HuggingFaceAdapter()

        if original_key:
            os.environ["HUGGINGFACE_API_KEY"] = original_key

    def test_provider_name(self, mock_env):
        from app.core.huggingface_adapter import HuggingFaceAdapter

        adapter = HuggingFaceAdapter("test-key")

        assert "huggingface-" in adapter.provider_name

    def test_repair_json(self, mock_env):
        from app.core.huggingface_adapter import HuggingFaceAdapter

        adapter = HuggingFaceAdapter("test-key")

        text = '```json\n{"key": "value"}\n```'
        result = adapter._repair_json(text)

        assert result == '{"key": "value"}'
