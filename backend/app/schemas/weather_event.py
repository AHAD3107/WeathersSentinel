from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ALLOWED_EVENT_TYPES = {
    "rainfall",
    "thunderstorm",
    "flooding",
    "heatwave",
    "fog",
    "dust_storm",
    "strong_wind",
    "other",
}

ALLOWED_SEVERITIES = {
    "low",
    "medium",
    "high",
    "extreme",
}


class WeatherEventCreate(BaseModel):
    location_id: UUID

    event_type: str = Field(
        min_length=1,
        max_length=30,
    )

    start_time: datetime

    end_time: datetime | None = None

    severity: str = Field(
        min_length=1,
        max_length=20,
    )

    confidence_score: Decimal = Field(
        ge=0,
        le=1,
        max_digits=3,
        decimal_places=2,
    )

    source: str = Field(
        min_length=1,
        max_length=50,
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        value = value.strip().lower()

        if value not in ALLOWED_EVENT_TYPES:
            raise ValueError(
                f"Invalid event_type. Allowed values: "
                f"{', '.join(sorted(ALLOWED_EVENT_TYPES))}"
            )

        return value

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        value = value.strip().lower()

        if value not in ALLOWED_SEVERITIES:
            raise ValueError(
                f"Invalid severity. Allowed values: "
                f"{', '.join(sorted(ALLOWED_SEVERITIES))}"
            )

        return value

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Source cannot be empty")

        return value

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_time is not None:
            if self.end_time < self.start_time:
                raise ValueError(
                    "end_time cannot be earlier than start_time"
                )

        return self


class WeatherEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_id: UUID

    event_type: str

    start_time: datetime
    end_time: datetime | None

    severity: str
    confidence_score: Decimal

    source: str
    created_at: datetime


class WeatherEventListResponse(BaseModel):
    items: list[WeatherEventResponse]

    total: int
    page: int
    page_size: int