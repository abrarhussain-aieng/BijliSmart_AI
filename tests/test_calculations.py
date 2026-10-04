from app.utils.calculations import (appliance_monthly_kwh, change, effective_rate, percent_change,
                                    savings_kwh, usage_percentage)


def test_appliance_monthly_kwh():
    assert appliance_monthly_kwh(1000, 1, 8, 30) == 240


def test_quantity_multiplies():
    assert appliance_monthly_kwh(75, 4, 10, 30) == 90


def test_usage_percentage():
    assert usage_percentage(50, 200) == 25
    assert usage_percentage(5, 0) == 0


def test_change_and_percent_change():
    assert change(430, 350) == 80
    assert round(percent_change(430, 350), 2) == 22.86
    assert percent_change(10, 0) is None


def test_savings_kwh():
    assert savings_kwh(1500, 1, 2, 30) == 90


def test_effective_rate():
    assert effective_rate(16700, 430) == 16700 / 430
    assert effective_rate(None, 430) is None
