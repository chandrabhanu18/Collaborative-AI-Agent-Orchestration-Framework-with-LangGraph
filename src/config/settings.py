"""
Configuration module for the Collaborative AI Agent Orchestration Framework.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # LLM Settings
    LLM_API_KEY: str = Field(default="sk-your-provider-key")
    LLM_PROVIDER: str = Field(default="openai")
    LLM_MODEL: str = Field(default="gpt-4o-mini")
    LLM_TEMPERATURE: float = Field(default=0.7)

    # Database Settings
    DATABASE_URL: str = Field(default="postgresql://user:password@localhost:5432/agent_db")
    ASYNC_DATABASE_URL: Optional[str] = Field(default=None)

    # Redis Settings
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")

    # Application Settings
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    APP_ENV: str = Field(default="production")
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE_PATH: str = Field(default="logs/agent_activity.log")

    @property
    def sync_database_url(self) -> str:
        """Returns a database URL compatible with psycopg2 / synchronous engines."""
        url = self.DATABASE_URL
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url

    @property
    def async_database_url(self) -> str:
        """Returns a database URL compatible with asyncpg / asynchronous engines."""
        if self.ASYNC_DATABASE_URL:
            return self.ASYNC_DATABASE_URL
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        return url


settings = Settings()
