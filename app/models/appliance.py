"""Appliance and ApplianceUsage tables."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class Appliance(Base):
    __tablename__ = "appliances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    power_watts: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usages: Mapped[list["ApplianceUsage"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class ApplianceUsage(Base):
    __tablename__ = "appliance_usages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appliance_id: Mapped[int] = mapped_column(ForeignKey("appliances.id"), index=True)
    hours_per_day: Mapped[float] = mapped_column(Float)
    days_per_month: Mapped[int] = mapped_column(Integer, default=30)
