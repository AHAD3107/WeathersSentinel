import json

from confluent_kafka import Consumer


KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
WEATHER_OBSERVATIONS_TOPIC = "weather.observations"


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
    """
    Consume weather messages from Kafka.

    Yields:
        tuple:
            (decoded_message, kafka_message)

    The Kafka message is returned so the worker can
    manually commit the offset only after successful processing.
    """

    try:
        while True:
            message = consumer.poll(1.0)

            if message is None:
                continue

            if message.error():
                raise RuntimeError(
                    f"Kafka consumer error: {message.error()}"
                )

            payload = json.loads(
                message.value().decode("utf-8")
            )

            yield payload, message

    finally:
        consumer.close()


def commit_weather_message(message) -> None:
    """
    Commit a Kafka message offset after successful processing.
    """

    consumer.commit(
        message=message,
        asynchronous=False,
    )