
"""API endpoints for temperature predictions and persisted forecasts."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
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
