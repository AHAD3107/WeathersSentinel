from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.services.weather_validation_service import validate_observation


@pytest.fixture
def valid_observation():
    return {
        "observed_at": datetime.now(timezone.utc),
        "temperature": Decimal("23.5"),
        "humidity": Decimal("65"),
        "pressure": Decimal("1013.25"),
        "rainfall": Decimal("0"),
        "wind_speed": Decimal("2.5"),
        "wind_direction": Decimal("180"),
        "visibility": Decimal("10"),
    }


def test_valid_observation_passes(valid_observation):
    is_valid, errors = validate_observation(**valid_observation)

    assert is_valid is True
    assert errors == []


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        (
            "temperature",
            Decimal("61"),
            "temperature must be between -80 and 60 °C",
        ),
        (
            "humidity",
            Decimal("101"),
            "humidity must be between 0 and 100%",
        ),
        (
            "pressure",
            Decimal("799"),
            "pressure must be between 800 and 1100 hPa",
        ),
        (
            "rainfall",
            Decimal("-1"),
            "rainfall cannot be negative",
        ),
        (
            "wind_speed",
            Decimal("-0.1"),
            "wind_speed cannot be negative",
        ),
        (
            "wind_direction",
            Decimal("361"),
            "wind_direction must be between 0 and 360 degrees",
        ),
        (
            "visibility",
            Decimal("-1"),
            "visibility cannot be negative",
        ),
    ],
)
def test_invalid_weather_values_are_rejected(
    valid_observation, field, value, expected_error
):
    valid_observation[field] = value

    is_valid, errors = validate_observation(**valid_observation)

    assert is_valid is False
    assert expected_error in errors


def test_missing_optional_weather_values_are_allowed(valid_observation):
    for field in (
        "temperature",
        "humidity",
        "pressure",
        "rainfall",
        "wind_speed",
        "wind_direction",
        "visibility",
    ):
        valid_observation[field] = None

    is_valid, errors = validate_observation(**valid_observation)

    assert is_valid is True
    assert errors == []
