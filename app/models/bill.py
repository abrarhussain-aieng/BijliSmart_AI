"""User, Bill, BillAnalysis and Recommendation tables."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base

BILL_FIELDS = (
    "consumer_id", "reference_number", "meter_number", "billing_month", "billing_date", "due_date",
    "previous_reading", "current_reading", "units", "electricity_charges", "taxes", "fpa", "gst",
    "other_charges", "amount", "tariff",
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), default="Default User")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (UniqueConstraint("user_id", "billing_month", name="uq_user_month"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    consumer_id: Mapped[str | None] = mapped_column(String(60))
    reference_number: Mapped[str | None] = mapped_column(String(60))
    meter_number: Mapped[str | None] = mapped_column(String(60))
    billing_month: Mapped[str] = mapped_column(String(7), index=True)
    billing_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    previous_reading: Mapped[float | None] = mapped_column(Float)
    current_reading: Mapped[float | None] = mapped_column(Float)
    units: Mapped[float | None] = mapped_column(Float)
    electricity_charges: Mapped[float | None] = mapped_column(Float)
    taxes: Mapped[float | None] = mapped_column(Float)
    fpa: Mapped[float | None] = mapped_column(Float)
    gst: Mapped[float | None] = mapped_column(Float)
    other_charges: Mapped[float | None] = mapped_column(Float)
    amount: Mapped[float | None] = mapped_column(Float)
    tariff: Mapped[str | None] = mapped_column(String(120))
    file_name: Mapped[str | None] = mapped_column(String(160))
    extraction_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    analyses: Mapped[list["BillAnalysis"]] = relationship(cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(cascade="all, delete-orphan")


class BillAnalysis(Base):
    __tablename__ = "bill_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str] = mapped_column(Text)
    appliance: Mapped[str | None] = mapped_column(String(80))
    estimated_kwh_saved: Mapped[float | None] = mapped_column(Float)
    estimated_cost_saved: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
