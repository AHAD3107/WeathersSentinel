from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WeatherObservationCreate(BaseModel):
    location_id: UUID
    source: str = Field(min_length=1, max_length=50)
    observed_at: datetime

    temperature: Decimal | None = None

    humidity: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    pressure: Decimal | None = None

    rainfall: Decimal | None = Field(
        default=None,
        ge=0,
    )

    wind_speed: Decimal | None = Field(
        default=None,
        ge=0,
    )

    wind_direction: Decimal | None = Field(
        default=None,
        ge=0,
        le=360,
    )

    visibility: Decimal | None = Field(
        default=None,
        ge=0,
    )

    weather_condition: str | None = Field(
        default=None,
        max_length=50,
    )

    raw_data: dict | None = None

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        return value.strip()

    @field_validator("weather_condition")
    @classmethod
    def validate_weather_condition(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value if value else None


class WeatherObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_id: UUID
    source: str
    observed_at: datetime

    temperature: Decimal | None = None
    humidity: Decimal | None = None
    pressure: Decimal | None = None
    rainfall: Decimal | None = None
    wind_speed: Decimal | None = None
    wind_direction: Decimal | None = None
    visibility: Decimal | None = None

    weather_condition: str | None = None
    raw_data: dict | None = None

    created_at: datetime


class WeatherObservationListResponse(BaseModel):
    items: list[WeatherObservationResponse]
    total: int
    page: int
    page_size: int