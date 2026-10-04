import pytest

from app.core.security import validate_upload
from app.utils.validators import (BillValidationError, FileValidationError, normalize_date,
                                  normalize_month, to_number, validate_extracted_bill)

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


def test_to_number():
    assert to_number("Rs. 16,700") == 16700
    assert to_number("430.5") == 430.5
    assert to_number(None) is None
    assert to_number("n/a") is None


def test_normalize_month():
    assert normalize_month("APR 25") == "2025-04"
    assert normalize_month("April 2025") == "2025-04"
    assert normalize_month("04/2025") == "2025-04"
    assert normalize_month("2025-04-30") == "2025-04"
    assert normalize_month("garbage") is None


def test_normalize_date():
    assert normalize_date("30-04-2025") == "2025-04-30"
    assert normalize_date("nope") is None


def test_validate_bill_computes_units_and_month():
    data, warnings = validate_extracted_bill({
        "previous_reading": "1,000", "current_reading": "1,430", "amount": "Rs. 16,700", "billing_date": "30-04-2025"})
    assert data["units"] == 430
    assert data["billing_month"] == "2025-04"
    assert warnings


def test_validate_bill_rejects_missing_values():
    with pytest.raises(BillValidationError):
        validate_extracted_bill({"billing_month": "2025-04"})


def test_validate_bill_rejects_negative():
    with pytest.raises(BillValidationError):
        validate_extracted_bill({"units": -5, "billing_month": "2025-04"})


def test_validate_upload_ok_and_errors():
    assert validate_upload("bill.png", PNG) == "image/png"
    with pytest.raises(FileValidationError):
        validate_upload("bill.exe", PNG)
    with pytest.raises(FileValidationError):
        validate_upload("bill.pdf", PNG)
    with pytest.raises(FileValidationError):
        validate_upload("bill.png", b"")
