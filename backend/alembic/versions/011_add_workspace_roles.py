"""add_workspace_roles_rbac

Revision ID: 011_add_workspace_roles
Revises: 010_add_occluded_views
Create Date: 2026-06-08 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "011_add_workspace_roles"
down_revision: Union[str, None] = "010_add_occluded_views"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workshop_id", UUID(as_uuid=True), sa.ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default=sa.text("'operator'")),
        sa.Column("invited_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "workshop_id", name="uq_user_workshop"),
    )

    op.add_column(
        "users",
        sa.Column("current_workshop_id", UUID(as_uuid=True), sa.ForeignKey("workshops.id", ondelete="SET NULL"), nullable=True),
    )

    op.add_column(
        "workshops",
        sa.Column("api_key_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workshops",
        sa.Column("api_key_revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workshops",
        sa.Column("api_key_ip_allowlist", JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")),
    )

    op.create_index("ix_workspace_roles_user", "workspace_roles", ["user_id"])
    op.create_index("ix_workspace_roles_workshop", "workspace_roles", ["workshop_id"])


def downgrade() -> None:
    op.drop_table("workspace_roles")
    op.drop_column("users", "current_workshop_id")
    op.drop_column("workshops", "api_key_expires_at")
    op.drop_column("workshops", "api_key_revoked_at")
    op.drop_column("workshops", "api_key_ip_allowlist")
