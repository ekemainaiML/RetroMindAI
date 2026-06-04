import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.audit import AuditLog
from core.auth import get_current_workshop
from core.database import get_db
from core.models import Intake, Job

router = APIRouter()


class RouteTelemetry(BaseModel):
    method: str
    path: str
    request_count: int
    avg_duration_ms: float | None


class Telemetry(BaseModel):
    total_requests: int
    overall_avg_duration_ms: float | None
    route_breakdown: list[RouteTelemetry]


class JobResponseV2(BaseModel):
    job_id: str
    status: str
    current_stage: str | None = None
    progress_pct: int = 0
    assessment_state: str | None = None
    completed_stages: list[str] = []
    missing_stages: list[str] = []
    result: dict | None = None
    retry_count: int = 0
    retry_available: bool = False
    error_message: str | None = None
    timed_out: bool = False
    infrastructure_degradation: list[dict] = []
    created_at: str | None = None
    updated_at: str | None = None
    telemetry: Telemetry | None = None


@router.get("/jobs/{job_id}", response_model=JobResponseV2)
async def get_job_v2(
    job_id: uuid.UUID,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(Job.id == job_id, Intake.workshop_id == uuid.UUID(workshop_id))
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    assessment_state = None
    degradation: list[dict] = []
    result = job.result
    if result:
        assessment_state = result.get("assessment_state")
        degradation = result.get("degradations") or []


    telemetry = None
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        workshop_uuid = uuid.UUID(workshop_id)

        total_req = (
            db.query(func.count(AuditLog.id))
            .filter(
                AuditLog.workshop_id == workshop_uuid,
                AuditLog.created_at >= cutoff,
            )
            .scalar()
        )

        avg_dur = (
            db.query(func.avg(AuditLog.duration_ms.cast(func.float)))
            .filter(
                AuditLog.workshop_id == workshop_uuid,
                AuditLog.created_at >= cutoff,
                AuditLog.duration_ms.isnot(None),
            )
            .scalar()
        )

        routes = (
            db.query(
                AuditLog.method,
                AuditLog.path,
                func.count().label("request_count"),
                func.avg(AuditLog.duration_ms.cast(func.float)).label("avg_duration_ms"),
            )
            .filter(
                AuditLog.workshop_id == workshop_uuid,
                AuditLog.created_at >= cutoff,
            )
            .group_by(AuditLog.method, AuditLog.path)
            .order_by(func.count().desc())
            .limit(10)
            .all()
        )

        telemetry = Telemetry(
            total_requests=total_req or 0,
            overall_avg_duration_ms=round(float(avg_dur), 1) if avg_dur is not None else None,
            route_breakdown=[
                RouteTelemetry(
                    method=r.method,
                    path=r.path,
                    request_count=r.request_count,
                    avg_duration_ms=round(float(r.avg_duration_ms), 1) if r.avg_duration_ms is not None else None,
                )
                for r in routes
            ],
        )
    except Exception:
        telemetry = None

    return JobResponseV2(
        job_id=str(job.id),
        status=job.status,
        current_stage=job.current_stage,
        progress_pct=job.progress_pct,
        assessment_state=assessment_state,
        completed_stages=job.completed_stages or [],
        missing_stages=job.missing_stages or [],
        result=result,
        retry_count=job.retry_count,
        retry_available=job.retry_count < (job.max_retries or 1),
        error_message=job.error_message,
        timed_out=job.status == "timed_out",
        infrastructure_degradation=degradation,
        created_at=job.created_at.isoformat() if job.created_at else None,
        updated_at=job.updated_at.isoformat() if job.updated_at else None,
        telemetry=telemetry,
    )
