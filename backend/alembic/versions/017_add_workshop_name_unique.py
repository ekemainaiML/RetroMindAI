"""add workshop name unique constraint

Revision ID: 017
Revises: 016_add_portal_sessions
Create Date: 2026-06-09 05:40:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "017_add_workshop_name_unique"
down_revision: Union[str, None] = "016_add_portal_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_workshops_name", "workshops", ["name"])


def downgrade() -> None:
    op.drop_constraint("uq_workshops_name", "workshops", type_="unique")
