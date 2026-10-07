from app.database import SessionLocal
from app.services.kafka_consumer import consume_weather_observations
from app.services.weather_kafka_processor import process_weather_message
from app.services.kafka_consumer import (
    consume_weather_observations,
    commit_weather_message,
)


def run_weather_kafka_worker() -> None:
    """
    Continuously consume weather observations from Kafka
    and process them into PostgreSQL.
    """

    print("WeatherSentinel Kafka worker started.")
    print("Listening on topic: weather.observations")

    for message, kafka_message in consume_weather_observations():
        db = SessionLocal()

        try:
            result = process_weather_message(
                db=db,
                message=message,
        )

            print(
            f"Processed weather message: {result}"
            )

            commit_weather_message(kafka_message)

        except Exception as exc:
            db.rollback()

            print(
                f"Error processing weather message: {exc}"
            )

        finally:
            db.close()

if __name__ == "__main__":
    run_weather_kafka_worker()