from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    OPENCODE_API_KEYS: str
    OPENCODE_BASE_URL: str = "https://opencode.ai/zen/v1"
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    LOG_DIR: str = "./logs"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    @property
    def api_keys(self) -> List[str]:
        return [k.strip() for k in self.OPENCODE_API_KEYS.split(",") if k.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
