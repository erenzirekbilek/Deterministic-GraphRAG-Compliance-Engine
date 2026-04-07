import logging
import requests
from app.core.llm_interface import LLMService

logger = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


class GeminiAdapter(LLMService):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        self.api_key = api_key

    @property
    def provider_name(self) -> str:
        return "google-gemini-2.0-flash"

    def generate(self, prompt: str) -> str:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 512,
            }
        }
        try:
            response = requests.post(
                f"{GEMINI_URL}?key={self.api_key}",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            logger.debug("Gemini raw output: %s", text)
            return text.strip()
        except requests.RequestException as e:
            logger.error("Gemini API call failed: %s", e)
            raise RuntimeError(f"Gemini request failed: {e}")
