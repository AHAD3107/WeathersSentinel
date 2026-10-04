from datetime import datetime, timezone
from decimal import Decimal

from app.services.weather_validation_service import (
    validate_humidity,
    validate_observation,
    validate_pressure,
    validate_rainfall,
    validate_temperature,
    validate_visibility,
    validate_wind_direction,
    validate_wind_speed,
)


def test_valid_observation():
    valid, errors = validate_observation(
        observed_at=datetime.now(timezone.utc),
        temperature=Decimal("25.0"),
        humidity=Decimal("70.0"),
        pressure=Decimal("1012.0"),
        rainfall=Decimal("5.0"),
        wind_speed=Decimal("10.0"),
        wind_direction=Decimal("180.0"),
        visibility=Decimal("8.0"),
    )

    assert valid is True
    assert errors == []


def test_invalid_temperature():
    assert validate_temperature(Decimal("100.0")) is False


def test_invalid_pressure():
    assert validate_pressure(Decimal("500.0")) is False


def test_invalid_humidity():
    assert validate_humidity(Decimal("150.0")) is False


def test_negative_rainfall():
    assert validate_rainfall(Decimal("-1.0")) is False


def test_negative_wind_speed():
    assert validate_wind_speed(Decimal("-5.0")) is False


def test_invalid_wind_direction():
    assert validate_wind_direction(Decimal("400.0")) is False


def test_negative_visibility():
    assert validate_visibility(Decimal("-1.0")) is False


def test_missing_values_are_allowed():
    valid, errors = validate_observation(
        observed_at=datetime.now(timezone.utc),
        temperature=None,
        humidity=None,
        pressure=None,
        rainfall=None,
        wind_speed=None,
        wind_direction=None,
        visibility=None,
    )

    assert valid is True
    assert errors == []


def test_multiple_validation_errors():
    valid, errors = validate_observation(
        observed_at=datetime.now(timezone.utc),
        temperature=Decimal("100.0"),
        humidity=Decimal("150.0"),
        pressure=Decimal("500.0"),
        rainfall=Decimal("-1.0"),
        wind_speed=Decimal("-5.0"),
        wind_direction=Decimal("400.0"),
        visibility=Decimal("-1.0"),
    )

    assert valid is False
    assert len(errors) == 7