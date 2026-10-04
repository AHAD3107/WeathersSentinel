from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.weather_observation import (
    WeatherObservationCreate,
    WeatherObservationListResponse,
    WeatherObservationResponse,
)
from app.services.weather_service import (
    create_weather_observation,
    get_weather_observation,
    get_weather_observations,
)


router = APIRouter(
    prefix="/api/v1/weather-observations",
    tags=["Weather Observations"],
)


@router.post(
    "/",
    response_model=WeatherObservationResponse,
)
def create_observation(
    data: WeatherObservationCreate,
    db: Session = Depends(get_db),
):
    return create_weather_observation(db, data)


@router.get(
    "/",
    response_model=WeatherObservationListResponse,
)
def list_observations(
    location_id: UUID | None = Query(default=None),
    source: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    observations, total = get_weather_observations(
        db=db,
        location_id=location_id,
        source=source,
        page=page,
        page_size=page_size,
    )

    return {
        "items": observations,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/{observation_id}",
    response_model=WeatherObservationResponse,
)
def get_observation(
    observation_id: UUID,
    db: Session = Depends(get_db),
):
    return get_weather_observation(db, observation_id)