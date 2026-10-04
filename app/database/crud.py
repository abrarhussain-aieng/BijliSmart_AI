"""Database access functions."""
import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appliance import Appliance, ApplianceUsage
from app.models.bill import BILL_FIELDS, Bill, BillAnalysis, Recommendation, User
from app.models.chat import ChatMessage

DEFAULT_USER_ID = 1


def get_default_user(db: Session) -> User:
    """Return the single local user, creating it on first use."""
    user = db.get(User, DEFAULT_USER_ID)
    if user is None:
        user = User(id=DEFAULT_USER_ID, name="Default User")
        db.add(user)
        db.commit()
    return user


def _to_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


# ----- bills -----
def upsert_bill(db: Session, user_id: int, data: dict, file_name: str | None) -> Bill:
    """Create the bill for a month, or replace the existing bill of that month."""
    month = data["billing_month"]
    bill = db.scalar(select(Bill).where(Bill.user_id == user_id, Bill.billing_month == month))
    if bill is None:
        bill = Bill(user_id=user_id, billing_month=month)
        db.add(bill)
    else:
        bill.analyses.clear()
        bill.recommendations.clear()
    for field in BILL_FIELDS:
        value = data.get(field)
        setattr(bill, field, _to_date(value) if field in ("billing_date", "due_date") else value)
    bill.file_name = file_name
    bill.extraction_json = json.dumps(data, default=str)
    db.commit()
    db.refresh(bill)
    return bill


def list_bills(db: Session, user_id: int) -> list[Bill]:
    """All bills, newest billing month first."""
    return list(db.scalars(select(Bill).where(Bill.user_id == user_id).order_by(Bill.billing_month.desc())))


def get_bill(db: Session, bill_id: int) -> Bill | None:
    return db.get(Bill, bill_id)


def save_analysis(db: Session, bill: Bill, analysis: dict, recommendations: list[dict]) -> None:
    """Replace the stored analysis and recommendations of a bill."""
    bill.analyses.clear()
    bill.recommendations.clear()
    db.flush()
    db.add(BillAnalysis(bill_id=bill.id, content=json.dumps(analysis, default=str)))
    for rec in recommendations:
        db.add(Recommendation(
            bill_id=bill.id, title=rec["title"], detail=rec["detail"], appliance=rec.get("appliance"),
            estimated_kwh_saved=rec.get("estimated_kwh_saved"), estimated_cost_saved=rec.get("estimated_cost_saved"),
        ))
    db.commit()


def latest_analysis(db: Session, bill_id: int) -> dict | None:
    row = db.scalar(select(BillAnalysis).where(BillAnalysis.bill_id == bill_id).order_by(BillAnalysis.id.desc()))
    return json.loads(row.content) if row else None


def list_recommendations(db: Session, bill_id: int) -> list[Recommendation]:
    return list(db.scalars(select(Recommendation).where(Recommendation.bill_id == bill_id).order_by(Recommendation.id)))


# ----- appliances -----
def create_appliance(db: Session, user_id: int, data: dict) -> Appliance:
    appliance = Appliance(user_id=user_id, name=data["name"], power_watts=data["power_watts"], quantity=data["quantity"])
    appliance.usages.append(ApplianceUsage(hours_per_day=data["hours_per_day"], days_per_month=data["days_per_month"]))
    db.add(appliance)
    db.commit()
    db.refresh(appliance)
    return appliance


def list_appliances(db: Session, user_id: int) -> list[Appliance]:
    return list(db.scalars(select(Appliance).where(Appliance.user_id == user_id).order_by(Appliance.id)))


def delete_appliance(db: Session, user_id: int, appliance_id: int) -> bool:
    appliance = db.get(Appliance, appliance_id)
    if appliance is None or appliance.user_id != user_id:
        return False
    db.delete(appliance)
    db.commit()
    return True


# ----- chat -----
def add_chat_message(db: Session, user_id: int, bill_id: int | None, role: str, content: str) -> None:
    db.add(ChatMessage(user_id=user_id, bill_id=bill_id, role=role, content=content))
    db.commit()


def recent_messages(db: Session, user_id: int, bill_id: int | None, limit: int = 6) -> list[dict]:
    """Last `limit` messages in the bill context, oldest first."""
    query = select(ChatMessage).where(ChatMessage.user_id == user_id)
    query = query.where(ChatMessage.bill_id == bill_id) if bill_id else query.where(ChatMessage.bill_id.is_(None))
    rows = list(db.scalars(query.order_by(ChatMessage.id.desc()).limit(limit)))
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]
