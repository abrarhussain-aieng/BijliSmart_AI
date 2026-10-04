"""Mistral embeddings used by the RAG pipeline."""
from langchain_mistralai import MistralAIEmbeddings

from app.core.config import settings
from app.utils.validators import AIServiceError


def get_embeddings() -> MistralAIEmbeddings:
    """Return the configured Mistral embedding model."""
    if not settings.mistral_api_key:
        raise AIServiceError("MISTRAL_API_KEY is not configured on the server.", 503)
    return MistralAIEmbeddings(model=settings.mistral_embedding_model, api_key=settings.mistral_api_key)
