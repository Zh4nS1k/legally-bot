import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    BOT_TOKEN: str
    MONGO_URI: str
    DB_NAME: str = "legally_db"
    PINECONE_API_KEY: str
    PINECONE_ENV: str = "gcp-starter"
    PINECONE_INDEX_NAME: str = "legally-knowledge-base"
    ADMIN_IDS: str  # Comma separated list of admin IDs

    @property
    def admin_ids_list(self) -> List[int]:
        return [int(id.strip()) for id in self.ADMIN_IDS.split(",") if id.strip()]

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
