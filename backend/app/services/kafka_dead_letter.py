import base64
import json
from datetime import datetime, timezone

from confluent_kafka import Producer


KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
WEATHER_DEAD_LETTER_TOPIC = "weather.observations.dlq"

producer = Producer(
    {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "enable.idempotence": True,
        "acks": "all",
    }
)


def publish_dead_letter(
    *,
    message: dict | None,
    errors: list[str],
    kafka_message,
    reason: str,
) -> None:
    """Publish a rejected Kafka message and wait for delivery confirmation."""

    source_topic = kafka_message.topic()
    partition = kafka_message.partition()
    offset = kafka_message.offset()
    raw_value = kafka_message.value()

    record = {
        "dead_lettered_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "errors": errors,
        "original_message": message,
        "source": {
            "topic": source_topic,
            "partition": partition,
            "offset": offset,
        },
    }

    if raw_value is not None:
        record["raw_value_base64"] = base64.b64encode(
            raw_value
        ).decode("ascii")

    delivery_errors = []
    delivery_confirmed = []

    def on_delivery(error, delivered_message):
        if error is not None:
            delivery_errors.append(str(error))
        else:
            delivery_confirmed.append(True)

    # The stable key helps identify repeated DLQ records if a worker
    # crashes after DLQ delivery but before committing the source offset.
    producer.produce(
        topic=WEATHER_DEAD_LETTER_TOPIC,
        key=f"{source_topic}:{partition}:{offset}",
        value=json.dumps(record, ensure_ascii=False),
        on_delivery=on_delivery,
    )

    remaining = producer.flush(10.0)

    if remaining:
        raise TimeoutError(
            f"{remaining} Kafka dead-letter message(s) remain undelivered."
        )

    if delivery_errors:
        raise RuntimeError(
            f"Dead-letter publishing failed: {delivery_errors[0]}"
        )

    if not delivery_confirmed:
        raise RuntimeError(
            "Kafka did not confirm dead-letter message delivery."
        )
