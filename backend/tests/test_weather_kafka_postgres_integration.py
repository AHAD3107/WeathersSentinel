from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from app.database import SessionLocal
from app.models.location import Location
from app.models.weather_event import WeatherEvent
from app.models.weather_observation import WeatherObservation
from app.models.temperature_forecast import TemperatureForecast
from app.services.weather_kafka_processor import process_weather_message


def test_forecast_database_failure_preserves_observation_and_event():
    db = SessionLocal()

    location_id = uuid4()
    source = "TEST_FORECAST_FAILURE"
    observed_at = datetime.now(timezone.utc)
    observation_ids = []

    try:
        # Create an isolated location for this integration test.
        location = Location(
            id=location_id,
            name=f"Forecast Failure Test {location_id.hex[:8]}",
            district="Test District",
            state="Maharashtra",
            country="India",
            latitude=Decimal("16.700000"),
            longitude=Decimal("74.200000"),
            geometry="SRID=4326;POINT(74.2 16.7)",
        )
        db.add(location)
        db.commit()

        message = {
            "location_id": str(location_id),
            "source": source,
            "observed_at": observed_at.isoformat(),
            "temperature": 25.0,
            "humidity": 60.0,
            "pressure": 1013.0,
            "rainfall": 0.0,
            "wind_speed": 3.0,
            "wind_direction": 180.0,
        }

        # Persist a real event in the outer transaction.
        def create_test_event(*, db, observation):
            event = WeatherEvent(
                location_id=observation.location_id,
                event_type="test_event",
                start_time=observation.observed_at,
                end_time=observation.observed_at,
                severity="low",
                confidence_score=Decimal("0.99"),
                source=source,
            )
            db.add(event)
            return [event]

        # Numeric(5, 2) cannot store 12345.67. PostgreSQL should
        # reject the forecast insert, exercising the nested savepoint.
        invalid_forecast = {
            "model": "integration-test-model",
            "location": "Test Location",
            "forecast_horizon_hours": 3,
            "predicted_temperature_c": "12345.67",
        }

        with (
            patch(
                "app.services.weather_kafka_processor.create_events_from_observation",
                side_effect=create_test_event,
            ),
            patch(
                "app.services.weather_kafka_processor.temperature_prediction_service.predict",
                return_value=invalid_forecast,
            ),
        ):
            result = process_weather_message(db=db, message=message)

        assert result["status"] == "processed"
        assert result["prediction_status"] == "failed"
        assert result["events_detected"] == 1

        observation = (
            db.query(WeatherObservation)
            .filter(
                WeatherObservation.location_id == location_id,
                WeatherObservation.source == source,
                WeatherObservation.observed_at == observed_at,
            )
            .first()
        )

        assert observation is not None
        observation_ids.append(observation.id)

        stored_event = (
            db.query(WeatherEvent)
            .filter(
                WeatherEvent.location_id == location_id,
                WeatherEvent.source == source,
            )
            .first()
        )
        assert stored_event is not None

        stored_forecast = (
            db.query(TemperatureForecast)
            .filter(
                TemperatureForecast.observation_id == observation.id
            )
            .first()
        )
        assert stored_forecast is None

    finally:
        # Delete only records created for this test.
        db.rollback()

        existing_ids = [
            row[0]
            for row in db.query(WeatherObservation.id)
            .filter(
                WeatherObservation.location_id == location_id,
                WeatherObservation.source == source,
            )
            .all()
        ]

        if existing_ids:
            db.query(TemperatureForecast).filter(
                TemperatureForecast.observation_id.in_(existing_ids)
            ).delete(synchronize_session=False)

        db.query(WeatherEvent).filter(
            WeatherEvent.location_id == location_id,
            WeatherEvent.source == source,
        ).delete(synchronize_session=False)

        db.query(WeatherObservation).filter(
            WeatherObservation.location_id == location_id,
            WeatherObservation.source == source,
        ).delete(synchronize_session=False)

        db.query(Location).filter(
            Location.id == location_id
        ).delete(synchronize_session=False)

        db.commit()
        db.close()
