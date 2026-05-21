from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    GITLAWB_OPENGATEWAY_API_KEY: str = ""
    GITLAWB_OPENGATEWAY_BASE_URL: str = "https://opengateway.gitlawb.com/v1"
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    LOG_DIR: str = "./logs"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    @property
    def api_keys(self) -> List[str]:
        return [k.strip() for k in self.GITLAWB_OPENGATEWAY_API_KEY.split(",") if k.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
