"""Bill-related request/response models."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class BillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    billing_month: str
    billing_date: date | None = None
    due_date: date | None = None
    consumer_id: str | None = None
    reference_number: str | None = None
    meter_number: str | None = None
    previous_reading: float | None = None
    current_reading: float | None = None
    units: float | None = None
    electricity_charges: float | None = None
    taxes: float | None = None
    fpa: float | None = None
    gst: float | None = None
    other_charges: float | None = None
    amount: float | None = None
    tariff: str | None = None
    file_name: str | None = None
    created_at: datetime | None = None


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    title: str
    detail: str
    appliance: str | None = None
    estimated_kwh_saved: float | None = None
    estimated_cost_saved: float | None = None


class BillUploadResponse(BaseModel):
    bill: BillOut
    warnings: list[str] = []


class BillDetail(BillOut):
    analysis: dict | None = None
    recommendations: list[RecommendationOut] = []


class AnalysisResponse(BaseModel):
    bill_id: int
    analysis: dict
    recommendations: list[RecommendationOut]
    errors: list[str] = []
