import json

from confluent_kafka import Consumer


KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
WEATHER_OBSERVATIONS_TOPIC = "weather.observations"


consumer = Consumer(
    {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "weathersentinel-consumer",
        "auto.offset.reset": "earliest",
    }
)

consumer.subscribe([WEATHER_OBSERVATIONS_TOPIC])


def consume_weather_observations():
    try:
        while True:
            message = consumer.poll(1.0)

            if message is None:
                continue

            if message.error():
                raise RuntimeError(f"Kafka consumer error: {message.error()}")

            yield json.loads(message.value().decode("utf-8"))

    finally:
        consumer.close()