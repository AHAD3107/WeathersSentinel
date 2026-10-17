import json

from confluent_kafka import Consumer


KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
WEATHER_OBSERVATIONS_TOPIC = "weather.observations"

INVALID_MESSAGE_MARKER = "__weathersentinel_invalid_message__"


consumer = Consumer(
    {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "weathersentinel-consumer",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    }
)

consumer.subscribe([WEATHER_OBSERVATIONS_TOPIC])


def consume_weather_observations():
    """Yield a decoded payload and its original Kafka message."""

    try:
        while True:
            kafka_message = consumer.poll(1.0)

            if kafka_message is None:
                continue

            if kafka_message.error():
                raise RuntimeError(
                    f"Kafka consumer error: {kafka_message.error()}"
                )

            raw_value = kafka_message.value()

            if raw_value is None:
                payload = {
                    INVALID_MESSAGE_MARKER: {
                        "reason": "empty_message",
                        "error": "Kafka message has no value.",
                    }
                }
            else:
                try:
                    decoded = json.loads(raw_value.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    payload = {
                        INVALID_MESSAGE_MARKER: {
                            "reason": "invalid_json",
                            "error": str(exc),
                        }
                    }
                else:
                    if isinstance(decoded, dict):
                        payload = decoded
                    else:
                        payload = {
                            INVALID_MESSAGE_MARKER: {
                                "reason": "invalid_json_structure",
                                "error": "JSON payload must be an object.",
                            }
                        }

            yield payload, kafka_message

    finally:
        consumer.close()


def commit_weather_message(message) -> None:
    """Commit a Kafka offset only after processing or DLQ delivery."""

    consumer.commit(
        message=message,
        asynchronous=False,
    )
