import json
from uuid import UUID

from confluent_kafka import Producer

from app.services.weather_ingestion_service import parse_noaa_isd_lite_line


KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
WEATHER_OBSERVATIONS_TOPIC = "weather.observations"


producer = Producer(
    {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
    }
)


def publish_noaa_observation(
    line: str,
    location_id: UUID | str,
) -> bool:
    """
    Parse one NOAA ISD-Lite record and publish it to Kafka.
    """

    parsed = parse_noaa_isd_lite_line(line)

    if parsed is None:
        return False

    message = {
        "source": "NOAA_ISD_LITE",
        "location_id": str(location_id),
        "observed_at": parsed["observed_at"].isoformat(),
        "temperature": (
            str(parsed["temperature"])
            if parsed["temperature"] is not None
            else None
        ),
        "dew_point": (
            str(parsed["dew_point"])
            if parsed["dew_point"] is not None
            else None
        ),
        "pressure": (
            str(parsed["pressure"])
            if parsed["pressure"] is not None
            else None
        ),
        "wind_direction": (
            str(parsed["wind_direction"])
            if parsed["wind_direction"] is not None
            else None
        ),
        "wind_speed": (
            str(parsed["wind_speed"])
            if parsed["wind_speed"] is not None
            else None
        ),
        "cloud_cover": (
            str(parsed["cloud_cover"])
            if parsed["cloud_cover"] is not None
            else None
        ),
        "rainfall": (
            str(parsed["rainfall"])
            if parsed["rainfall"] is not None
            else None
        ),
        "precipitation_6h": (
            str(parsed["precipitation_6h"])
            if parsed["precipitation_6h"] is not None
            else None
        ),
    }

    producer.produce(
        WEATHER_OBSERVATIONS_TOPIC,
        value=json.dumps(message).encode("utf-8"),
    )

    producer.flush()

    return True