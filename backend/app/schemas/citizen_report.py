from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

ALLOWED_STATUSES = {
    "pending",
    "verified",
    "rejected",
    "suspicious",
}


class CitizenReportCreate(BaseModel):
    user_id: UUID
    location_id: UUID
    event_type: str = Field(min_length=1, max_length=30)
    description: str = Field(min_length=5)
    reported_at: datetime
    image_url: str | None = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        value = value.strip().lower()

        if value not in ALLOWED_EVENT_TYPES:
            raise ValueError(
                f"Invalid event type. Allowed values: "
                f"{', '.join(sorted(ALLOWED_EVENT_TYPES))}"
            )

        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Description cannot be empty")

        return value


class CitizenReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    location_id: UUID
    event_type: str
    description: str
    reported_at: datetime
    image_url: str | None
    status: str
    created_at: datetime


class CitizenReportListResponse(BaseModel):
    items: list[CitizenReportResponse]
    total: int
    page: int
    page_size: int