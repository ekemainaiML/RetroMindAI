"""add_enhanced_views_to_intake

Revision ID: 009_add_enhanced_views
Revises: 008_add_oem_model_id_to_intake
Create Date: 2026-06-06 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "009_add_enhanced_views"
down_revision: Union[str, None] = "008_add_oem_model_id_to_intake"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "intake",
        sa.Column("enhanced_views", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("intake", "enhanced_views")
