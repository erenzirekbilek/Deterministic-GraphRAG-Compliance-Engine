import logging
import requests
from app.core.llm_interface import LLMService

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqAdapter(LLMService):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set.")
        self.api_key = api_key

    @property
    def provider_name(self) -> str:
        return "groq-llama3-8b"

    def generate(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a compliance assistant. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 512
        }
        try:
            response = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            logger.debug("Groq raw output: %s", text)
            return text.strip()
        except requests.RequestException as e:
            logger.error("Groq API call failed: %s", e)
            raise RuntimeError(f"Groq request failed: {e}")
