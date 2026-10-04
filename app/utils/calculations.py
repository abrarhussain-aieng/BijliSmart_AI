"""Deterministic calculations. The LLM explains results; Python computes them."""


def appliance_monthly_kwh(power_watts: float, quantity: int, hours_per_day: float, days: int) -> float:
    """monthly_kwh = (watts / 1000) x quantity x hours/day x days."""
    return (power_watts / 1000) * quantity * hours_per_day * days


def usage_percentage(part: float, total: float) -> float:
    """Share of `part` in `total`, in percent (0 when total is 0)."""
    return (part / total) * 100 if total else 0.0


def change(current: float, previous: float) -> float:
    """Absolute change between two values."""
    return current - previous


def percent_change(current: float, previous: float) -> float | None:
    """Percentage change versus previous (None when previous is 0)."""
    if not previous:
        return None
    return ((current - previous) / previous) * 100


def savings_kwh(power_watts: float, quantity: int, hours_reduced: float, days: int) -> float:
    """Estimated kWh saved by reducing usage by `hours_reduced` per day."""
    return appliance_monthly_kwh(power_watts, quantity, hours_reduced, days)


def effective_rate(amount: float | None, units: float | None) -> float | None:
    """Average cost per unit from the user's own bill (amount / units)."""
    if not amount or not units:
        return None
    return amount / units
