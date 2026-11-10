from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    firebase_project_id: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: float = 30
    daily_message_limit: int = 50
    max_message_length: int = 500
    cors_origins: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
