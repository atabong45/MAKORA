"""
MODULE : api/config.py
DESCRIPTION : Configuration centralisée MAKORA via pydantic-settings.
Toutes les valeurs sont externalisées — jamais de hardcode dans le Kernel.
"""
from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SECRET_KEY: str = "makora-dev-secret-CHANGE-IN-PROD"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RESET_TOKEN_EXPIRE_MINUTES: int = 30

    DATABASE_URL: str = "postgresql://makora:makora@localhost:5432/makora_db"

    MAKORA_DATA_PATH: str = "./data"
    MAKORA_DOCUMENTS_PATH: str = "./data/documents"
    MAKORA_EXPORTS_PATH: str = "./data/exports"

    OLLAMA_URL: str = "http://localhost:11434"

    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    PROJECT_NAME: str = "MAKORA"
    VERSION: str = "1.0.0"

    LOGIN_RATE_LIMIT: str = "5/minute"
    DEFAULT_RATE_LIMIT: str = "100/minute"

    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_MIME_TYPES: list[str] = [
        "application/pdf", "image/jpeg", "image/png",
        "text/csv", "application/json",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
