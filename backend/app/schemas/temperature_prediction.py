"""Schemas for three-hour temperature prediction."""

from pydantic import BaseModel, ConfigDict, Field

from datetime import datetime
from decimal import Decimal
from uuid import UUID



class TemperaturePredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temperature_c: float = Field(description="Current temperature in Celsius")
    dew_point_c: float | None = None
    pressure_hpa: float | None = None
    wind_speed_ms: float | None = None
    wind_direction: float | None = None
    hour: int = Field(ge=0, le=23)
    day_of_week: int = Field(ge=0, le=6)
    month: int = Field(ge=1, le=12)


class TemperaturePredictionResponse(BaseModel):
    model: str
    location: str
    forecast_horizon_hours: int
    predicted_temperature_c: float

class TemperatureForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    observation_id: UUID
    model_name: str
    location: str
    forecast_horizon_hours: int
    predicted_temperature_c: Decimal
    created_at: datetime

