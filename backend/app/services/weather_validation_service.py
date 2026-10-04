from datetime import datetime
from decimal import Decimal


def validate_temperature(
    temperature: Decimal | None,
) -> bool:
    """Validate air temperature in Celsius."""

    if temperature is None:
        return True

    return Decimal("-80") <= temperature <= Decimal("60")


def validate_pressure(
    pressure: Decimal | None,
) -> bool:
    """Validate atmospheric pressure in hPa."""

    if pressure is None:
        return True

    return Decimal("800") <= pressure <= Decimal("1100")


def validate_humidity(
    humidity: Decimal | None,
) -> bool:
    """Validate relative humidity as a percentage."""

    if humidity is None:
        return True

    return Decimal("0") <= humidity <= Decimal("100")


def validate_rainfall(
    rainfall: Decimal | None,
) -> bool:
    """Validate rainfall in millimeters."""

    if rainfall is None:
        return True

    return rainfall >= Decimal("0")


def validate_wind_speed(
    wind_speed: Decimal | None,
) -> bool:
    """Validate wind speed in m/s."""

    if wind_speed is None:
        return True

    return wind_speed >= Decimal("0")


def validate_wind_direction(
    wind_direction: Decimal | None,
) -> bool:
    """Validate wind direction in degrees."""

    if wind_direction is None:
        return True

    return Decimal("0") <= wind_direction <= Decimal("360")


def validate_visibility(
    visibility: Decimal | None,
) -> bool:
    """Validate visibility."""

    if visibility is None:
        return True

    return visibility >= Decimal("0")


def validate_observation(
    *,
    observed_at: datetime,
    temperature: Decimal | None = None,
    humidity: Decimal | None = None,
    pressure: Decimal | None = None,
    rainfall: Decimal | None = None,
    wind_speed: Decimal | None = None,
    wind_direction: Decimal | None = None,
    visibility: Decimal | None = None,
) -> tuple[bool, list[str]]:
    """
    Validate a weather observation.

    Returns:
        (
            is_valid,
            list_of_validation_errors
        )
    """

    errors: list[str] = []

    # ---------------------------------------------------------
    # Timestamp
    # ---------------------------------------------------------

    if not isinstance(observed_at, datetime):
        errors.append("observed_at must be a datetime")

    # ---------------------------------------------------------
    # Temperature
    # ---------------------------------------------------------

    if not validate_temperature(temperature):
        errors.append(
            "temperature must be between -80 and 60 °C"
        )

    # ---------------------------------------------------------
    # Humidity
    # ---------------------------------------------------------

    if not validate_humidity(humidity):
        errors.append(
            "humidity must be between 0 and 100%"
        )

    # ---------------------------------------------------------
    # Pressure
    # ---------------------------------------------------------

    if not validate_pressure(pressure):
        errors.append(
            "pressure must be between 800 and 1100 hPa"
        )

    # ---------------------------------------------------------
    # Rainfall
    # ---------------------------------------------------------

    if not validate_rainfall(rainfall):
        errors.append(
            "rainfall cannot be negative"
        )

    # ---------------------------------------------------------
    # Wind speed
    # ---------------------------------------------------------

    if not validate_wind_speed(wind_speed):
        errors.append(
            "wind_speed cannot be negative"
        )

    # ---------------------------------------------------------
    # Wind direction
    # ---------------------------------------------------------

    if not validate_wind_direction(wind_direction):
        errors.append(
            "wind_direction must be between 0 and 360 degrees"
        )

    # ---------------------------------------------------------
    # Visibility
    # ---------------------------------------------------------

    if not validate_visibility(visibility):
        errors.append(
            "visibility cannot be negative"
        )

    return len(errors) == 0, errors