import json
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_workshop
from core.config import settings
from core.database import get_db
from core.models import Intake, Job

router = APIRouter()

CACHE_TTL = 3600


class MonthlyStat(BaseModel):
    month: str
    total_jobs: int
    completed: int
    partial_complete: int
    failed: int
    timed_out: int
    avg_confidence: float | None
    avg_processing_sec: float | None


class DeviationTypeCount(BaseModel):
    component: str
    count: int


class WorkshopStatsResponse(BaseModel):
    monthly: list[MonthlyStat]
    total_jobs: int
    total_completed: int
    overall_avg_confidence: float | None
    overall_avg_processing_sec: float | None
    top_deviations: list[DeviationTypeCount]


async def _get_cached_stats(workshop_id: str) -> dict | None:
    try:
        r = aioredis.from_url(settings.redis_url)
        data = await r.get(f"workshop_stats:{workshop_id}")
        await r.aclose()
        if data:
            return json.loads(data)
    except Exception:
        return None
    return None


async def _set_cached_stats(workshop_id: str, data: dict) -> None:
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.setex(f"workshop_stats:{workshop_id}", CACHE_TTL, json.dumps(data, default=str))
        await r.aclose()
    except Exception:
        pass


@router.get("/workshop/stats", response_model=WorkshopStatsResponse)
async def get_workshop_stats(
    months: int = Query(12, ge=1, le=36),
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    cached = await _get_cached_stats(workshop_id)
    if cached:
        return WorkshopStatsResponse(**cached)

    workshop_uuid = uuid.UUID(workshop_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30 * months)

    jobs = (
        db.query(Job)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(
            Intake.workshop_id == workshop_uuid,
            Job.created_at >= cutoff,
        )
        .all()
    )

    monthly_map: dict[str, dict] = {}
    total_jobs = len(jobs)
    total_completed = 0
    confidence_scores: list[float] = []
    processing_times: list[float] = []
    deviation_counter: Counter = Counter()

    for job in jobs:
        created = job.created_at
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        month_key = created.strftime("%Y-%m") if created else "unknown"

        if month_key not in monthly_map:
            monthly_map[month_key] = {
                "total_jobs": 0, "completed": 0, "partial_complete": 0,
                "failed": 0, "timed_out": 0, "confidence_sum": 0.0,
                "confidence_count": 0, "processing_sum": 0.0,
                "processing_count": 0,
            }

        monthly_map[month_key]["total_jobs"] += 1

        if job.status == "completed":
            monthly_map[month_key]["completed"] += 1
            total_completed += 1
        elif job.status == "partial_complete":
            monthly_map[month_key]["partial_complete"] += 1
        elif job.status == "failed":
            monthly_map[month_key]["failed"] += 1
        elif job.status == "timed_out":
            monthly_map[month_key]["timed_out"] += 1

        result = job.result or {}
        cs = result.get("confidence_score")
        if cs is not None:
            val = float(cs)
            monthly_map[month_key]["confidence_sum"] += val
            monthly_map[month_key]["confidence_count"] += 1
            confidence_scores.append(val)

        updated = job.updated_at
        if created and updated:
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            delta = (updated - created).total_seconds()
            if delta >= 0 and job.status in ("completed", "failed", "partial_complete"):
                monthly_map[month_key]["processing_sum"] += delta
                monthly_map[month_key]["processing_count"] += 1
                processing_times.append(delta)

        deviations = result.get("deviations") or []
        for d in deviations:
            component = d.get("component", "unknown")
            deviation_counter[component] += 1

    monthly = []
    for month_key in sorted(monthly_map.keys()):
        m = monthly_map[month_key]
        avg_conf = m["confidence_sum"] / m["confidence_count"] if m["confidence_count"] else None
        avg_proc = m["processing_sum"] / m["processing_count"] if m["processing_count"] else None
        monthly.append(MonthlyStat(
            month=month_key,
            total_jobs=m["total_jobs"],
            completed=m["completed"],
            partial_complete=m["partial_complete"],
            failed=m["failed"],
            timed_out=m["timed_out"],
            avg_confidence=round(avg_conf, 1) if avg_conf is not None else None,
            avg_processing_sec=round(avg_proc, 1) if avg_proc is not None else None,
        ))

    top_deviations = [
        DeviationTypeCount(component=comp, count=cnt)
        for comp, cnt in deviation_counter.most_common(10)
    ]

    overall_avg_conf = (
        round(sum(confidence_scores) / len(confidence_scores), 1)
        if confidence_scores else None
    )
    overall_avg_proc = (
        round(sum(processing_times) / len(processing_times), 1)
        if processing_times else None
    )

    response = WorkshopStatsResponse(
        monthly=monthly,
        total_jobs=total_jobs,
        total_completed=total_completed,
        overall_avg_confidence=overall_avg_conf,
        overall_avg_processing_sec=overall_avg_proc,
        top_deviations=top_deviations,
    )

    await _set_cached_stats(workshop_id, response.model_dump())
    return response
