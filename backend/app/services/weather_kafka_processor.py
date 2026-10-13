
from datetime import datetime
from decimal import Decimal
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
    return Decimal(str(value))


def process_weather_message(
    db: Session,
    message: dict,
) -> dict:
    """Validate and persist a Kafka observation, detect events, and forecast."""
    location_id = UUID(str(message["location_id"]))
    source = str(message["source"])
    observed_at = datetime.fromisoformat(message["observed_at"])

    temperature = _to_decimal(message.get("temperature"))
    pressure = _to_decimal(message.get("pressure"))
    rainfall = _to_decimal(message.get("rainfall"))
    wind_speed = _to_decimal(message.get("wind_speed"))
    wind_direction = _to_decimal(message.get("wind_direction"))

    is_valid, errors = validate_observation(
        observed_at=observed_at,
        temperature=temperature,
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
        return {
            "status": "duplicate",
            "observation_id": str(existing.id),
        }

    observation = WeatherObservation(
        location_id=location_id,
        source=source,
        observed_at=observed_at,
        temperature=temperature,
        humidity=_to_decimal(message.get("humidity")),
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
            return {
                "status": "duplicate",
                "observation_id": str(existing.id),
            }
        raise

    events = create_events_from_observation(
        db=db,
        observation=observation,
    )

    # Match the exact feature names used during model training.
    # Open-Meteo provides wind speed in km/h; the model expects m/s.
    timestamp = observed_at
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone().replace(tzinfo=None)

    prediction_input = {
        "temperature_c": (
            float(temperature) if temperature is not None else None
        ),
        # Open-Meteo's current request does not include dew point.
        # The trained median imputer handles this missing feature.
        "dew_point_c": None,
        "pressure_hpa": (
            float(pressure) if pressure is not None else None
        ),
        "wind_speed_ms": (
            float(wind_speed) / 3.6 if wind_speed is not None else None
        ),
        "wind_direction": (
            float(wind_direction)
            if wind_direction is not None
            else None
        ),
        "hour": timestamp.hour,
        "day_of_week": timestamp.weekday(),
        "month": timestamp.month,
    }

    forecast_result = None
    prediction_error = None

    try:
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
        # Do not lose a valid weather observation because the ML step failed.
        prediction_error = str(exc)

    db.commit()
    db.refresh(observation)

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
