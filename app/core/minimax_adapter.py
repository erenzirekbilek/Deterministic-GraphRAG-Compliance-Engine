import logging
import os
import re
import time
import requests
from app.core.llm_interface import LLMService

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
INITIAL_BACKOFF = 2
MAX_TOKENS = 4096


class MiniMaxAdapter(LLMService):
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY")
        self.model = model or os.getenv("MINIMAX_MODEL", "MiniMax-M2.1")
        
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY is not set.")
        
        base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")
        self.api_url = f"{base_url}/text/chatcompletion_v2"

    @property
    def provider_name(self) -> str:
        return f"minimax-{self.model}"

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
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a strict JSON generator. Output ONLY valid JSON. No explanations, no markdown, no text before or after. Start with { and end with }."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": MAX_TOKENS
        }
        backoff = INITIAL_BACKOFF
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
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
                
                if not data or "choices" not in data or not data.get("choices"):
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"Empty API response, retrying in {backoff}s")
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    else:
                        raise RuntimeError("API quota reached or service unavailable. Please try again later.")
                
                text = data["choices"][0]["message"]["content"]
                if not text:
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"Empty text in response, retrying in {backoff}s")
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    else:
                        raise RuntimeError("API returned empty response. Please try again later.")
                
                logger.debug("MiniMax raw output: %s", text[:200])
                repaired = self._repair_json(text)
                return repaired
                
            except requests.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"MiniMax API call failed: {e}, retrying in {backoff}s")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error("MiniMax API call failed after all retries: %s", e)
                    raise RuntimeError(f"MiniMax request failed: {e}")
            except (KeyError, TypeError, IndexError) as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Invalid response format: {e}, retrying in {backoff}s")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error("Invalid response format after retries: %s", e)
                    raise RuntimeError(f"Invalid API response: {e}")
