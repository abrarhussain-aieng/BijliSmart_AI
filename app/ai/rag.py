"""RAG pipeline: load -> clean -> chunk -> Mistral embeddings -> ChromaDB -> retriever.

Build the index with:  python -m app.ai.rag
"""
import logging
import re
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ai.embeddings import get_embeddings
from app.core.config import settings
from app.utils.validators import AIServiceError, AppError

logger = logging.getLogger(__name__)
COLLECTION = "bijliwise_knowledge"


def get_vectorstore() -> Chroma:
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_directory,
    )


def load_documents() -> list[Document]:
    """Load .md/.txt/.pdf files; the sub-folder name becomes the category."""
    root = Path(settings.knowledge_base_dir)
    docs: list[Document] = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in {".md", ".txt", ".pdf"} or not path.is_file():
            continue
        try:
            loader = PyPDFLoader(str(path)) if path.suffix.lower() == ".pdf" else TextLoader(str(path), encoding="utf-8")
            loaded = loader.load()
        except Exception:
            logger.exception("Could not load %s", path)
            continue
        category = path.parent.name if path.parent != root else "general"
        for doc in loaded:
            doc.page_content = re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", doc.page_content)).strip()
            doc.metadata.update({"source": path.name, "category": category})
            if doc.page_content:
                docs.append(doc)
    return docs


def build_index() -> int:
    """(Re)build the vector index from the knowledge base. Returns the chunk count."""
    docs = load_documents()
    if not docs:
        raise AppError("No documents found in the knowledge base folder.", 404)
    chunks = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150).split_documents(docs)
    try:
        get_vectorstore().delete_collection()
    except Exception:
        logger.info("No existing collection to delete.")
    store = get_vectorstore()
    for i in range(0, len(chunks), 32):
        store.add_documents(chunks[i:i + 32])
    logger.info("Indexed %d chunks from %d documents", len(chunks), len(docs))
    return len(chunks)


def search(query: str, k: int = 4) -> list[dict]:
    """Retrieve the k most relevant knowledge-base chunks (builds the index on first use)."""
    try:
        store = get_vectorstore()
        if store._collection.count() == 0:
            build_index()
            store = get_vectorstore()
        results = store.similarity_search_with_score(query, k=k)
    except AppError:
        raise
    except Exception as exc:
        logger.exception("RAG search failed")
        raise AIServiceError(f"Knowledge-base search failed ({exc.__class__.__name__}).") from exc
    return [
        {
            "content": doc.page_content,
            "source": doc.metadata.get("source"),
            "category": doc.metadata.get("category"),
            "page": doc.metadata.get("page"),
            "distance": round(float(score), 4),
        }
        for doc, score in results
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Indexed {build_index()} chunks.")
