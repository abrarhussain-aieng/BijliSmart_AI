"""Appliance-level consumption estimates (user-entered wattage and hours)."""
from app.models.appliance import Appliance
from app.utils.calculations import appliance_monthly_kwh, usage_percentage

ESTIMATE_NOTE = (
    "Calculated estimates based on the wattage and hours you entered. A bill alone cannot show the exact "
    "consumption of each appliance. Cost uses the average rate from your latest bill (amount / units)."
)


def estimate_appliances(appliances: list[Appliance], rate: float | None) -> dict:
    """Return per-appliance monthly kWh, share of total, and estimated cost."""
    rows = []
    for a in appliances:
        usage = a.usages[0] if a.usages else None
        hours = usage.hours_per_day if usage else 0.0
        days = usage.days_per_month if usage else 30
        rows.append({
            "id": a.id, "name": a.name, "power_watts": a.power_watts, "quantity": a.quantity,
            "hours_per_day": hours, "days_per_month": days,
            "monthly_kwh": appliance_monthly_kwh(a.power_watts, a.quantity, hours, days),
        })
    total = sum(r["monthly_kwh"] for r in rows)
    for r in rows:
        r["percentage"] = usage_percentage(r["monthly_kwh"], total)
        r["estimated_cost"] = r["monthly_kwh"] * rate if rate else None
        r["label"] = "Calculated Estimate"
    rows.sort(key=lambda r: r["monthly_kwh"], reverse=True)
    return {"items": rows, "total_kwh": total, "total_cost": total * rate if rate else None,
            "effective_rate": rate, "note": ESTIMATE_NOTE}
