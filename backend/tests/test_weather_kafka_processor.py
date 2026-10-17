from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.weather_kafka_processor import process_weather_message


def make_message(**overrides):
    message = {
        "location_id": str(uuid4()),
        "source": "OPEN_METEO",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "temperature": 25.0,
        "humidity": 60.0,
        "pressure": 1013.0,
        "rainfall": 0.0,
        "wind_speed": 18.0,
        "wind_direction": 180.0,
    }
    message.update(overrides)
    return message


def test_invalid_temperature_is_rejected_before_database_query():
    db = MagicMock()
    message = make_message(temperature=100.0)

    result = process_weather_message(db=db, message=message)

    assert result["status"] == "validation_failed"
    assert any(
        "temperature must be between -80 and 60" in error
        for error in result["errors"]
    )
    db.query.assert_not_called()
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_open_meteo_wind_speed_is_converted_before_validation():
    db = MagicMock()
    message = make_message(wind_speed=36.0)

    with patch(
        "app.services.weather_kafka_processor.validate_observation",
        return_value=(False, ["test rejection"]),
    ) as mock_validate:
        result = process_weather_message(db=db, message=message)

    assert result["status"] == "validation_failed"

    validated_wind_speed = mock_validate.call_args.kwargs["wind_speed"]
    assert validated_wind_speed == Decimal("10.0")

    db.query.assert_not_called()
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_forecast_failure_does_not_roll_back_observation_or_events():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    message = make_message()

    with (
        patch(
            "app.services.weather_kafka_processor.create_events_from_observation",
            return_value=[],
        ) as mock_events,
        patch(
            "app.services.weather_kafka_processor.temperature_prediction_service.predict",
            side_effect=RuntimeError("simulated forecast failure"),
        ),
    ):
        result = process_weather_message(db=db, message=message)

    assert result["status"] == "processed"
    assert result["prediction_status"] == "failed"
    assert result["prediction_error"] == "simulated forecast failure"

    # The observation is added once; no forecast is added.
    assert db.add.call_count == 1

    # Events are processed once, without a recovery retry.
    mock_events.assert_called_once()

    # A forecast failure must not roll back the outer transaction.
    db.rollback.assert_not_called()
    db.commit.assert_called_once()


def test_duplicate_observation_is_skipped_without_reprocessing():
    db = MagicMock()
    message = make_message()

    existing = MagicMock()
    existing.id = uuid4()

    db.query.return_value.filter.return_value.first.return_value = existing

    with (
        patch(
            "app.services.weather_kafka_processor.create_events_from_observation"
        ) as mock_events,
        patch(
            "app.services.weather_kafka_processor.temperature_prediction_service.predict"
        ) as mock_prediction,
    ):
        result = process_weather_message(db=db, message=message)

    assert result == {
        "status": "duplicate",
        "observation_id": str(existing.id),
    }

    db.add.assert_not_called()
    db.commit.assert_not_called()
    db.begin_nested.assert_not_called()
    mock_events.assert_not_called()
    mock_prediction.assert_not_called()
