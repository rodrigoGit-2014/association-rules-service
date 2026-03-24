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

    # Server
    PORT: int = Field(default=8002, description="Server port")

    # JWT
    JWT_SECRET: str = Field(
        default="change-me-in-production-use-a-long-random-string",
        description="Secret key for JWT signing"
    )

    # Performance tuning
    CACHE_TTL_SECONDS: int = Field(default=900, description="Default cache TTL (15 min)")

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
