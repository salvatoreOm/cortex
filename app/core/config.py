from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Cortex"
    log_level: str = "INFO"

    # Special characters in the password must be URL-encoded (e.g. @ -> %40).
    database_url: str

    # Azure AI Foundry — unused until Phase 2, so optional for now.
    azure_ai_endpoint: str | None = None
    azure_ai_key: str | None = None
    azure_chat_deployment: str | None = None
    azure_embedding_deployment: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
