from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.weather_observation import WeatherObservation
from app.services.event_detection_service import create_events_from_observation
from app.services.weather_validation_service import validate_observation


def _to_decimal(value):
    if value is None:
        return None

    return Decimal(str(value))


def process_weather_message(
    db: Session,
    message: dict,
) -> dict:
    """
    Process one weather observation received from Kafka.

    Kafka message
        ↓
    Deserialize
        ↓
    Validate
        ↓
    Duplicate check
        ↓
    PostgreSQL
        ↓
    Weather event detection
    """

    location_id = UUID(str(message["location_id"]))
    source = str(message["source"])
    observed_at = datetime.fromisoformat(message["observed_at"])

    temperature = _to_decimal(message.get("temperature"))
    pressure = _to_decimal(message.get("pressure"))
    rainfall = _to_decimal(message.get("rainfall"))
    wind_speed = _to_decimal(message.get("wind_speed"))
    wind_direction = _to_decimal(message.get("wind_direction"))

    # ---------------------------------------------------------
    # Validate observation
    # ---------------------------------------------------------

    is_valid, errors = validate_observation(
        observed_at=observed_at,
        temperature=temperature,
        pressure=pressure,
        rainfall=rainfall,
        wind_speed=wind_speed,
        wind_direction=wind_direction,
    )

    if not is_valid:
        return {
            "status": "validation_failed",
            "errors": errors,
        }

    # ---------------------------------------------------------
    # Application-level duplicate check
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Create database observation
    # ---------------------------------------------------------

    observation = WeatherObservation(
        location_id=location_id,
        source=source,
        observed_at=observed_at,
        temperature=temperature,
        humidity=None,
        pressure=pressure,
        rainfall=rainfall,
        wind_speed=wind_speed,
        wind_direction=wind_direction,
        visibility=None,
        weather_condition=None,
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

    # ---------------------------------------------------------
    # Detect weather events
    # ---------------------------------------------------------

    events = create_events_from_observation(
        db=db,
        observation=observation,
    )

    db.commit()
    db.refresh(observation)

    return {
        "status": "processed",
        "observation_id": str(observation.id),
        "events_detected": len(events),
    }