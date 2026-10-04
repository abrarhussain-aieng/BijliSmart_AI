"""Custom exceptions and validation/normalisation of extracted bill values."""
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
    """Parse numbers such as 'Rs. 16,700' or '430.5'. Returns None if absent."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group()) if match else None


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
    """Normalise extracted fields and verify them. Returns (clean_data, warnings)."""
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

    # fix negative values other than units
    for field in NUMERIC_FIELDS:
        if field == "units":
            continue
        if data[field] is not None and data[field] < 0:
            data[field] = abs(data[field])
            warnings.append(f"{field} was negative and corrected to positive.")

    # fix swapped or wrong meter readings
    prev, curr = data["previous_reading"], data["current_reading"]
    if prev is not None and curr is not None and curr < prev:
        data["previous_reading"], data["current_reading"] = curr, prev
        prev, curr = curr, prev
        warnings.append("Meter readings were swapped by OCR and have been corrected.")

    # calculate units from readings if missing
    if data["units"] is None and prev is not None and curr is not None:
        data["units"] = curr - prev
        warnings.append("Units were calculated from the meter readings.")

    # fix negative units
    if data["units"] is not None and data["units"] < 0:
        data["units"] = abs(data["units"])
        warnings.append("Units were negative and have been corrected to positive.")

    # warn if units don't match readings
    prev, curr = data["previous_reading"], data["current_reading"]
    if prev is not None and curr is not None and data["units"] is not None:
        if abs((curr - prev) - data["units"]) > 2:
            warnings.append(
                "Units differ from the meter reading difference "
                "(a meter multiplier may apply)."
            )

    # estimate total if missing
    if data["amount"] is None:
        parts = [
            data[f] for f in
            ("electricity_charges", "taxes", "fpa", "gst", "other_charges")
            if data[f] is not None
        ]
        if parts:
            data["amount"] = sum(parts)
            warnings.append("Total amount was estimated by summing the extracted charges.")

    # final checks
    if data["units"] is None and data["amount"] is None:
        raise BillValidationError(
            "Could not find units consumed or the bill amount. Upload a clearer bill."
        )
    if data["units"] is not None and data["units"] > 100000:
        raise BillValidationError("Extracted units value is unrealistically high.")
    if data["amount"] is not None and data["amount"] <= 0:
        warnings.append("Bill amount is zero or negative; please verify it.")
    if not data["billing_month"]:
        raise BillValidationError(
            "Could not determine the billing month from this bill."
        )

    return data, warnings