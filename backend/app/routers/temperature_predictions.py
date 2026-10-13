"""API endpoints for temperature predictions and persisted forecasts."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.temperature_forecast import TemperatureForecast
from app.schemas.temperature_prediction import (
    TemperatureForecastResponse,
    TemperaturePredictionRequest,
    TemperaturePredictionResponse,
)
from app.services.temperature_forecast_service import (
    create_temperature_forecast,
)
from app.services.temperature_prediction_service import (
    temperature_prediction_service,
)


router = APIRouter(
    prefix="/api/v1/temperature-predictions",
    tags=["Temperature Predictions"],
)


@router.post("/", response_model=TemperaturePredictionResponse)
def predict_temperature(
    data: TemperaturePredictionRequest,
) -> TemperaturePredictionResponse:
    """Predict temperature from features supplied in the request."""
    try:
        result = temperature_prediction_service.predict(data.model_dump())
        return TemperaturePredictionResponse(**result)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/from-observation/{observation_id}",
    response_model=TemperatureForecastResponse,
    status_code=201,
)
def predict_temperature_from_observation(
    observation_id: UUID,
    db: Session = Depends(get_db),
) -> TemperatureForecastResponse:
    """Generate and persist a forecast from a stored weather observation."""
    return create_temperature_forecast(
        db=db,
        observation_id=observation_id,
    )


@router.get(
    "/forecasts",
    response_model=list[TemperatureForecastResponse],
)
def list_temperature_forecasts(
    location: str | None = Query(default=None, min_length=1, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[TemperatureForecast]:
    """List persisted forecasts, newest first, with optional location filtering."""
    query = db.query(TemperatureForecast)

    if location:
        query = query.filter(
            TemperatureForecast.location.ilike(f"%{location}%")
        )

    offset = (page - 1) * page_size

    return (
        query.order_by(TemperatureForecast.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )


@router.get("/summary")
def get_temperature_forecast_summary(
    db: Session = Depends(get_db),
) -> dict:
    """Return aggregate statistics for forecasts saved in the database."""

    summary = (
        db.query(
            func.count(TemperatureForecast.id).label("total_forecasts"),
            func.avg(
                TemperatureForecast.predicted_temperature_c
            ).label("average_predicted_temperature_c"),
            func.min(
                TemperatureForecast.predicted_temperature_c
            ).label("minimum_predicted_temperature_c"),
            func.max(
                TemperatureForecast.predicted_temperature_c
            ).label("maximum_predicted_temperature_c"),
            func.max(TemperatureForecast.created_at).label(
                "latest_forecast_at"
            ),
        )
        .one()
    )

    model_counts = (
        db.query(
            TemperatureForecast.model_name,
            func.count(TemperatureForecast.id).label("count"),
        )
        .group_by(TemperatureForecast.model_name)
        .order_by(TemperatureForecast.model_name)
        .all()
    )

    return {
        "total_forecasts": summary.total_forecasts,
        "average_predicted_temperature_c": (
            float(summary.average_predicted_temperature_c)
            if summary.average_predicted_temperature_c is not None
            else None
        ),
        "minimum_predicted_temperature_c": (
            float(summary.minimum_predicted_temperature_c)
            if summary.minimum_predicted_temperature_c is not None
            else None
        ),
        "maximum_predicted_temperature_c": (
            float(summary.maximum_predicted_temperature_c)
            if summary.maximum_predicted_temperature_c is not None
            else None
        ),
        "latest_forecast_at": summary.latest_forecast_at,
        "forecasts_by_model": [
            {
                "model_name": row.model_name,
                "count": row.count,
            }
            for row in model_counts
        ],
    }
