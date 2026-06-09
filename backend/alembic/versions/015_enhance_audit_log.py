"""enhance_audit_log

Revision ID: 015_enhance_audit_log
Revises: 014_add_email_preferences
Create Date: 2026-06-09 03:52:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "015_enhance_audit_log"
down_revision: Union[str, None] = "014_add_email_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("audit_logs", sa.Column("correlation_id", sa.String(36), nullable=True))
    op.add_column("audit_logs", sa.Column("event_type", sa.String(50), nullable=True))
    op.add_column("audit_logs", sa.Column("resource_type", sa.String(50), nullable=True))
    op.add_column("audit_logs", sa.Column("resource_id", sa.String(36), nullable=True))
    op.add_column("audit_logs", sa.Column("changes", postgresql.JSONB, nullable=True))
    op.add_column("audit_logs", sa.Column("request_body_snippet", sa.Text, nullable=True))
    op.add_column("audit_logs", sa.Column("user_agent", sa.String, nullable=True))
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_resource", table_name="audit_logs")
    op.drop_index("ix_audit_logs_event_type", table_name="audit_logs")
    op.drop_column("audit_logs", "user_agent")
    op.drop_column("audit_logs", "request_body_snippet")
    op.drop_column("audit_logs", "changes")
    op.drop_column("audit_logs", "resource_id")
    op.drop_column("audit_logs", "resource_type")
    op.drop_column("audit_logs", "event_type")
    op.drop_column("audit_logs", "correlation_id")
    op.drop_column("audit_logs", "user_id")
