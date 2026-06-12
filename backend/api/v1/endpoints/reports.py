import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_workshop
from core.config import settings
from core.database import get_db
from core.models import Intake, Job

logger = logging.getLogger(__name__)

router = APIRouter()


class ReportSection(BaseModel):
    id: str
    title: str
    content: dict


class ComplianceReport(BaseModel):
    report_id: str
    job_id: str
    intake_id: str
    generated_at: str
    job_status: str
    sections: list[ReportSection]


def _check_all_services() -> dict[str, str]:
    results = {}
    try:
        import psycopg2
        conn = psycopg2.connect(settings.database_url)
        conn.close()
        results["postgres"] = "connected"
    except Exception as e:
        results["postgres"] = f"error: {e}"
    try:
        import redis as redis_lib
        client = redis_lib.from_url(settings.redis_url, socket_connect_timeout=3)
        client.ping()
        client.close()
        results["redis"] = "connected"
    except Exception as e:
        results["redis"] = f"error: {e}"
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        driver.verify_connectivity()
        driver.close()
        results["neo4j"] = "connected"
    except Exception as e:
        results["neo4j"] = f"error: {e}"
    return results


@router.get("/reports/{job_id}", response_model=ComplianceReport)
async def get_report(
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
    if not job.result:
        raise HTTPException(status_code=400, detail="Job has no result to report")

    result = job.result
    intake = db.query(Intake).filter(Intake.id == job.intake_id).first()

    return ComplianceReport(
        report_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"report-{job_id}")),
        job_id=str(job.id),
        intake_id=str(job.intake_id),
        generated_at=datetime.now(timezone.utc).isoformat(),
        job_status=job.status,
        sections=build_report_sections(job, intake, result),
    )


def build_report_sections(job: Job, intake: Intake | None, result: dict) -> list[ReportSection]:
    sections: list[ReportSection] = []

    sections.append(ReportSection(
        id="assessment_metadata",
        title="Assessment Metadata",
        content={
            "job_id": str(job.id),
            "intake_id": str(job.intake_id),
            "workshop_id": str(intake.workshop_id) if intake else "unknown",
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "completed_stages": list(job.completed_stages or []),
        },
    ))

    vc = result.get("vehicle_classification", {})
    sections.append(ReportSection(
        id="vehicle_classification",
        title="Vehicle Classification",
        content={
            "type": vc.get("type", "unknown"),
            "confidence": vc.get("confidence", 0),
            "human_confirmed": vc.get("human_confirmed", False),
            "classifier": vc.get("classifier", "N/A"),
            "alternatives": vc.get("alternatives", []),
            "model_loaded": vc.get("model_loaded", False),
        },
    ))

    REQUIRED_SLOTS = ["left_side_profile", "right_side_profile", "rear_view"]

    view_slots = dict(intake.view_slots) if intake and intake.view_slots else {}
    submitted_views = [k for k, v in view_slots.items() if v is not None]
    missing_views = [s for s in REQUIRED_SLOTS if view_slots.get(s) is None]

    sections.append(ReportSection(
        id="evidence_summary",
        title="Evidence Summary",
        content={
            "views_submitted": submitted_views,
            "all_required_views_submitted": len(missing_views) == 0,
            "quality_scores": dict(intake.quality_scores) if intake and intake.quality_scores else {},
            "missing_views": missing_views,
            "low_quality_views": list(intake.low_quality_views) if intake and intake.low_quality_views else [],
            "swap_suspected": intake.swap_detected if intake else False,
            "attempts": dict(intake.attempts) if intake and intake.attempts else {},
            "occluded_views": list(intake.occluded_views) if intake and intake.occluded_views else [],
            "enhanced_views": list(intake.enhanced_views) if intake and intake.enhanced_views else [],
            "safety_overrides": result.get("safety_overrides", []),
        },
    ))

    ds = result.get("deviation_summary", {})
    dev_result = result.get("deviation_result", {})
    sections.append(ReportSection(
        id="deviation_summary",
        title="Deviation Summary",
        content={
            "anomalies_detected": ds.get("anomalies_detected", 0),
            "severity": ds.get("severity", "low"),
            "top_issues": ds.get("top_issues", []),
            "deviation_score": dev_result.get("deviation_score", 100),
            "deviation_certainty": dev_result.get("deviation_certainty", 0),
            "critical_delamination": dev_result.get("critical_delamination", False),
            "salvage_potential": dev_result.get("salvage_potential", 100),
            "deviations": [
                {
                    "parameter": d.get("parameter"),
                    "estimated": d.get("estimated"),
                    "reference": d.get("reference"),
                    "delta_pct": d.get("delta_pct"),
                    "severity": d.get("severity"),
                }
                for d in (dev_result.get("deviations", []) if dev_result else [])
            ],
        },
    ))

    risk_summary = result.get("risk_summary", {})
    sections.append(ReportSection(
        id="confidence_and_risk",
        title="Confidence & Risk Summary",
        content={
            "assessment_state": result.get("assessment_state", "unknown"),
            "confidence_score": result.get("confidence_score", 0),
            "confidence_factors": result.get("confidence_factors", {}),
            "safety_overrides": result.get("safety_overrides", []),
            "system_risk_state": risk_summary.get("system_risk_state", "normal"),
            "risk_counts": {
                "critical": risk_summary.get("critical_count", 0),
                "high": risk_summary.get("high_count", 0),
                "medium": risk_summary.get("medium_count", 0),
                "low": risk_summary.get("low_count", 0),
            },
            "risk_register": result.get("risks", []),
        },
    ))

    sections.append(ReportSection(
        id="compliance_state",
        title="Compliance State",
        content={
            "compliance_state": result.get("compliance_state", "not_assessed"),
            "needs_confirmation": result.get("needs_confirmation", False),
            "feasibility_score": result.get("feasibility_score", 0),
            "feasibility_label": result.get("feasibility_label", "unknown"),
        },
    ))

    recommendations = result.get("recommendations", [])
    _PRIORITY_MAP = {"high": "essential", "medium": "recommended", "low": "optional"}
    mapped = []
    for r in recommendations:
        entry = dict(r)
        raw = entry.get("priority", "")
        entry["priority"] = _PRIORITY_MAP.get(raw, raw)
        mapped.append(entry)

    sections.append(ReportSection(
        id="recommendations_overview",
        title="Recommendations Overview",
        content={
            "total_recommendations": len(mapped),
            "essential_count": sum(1 for r in mapped if r.get("priority") == "essential"),
            "recommended_count": sum(1 for r in mapped if r.get("priority") == "recommended"),
            "recommendations": [
                {
                    "title": r.get("title"),
                    "priority": r.get("priority"),
                    "category": r.get("category"),
                    "description": r.get("description"),
                    "blocking": r.get("blocking", False),
                    "depends_on": r.get("depends_on", []),
                }
                for r in mapped
            ],
        },
    ))

    sections.append(ReportSection(
        id="battery_placement",
        title="Battery Placement",
        content={
            "battery_recommendations": [
                r for r in recommendations
                if r.get("category") == "battery_placement"
            ],
            "battery_zones": result.get("battery_placement"),
        },
    ))

    sections.append(ReportSection(
        id="wiring_guidance",
        title="Wiring Guidance",
        content={
            "wiring_recommendations": [
                r for r in recommendations
                if r.get("category") in ("electrical", "wiring")
            ],
        },
    ))

    total_cost = result.get("estimated_total_cost_inr", {})
    if isinstance(total_cost, (int, float)):
        cost_low = int(total_cost * 0.85)
        cost_mid = int(total_cost)
        cost_high = int(total_cost * 1.15)
    elif isinstance(total_cost, dict):
        cost_low = total_cost.get("low", total_cost.get("min", 0))  # type: ignore[assignment]
        cost_mid = total_cost.get("mid", total_cost.get("max", 0))  # type: ignore[assignment]
        cost_high = total_cost.get("high", total_cost.get("max", 0))  # type: ignore[assignment]
    else:
        cost_low = cost_mid = cost_high = 0

    sections.append(ReportSection(
        id="cost_estimation",
        title="Cost Estimation",
        content={
            "estimated_total_cost_inr": {
                "low": cost_low,
                "mid": cost_mid,
                "high": cost_high,
            },
            "recommendation_breakdown": [
                {
                    "title": r.get("title"),
                    "cost_estimate": r.get("cost_estimate"),
                }
                for r in recommendations
                if r.get("cost_estimate")
            ],
            "estimated_days": result.get("estimated_days", 0),
        },
    ))

    sections.append(ReportSection(
        id="tooling_and_skills",
        title="Tooling & Skill Requirements",
        content={
            "tooling_required": result.get("tooling_required", []),
            "skill_level_required": result.get("skill_level_required", "intermediate"),
        },
    ))

    sections.append(ReportSection(
        id="digital_twin",
        title="Digital Twin Data",
        content={
            "twin_available": result.get("digital_twin") is not None,
            "dimensions": (result.get("digital_twin") or {}).get("dimensions"),
            "deviations_3d": (result.get("digital_twin") or {}).get("deviations_3d", []),
            "retrofit_components": (result.get("digital_twin") or {}).get("retrofit_components", []),
        },
    ))

    active_degradations = result.get("degradations", [])
    service_status = _check_all_services()
    all_operational = all(s == "connected" for s in service_status.values()) and len(active_degradations) == 0

    sections.append(ReportSection(
        id="infrastructure_degradation",
        title="Infrastructure Degradation",
        content={
            "degradations": active_degradations,
            "has_degradations": not all_operational,
            "service_status": service_status,
            "all_operational": all_operational,
        },
    ))

    similar = result.get("similar_retrofits", [])
    sections.append(ReportSection(
        id="retrofit_dna",
        title="Retrofit DNA Matches",
        content={
            "current_vehicle_type": vc.get("type", "unknown"),
            "current_vehicle_label": vc.get("type", "unknown"),
            "current_intake_id": str(job.intake_id)[:8],
            "matches_found": len(similar),
            "matches": similar,
        },
    ))

    return sections
