"""Tools the LangGraph agent can call. All numbers come from deterministic Python code."""
from sqlalchemy.orm import Session

from app.database import crud
from app.models.bill import Bill
from app.services import appliance_service, bill_analyzer, history_service, tariff_service
from app.utils.calculations import effective_rate, savings_kwh, usage_percentage


class AgentTools:
    """Request-scoped toolbox bound to a database session, user and (optional) bill."""

    def __init__(self, db: Session, user_id: int, bill_id: int | None = None) -> None:
        self.db = db
        self.user_id = user_id
        self.bill_id = bill_id
        self._bills: list[Bill] | None = None

    def _all_bills(self) -> list[Bill]:
        if self._bills is None:
            self._bills = crud.list_bills(self.db, self.user_id)
        return self._bills

    def _current(self) -> Bill | None:
        bills = self._all_bills()
        if self.bill_id:
            return next((b for b in bills if b.id == self.bill_id), None)
        return bills[0] if bills else None

    def get_current_bill(self) -> dict | None:
        """The selected (or latest) bill as User Bill Data."""
        bill = self._current()
        return bill_analyzer.bill_to_dict(bill) if bill else None

    def get_bill_history(self) -> list[dict]:
        """All stored months, oldest first."""
        return history_service.build_history(self._all_bills())

    def compare_previous_bill(self) -> dict:
        """Current vs previous vs average usage."""
        bill = self._current()
        return history_service.build_summary(self._all_bills(), bill.id if bill else None)

    def calculate_appliance_usage(self) -> dict:
        """Calculated Estimate of appliance consumption."""
        bill = self._current()
        rate = effective_rate(bill.amount, bill.units) if bill else None
        return appliance_service.estimate_appliances(crud.list_appliances(self.db, self.user_id), rate)

    def calculate_estimated_savings(self, appliance_name: str, hours_reduced: float, days: int | None = None) -> dict:
        """Estimate kWh/cost saved by cutting an appliance's usage by `hours_reduced` per day."""
        estimates = self.calculate_appliance_usage()
        wanted = appliance_name.lower()
        item = next((i for i in estimates["items"] if wanted in i["name"].lower() or i["name"].lower() in wanted), None)
        if item is None:
            return {"error": f"No appliance matching '{appliance_name}' has been entered. Add it on the Appliances page."}
        hours = min(hours_reduced, item["hours_per_day"])
        period = days or item["days_per_month"]
        kwh = savings_kwh(item["power_watts"], item["quantity"], hours, period)
        rate = estimates["effective_rate"]
        return {
            "label": "Calculated Estimate", "appliance": item["name"], "hours_reduced_per_day": hours,
            "days": period, "formula": f"({item['power_watts']:g} W / 1000) x {item['quantity']} x {hours:g} h x {period} days",
            "estimated_kwh_saved": kwh, "estimated_cost_saved": kwh * rate if rate else None,
            "note": "Estimate based on the wattage you entered; actual savings will vary.",
        }

    def search_tariff_knowledge(self, query: str) -> dict:
        """Retrieve knowledge-base excerpts about tariffs and billing."""
        return tariff_service.retrieve_tariff_context(query)

    def analyze_consumption(self) -> dict:
        """Current usage in context: rate, change vs previous/average, appliance coverage."""
        bill = self._current()
        if bill is None:
            return {"available": False}
        summary = self.compare_previous_bill()
        appliances = self.calculate_appliance_usage()
        total = appliances["total_kwh"]
        return {
            "available": True, "label": "Calculated Estimate", "units": bill.units, "amount": bill.amount,
            "effective_rate": effective_rate(bill.amount, bill.units),
            "comparison": summary["comparison"], "average_units": summary["average_units"],
            "appliance_estimated_kwh": total,
            "appliance_coverage_pct": usage_percentage(total, bill.units) if bill.units and total else None,
        }
