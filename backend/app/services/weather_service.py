from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.weather_observation import WeatherObservation
from app.schemas.weather_observation import WeatherObservationCreate
from app.services.event_detection_service import (
    create_events_from_observation,
)


def create_weather_observation(
    db: Session,
    data: WeatherObservationCreate,
) -> WeatherObservation:

    observation = WeatherObservation(
        location_id=data.location_id,
        source=data.source,
        observed_at=data.observed_at,
        temperature=data.temperature,
        humidity=data.humidity,
        pressure=data.pressure,
        rainfall=data.rainfall,
        wind_speed=data.wind_speed,
        wind_direction=data.wind_direction,
        visibility=data.visibility,
        weather_condition=data.weather_condition,
        raw_data=data.raw_data,
    )

    db.add(observation)
    db.flush()

    create_events_from_observation(
        db=db,
        observation=observation,
    )

    db.commit()
    db.refresh(observation)

    return observation


def get_weather_observations(
    db: Session,
    location_id: UUID | None = None,
    source: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[WeatherObservation], int]:

    query = db.query(WeatherObservation)

    if location_id is not None:
        query = query.filter(
            WeatherObservation.location_id == location_id
        )

    if source is not None:
        query = query.filter(
            WeatherObservation.source == source
        )

    total = query.count()

    offset = (page - 1) * page_size

    observations = (
        query
        .order_by(WeatherObservation.observed_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return observations, total


def get_weather_observation(
    db: Session,
    observation_id: UUID,
) -> WeatherObservation:

    observation = (
        db.query(WeatherObservation)
        .filter(WeatherObservation.id == observation_id)
        .first()
    )

    if observation is None:
        raise HTTPException(
            status_code=404,
            detail="Weather observation not found",
        )

    return observation