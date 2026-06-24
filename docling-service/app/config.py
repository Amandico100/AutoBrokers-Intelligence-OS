"""
Docling Service Configuration
"""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for the Docling microservice."""

    # Service auth
    SERVICE_KEY: str = ""

    # Ambiente: 'production' (estrito) | 'local'|'dev'|'test' (permite localhost).
    ENV: str = "production"

    # Redis (broker + result backend do Celery) — FONTE ÚNICA. Sem fallback localhost em produção.
    REDIS_URL: str = ""

    # Vision LLM for image descriptions
    VISION_MODEL: str = "gpt-4o-mini"
    VISION_API_URL: str = "https://api.openai.com/v1/chat/completions"
    OPENAI_API_KEY: str = ""

    # OCR engine
    OCR_ENGINE: str = "easyocr"

    # Limits
    MAX_FILE_SIZE_MB: int = 100

    # Task result TTL
    RESULT_TTL_SECONDS: int = 3600  # 1 hour

    # MinIO (shared object storage with Smith)
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "documents"
    MINIO_SECURE: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def _resolve_redis() -> None:
    """REDIS_URL é a fonte única (broker+result). Normaliza aliases legados e
    FALHA claramente se faltar/usar localhost em produção (sem fallback silencioso)."""
    if not settings.REDIS_URL:
        legacy = os.getenv("CELERY_BROKER_URL") or os.getenv("CELERY_RESULT_BACKEND")
        if legacy:
            settings.REDIS_URL = legacy
    is_local = settings.ENV.strip().lower() in ("local", "dev", "development", "test")
    has_localhost = ("localhost" in settings.REDIS_URL) or ("127.0.0.1" in settings.REDIS_URL)
    if not settings.REDIS_URL:
        if is_local:
            settings.REDIS_URL = "redis://localhost:6379/0"
        else:
            raise RuntimeError(
                "REDIS_URL ausente. Configure REDIS_URL (broker+result do Celery) "
                "no Docling API E no Docling Worker. localhost só é permitido com ENV local/dev/test."
            )
    elif has_localhost and not is_local:
        raise RuntimeError(
            "REDIS_URL aponta para localhost em produção. Use o endereço do Redis interno "
            "real em REDIS_URL (mesma URL na API e no Worker). Defina ENV=local para permitir localhost."
        )


_resolve_redis()
