from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.weather_event import WeatherEvent
from app.models.weather_observation import WeatherObservation


RAINFALL_THRESHOLD_MM = Decimal("50")
HEATWAVE_THRESHOLD_C = Decimal("40")
WIND_SPEED_THRESHOLD = Decimal("50")


def detect_events(observation: WeatherObservation) -> list[dict]:
    detected_events = []

    if (
        observation.rainfall is not None
        and observation.rainfall >= RAINFALL_THRESHOLD_MM
    ):
        confidence = min(
            Decimal("0.99"),
            Decimal("0.60") + (observation.rainfall / Decimal("100")),
        )

        detected_events.append(
            {
                "event_type": "rainfall",
                "severity": "high",
                "confidence_score": confidence,
            }
        )

    if (
        observation.temperature is not None
        and observation.temperature >= HEATWAVE_THRESHOLD_C
    ):
        confidence = min(
            Decimal("0.99"),
            Decimal("0.60")
            + (
                (observation.temperature - HEATWAVE_THRESHOLD_C)
                / Decimal("20")
            ),
        )

        detected_events.append(
            {
                "event_type": "heatwave",
                "severity": "high",
                "confidence_score": confidence,
            }
        )

    if (
        observation.wind_speed is not None
        and observation.wind_speed >= WIND_SPEED_THRESHOLD
    ):
        confidence = min(
            Decimal("0.99"),
            Decimal("0.60") + (observation.wind_speed / Decimal("100")),
        )

        detected_events.append(
            {
                "event_type": "strong_wind",
                "severity": "high",
                "confidence_score": confidence,
            }
        )

    return detected_events


def create_events_from_observation(
    db: Session,
    observation: WeatherObservation,
) -> list[WeatherEvent]:

    detected_events = detect_events(observation)

    created_events = []

    for event_data in detected_events:
        event = WeatherEvent(
            location_id=observation.location_id,
            event_type=event_data["event_type"],
            start_time=observation.observed_at,
            end_time=observation.observed_at,
            severity=event_data["severity"],
            confidence_score=event_data["confidence_score"],
            source=observation.source,
        )

        db.add(event)
        created_events.append(event)

    return created_events