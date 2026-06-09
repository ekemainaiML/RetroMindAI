"""add batch and batch_jobs tables

Revision ID: 018_add_batch_tables
Revises: 017_add_workshop_name_unique
Create Date: 2026-06-09 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "018_add_batch_tables"
down_revision: Union[str, None] = "017_add_workshop_name_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "batches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workshop_id", UUID(as_uuid=True), sa.ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, default="processing"),
        sa.Column("total", sa.Integer(), nullable=False, default=0),
        sa.Column("completed", sa.Integer(), nullable=False, default=0),
        sa.Column("failed", sa.Integer(), nullable=False, default=0),
        sa.Column("avg_feasibility", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "batch_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workshop_id", UUID(as_uuid=True), sa.ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", UUID(as_uuid=True), sa.ForeignKey("batches.id", ondelete="CASCADE"), nullable=True),
        sa.Column("vehicle_name", sa.String(), nullable=False),
        sa.Column("intake_id", UUID(as_uuid=True), sa.ForeignKey("intake.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(), nullable=False, default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("batch_jobs")
    op.drop_table("batches")
