from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.weather_event import WeatherEvent
from app.schemas.weather_event import WeatherEventCreate


def create_weather_event(
    db: Session,
    data: WeatherEventCreate,
) -> WeatherEvent:

    event = WeatherEvent(
        location_id=data.location_id,
        event_type=data.event_type,
        start_time=data.start_time,
        end_time=data.end_time,
        severity=data.severity,
        confidence_score=data.confidence_score,
        source=data.source,
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return event


def get_weather_events(
    db: Session,
    location_id: UUID | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[WeatherEvent], int]:

    query = db.query(WeatherEvent)

    if location_id is not None:
        query = query.filter(
            WeatherEvent.location_id == location_id
        )

    if event_type is not None:
        query = query.filter(
            WeatherEvent.event_type == event_type.lower()
        )

    if severity is not None:
        query = query.filter(
            WeatherEvent.severity == severity.lower()
        )

    total = query.count()

    offset = (page - 1) * page_size

    events = (
        query
        .order_by(WeatherEvent.start_time.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return events, total


def get_weather_event(
    db: Session,
    event_id: UUID,
) -> WeatherEvent:

    event = (
        db.query(WeatherEvent)
        .filter(WeatherEvent.id == event_id)
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Weather event not found",
        )

    return event