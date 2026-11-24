"""Custom exceptions and validation/normalisation of extracted bill values."""
import math
import re
from datetime import datetime


class AppError(Exception):
    """Base error carrying an HTTP status code and a user-safe message."""

    status_code = 400

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code:
            self.status_code = status_code


class FileValidationError(AppError):
    status_code = 400


class BillValidationError(AppError):
    status_code = 422


class AIServiceError(AppError):
    status_code = 502


class NotFoundError(AppError):
    status_code = 404


NUMERIC_FIELDS = (
    "previous_reading", "current_reading", "units", "electricity_charges",
    "taxes", "fpa", "gst", "other_charges", "amount",
)
TEXT_FIELDS = ("consumer_id", "reference_number", "meter_number", "tariff")
MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
DATE_FORMATS = (
    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%y",
    "%d-%b-%Y", "%d %b %Y", "%d %B %Y", "%d.%m.%Y"
)


def to_number(value: object) -> float | None:
    """Parse numbers such as 'Rs. 16,700' or '430.5'. Returns None if absent or non-finite."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        num = float(value)
        return num if math.isfinite(num) else None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    if not match:
        return None
    num = float(match.group())
    return num if math.isfinite(num) else None


def normalize_month(value: object) -> str | None:
    """Normalise 'APR 25', 'April 2025', '04/2025' or '2025-04-30' to 'YYYY-MM'."""
    if not value:
        return None
    text = str(value).strip().lower()
    m = re.match(r"(\d{4})-(\d{1,2})", text)
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.match(r"(\d{1,2})[/-](\d{4})$", text)
    if m and 1 <= int(m.group(1)) <= 12:
        return f"{m.group(2)}-{int(m.group(1)):02d}"
    name = re.search(r"[a-z]{3}", text)
    if name and name.group() in MONTHS:
        year = re.search(r"\d{4}", text)
        if year:
            return f"{year.group()}-{MONTHS[name.group()]:02d}"
        short = re.search(r"\b(\d{2})\b", text)
        if short:
            return f"20{short.group(1)}-{MONTHS[name.group()]:02d}"
    return None


def normalize_date(value: object) -> str | None:
    """Normalise a date string to 'YYYY-MM-DD' or None."""
    if not value:
        return None
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def validate_extracted_bill(raw: dict) -> tuple[dict, list[str]]:
    """Normalise extracted fields and verify invariants. Returns (clean_data, warnings)."""
    if not isinstance(raw, dict):
        raise BillValidationError("Extracted bill payload must be a JSON object.")

    warnings: list[str] = []
    data: dict = {f: to_number(raw.get(f)) for f in NUMERIC_FIELDS}

    for field in TEXT_FIELDS:
        value = raw.get(field)
        data[field] = str(value).strip() if value not in (None, "") else None

    data["billing_date"] = normalize_date(raw.get("billing_date"))
    data["due_date"] = normalize_date(raw.get("due_date"))
    data["billing_month"] = (
        normalize_month(raw.get("billing_month"))
        or normalize_month(data["billing_date"])
    )

    # Reject negative numbers across every numeric field rather than silently flipping signs
    for field in NUMERIC_FIELDS:
        if data[field] is not None and data[field] < 0:
            raise BillValidationError(f"Invalid negative value for '{field}': {data[field]}.")

    # Correct swapped meter readings if OCR inverted previous and current
    prev, curr = data["previous_reading"], data["current_reading"]
    if prev is not None and curr is not None and curr < prev:
        data["previous_reading"], data["current_reading"] = curr, prev
        prev, curr = curr, prev
        warnings.append("Meter readings were swapped by OCR and have been corrected.")

    # Calculate units from readings if missing
    if data["units"] is None and prev is not None and curr is not None:
        data["units"] = round(curr - prev, 4)
        warnings.append("Units were calculated from the meter readings.")

    # Warn if extracted units differ significantly from meter reading difference
    prev, curr = data["previous_reading"], data["current_reading"]
    if prev is not None and curr is not None and data["units"] is not None:
        if abs((curr - prev) - data["units"]) > 2:
            warnings.append(
                "Units differ from the meter reading difference "
                "(a meter multiplier may apply)."
            )

    # Estimate total if missing
    if data["amount"] is None:
        parts = [
            data[f] for f in
            ("electricity_charges", "taxes", "fpa", "gst", "other_charges")
            if data[f] is not None
        ]
        if parts:
            data["amount"] = round(sum(parts), 2)
            warnings.append("Total amount was estimated by summing the extracted charges.")

    # Final invariant checks
    if data["units"] is None and data["amount"] is None:
        raise BillValidationError(
            "Could not find units consumed or the bill amount. Upload a clearer bill."
        )
    if data["units"] is not None and data["units"] > 100000:
        raise BillValidationError("Extracted units value is unrealistically high.")
    if data["amount"] is not None and data["amount"] <= 0:
        raise BillValidationError("Bill amount must be greater than zero.")
    if not data["billing_month"]:
        raise BillValidationError(
            "Could not determine the billing month from this bill."
        )

    return data, warnings