"""Application configuration management using Pydantic Settings"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database Configuration (same PostgreSQL as sales-insight-service)
    DATABASE_URL: str = Field(
        default="postgresql://sales_user:sales_password@localhost:5432/sales_db",
        description="PostgreSQL database URL"
    )

    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Redis connection URL"
    )

    # Celery Configuration
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/1",
        description="Celery result backend URL"
    )

    # Application Configuration
    APP_NAME: str = Field(default="Apriori Association Rules API", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    DEBUG: bool = Field(default=False, description="Debug mode")

    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )

    # API Configuration
    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1 path prefix")

    # LLM Configuration (optional, feature-flagged)
    LLM_ENABLED: bool = Field(default=False, description="Enable LLM interpretation")
    LLM_PROVIDER: str = Field(default="anthropic", description="LLM provider: anthropic or openai")
    LLM_API_KEY: str = Field(default="", description="LLM API key")
    LLM_MODEL: str = Field(default="claude-sonnet-4-6-20250514", description="LLM model name")
    LLM_MAX_BATCH_SIZE: int = Field(default=15, description="Max rules per LLM batch")

    model_config = {"env_file": ".env", "case_sensitive": False}


# Global settings instance
settings = Settings()
