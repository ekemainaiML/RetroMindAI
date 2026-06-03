"""add_workshop_email_tier

Revision ID: 003_add_workshop_email_tier
Revises: 002_add_audit_logs
Create Date: 2026-05-28 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_add_workshop_email_tier"
down_revision: Union[str, None] = "002_add_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workshops", sa.Column("email", sa.String(), nullable=True))
    op.add_column("workshops", sa.Column("tier", sa.String(), nullable=False, server_default=sa.text("'standard'")))


def downgrade() -> None:
    op.drop_column("workshops", "tier")
    op.drop_column("workshops", "email")
