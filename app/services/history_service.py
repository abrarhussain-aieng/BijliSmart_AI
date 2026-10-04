"""Bill history, trends and month-over-month comparison."""
from datetime import datetime

from app.models.bill import Bill
from app.utils.calculations import change, percent_change


def month_label(month: str) -> str:
    """'2025-04' -> 'Apr 2025'."""
    try:
        return datetime.strptime(month + "-01", "%Y-%m-%d").strftime("%b %Y")
    except ValueError:
        return month


def build_history(bills: list[Bill]) -> list[dict]:
    """Chronological (oldest first) list of monthly records."""
    return [
        {
            "bill_id": b.id,
            "month": b.billing_month,
            "label": month_label(b.billing_month),
            "billing_date": b.billing_date.isoformat() if b.billing_date else None,
            "units": b.units,
            "amount": b.amount,
            "tariff": b.tariff,
        }
        for b in sorted(bills, key=lambda x: x.billing_month)
    ]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def build_summary(bills: list[Bill], current_bill_id: int | None = None) -> dict:
    """Current vs previous vs average usage, with deterministic change figures."""
    history = build_history(bills)
    if not history:
        return {"has_data": False, "history": [], "current": None, "previous": None,
                "average_units": None, "average_amount": None, "comparison": None}
    idx = next((i for i, h in enumerate(history) if h["bill_id"] == current_bill_id), len(history) - 1)
    current = history[idx]
    previous = history[idx - 1] if idx > 0 else None
    earlier = history[:idx]
    avg_units = _mean([h["units"] for h in earlier if h["units"] is not None])
    avg_amount = _mean([h["amount"] for h in earlier if h["amount"] is not None])

    comparison = None
    if previous and None not in (current["units"], previous["units"]):
        comparison = {
            "previous_label": previous["label"],
            "current_label": current["label"],
            "unit_change": change(current["units"], previous["units"]),
            "unit_percentage_change": percent_change(current["units"], previous["units"]),
            "bill_change": None,
            "bill_percentage_change": None,
            "vs_average_percentage": (
                percent_change(current["units"], avg_units) if avg_units else None
            ),
        }
        if None not in (current["amount"], previous["amount"]):
            comparison["bill_change"] = change(current["amount"], previous["amount"])
            comparison["bill_percentage_change"] = percent_change(current["amount"], previous["amount"])
    return {"has_data": True, "history": history, "current": current, "previous": previous,
            "average_units": avg_units, "average_amount": avg_amount, "comparison": comparison}
