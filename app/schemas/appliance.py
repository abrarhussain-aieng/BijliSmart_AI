"""Appliance request/response models."""
from pydantic import BaseModel, Field


class ApplianceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    power_watts: float = Field(gt=0, le=20000)
    quantity: int = Field(default=1, ge=1, le=100)
    hours_per_day: float = Field(ge=0, le=24)
    days_per_month: int = Field(default=30, ge=1, le=31)


class ApplianceOut(BaseModel):
    id: int
    name: str
    power_watts: float
    quantity: int
    hours_per_day: float
    days_per_month: int
    monthly_kwh: float
    percentage: float
    estimated_cost: float | None = None
    label: str = "Calculated Estimate"


class ApplianceListResponse(BaseModel):
    items: list[ApplianceOut]
    total_kwh: float
    total_cost: float | None = None
    effective_rate: float | None = None
    note: str
