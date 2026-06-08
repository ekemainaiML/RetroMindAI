"""add_sso_fields

Revision ID: 013_add_sso_fields
Revises: 012_add_billing_and_usage
Create Date: 2026-06-08 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "013_add_sso_fields"
down_revision: Union[str, None] = "012_add_billing_and_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("sso_provider", sa.String(20), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("sso_subject", sa.String(255), nullable=True),
    )
    op.create_index("ix_users_sso", "users", ["sso_provider", "sso_subject"])


def downgrade() -> None:
    op.drop_index("ix_users_sso", table_name="users")
    op.drop_column("users", "sso_subject")
    op.drop_column("users", "sso_provider")
