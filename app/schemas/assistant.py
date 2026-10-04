"""Assistant and RAG request/response models."""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    bill_id: int | None = None


class ChatResponse(BaseModel):
    answer: str
    bill_id: int | None = None
    tools_used: list[str] = []
    sources: list[dict] = []
    warnings: list[str] = []


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    k: int = Field(default=4, ge=1, le=10)


class RagSearchResponse(BaseModel):
    label: str = "Retrieved Data"
    results: list[dict]
