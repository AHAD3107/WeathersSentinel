
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.temperature_forecast import TemperatureForecast
from app.models.weather_observation import WeatherObservation
from app.services.event_detection_service import create_events_from_observation
from app.services.temperature_prediction_service import (
    temperature_prediction_service,
)
from app.services.weather_validation_service import validate_observation


def _to_decimal(value):
    if value is None:
        return None

    number = Decimal(str(value))

    if not number.is_finite():
        raise ValueError(
            f"Weather numeric value must be finite, got {value!r}"
        )

    return number


def _parse_timestamp(value: str) -> datetime:
    """Parse an observation timestamp and normalize it to UTC."""
    timestamp = datetime.fromisoformat(value)

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)

    return timestamp.astimezone(timezone.utc)


def process_weather_message(db: Session, message: dict) -> dict:
    """Validate and persist an observation, detect events, and forecast."""
    if not isinstance(message, dict):
        return {
            "status": "validation_failed",
            "errors": ["Weather message must be a JSON object."],
        }

    try:
        location_id = UUID(str(message["location_id"]))

        raw_source = message["source"]
        if not isinstance(raw_source, str) or not raw_source.strip():
            raise ValueError("source must be a non-empty string")
        source = raw_source.upper()

        observed_at = _parse_timestamp(message["observed_at"])

        temperature = _to_decimal(message.get("temperature"))
        humidity = _to_decimal(message.get("humidity"))
        pressure = _to_decimal(message.get("pressure"))
        rainfall = _to_decimal(message.get("rainfall"))
        wind_speed = _to_decimal(message.get("wind_speed"))
        wind_direction = _to_decimal(message.get("wind_direction"))

    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        return {
            "status": "validation_failed",
            "errors": [f"Invalid message structure or field value: {exc}"],
        }

    # Open-Meteo reports wind speed in km/h. NOAA ISD-Lite
    # values are already in m/s and must not be converted again.
    if source == "OPEN_METEO" and wind_speed is not None:
        wind_speed = wind_speed / Decimal("3.6")

    is_valid, errors = validate_observation(
        observed_at=observed_at,
        temperature=temperature,
        humidity=humidity,
        pressure=pressure,
        rainfall=rainfall,
        wind_speed=wind_speed,
        wind_direction=wind_direction,
    )

    if not is_valid:
        return {"status": "validation_failed", "errors": errors}

    existing = (
        db.query(WeatherObservation)
        .filter(
            WeatherObservation.location_id == location_id,
            WeatherObservation.source == source,
            WeatherObservation.observed_at == observed_at,
        )
        .first()
    )
    if existing is not None:
        return {"status": "duplicate", "observation_id": str(existing.id)}

    # Keep source units in raw_data for traceability, while the normalized
    # database field wind_speed is always stored in m/s.
    observation = WeatherObservation(
        location_id=location_id,
        source=source,
        observed_at=observed_at,
        temperature=temperature,
        humidity=humidity,
        pressure=pressure,
        rainfall=rainfall,
        wind_speed=wind_speed,
        wind_direction=wind_direction,
        visibility=None,
        weather_condition=message.get("weather_condition"),
        raw_data=message,
    )
    db.add(observation)

    try:
        # Flush inside a savepoint so a uniqueness race can be handled
        # without invalidating the outer transaction.
        with db.begin_nested():
            db.flush()
    except IntegrityError:
        existing = (
            db.query(WeatherObservation)
            .filter(
                WeatherObservation.location_id == location_id,
                WeatherObservation.source == source,
                WeatherObservation.observed_at == observed_at,
            )
            .first()
        )
        if existing is not None:
            return {"status": "duplicate", "observation_id": str(existing.id)}
        raise

    events = create_events_from_observation(db=db, observation=observation)

    # Use UTC consistently for time-derived model features.
    raw_dew_point = message.get("dew_point_c")
    if raw_dew_point is None:
        raw_dew_point = message.get("dew_point")

    prediction_input = {
        "temperature_c": float(temperature) if temperature is not None else None,
        "dew_point_c": (
            float(_to_decimal(raw_dew_point))
            if raw_dew_point is not None
            else None
        ),
        "pressure_hpa": float(pressure) if pressure is not None else None,
        "wind_speed_ms": float(wind_speed) if wind_speed is not None else None,
        "wind_direction": (
            float(wind_direction) if wind_direction is not None else None
        ),
        "hour": observed_at.hour,
        # Match PySpark dayofweek(): Sunday=1 through Saturday=7.
        "day_of_week": ((observed_at.weekday() + 1) % 7) + 1,
        "month": observed_at.month,
    }

    forecast_result = None
    prediction_error = None

    try:
        # Isolate forecast writes from observation and event writes.
        with db.begin_nested():
            prediction = temperature_prediction_service.predict(
                prediction_input
            )

            forecast = TemperatureForecast(
                observation_id=observation.id,
                model_name=str(prediction["model"]),
                location=str(prediction["location"]),
                forecast_horizon_hours=int(
                    prediction["forecast_horizon_hours"]
                ),
                predicted_temperature_c=Decimal(
                    str(prediction["predicted_temperature_c"])
                ),
            )
            db.add(forecast)
            db.flush()

            forecast_result = {
                "forecast_id": str(forecast.id),
                "model": forecast.model_name,
                "forecast_horizon_hours": forecast.forecast_horizon_hours,
                "predicted_temperature_c": float(
                    forecast.predicted_temperature_c
                ),
            }
    except Exception as exc:
        # Preserve the outer transaction if forecast creation fails.
        prediction_error = str(exc)

    try:
        db.commit()
        db.refresh(observation)
    except Exception:
        db.rollback()
        raise

    result = {
        "status": "processed",
        "observation_id": str(observation.id),
        "events_detected": len(events),
        "temperature_forecast": forecast_result,
    }

    if prediction_error is not None:
        result["prediction_status"] = "failed"
        result["prediction_error"] = prediction_error
    else:
        result["prediction_status"] = "saved"

    return result
