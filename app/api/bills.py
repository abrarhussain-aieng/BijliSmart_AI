"""Bill upload, listing, detail and analysis endpoints."""
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.agents.graph import run_graph
from app.ai.tools import AgentTools
from app.core.security import sanitize_filename, validate_upload
from app.core.config import settings
from app.database import crud
from app.database.database import get_db
from app.schemas.bill import (AnalysisResponse, BillDetail, BillOut, BillUploadResponse, RecommendationOut)
from app.utils.validators import NotFoundError

router = APIRouter(prefix="/api/bills", tags=["bills"])


@router.post("/upload", response_model=BillUploadResponse)
def upload_bill(file: UploadFile = File(...), db: Session = Depends(get_db)) -> BillUploadResponse:
    """Validate the file, extract and validate bill data (LangGraph upload flow), then store it."""
    content = file.file.read(settings.max_upload_bytes + 1)
    mime = validate_upload(file.filename or "", content)
    state = run_graph({"mode": "upload", "file_bytes": content, "content_type": mime})
    user = crud.get_default_user(db)
    bill = crud.upsert_bill(db, user.id, state["bill_data"], sanitize_filename(file.filename or "bill"))
    return BillUploadResponse(bill=BillOut.model_validate(bill), warnings=state.get("warnings", []))


@router.get("", response_model=list[BillOut])
def list_bills(db: Session = Depends(get_db)) -> list[BillOut]:
    user = crud.get_default_user(db)
    return [BillOut.model_validate(b) for b in crud.list_bills(db, user.id)]


@router.get("/{bill_id}", response_model=BillDetail)
def get_bill(bill_id: int, db: Session = Depends(get_db)) -> BillDetail:
    bill = crud.get_bill(db, bill_id)
    if bill is None:
        raise NotFoundError("Bill not found.")
    return BillDetail(
        **BillOut.model_validate(bill).model_dump(),
        analysis=crud.latest_analysis(db, bill_id),
        recommendations=[RecommendationOut.model_validate(r) for r in crud.list_recommendations(db, bill_id)],
    )


@router.post("/{bill_id}/analyze", response_model=AnalysisResponse)
def analyze_bill(bill_id: int, db: Session = Depends(get_db)) -> AnalysisResponse:
    """Run the full LangGraph analysis workflow for a bill and store the result."""
    bill = crud.get_bill(db, bill_id)
    if bill is None:
        raise NotFoundError("Bill not found.")
    user = crud.get_default_user(db)
    state = run_graph({"mode": "analyze", "bill_id": bill_id, "tools": AgentTools(db, user.id, bill_id),
                       "errors": [], "warnings": []})
    analysis = {**state.get("analysis", {}), "warnings": state.get("warnings", [])}
    crud.save_analysis(db, bill, analysis, state.get("recommendations", []))
    return AnalysisResponse(
        bill_id=bill_id, analysis=analysis, errors=state.get("errors", []),
        recommendations=[RecommendationOut.model_validate(r) for r in crud.list_recommendations(db, bill_id)],
    )
