"""add_job_trained_on

Revision ID: 004_add_job_trained_on
Revises: 003_add_workshop_email_tier
Create Date: 2026-05-28 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_add_job_trained_on"
down_revision: Union[str, None] = "003_add_workshop_email_tier"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("trained_on", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "trained_on")
