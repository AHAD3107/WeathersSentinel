
"""Database model for temperature forecasts."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TemperatureForecast(Base):
    __tablename__ = "temperature_forecasts"

    __table_args__ = (
        Index(
            "idx_temperature_forecasts_observation_id",
            "observation_id",
        ),
        Index(
            "idx_temperature_forecasts_created_at",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("weather_observations.id", ondelete="RESTRICT"),
        nullable=False,
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    location: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    forecast_horizon_hours: Mapped[int] = mapped_column(
        nullable=False,
    )

    predicted_temperature_c: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
