"""Application settings loaded from environment variables / .env."""
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed configuration. Secrets are never hardcoded."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mistral_api_key: str = ""
    database_url: str = ""
    chroma_persist_directory: str = ""

    # Model names are configurable so they can change without code changes.
    mistral_chat_model: str = "mistral-small-latest"
    mistral_embedding_model: str = "mistral-embed"
    mistral_ocr_model: str = "mistral-ocr-latest"

    max_upload_mb: int = 8
    knowledge_base_dir: str = str(BASE_DIR / "data" / "knowledge_base")

    @model_validator(mode="after")
    def _apply_defaults(self) -> "Settings":
        if not self.database_url:
            self.database_url = f"sqlite:///{(BASE_DIR / 'bijliwise.db').as_posix()}"
        for prefix in ("postgres://", "postgresql://"):
            if self.database_url.startswith(prefix):
                self.database_url = "postgresql+psycopg://" + self.database_url[len(prefix):]
        if not self.chroma_persist_directory:
            self.chroma_persist_directory = str(BASE_DIR / "data" / "chroma")
        return self

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
