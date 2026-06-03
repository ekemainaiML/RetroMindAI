import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_workshop
from core.database import get_db
from core.models import Intake, Job

router = APIRouter()


class ComparisonJob(BaseModel):
    job_id: str
    vehicle_type: str
    confidence_score: float
    compliance_state: str
    feasibility_score: float
    feasibility_label: str
    deviation_score: float
    deviation_certainty: float
    salvage_potential: float
    risk_counts: dict[str, int]
    system_risk_state: str
    top_issues: list[str]
    recommendation_count: int
    degradation_count: int


class ComparisonResponse(BaseModel):
    jobs: list[ComparisonJob]


def _pick(d: dict | None, key: str, default=0):
    if not d:
        return default
    return d.get(key, default)


@router.get("/comparison", response_model=ComparisonResponse)
async def compare_jobs(
    job_ids: str = Query(..., description="Comma-separated job UUIDs"),
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    ids = [UUID(s.strip()) for s in job_ids.split(",") if s.strip()]
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 job IDs")
    if len(ids) > 6:
        raise HTTPException(status_code=400, detail="Maximum 6 jobs for comparison")

    workshop_uuid = uuid.UUID(workshop_id)
    jobs: list[Job] = (
        db.query(Job)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(
            Job.id.in_(ids),
            Job.result.isnot(None),
            Intake.workshop_id == workshop_uuid,
        )
        .all()
    )

    if len(jobs) < 2:
        raise HTTPException(status_code=400, detail="At least 2 jobs with results required")

    result: list[ComparisonJob] = []
    for job in jobs:
        r = job.result or {}
        vc = r.get("vehicle_classification", {}) or {}
        risks = r.get("risk_summary", {}) or {}
        dev = r.get("deviation_result", {}) or {}
        ds = r.get("deviation_summary", {}) or {}
        recs = r.get("recommendations", []) or []
        degs = r.get("degradations", []) or []

        result.append(ComparisonJob(
            job_id=str(job.id),
            vehicle_type=vc.get("type", "unknown"),
            confidence_score=r.get("confidence_score", 0),
            compliance_state=r.get("compliance_state", "not_assessed"),
            feasibility_score=r.get("feasibility_score", 0),
            feasibility_label=r.get("feasibility_label", "unknown"),
            deviation_score=dev.get("deviation_score", 100),
            deviation_certainty=dev.get("deviation_certainty", 0),
            salvage_potential=dev.get("salvage_potential", 100),
            risk_counts={
                "critical": risks.get("critical_count", 0),
                "high": risks.get("high_count", 0),
                "medium": risks.get("medium_count", 0),
                "low": risks.get("low_count", 0),
            },
            system_risk_state=risks.get("system_risk_state", "normal"),
            top_issues=ds.get("top_issues", [])[:3],
            recommendation_count=len(recs),
            degradation_count=len(degs),
        ))

    return ComparisonResponse(jobs=result)
