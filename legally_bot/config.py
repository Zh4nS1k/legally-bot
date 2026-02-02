import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    BOT_TOKEN: str
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "legally_db"
    
    WELCOME_IMAGE_URL: str = "https://drive.google.com/uc?export=view&id=1ZrFuY83E8EQLFAAchSSU0RIQ3YwGIT-m"
    
    PINECONE_API_KEY: str
    PINECONE_ENV: str
    PINECONE_INDEX_NAME: str
    GEMINI_API_KEY: str
    OPENROUTER_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    
    # SMTP Settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = "noreply@legallybot.com"

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
