"""add_oem_model_id_to_intake

Revision ID: 008_add_oem_model_id_to_intake
Revises: 007_add_oem_tables
Create Date: 2026-05-31 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "008_add_oem_model_id_to_intake"
down_revision: Union[str, None] = "007_add_oem_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "intake",
        sa.Column(
            "oem_model_id",
            UUID(as_uuid=True),
            sa.ForeignKey("oem_vehicle_models.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("intake", "oem_model_id")
