from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.weather_event import (
    WeatherEventCreate,
    WeatherEventListResponse,
    WeatherEventResponse,
)
from app.services.weather_event_service import (
    create_weather_event,
    get_weather_event,
    get_weather_events,
)


router = APIRouter(
    prefix="/api/v1/weather-events",
    tags=["Weather Events"],
)


@router.post(
    "/",
    response_model=WeatherEventResponse,
)
def create_event(
    data: WeatherEventCreate,
    db: Session = Depends(get_db),
):
    return create_weather_event(db, data)


@router.get(
    "/",
    response_model=WeatherEventListResponse,
)
def list_events(
    location_id: UUID | None = Query(default=None),
    event_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    events, total = get_weather_events(
        db=db,
        location_id=location_id,
        event_type=event_type,
        severity=severity,
        page=page,
        page_size=page_size,
    )

    return {
        "items": events,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/{event_id}",
    response_model=WeatherEventResponse,
)
def get_event(
    event_id: UUID,
    db: Session = Depends(get_db),
):
    return get_weather_event(db, event_id)