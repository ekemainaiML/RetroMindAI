"""add_billing_and_usage

Revision ID: 012_add_billing_and_usage
Revises: 011_add_workspace_roles
Create Date: 2026-06-08 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "012_add_billing_and_usage"
down_revision: Union[str, None] = "011_add_workspace_roles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pricing_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tier", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("price_monthly", sa.Integer(), nullable=False),
        sa.Column("price_yearly", sa.Integer(), nullable=False),
        sa.Column("max_users", sa.Integer(), nullable=True),
        sa.Column("max_assessments", sa.Integer(), nullable=True),
        sa.Column("max_storage_mb", sa.Integer(), nullable=True),
        sa.Column("rate_limit", sa.Integer(), nullable=True),
        sa.Column("features", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "usage_metering",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workshop_id", UUID(as_uuid=True), sa.ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric", sa.String(50), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_usage_metering_lookup", "usage_metering", ["workshop_id", "metric", "recorded_at"])

    op.add_column(
        "workshops",
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
    )
    op.add_column(
        "workshops",
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
    )
    op.add_column(
        "workshops",
        sa.Column("subscription_status", sa.String(), nullable=True, server_default=sa.text("'active'")),
    )
    op.add_column(
        "workshops",
        sa.Column("billing_period_start", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workshops",
        sa.Column("billing_period_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workshops",
        sa.Column("branding", JSONB, nullable=True, server_default=sa.text("'{}'::jsonb")),
    )

    op.execute(
        sa.text("""
            INSERT INTO pricing_plans (id, tier, name, price_monthly, price_yearly, max_users, max_assessments, max_storage_mb, rate_limit, features)
            VALUES
                (gen_random_uuid(), 'free', 'Free', 0, 0, 1, 10, 500, 100, '["basic_assessments", "standard_reports"]'),
                (gen_random_uuid(), 'pro', 'Pro', 2900, 29000, 5, 100, 5000, 500, '["basic_assessments", "advanced_reports", "team_members", "pdf_exports", "email_notifications"]'),
                (gen_random_uuid(), 'enterprise', 'Enterprise', 9900, 99000, NULL, NULL, 50000, 5000, '["unlimited_assessments", "advanced_reports", "team_members", "pdf_exports", "email_notifications", "white_labeling", "api_access", "priority_support", "customer_portal", "batch_operations"]')
        """)
    )


def downgrade() -> None:
    op.drop_table("usage_metering")
    op.drop_table("pricing_plans")
    op.drop_column("workshops", "stripe_customer_id")
    op.drop_column("workshops", "stripe_subscription_id")
    op.drop_column("workshops", "subscription_status")
    op.drop_column("workshops", "billing_period_start")
    op.drop_column("workshops", "billing_period_end")
    op.drop_column("workshops", "branding")
