import uuid
from datetime import datetime, timezone

import sqlalchemy
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from core.database import Base


VALID_JOB_STATES = {
    "queued", "running", "retrying",
    "completed", "partial_complete", "failed",
    "timed_out", "cancelled", "expired",
}


class PricingPlan(Base):
    __tablename__ = "pricing_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tier = Column(String(20), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    price_monthly = Column(Integer, nullable=False)
    price_yearly = Column(Integer, nullable=False)
    max_users = Column(Integer, nullable=True)
    max_assessments = Column(Integer, nullable=True)
    max_storage_mb = Column(Integer, nullable=True)
    rate_limit = Column(Integer, nullable=True)
    features = Column(JSONB, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    current_workshop_id = Column(UUID(as_uuid=True), ForeignKey("workshops.id", ondelete="SET NULL"), nullable=True)
    sso_provider = Column(String(20), nullable=True)
    sso_subject = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    workshops = relationship("Workshop", back_populates="owner", foreign_keys="Workshop.user_id", cascade="all, delete-orphan")
    workspace_roles = relationship("WorkspaceRole", back_populates="user", foreign_keys="WorkspaceRole.user_id", cascade="all, delete-orphan")


class EmailPreferences(Base):
    __tablename__ = "email_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workshop_id = Column(UUID(as_uuid=True), ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False, unique=True)
    preferences = Column(JSONB, nullable=False, default=dict)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UsageMetering(Base):
    __tablename__ = "usage_metering"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workshop_id = Column(UUID(as_uuid=True), ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False)
    metric = Column(String(50), nullable=False)
    amount = Column(Integer, nullable=False, default=0)
    recorded_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        sqlalchemy.Index("ix_usage_metering_lookup", "workshop_id", "metric", "recorded_at"),
    )


class WorkspaceRole(Base):
    __tablename__ = "workspace_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workshop_id = Column(UUID(as_uuid=True), ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False, default="operator")
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    invited_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        sqlalchemy.UniqueConstraint("user_id", "workshop_id", name="uq_user_workshop"),
    )

    user = relationship("User", back_populates="workspace_roles", foreign_keys=[user_id])
    workshop = relationship("Workshop", back_populates="workspace_roles", foreign_keys=[workshop_id])
    inviter = relationship("User", foreign_keys=[invited_by], remote_side=[User.id])


class Workshop(Base):
    __tablename__ = "workshops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    tier = Column(String, nullable=False, default="standard")
    api_key_hash = Column(String, nullable=False)
    api_key_prefix = Column(String, nullable=False)
    demo_raw_key = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    api_key_expires_at = Column(DateTime(timezone=True), nullable=True)
    api_key_revoked_at = Column(DateTime(timezone=True), nullable=True)
    api_key_ip_allowlist = Column(JSONB, nullable=True, default=[])
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_status = Column(String, nullable=True, default="active")
    billing_period_start = Column(DateTime(timezone=True), nullable=True)
    billing_period_end = Column(DateTime(timezone=True), nullable=True)
    branding = Column(JSONB, nullable=True, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    owner = relationship("User", back_populates="workshops", foreign_keys="Workshop.user_id")
    intakes = relationship("Intake", back_populates="workshop", cascade="all, delete-orphan")
    workspace_roles = relationship("WorkspaceRole", back_populates="workshop", cascade="all, delete-orphan")


class Intake(Base):
    __tablename__ = "intake"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workshop_id = Column(
        UUID(as_uuid=True), ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False
    )
    view_slots = Column(JSONB, nullable=False, default=dict)
    attempts = Column(JSONB, nullable=False, default=dict)
    quality_scores = Column(JSONB, nullable=False, default=dict)
    low_quality_views = Column(JSONB, nullable=False, default=list)
    enhanced_views = Column(JSONB, nullable=False, default=list)
    occluded_views = Column(JSONB, nullable=False, default=list)
    swap_detected = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False, default="validating")
    failure_reason = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    oem_model_id = Column(UUID(as_uuid=True), ForeignKey("oem_vehicle_models.id", ondelete="SET NULL"), nullable=True)

    workshop = relationship("Workshop", back_populates="intakes")
    jobs = relationship("Job", back_populates="intake", cascade="all, delete-orphan")
    oem_model = relationship("OEMVehicleModel")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intake_id = Column(
        UUID(as_uuid=True), ForeignKey("intake.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(String, nullable=False, default="queued")
    current_stage = Column(String, nullable=True)
    progress_pct = Column(Integer, nullable=False, default=0)
    completed_stages = Column(JSONB, nullable=False, default=list)
    missing_stages = Column(JSONB, nullable=False, default=list)
    result = Column(JSONB, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=1)
    timeout_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    last_polled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    trained_on = Column(DateTime(timezone=True), nullable=True)

    intake = relationship("Intake", back_populates="jobs")
    feedbacks = relationship("RecommendationFeedback", back_populates="job", cascade="all, delete-orphan")


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    state_features = Column(JSONB, nullable=False, default=list)
    action_taken = Column(JSONB, nullable=False, default=dict)
    was_accepted = Column(Boolean, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    job = relationship("Job", back_populates="feedbacks")


class OEMManufacturer(Base):
    __tablename__ = "oem_manufacturers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True, index=True)
    country = Column(String, nullable=True)
    founded_year = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    models = relationship("OEMVehicleModel", back_populates="manufacturer", cascade="all, delete-orphan")


class OEMVehicleModel(Base):
    __tablename__ = "oem_vehicle_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manufacturer_id = Column(
        UUID(as_uuid=True), ForeignKey("oem_manufacturers.id", ondelete="CASCADE"), nullable=False
    )
    model_name = Column(String, nullable=False)
    generation = Column(String, nullable=True)
    vehicle_type = Column(String, nullable=False, index=True)
    year_start = Column(Integer, nullable=True)
    year_end = Column(Integer, nullable=True)
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    manufacturer = relationship("OEMManufacturer", back_populates="models")
    specifications = relationship("OEMSpecification", back_populates="vehicle_model", cascade="all, delete-orphan")
    mounting_points = relationship("OEMMountingPoint", back_populates="vehicle_model", cascade="all, delete-orphan")
    routing_paths = relationship("OEMRoutingPath", back_populates="vehicle_model", cascade="all, delete-orphan")


class OEMSpecification(Base):
    __tablename__ = "oem_specifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(
        UUID(as_uuid=True), ForeignKey("oem_vehicle_models.id", ondelete="CASCADE"), nullable=False
    )
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_to = Column(DateTime(timezone=True), nullable=True)
    wheelbase_mm = Column(Integer, nullable=True)
    overall_length_mm = Column(Integer, nullable=True)
    overall_width_mm = Column(Integer, nullable=True)
    overall_height_mm = Column(Integer, nullable=True)
    ground_clearance_mm = Column(Integer, nullable=True)
    cargo_length_mm = Column(Integer, nullable=True)
    cargo_width_mm = Column(Integer, nullable=True)
    kerb_weight_kg = Column(Integer, nullable=True)
    gross_weight_kg = Column(Integer, nullable=True)
    payload_kg = Column(Integer, nullable=True)
    seating_capacity = Column(Integer, nullable=True)
    engine_cc = Column(Integer, nullable=True)
    fuel_type = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    vehicle_model = relationship("OEMVehicleModel", back_populates="specifications")


class OEMMountingPoint(Base):
    __tablename__ = "oem_mounting_points"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(
        UUID(as_uuid=True), ForeignKey("oem_vehicle_models.id", ondelete="CASCADE"), nullable=False
    )
    point_name = Column(String, nullable=False)
    point_type = Column(String, nullable=False, index=True)
    position_x_mm = Column(Integer, nullable=True)
    position_y_mm = Column(Integer, nullable=True)
    position_z_mm = Column(Integer, nullable=True)
    bolt_pattern = Column(String, nullable=True)
    torque_spec_nm = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    vehicle_model = relationship("OEMVehicleModel", back_populates="mounting_points")


class OEMRoutingPath(Base):
    __tablename__ = "oem_routing_paths"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(
        UUID(as_uuid=True), ForeignKey("oem_vehicle_models.id", ondelete="CASCADE"), nullable=False
    )
    path_name = Column(String, nullable=False)
    path_type = Column(String, nullable=False, index=True)
    start_point = Column(String, nullable=True)
    end_point = Column(String, nullable=True)
    length_estimate_mm = Column(Integer, nullable=True)
    constraints = Column(JSONB, nullable=True, default=dict)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    vehicle_model = relationship("OEMVehicleModel", back_populates="routing_paths")
