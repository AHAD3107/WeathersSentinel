
"""Generate and persist temperature forecasts from stored observations."""

from datetime import timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.location import Location
from app.models.temperature_forecast import TemperatureForecast
from app.models.weather_observation import WeatherObservation
from app.services.temperature_prediction_service import (
    temperature_prediction_service,
)


def _numeric_value(value: Any) -> float | None:
    """Convert a database value to float without inventing missing data."""
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def create_temperature_forecast(
    db: Session,
    observation_id: UUID,
) -> TemperatureForecast:
    """Predict temperature three hours ahead and save the forecast."""

    observation = (
        db.query(WeatherObservation)
        .filter(WeatherObservation.id == observation_id)
        .first()
    )

    if observation is None:
        raise HTTPException(
            status_code=404,
            detail="Weather observation not found",
        )

    location = (
        db.query(Location)
        .filter(Location.id == observation.location_id)
        .first()
    )

    if location is None:
        raise HTTPException(
            status_code=422,
            detail="The source observation has no valid linked location",
        )

    raw_data = observation.raw_data or {}

    observed_at = observation.observed_at
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)

    features = {
        "temperature_c": _numeric_value(observation.temperature),
        "dew_point_c": _numeric_value(raw_data.get("dew_point_c")),
        "pressure_hpa": _numeric_value(observation.pressure),
        "wind_speed_ms": _numeric_value(observation.wind_speed),
        "wind_direction": _numeric_value(observation.wind_direction),
        "hour": observed_at.hour,
        # Match PySpark dayofweek(): Sunday=1 through Saturday=7.
        "day_of_week": ((observed_at.weekday() + 1) % 7) + 1,
        "month": observed_at.month,
    }

    if features["temperature_c"] is None:
        raise HTTPException(
            status_code=422,
            detail="The source observation has no temperature value",
        )

    result = temperature_prediction_service.predict(features)

    forecast = TemperatureForecast(
        observation_id=observation.id,
        model_name=result["model"],
        location=f"{location.name}, {location.state}, {location.country}",
        forecast_horizon_hours=result["forecast_horizon_hours"],
        predicted_temperature_c=Decimal(
            str(result["predicted_temperature_c"])
        ),
    )

    try:
        db.add(forecast)
        db.commit()
        db.refresh(forecast)
    except Exception:
        db.rollback()
        raise

    return forecast
