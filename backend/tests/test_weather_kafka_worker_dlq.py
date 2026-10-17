from unittest.mock import MagicMock, patch

import pytest

from app.services.kafka_consumer import INVALID_MESSAGE_MARKER
from app.services.weather_kafka_worker import run_weather_kafka_worker


def run_worker_with_message(payload):
    db = MagicMock()
    kafka_message = MagicMock()

    patches = [
        patch(
            "app.services.weather_kafka_worker.SessionLocal",
            return_value=db,
        ),
        patch(
            "app.services.weather_kafka_worker.consume_weather_observations",
            return_value=[(payload, kafka_message)],
        ),
    ]
    return db, kafka_message, patches


def test_malformed_payload_is_dead_lettered_before_commit():
    payload = {
        INVALID_MESSAGE_MARKER: {
            "reason": "invalid_json",
            "error": "Malformed JSON",
        }
    }
    db, kafka_message, patches = run_worker_with_message(payload)
    order = []

    with (
        patches[0],
        patches[1],
        patch(
            "app.services.weather_kafka_worker.publish_dead_letter",
            side_effect=lambda **kwargs: order.append("dlq"),
        ) as publish,
        patch(
            "app.services.weather_kafka_worker.commit_weather_message",
            side_effect=lambda msg: order.append("commit"),
        ) as commit,
        patch(
            "app.services.weather_kafka_worker.process_weather_message"
        ) as process,
    ):
        run_weather_kafka_worker()

    assert order == ["dlq", "commit"]
    assert publish.call_args.kwargs["reason"] == "invalid_json"
    assert commit.call_count == 1
    process.assert_not_called()
    db.close.assert_called_once()


def test_invalid_weather_fields_are_dead_lettered_before_commit():
    # Missing required fields causes the real processor to return
    # validation_failed without querying or modifying the database.
    payload = {"source": "OPEN_METEO"}
    db, kafka_message, patches = run_worker_with_message(payload)
    order = []

    with (
        patches[0],
        patches[1],
        patch(
            "app.services.weather_kafka_worker.publish_dead_letter",
            side_effect=lambda **kwargs: order.append("dlq"),
        ) as publish,
        patch(
            "app.services.weather_kafka_worker.commit_weather_message",
            side_effect=lambda msg: order.append("commit"),
        ) as commit,
    ):
        run_weather_kafka_worker()

    assert order == ["dlq", "commit"]
    assert publish.call_args.kwargs["reason"] == "validation_failed"
    assert commit.call_count == 1
    db.query.assert_not_called()
    db.add.assert_not_called()
    db.close.assert_called_once()


def test_dlq_publish_failure_does_not_commit_source_offset():
    payload = {"temperature": 1000}
    db, kafka_message, patches = run_worker_with_message(payload)

    with (
        patches[0],
        patches[1],
        patch(
            "app.services.weather_kafka_worker.process_weather_message",
            return_value={
                "status": "validation_failed",
                "errors": ["invalid temperature"],
            },
        ),
        patch(
            "app.services.weather_kafka_worker.publish_dead_letter",
            side_effect=RuntimeError("DLQ unavailable"),
        ),
        patch(
            "app.services.weather_kafka_worker.commit_weather_message"
        ) as commit,
        pytest.raises(RuntimeError, match="DLQ unavailable"),
    ):
        run_weather_kafka_worker()

    commit.assert_not_called()
    db.rollback.assert_called_once()
    db.close.assert_called_once()
