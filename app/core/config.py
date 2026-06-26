"""
Application configuration — loaded from environment variables via pydantic-settings.
"""

from functools import lru_cache
from typing import Any, Literal

from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ──────────────────────────────────────────────────────────
    app_name: str = "VeriTrust"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # ─── Security ─────────────────────────────────────────────────────────────
    secret_key: str = "supersecretkey-change-in-production-min-32chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # ─── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://veritrust:veritrust@localhost:5432/veritrust"

    # ─── Redis ────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ─── Celery ───────────────────────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ─── AWS / LocalStack ─────────────────────────────────────────────────────
    aws_endpoint_url: str | None = "http://localhost:4566"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_default_region: str = "us-east-1"
    s3_bucket_name: str = "veritrust-docs"

    # ─── Email / Mailpit ──────────────────────────────────────────────────────
    mailpit_host: str = "localhost"
    mailpit_port: int = 1025
    email_from: str = "noreply@veritrust.local"
    email_from_name: str = "VeriTrust"

    # ─── Rate Limiting ────────────────────────────────────────────────────────
    rate_limit_per_minute: int = 100
    rate_limit_burst: int = 20

    # ─── CORS ─────────────────────────────────────────────────────────────────
    allowed_origins: Any = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v

    # ─── Monitoring ───────────────────────────────────────────────────────────
    prometheus_enabled: bool = True

    @field_validator("secret_key", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """
        In production we must have a strong, non-placeholder secret key.
        The validator runs after the value is parsed, so we can also look
        at other fields (e.g. `environment`) if needed.
        """
        # If we are running in production, enforce the check
        env = info.data.get("environment", "development")
        if env == "production":
            # Detect the obvious placeholder used in the repo
            placeholder_indicators = ["supersecretkey", "change-in-production"]
            # A minimal length of 32 characters is a common baseline
            if any(ind in v.lower() for ind in placeholder_indicators) or len(v) < 32:
                raise ValueError(
                    "SECURITY: `secret_key` must be set to a strong random value in production."
                )
        # In development we silently allow the placeholder
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
