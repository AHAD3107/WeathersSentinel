from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ALLOWED_VERIFICATION_STATUSES = {
    "pending",
    "likely_valid",
    "uncertain",
    "likely_misleading",
}


class VerificationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_id: UUID
    credibility_score: Decimal = Field(
        ge=0,
        le=1,
    )
    verification_status: str
    supporting_observations: dict | None
    verification_reason: str | None
    model_version: str | None
    created_at: datetime