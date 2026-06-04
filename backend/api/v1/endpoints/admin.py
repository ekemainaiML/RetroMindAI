import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from core.auth import get_admin_user
from core.database import get_db
from core.feature_flags import FeatureFlagStore
from core.models import Intake, Job, User, Workshop
from core.audit import AuditLog

router = APIRouter()


class WorkshopItem(BaseModel):
    id: str
    name: str
    api_key_prefix: str
    is_active: bool
    intake_count: int
    created_at: str
    user_id: str | None = None
    user_email: str | None = None


class WorkshopListResponse(BaseModel):
    workshops: list[WorkshopItem]
    total: int


class UserItem(BaseModel):
    id: str
    email: str
    name: str
    is_active: bool
    workshop_count: int
    created_at: str


class UserListResponse(BaseModel):
    users: list[UserItem]
    total: int


class AuditLogItem(BaseModel):
    id: str
    workshop_id: str | None
    method: str
    path: str
    status_code: str
    duration_ms: str | None
    ip_address: str | None
    created_at: str


class AuditLogResponse(BaseModel):
    logs: list[AuditLogItem]
    total: int


class MetricsResponse(BaseModel):
    total_workshops: int
    total_intakes: int
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    timed_out_jobs: int
    active_jobs: int
    unique_workshops_24h: int


@router.get("/admin/workshops", response_model=WorkshopListResponse)
async def list_workshops(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: str = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    total = db.query(Workshop).count()
    workshops = (
        db.query(Workshop)
        .order_by(desc(Workshop.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for w in workshops:
        intake_count = (
            db.query(Intake)
            .filter(Intake.workshop_id == w.id)
            .count()
        )
        user_email = None
        if w.user_id:
            owner = db.query(User).filter(User.id == w.user_id).first()
            user_email = owner.email if owner else None
        items.append(WorkshopItem(
            id=str(w.id),
            name=w.name,
            api_key_prefix=w.api_key_prefix,
            is_active=w.is_active,
            intake_count=intake_count,
            created_at=w.created_at.isoformat() if w.created_at else "",
            user_id=str(w.user_id) if w.user_id else None,
            user_email=user_email,
        ))

    return WorkshopListResponse(workshops=items, total=total)


@router.get("/admin/users", response_model=UserListResponse)
def list_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: str = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    total = db.query(User).count()
    users = (
        db.query(User)
        .order_by(desc(User.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = []
    for u in users:
        workshop_count = (
            db.query(Workshop).filter(Workshop.user_id == u.id).count()
        )
        items.append(UserItem(
            id=str(u.id),
            email=u.email,
            name=u.name,
            is_active=u.is_active,
            workshop_count=workshop_count,
            created_at=u.created_at.isoformat() if u.created_at else "",
        ))
    return UserListResponse(users=items, total=total)


@router.get("/admin/audit-logs", response_model=AuditLogResponse)
async def list_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    workshop_id: str | None = Query(None),
    method: str | None = Query(None),
    status_code: str | None = Query(None),
    admin: str = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if workshop_id:
        q = q.filter(AuditLog.workshop_id == uuid.UUID(workshop_id))
    if method:
        q = q.filter(AuditLog.method == method.upper())
    if status_code:
        q = q.filter(AuditLog.status_code == status_code)

    total = q.count()
    logs = (
        q.order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        AuditLogItem(
            id=str(log.id),
            workshop_id=str(log.workshop_id) if log.workshop_id else None,
            method=log.method,
            path=log.path,
            status_code=log.status_code,
            duration_ms=log.duration_ms,
            ip_address=log.ip_address,
            created_at=log.created_at.isoformat() if log.created_at else "",
        )
        for log in logs
    ]

    return AuditLogResponse(logs=items, total=total)


@router.get("/admin/metrics", response_model=MetricsResponse)
async def admin_metrics(
    admin: str = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    total_workshops = db.query(Workshop).count()
    total_intakes = db.query(Intake).count()
    total_jobs = db.query(Job).count()
    completed_jobs = db.query(Job).filter(Job.status == "completed").count()
    failed_jobs = db.query(Job).filter(Job.status == "failed").count()
    timed_out_jobs = db.query(Job).filter(Job.status == "timed_out").count()
    active_jobs = db.query(Job).filter(
        Job.status.in_(["queued", "running", "retrying"])
    ).count()

    cutoff = datetime.now(timezone.utc)
    unique_workshops_24h = (
        db.query(Workshop.id)
        .join(Intake, Intake.workshop_id == Workshop.id)
        .filter(Intake.created_at >= cutoff.replace(hour=0, minute=0, second=0, microsecond=0))
        .distinct()
        .count()
    )

    return MetricsResponse(
        total_workshops=total_workshops,
        total_intakes=total_intakes,
        total_jobs=total_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        timed_out_jobs=timed_out_jobs,
        active_jobs=active_jobs,
        unique_workshops_24h=unique_workshops_24h,
    )


class CapabilityItem(BaseModel):
    name: str
    label: str
    description: str
    env_value: bool
    runtime_override: bool | None = Field(None)
    effective: bool
    dep_installed: bool
    dep: str


class CapabilityToggleRequest(BaseModel):
    value: bool


@router.get("/admin/capabilities")
def list_capabilities(
    admin: str = Depends(get_admin_user),
):
    return {"capabilities": FeatureFlagStore.all_flags()}


@router.put("/admin/capabilities/{name}")
def toggle_capability(
    name: str,
    body: CapabilityToggleRequest,
    admin: str = Depends(get_admin_user),
):
    ok = FeatureFlagStore.set_override(name, body.value)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Unknown capability '{name}'")
    return {"name": name, "effective": FeatureFlagStore.get_effective(name)}
