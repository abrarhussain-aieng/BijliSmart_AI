"""Gemini embeddings used by the RAG pipeline."""
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings
from app.utils.validators import AIServiceError


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Return the configured Gemini embedding model."""
    if not settings.gemini_api_key:
        raise AIServiceError("GEMINI_API_KEY is not configured on the server.", 503)
    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=settings.gemini_api_key,
    )