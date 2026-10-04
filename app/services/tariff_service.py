"""Tariff knowledge retrieval (RAG). Never invents rates."""
import logging

from app.ai import rag
from app.utils.validators import AppError

logger = logging.getLogger(__name__)


def retrieve_tariff_context(query: str, k: int = 4) -> dict:
    """Retrieve knowledge-base excerpts. Returns status 'unavailable' instead of raising."""
    try:
        docs = rag.search(query, k=k)
    except AppError as exc:
        logger.warning("Tariff retrieval unavailable: %s", exc.message)
        return {"label": "Retrieved Data", "status": "unavailable", "documents": [], "note": exc.message}
    if not docs:
        return {"label": "Retrieved Data", "status": "empty", "documents": [],
                "note": "No relevant tariff information was found in the knowledge base."}
    return {"label": "Retrieved Data", "status": "ok", "documents": docs,
            "note": "Excerpts from the knowledge base. Verify rates against the latest official NEPRA/DISCO notification."}
