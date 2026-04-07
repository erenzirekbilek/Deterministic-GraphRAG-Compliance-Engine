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


class HuggingFaceAdapter(LLMService):
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("HUGGINGFACE_API_KEY")
        self.model = model or os.getenv("HUGGINGFACE_MODEL", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
        
        if not self.api_key:
            raise ValueError("HUGGINGFACE_API_KEY is not set.")
        
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model}"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    @property
    def provider_name(self) -> str:
        return f"huggingface-{self.model}"

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
        backoff = INITIAL_BACKOFF
        
        prompt_with_instructions = f"""You are a strict JSON generator. Output ONLY valid JSON. No explanations, no markdown, no text before or after. Start with {{ and end with }}.

{prompt}"""
        
        for attempt in range(MAX_RETRIES):
            try:
                payload = {
                    "inputs": prompt_with_instructions,
                    "parameters": {
                        "max_new_tokens": MAX_TOKENS,
                        "temperature": 0.1,
                        "return_full_text": False
                    },
                    "options": {
                        "use_cache": True
                    }
                }
                
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=90
                )
                
                if response.status_code == 429:
                    logger.warning(f"Rate limit hit, retrying in {backoff}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                
                if response.status_code == 503:
                    logger.warning(f"Model loading, retrying in {backoff}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                    
                response.raise_for_status()
                data = response.json()
                
                if not data or not isinstance(data, list) or not data[0].get("generated_text"):
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"Empty API response, retrying in {backoff}s")
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    else:
                        raise RuntimeError("API returned empty response. Please try again later.")
                
                text = data[0]["generated_text"]
                if not text:
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"Empty text in response, retrying in {backoff}s")
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    else:
                        raise RuntimeError("API returned empty text. Please try again later.")
                
                logger.debug("HuggingFace raw output: %s", text[:200])
                repaired = self._repair_json(text)
                return repaired
                
            except requests.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"HuggingFace API call failed: {e}, retrying in {backoff}s")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error("HuggingFace API call failed after all retries: %s", e)
                    raise RuntimeError(f"HuggingFace request failed: {e}")
            except (KeyError, TypeError, IndexError) as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Invalid response format: {e}, retrying in {backoff}s")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error("Invalid response format after retries: %s", e)
                    raise RuntimeError(f"Invalid API response: {e}")
