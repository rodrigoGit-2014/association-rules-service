"""Application configuration management using Pydantic Settings"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://sales_user:sales_password@localhost:5432/sales_db",
        description="PostgreSQL database URL"
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/2",
        description="Redis connection URL for caching"
    )

    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/2",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL"
    )

    # Application
    APP_NAME: str = Field(default="Apriori Market Basket Analysis API v2")
    APP_VERSION: str = Field(default="2.0.0")
    LOG_LEVEL: str = Field(default="INFO")
    DEBUG: bool = Field(default=False)

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"]
    )

    # API
    API_V1_PREFIX: str = Field(default="/api/v1")
    PORT: int = Field(default=8002, description="Server port")

    # Performance tuning
    CACHE_TTL_SECONDS: int = Field(default=900, description="Default cache TTL (15 min)")
    SYNC_THRESHOLD: int = Field(default=50000, description="Max transactions for sync Apriori execution")
    MATVIEW_REFRESH_MINUTES: int = Field(default=30, description="Materialized view refresh interval")
    BATCH_SIZE: int = Field(default=10000, description="Batch size for large data processing")

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
