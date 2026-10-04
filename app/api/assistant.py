"""AI assistant chat and RAG search endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.graph import run_graph
from app.ai import rag
from app.ai.tools import AgentTools
from app.database import crud
from app.database.database import get_db
from app.schemas.assistant import ChatRequest, ChatResponse, RagSearchRequest, RagSearchResponse
from app.utils.validators import NotFoundError

router = APIRouter(prefix="/api", tags=["assistant"])


@router.post("/assistant/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Answer a question using the user's bills, history, appliances and the tariff knowledge base."""
    user = crud.get_default_user(db)
    bill_id = payload.bill_id
    if bill_id is not None and crud.get_bill(db, bill_id) is None:
        raise NotFoundError("Bill not found.")
    if bill_id is None:
        bills = crud.list_bills(db, user.id)
        bill_id = bills[0].id if bills else None

    history = crud.recent_messages(db, user.id, bill_id)
    state = run_graph({
        "mode": "chat", "user_question": payload.message, "chat_history": history, "bill_id": bill_id,
        "tools": AgentTools(db, user.id, bill_id), "errors": [], "warnings": [],
    })
    answer = state.get("final_response", "Sorry, I could not produce an answer.")
    crud.add_chat_message(db, user.id, bill_id, "user", payload.message)
    crud.add_chat_message(db, user.id, bill_id, "assistant", answer)
    sources = [{"source": d["source"], "category": d["category"]} for d in state.get("retrieved_documents", [])]
    return ChatResponse(
        answer=answer, bill_id=bill_id, tools_used=[n for n in state.get("required_nodes", []) if n != "assistant_response"],
        sources=list({(s["source"], s["category"]): s for s in sources}.values()),
        warnings=[*state.get("warnings", []), *state.get("errors", [])],
    )


@router.post("/rag/search", response_model=RagSearchResponse)
def rag_search(payload: RagSearchRequest) -> RagSearchResponse:
    """Search the electricity knowledge base."""
    return RagSearchResponse(results=rag.search(payload.query, payload.k))
