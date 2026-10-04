"""Bill breakdown, insights and rule-based recommendation candidates."""
import re

from app.models.bill import BILL_FIELDS, Bill
from app.services.history_service import month_label
from app.utils.calculations import effective_rate, savings_kwh

TIPS = (
    (r"\bac\b|air.?con|split", "Set the thermostat near 26°C, use the sleep timer and keep filters clean."),
    (r"heater|geyser", "Use a timer, lower the temperature setting and insulate the tank."),
    (r"fridge|refrigerator|freezer", "Keep door seals tight, avoid overfilling and leave space behind it."),
    (r"fan", "Switch fans off in empty rooms; consider an efficient (inverter/BLDC) fan."),
    (r"light|bulb|led|tube", "Switch to LED lighting and turn lights off when leaving a room."),
    (r"pump|motor", "Run the pump only as needed, ideally in a fixed schedule."),
    (r"iron", "Iron clothes in one batch instead of several short sessions."),
    (r"wash", "Run full loads and avoid unnecessary hot cycles."),
)


def bill_to_dict(bill: Bill) -> dict:
    """Serialise a bill as plain data (User Bill Data)."""
    data = {"bill_id": bill.id, "label": "User Bill Data", "billing_label": month_label(bill.billing_month)}
    for field in BILL_FIELDS:
        value = getattr(bill, field)
        data[field] = value.isoformat() if hasattr(value, "isoformat") else value
    data["effective_rate"] = effective_rate(bill.amount, bill.units)
    return data


def bill_breakdown(bill: dict) -> dict:
    """Charges breakdown exactly as printed on the bill."""
    return {
        "label": "User Bill Data",
        "units": bill["units"],
        "readings": {"previous": bill["previous_reading"], "current": bill["current_reading"]},
        "electricity_charges": bill["electricity_charges"],
        "taxes": bill["taxes"], "fpa": bill["fpa"], "gst": bill["gst"],
        "other_charges": bill["other_charges"], "total": bill["amount"],
        "tariff": bill["tariff"], "effective_rate": bill["effective_rate"],
    }


def build_insights(bill: dict | None, summary: dict, estimates: dict) -> list[dict]:
    """Short factual insights computed from the data."""
    out: list[dict] = []
    comp = summary.get("comparison")
    if comp and comp["unit_percentage_change"] is not None:
        up = comp["unit_change"] > 0
        pct = comp["bill_percentage_change"]
        title = (f"Your bill {'increased' if up else 'decreased'} by ~{abs(pct):.0f}%" if pct is not None
                 else f"Your units {'increased' if up else 'decreased'} by {abs(comp['unit_percentage_change']):.0f}%")
        out.append({"title": title, "tone": "bad" if up else "good",
                    "text": f"Units changed by {comp['unit_change']:+.0f} ({comp['unit_percentage_change']:+.1f}%) "
                            f"compared with {comp['previous_label']}."})
    if comp and comp["vs_average_percentage"] is not None:
        diff = comp["vs_average_percentage"]
        out.append({"title": f"{abs(diff):.0f}% {'above' if diff > 0 else 'below'} your earlier average",
                    "tone": "bad" if diff > 0 else "good",
                    "text": f"Average of your earlier bills: {summary['average_units']:.0f} units."})
    items = estimates.get("items") or []
    if items and items[0]["monthly_kwh"] > 0:
        top = items[0]
        out.append({"title": f"{top['name']} is your largest estimated load", "tone": "info",
                    "text": f"About {top['percentage']:.0f}% of the usage you entered (~{top['monthly_kwh']:.0f} kWh/month, estimate)."})
    if not out:
        out.append({"title": "Add more data for insights", "tone": "info",
                    "text": "Upload previous months' bills and enter your appliances to see trends and estimates."})
    return out[:3]


def build_recommendations(estimates: dict, rate: float | None) -> list[dict]:
    """Rule-based candidates: trim the top loads by up to 2 h/day (max 25% of their usage)."""
    recs: list[dict] = []
    for item in estimates.get("items", [])[:3]:
        hours = round(min(2.0, item["hours_per_day"] * 0.25), 1)
        if hours <= 0:
            continue
        kwh = savings_kwh(item["power_watts"], item["quantity"], hours, item["days_per_month"])
        cost = kwh * rate if rate else None
        tip = next((t for pattern, t in TIPS if re.search(pattern, item["name"].lower())),
                   "Use it only when needed and switch it off completely afterwards.")
        cost_text = f" (approximately Rs. {cost:,.0f})" if cost is not None else ""
        recs.append({
            "title": f"Reduce {item['name']} by ~{hours:g} h/day",
            "detail": f"Estimated saving: ~{kwh:.0f} kWh/month{cost_text}, based on the values you entered. {tip}",
            "appliance": item["name"], "estimated_kwh_saved": kwh, "estimated_cost_saved": cost,
            "label": "AI Recommendation",
        })
    return recs
