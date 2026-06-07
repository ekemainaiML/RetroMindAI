"""add_occluded_views_to_intake

Revision ID: 010_add_occluded_views
Revises: 009_add_enhanced_views
Create Date: 2026-06-06 20:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "010_add_occluded_views"
down_revision: Union[str, None] = "009_add_enhanced_views"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "intake",
        sa.Column("occluded_views", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("intake", "occluded_views")
