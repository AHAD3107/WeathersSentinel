import logging

from app.database import SessionLocal
from app.services.kafka_consumer import (
    INVALID_MESSAGE_MARKER,
    commit_weather_message,
    consume_weather_observations,
)
from app.services.kafka_dead_letter import publish_dead_letter
from app.services.weather_kafka_processor import process_weather_message


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def run_weather_kafka_worker() -> None:
    """Process weather records and route rejected messages to the DLQ."""
    logger.info("WeatherSentinel Kafka worker started.")
    logger.info("Listening on topic: weather.observations")

    for message, kafka_message in consume_weather_observations():
        db = SessionLocal()

        try:
            invalid_details = (
                message.get(INVALID_MESSAGE_MARKER)
                if isinstance(message, dict)
                else None
            )

            if invalid_details is not None:
                reason = invalid_details.get(
                    "reason", "invalid_message"
                )
                errors = [
                    invalid_details.get(
                        "error", "Invalid Kafka message."
                    )
                ]

                publish_dead_letter(
                    message=None,
                    errors=errors,
                    kafka_message=kafka_message,
                    reason=reason,
                )

                logger.warning(
                    "Invalid Kafka payload sent to DLQ: %s",
                    reason,
                )

            else:
                result = process_weather_message(
                    db=db,
                    message=message,
                )
                status = result.get("status")

                if status == "validation_failed":
                    errors = result.get("errors", [])

                    # Publish first. If publishing fails, the original
                    # message must remain uncommitted for retry.
                    publish_dead_letter(
                        message=message,
                        errors=errors,
                        kafka_message=kafka_message,
                        reason="validation_failed",
                    )

                    logger.warning(
                        "Rejected weather message sent to DLQ: %s",
                        errors,
                    )

                elif status == "duplicate":
                    logger.info(
                        "Skipped duplicate observation: %s",
                        result.get("observation_id"),
                    )

                else:
                    logger.info(
                        "Weather message processed: %s",
                        result,
                    )

            # Reached only after normal processing or confirmed DLQ delivery.
            commit_weather_message(kafka_message)

        except Exception:
            db.rollback()
            logger.exception(
                "Message processing failed. Its offset was not "
                "intentionally committed; the worker will stop."
            )
            raise

        finally:
            db.close()


if __name__ == "__main__":
    run_weather_kafka_worker()
