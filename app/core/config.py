"""Application settings loaded from environment variables / .env."""
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed configuration. Secrets are never hardcoded."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM Provider API Keys (Fallback order: Groq -> Cerebras -> Gemini)
    groq_api_key: str = ""
    cerebras_api_key: str = ""
    gemini_api_key: str = ""

    database_url: str = ""
    chroma_persist_directory: str = ""

    # Configurable model names (automatically read GROQ_MODEL, CEREBRAS_MODEL, GEMINI_MODEL)
    groq_model: str = "openai/gpt-oss-120b"
    cerebras_model: str = "gpt-oss-120b"
    gemini_model: str = "gemini-3.8-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    # Free OCR setting (RapidOCR primary + Gemini Vision backup if scan is unclear)
    ocr_use_gemini_vision_fallback: bool = True

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