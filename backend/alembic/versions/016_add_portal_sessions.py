"""add_portal_sessions

Revision ID: 016_add_portal_sessions
Revises: 015_enhance_audit_log
Create Date: 2026-06-09 04:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "016_add_portal_sessions"
down_revision: Union[str, None] = "015_enhance_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "portal_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workshop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String, nullable=False, unique=True),
        sa.Column("customer_email", sa.String, nullable=False),
        sa.Column("customer_name", sa.String, nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_portal_sessions_token", "portal_sessions", ["token"])
    op.create_index("ix_portal_sessions_job", "portal_sessions", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_portal_sessions_job", table_name="portal_sessions")
    op.drop_index("ix_portal_sessions_token", table_name="portal_sessions")
    op.drop_table("portal_sessions")
