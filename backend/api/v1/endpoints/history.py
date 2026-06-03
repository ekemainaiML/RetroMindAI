import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from core.auth import get_current_workshop
from core.database import get_db
from core.models import Intake, Job

router = APIRouter()


class HistoryItem(BaseModel):
    job_id: str
    intake_id: str
    workshop_id: str
    status: str
    vehicle_type: str | None
    compliance_state: str | None
    confidence_score: int | None
    feasibility_label: str | None
    view_count: int
    created_at: str
    updated_at: str


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    workshop_uuid = uuid.UUID(workshop_id)
    query = (
        db.query(Job)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(Intake.workshop_id == workshop_uuid)
        .order_by(desc(Job.updated_at))
        .offset(offset)
        .limit(limit)
    )
    jobs = query.all()

    total = (
        db.query(Job)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(Intake.workshop_id == workshop_uuid)
        .count()
    )

    items: list[HistoryItem] = []
    for job in jobs:
        intake = db.query(Intake).filter(Intake.id == job.intake_id).first()
        result = job.result or {}
        vc = result.get("vehicle_classification", {}) or {}

        items.append(HistoryItem(
            job_id=str(job.id),
            intake_id=str(job.intake_id),
            workshop_id=str(intake.workshop_id) if intake else "unknown",
            status=job.status,
            vehicle_type=vc.get("type"),
            compliance_state=result.get("compliance_state"),
            confidence_score=result.get("confidence_score"),
            feasibility_label=result.get("feasibility_label"),
            view_count=len(intake.view_slots) if intake else 0,
            created_at=job.created_at.isoformat() if job.created_at else "",
            updated_at=job.updated_at.isoformat() if job.updated_at else "",
        ))

    return HistoryResponse(items=items, total=total)
