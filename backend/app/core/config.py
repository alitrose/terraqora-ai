from functools import lru_cache
import os
from pathlib import Path
import secrets
from typing import Literal
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ROOT_ENV = _PROJECT_ROOT / ".env"


def _normalize_database_url(raw_url: str) -> str:
    url = raw_url.strip()
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg" not in url and "+asyncpg" not in url:
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "TerraQora AI"
    APP_ENV: Literal["development", "test", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # Security & JWT (never hardcoded in source)
    JWT_SECRET_KEY: str = Field(default="")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./terraqora_dev.db"
        if os.getenv("APP_ENV", "development") != "production"
        else ""
    )

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Rate limits & Upload caps (wired across endpoints)
    MAX_UPLOAD_IMAGE_MB: int = 5
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_AI: str = "20/minute"

    @model_validator(mode="after")
    def validate_security_and_db(self) -> "Settings":
        placeholder_secrets = {
            "",
            "replace-with-secure-random-64-char-secret",
            "changeme",
            "secret",
        }
        if self.APP_ENV == "production":
            if self.JWT_SECRET_KEY.strip() in placeholder_secrets or len(self.JWT_SECRET_KEY.strip()) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a strong >= 32 char random secret in production."
                )
            if not self.DATABASE_URL.strip() or self.DATABASE_URL.startswith("sqlite"):
                raise ValueError(
                    "DATABASE_URL must point to PostgreSQL in production."
                )
        elif self.JWT_SECRET_KEY.strip() in placeholder_secrets:
            # Generate an ephemeral per-process secret in local dev/test when no key is set
            object.__setattr__(self, "JWT_SECRET_KEY", secrets.token_urlsafe(48))

        object.__setattr__(
            self, "DATABASE_URL", _normalize_database_url(self.DATABASE_URL)
        )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        raw = self.CORS_ORIGINS.strip()
        if not raw:
            return []
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
