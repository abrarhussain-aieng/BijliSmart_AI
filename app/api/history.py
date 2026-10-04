"""Bill history endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import crud
from app.database.database import get_db
from app.services import history_service

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def get_history(db: Session = Depends(get_db)) -> list[dict]:
    """Month, billing date, units, amount and tariff for every stored bill (oldest first)."""
    user = crud.get_default_user(db)
    return history_service.build_history(crud.list_bills(db, user.id))


@router.get("/summary")
def get_history_summary(db: Session = Depends(get_db)) -> dict:
    """Trends plus current vs previous vs average comparison."""
    user = crud.get_default_user(db)
    return history_service.build_summary(crud.list_bills(db, user.id))
