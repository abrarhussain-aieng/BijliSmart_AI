"""Appliance endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.tools import AgentTools
from app.database import crud
from app.database.database import get_db
from app.schemas.appliance import ApplianceCreate, ApplianceListResponse, ApplianceOut
from app.utils.validators import NotFoundError

router = APIRouter(prefix="/api/appliances", tags=["appliances"])


def _estimates(db: Session) -> dict:
    user = crud.get_default_user(db)
    return AgentTools(db, user.id).calculate_appliance_usage()


@router.post("", response_model=ApplianceOut, status_code=201)
def add_appliance(payload: ApplianceCreate, db: Session = Depends(get_db)) -> dict:
    user = crud.get_default_user(db)
    created = crud.create_appliance(db, user.id, payload.model_dump())
    return next(i for i in _estimates(db)["items"] if i["id"] == created.id)


@router.get("", response_model=ApplianceListResponse)
def list_appliances(db: Session = Depends(get_db)) -> dict:
    return _estimates(db)


@router.delete("/{appliance_id}", status_code=204)
def remove_appliance(appliance_id: int, db: Session = Depends(get_db)) -> None:
    user = crud.get_default_user(db)
    if not crud.delete_appliance(db, user.id, appliance_id):
        raise NotFoundError("Appliance not found.")
