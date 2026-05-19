import os
import random
import time
from openai import OpenAI
from src.core.config import settings
from loguru import logger

class KeyRotatingClient:
    def __init__(self):
        self.keys = settings.api_keys
        self.base_url = settings.OPENCODE_BASE_URL
        self.client = None
        self._rotate_key()
    
    def _rotate_key(self):
        if not self.keys:
            raise ValueError("No API keys configured")
        api_key = random.choice(self.keys)
        logger.info(f"Rotating API key (using key ending in ...{api_key[-4:]})")
        self.client = OpenAI(api_key=api_key, base_url=self.base_url)
    
    def request_with_retry(self, func_name, *args, max_retries=3, **kwargs):
        for attempt in range(max_retries):
            try:
                # Get the function from the client (e.g., self.client.chat.completions.create)
                # This is a bit tricky with nested attributes, so we'll assume it's passed correctly
                # or handle common cases.
                
                # Simplified for this specific client use case:
                if func_name == "chat":
                    func = self.client.chat.completions.create
                elif func_name == "embeddings":
                    func = self.client.embeddings.create
                else:
                    raise ValueError(f"Unsupported function: {func_name}")

                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "5" in error_str:
                    logger.warning(f"Error {error_str} on attempt {attempt + 1}. Rotating key and retrying...")
                    self._rotate_key()
                    time.sleep(2 ** attempt)
                    continue
                logger.error(f"Request failed: {error_str}")
                raise
        raise Exception("Max retries exceeded")

opencode_client = KeyRotatingClient()
