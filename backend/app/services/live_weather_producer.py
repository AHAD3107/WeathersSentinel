
import argparse
import json
import logging
import os
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from confluent_kafka import Producer
from sqlalchemy import select

from app.database import SessionLocal
from app.models.location import Location


API_URL = "https://api.open-meteo.com/v1/forecast"
KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
)
WEATHER_OBSERVATIONS_TOPIC = "weather.observations"

# Default polling interval: 15 minutes.
POLL_INTERVAL_SECONDS = int(
    os.getenv("WEATHER_POLL_INTERVAL_SECONDS", "900")
)

# Pune, Maharashtra
DEFAULT_LATITUDE = 18.5204
DEFAULT_LONGITUDE = 73.8567
LOCATION_NAME = "Pune"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def describe_weather_code(code: int | None) -> str:
    """Convert a WMO weather code into a readable condition."""
    if code is None:
        return "unknown"
    if code == 0:
        return "clear sky"
    if code in (1, 2, 3):
        return "mainly clear, partly cloudy, or overcast"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57):
        return "drizzle"
    if code in (61, 63, 65, 66, 67):
        return "rain"
    if code in (71, 73, 75, 77):
        return "snow"
    if code in (80, 81, 82):
        return "rain showers"
    if code in (85, 86):
        return "snow showers"
    if code in (95, 96, 99):
        return "thunderstorm"
    return "other weather conditions"


def fetch_current_weather(
    latitude: float = DEFAULT_LATITUDE,
    longitude: float = DEFAULT_LONGITUDE,
) -> dict:
    """Fetch the current weather observation from Open-Meteo."""
    params = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,relative_humidity_2m,precipitation,"
                "rain,weather_code,cloud_cover,pressure_msl,"
                "wind_speed_10m,wind_direction_10m"
            ),
            "timezone": "UTC",
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
        }
    )

    request = Request(
        f"{API_URL}?{params}",
        headers={"User-Agent": "WeatherSentinel/1.0"},
    )

    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"Weather API request failed: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Weather API returned invalid JSON."
        ) from exc

    current = payload.get("current")
    if not isinstance(current, dict) or not current.get("time"):
        raise RuntimeError(
            "Weather API response has no current observation."
        )

    observed_at = datetime.fromisoformat(current["time"])

    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    else:
        observed_at = observed_at.astimezone(timezone.utc)

    weather_code = current.get("weather_code")

    return {
        "source": "OPEN_METEO",
        "observed_at": observed_at.isoformat(),
        "temperature": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "pressure": current.get("pressure_msl"),
        "rainfall": current.get("precipitation"),
        "wind_speed": current.get("wind_speed_10m"),
        "wind_direction": current.get("wind_direction_10m"),
        "weather_condition": describe_weather_code(weather_code),
        "weather_code": weather_code,
        "cloud_cover": current.get("cloud_cover"),
        "latitude": payload.get("latitude", latitude),
        "longitude": payload.get("longitude", longitude),
    }


def find_pune_location_id():
    """Find exactly one database location named Pune."""
    with SessionLocal() as db:
        statement = select(Location).where(
            Location.name == LOCATION_NAME
        )
        locations = list(db.scalars(statement).all())

        if len(locations) != 1:
            raise RuntimeError(
                f"Expected exactly one location named "
                f"'{LOCATION_NAME}', but found {len(locations)}. "
                "Check the locations table before publishing."
            )

        return locations[0].id


def build_message(location_id, weather: dict) -> dict:
    """Build the JSON-compatible Kafka observation."""
    return {
        "source": weather["source"],
        "location_id": str(location_id),
        "observed_at": weather["observed_at"],
        "temperature": weather["temperature"],
        "humidity": weather["humidity"],
        "pressure": weather["pressure"],
        "rainfall": weather["rainfall"],
        "wind_speed": weather["wind_speed"],
        "wind_direction": weather["wind_direction"],
        "weather_condition": weather["weather_condition"],
        "weather_code": weather["weather_code"],
        "cloud_cover": weather["cloud_cover"],
        "latitude": weather["latitude"],
        "longitude": weather["longitude"],
    }


def publish_live_weather() -> None:
    """Fetch one observation and confirm Kafka delivery."""
    location_id = find_pune_location_id()
    weather = fetch_current_weather()
    message = build_message(location_id, weather)

    producer = Producer(
        {"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS}
    )
    delivery_errors = []

    def on_delivery(error, kafka_message):
        if error is not None:
            delivery_errors.append(str(error))
            logger.error("Kafka delivery failed: %s", error)

    try:
        producer.produce(
            WEATHER_OBSERVATIONS_TOPIC,
            key=f"{location_id}:{message['observed_at']}",
            value=json.dumps(message).encode("utf-8"),
            callback=on_delivery,
        )
    except BufferError as exc:
        raise RuntimeError(
            "Kafka producer queue is full; message was not queued."
        ) from exc

    remaining = producer.flush(15)

    if remaining:
        raise RuntimeError(
            f"{remaining} Kafka message(s) remain undelivered "
            "after waiting 15 seconds."
        )

    if delivery_errors:
        raise RuntimeError(
            "Kafka delivery failed: " + "; ".join(delivery_errors)
        )

    logger.info(
        "Observation delivered: source=%s location=%s "
        "temperature=%s C observed_at=%s topic=%s",
        message["source"],
        LOCATION_NAME,
        message["temperature"],
        message["observed_at"],
        WEATHER_OBSERVATIONS_TOPIC,
    )


def run_scheduler() -> None:
    """Publish immediately, then repeat at the configured interval."""
    if POLL_INTERVAL_SECONDS < 60:
        raise ValueError(
            "WEATHER_POLL_INTERVAL_SECONDS must be at least 60."
        )

    logger.info(
        "Starting scheduled weather ingestion: location=%s interval=%s "
        "seconds topic=%s",
        LOCATION_NAME,
        POLL_INTERVAL_SECONDS,
        WEATHER_OBSERVATIONS_TOPIC,
    )

    while True:
        started_at = time.monotonic()

        try:
            publish_live_weather()
        except Exception:
            logger.exception(
                "Weather ingestion cycle failed; will retry next cycle."
            )

        elapsed = time.monotonic() - started_at
        sleep_seconds = max(0, POLL_INTERVAL_SECONDS - elapsed)

        logger.info(
            "Next collection attempt in %.0f seconds.",
            sleep_seconds,
        )
        time.sleep(sleep_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="WeatherSentinel live weather Kafka producer"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Fetch and publish one observation, then exit.",
    )
    args = parser.parse_args()

    try:
        if args.once:
            publish_live_weather()
        else:
            run_scheduler()
    except KeyboardInterrupt:
        logger.info("Shutdown requested. Weather producer stopped.")


if __name__ == "__main__":
    main()
