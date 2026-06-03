"""add_recommendation_feedback

Revision ID: 005_add_recommendation_feedback
Revises: 004_add_job_trained_on
Create Date: 2026-05-28 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "005_add_recommendation_feedback"
down_revision: Union[str, None] = "004_add_job_trained_on"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recommendation_feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "assessment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state_features", JSONB, nullable=False, default=list),
        sa.Column("action_taken", JSONB, nullable=False, default=dict),
        sa.Column("was_accepted", sa.Boolean, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("recommendation_feedback")
