"""initial_schema

Revision ID: 001_initial
Revises:
Create Date: 2026-05-27 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workshops",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("api_key_hash", sa.String(), nullable=False),
        sa.Column("api_key_prefix", sa.String(), nullable=False),
        sa.Column("demo_raw_key", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "intake",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workshop_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workshops.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("view_slots", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("attempts", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("quality_scores", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("low_quality_views", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("swap_detected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'validating'")),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "intake_id",
            UUID(as_uuid=True),
            sa.ForeignKey("intake.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("current_stage", sa.String(), nullable=True),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completed_stages", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("missing_stages", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("timeout_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_jobs_intake_id", "jobs", ["intake_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_intake_workshop_id", "intake", ["workshop_id"])
    op.create_index("ix_intake_status", "intake", ["status"])


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_table("intake")
    op.drop_table("workshops")
