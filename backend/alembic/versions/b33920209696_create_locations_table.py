"""create locations table

Revision ID: b33920209696
Revises: 5316e32f592b
Create Date: 2026-09-30 20:19:32.522422
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = "b33920209696"
down_revision: Union[str, Sequence[str], None] = "5316e32f592b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the locations table."""

    op.create_table(
        "locations",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "district",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "state",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "country",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "latitude",
            sa.Numeric(
                precision=9,
                scale=6,
            ),
            nullable=False,
        ),

        sa.Column(
            "longitude",
            sa.Numeric(
                precision=9,
                scale=6,
            ),
            nullable=False,
        ),

        sa.Column(
            "geometry",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeogFromText",
                name="geography",
                nullable=False,
            ),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Remove the locations table."""

    op.drop_table("locations")