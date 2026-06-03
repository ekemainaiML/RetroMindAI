"""add_oem_tables

Revision ID: 007_add_oem_tables
Revises: 006_add_users
Create Date: 2026-05-31 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "007_add_oem_tables"
down_revision: Union[str, None] = "006_add_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oem_manufacturers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String, nullable=False, unique=True, index=True),
        sa.Column("country", sa.String, nullable=True),
        sa.Column("founded_year", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "oem_vehicle_models",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            UUID(as_uuid=True),
            sa.ForeignKey("oem_manufacturers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_name", sa.String, nullable=False),
        sa.Column("generation", sa.String, nullable=True),
        sa.Column("vehicle_type", sa.String, nullable=False, index=True),
        sa.Column("year_start", sa.Integer, nullable=True),
        sa.Column("year_end", sa.Integer, nullable=True),
        sa.Column("image_url", sa.String, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "oem_specifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_id",
            UUID(as_uuid=True),
            sa.ForeignKey("oem_vehicle_models.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wheelbase_mm", sa.Integer, nullable=True),
        sa.Column("overall_length_mm", sa.Integer, nullable=True),
        sa.Column("overall_width_mm", sa.Integer, nullable=True),
        sa.Column("overall_height_mm", sa.Integer, nullable=True),
        sa.Column("ground_clearance_mm", sa.Integer, nullable=True),
        sa.Column("cargo_length_mm", sa.Integer, nullable=True),
        sa.Column("cargo_width_mm", sa.Integer, nullable=True),
        sa.Column("kerb_weight_kg", sa.Integer, nullable=True),
        sa.Column("gross_weight_kg", sa.Integer, nullable=True),
        sa.Column("payload_kg", sa.Integer, nullable=True),
        sa.Column("seating_capacity", sa.Integer, nullable=True),
        sa.Column("engine_cc", sa.Integer, nullable=True),
        sa.Column("fuel_type", sa.String, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "oem_mounting_points",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_id",
            UUID(as_uuid=True),
            sa.ForeignKey("oem_vehicle_models.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("point_name", sa.String, nullable=False),
        sa.Column("point_type", sa.String, nullable=False, index=True),
        sa.Column("position_x_mm", sa.Integer, nullable=True),
        sa.Column("position_y_mm", sa.Integer, nullable=True),
        sa.Column("position_z_mm", sa.Integer, nullable=True),
        sa.Column("bolt_pattern", sa.String, nullable=True),
        sa.Column("torque_spec_nm", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "oem_routing_paths",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_id",
            UUID(as_uuid=True),
            sa.ForeignKey("oem_vehicle_models.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path_name", sa.String, nullable=False),
        sa.Column("path_type", sa.String, nullable=False, index=True),
        sa.Column("start_point", sa.String, nullable=True),
        sa.Column("end_point", sa.String, nullable=True),
        sa.Column("length_estimate_mm", sa.Integer, nullable=True),
        sa.Column("constraints", JSONB, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("oem_routing_paths")
    op.drop_table("oem_mounting_points")
    op.drop_table("oem_specifications")
    op.drop_table("oem_vehicle_models")
    op.drop_table("oem_manufacturers")
