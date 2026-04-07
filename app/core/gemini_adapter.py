import logging
import re
import time
import requests
from app.core.llm_interface import LLMService

logger = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
MAX_RETRIES = 3
INITIAL_BACKOFF = 2
MAX_TOKENS = 4096


class GeminiAdapter(LLMService):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        self.api_key = api_key

    @property
    def provider_name(self) -> str:
        return "google-gemini-2.0-flash"

    def _repair_json(self, text: str) -> str:
        """Repair malformed JSON by extracting JSON object from text."""
        text = text.strip()
        
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"```$", "", text)
        
        text = re.sub(r'^Here is the JSON[,\s]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^Here[^\n]*:\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^Here is[^\n]*:\s*', '', text, flags=re.IGNORECASE)
        
        text = re.sub(r'\n}$', '}', text)
        
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return match.group(0)
        
        return text

    def generate(self, prompt: str) -> str:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": MAX_TOKENS,
                "responseModalities": ["TEXT"]
            }
        }
        backoff = INITIAL_BACKOFF
        last_error = None
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    f"{GEMINI_URL}?key={self.api_key}",
                    json=payload,
                    timeout=60
                )
                if response.status_code == 429:
                    logger.warning(f"Rate limit hit, retrying in {backoff}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                if response.status_code == 503:
                    logger.warning(f"Service unavailable, retrying in {backoff}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                response.raise_for_status()
                data = response.json()
                
                if not data or "candidates" not in data or not data.get("candidates"):
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"Empty API response, retrying in {backoff}s")
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    else:
                        raise RuntimeError("API quota reached or service unavailable. Please try again later.")
                
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                if not text:
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"Empty text in response, retrying in {backoff}s")
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    else:
                        raise RuntimeError("API returned empty response. Please try again later.")
                
                logger.debug("Gemini raw output: %s", text[:200])
                repaired = self._repair_json(text)
                return repaired
            except (requests.RequestException, KeyError, TypeError) as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Gemini API call failed: {e}, retrying in {backoff}s")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error("Gemini API call failed after all retries: %s", e)
                    raise RuntimeError(f"Gemini request failed: {e}")
