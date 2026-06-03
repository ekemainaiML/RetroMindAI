import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from api.v1.models.intake import ConfirmRequest, JobResponse
from core.auth import get_current_workshop
from core.confidence import ConfidenceEngine
from core.config import settings
from core.database import get_db
from core.models import Intake, Job

router = APIRouter()


def _dt_iso(val):
    if isinstance(val, datetime):
        return val.isoformat()
    return None


TERMINAL_STATUSES = {
    "completed",
    "partial_complete",
    "failed",
    "timed_out",
    "cancelled",
    "expired",
}

EXPIRY_SECONDS = 1800

SUPPORTED_CONFIRM_TYPES = {"vehicle_classification"}


def _try_get_cached_job(job_id: uuid.UUID, workshop_id: str) -> dict | None:
    if settings.poll_cache_ttl <= 0:
        return None
    try:
        from redis import Redis
        r = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        key = f"job_cache:{job_id}:{workshop_id}"
        cached = r.get(key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    return None


def _try_set_job_cache(job_id: uuid.UUID, workshop_id: str, data: dict) -> None:
    if settings.poll_cache_ttl <= 0:
        return
    try:
        from redis import Redis
        r = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        key = f"job_cache:{job_id}:{workshop_id}"
        r.setex(key, settings.poll_cache_ttl, json.dumps(data, default=str))
    except Exception:
        pass


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    cached = _try_get_cached_job(job_id, workshop_id)
    if cached is not None:
        return JobResponse(**cached)

    job = (
        db.query(Job)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(Job.id == job_id, Intake.workshop_id == uuid.UUID(workshop_id))
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in TERMINAL_STATUSES and job.updated_at:
        elapsed = (datetime.now(timezone.utc) - job.updated_at).total_seconds()
        if elapsed > EXPIRY_SECONDS and job.status != "expired":
            job.status = "expired"
            job.last_polled_at = datetime.now(timezone.utc)
            db.commit()

    job.last_polled_at = datetime.now(timezone.utc)
    db.commit()

    assessment_state = None
    degradation: list[dict] = []
    if job.result and isinstance(job.result, dict):
        assessment_state = job.result.get("assessment_state")
        degradation = job.result.get("degradations", [])

    response = JobResponse(
        job_id=str(job.id),
        status=job.status,
        current_stage=job.current_stage,
        progress_pct=job.progress_pct,
        assessment_state=assessment_state,
        completed_stages=list(job.completed_stages or []),
        missing_stages=list(job.missing_stages or []),
        result=job.result,
        retry_count=job.retry_count,
        retry_available=bool(
            isinstance(job.max_retries, int)
            and job.retry_count < job.max_retries
        ),
        error_message=job.error_message,
        timed_out=job.status == "timed_out",
        infrastructure_degradation=degradation,
        created_at=_dt_iso(job.created_at),
        updated_at=_dt_iso(job.updated_at),
    )

    if job.status not in ("queued", "running"):
        _try_set_job_cache(job_id, workshop_id, response.model_dump())

    return response


@router.get("/jobs/{job_id}/events")
async def job_events(
    job_id: uuid.UUID,
    request: Request,
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

    intake_id = str(job.intake_id)
    channel = f"job:{intake_id}:events"

    async def event_generator():
        pubsub = None
        try:
            from redis import asyncio as aioredis
            r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
            pubsub = r.pubsub()
            await pubsub.subscribe(channel)

            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(pubsub.get_message(timeout=None), timeout=1.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if message and message["type"] == "message":
                    data = message["data"].decode("utf-8")
                    yield f"data: {data}\n\n"
                    parsed = json.loads(data)
                    if parsed.get("data", {}).get("status") in (
                        "completed", "partial_complete", "failed", "timed_out", "cancelled"
                    ):
                        break
        except Exception:
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': 'SSE connection error'}})}\n\n"
        finally:
            if pubsub:
                await pubsub.unsubscribe(channel)
                await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/jobs/{job_id}/confirm")
async def confirm_job(
    job_id: uuid.UUID,
    body: ConfirmRequest,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    if body.confirmation_type not in SUPPORTED_CONFIRM_TYPES:
        logger.warning("Confirm failed: unsupported confirmation_type '%s'", body.confirmation_type)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported confirmation_type '{body.confirmation_type}'. Supported: {', '.join(sorted(SUPPORTED_CONFIRM_TYPES))}",
        )

    job = (
        db.query(Job)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(Job.id == job_id, Intake.workshop_id == uuid.UUID(workshop_id))
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ("completed", "partial_complete"):
        logger.warning("Confirm failed: job %s status is '%s'", job_id, job.status)
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm job with status '{job.status}'. Must be 'completed' or 'partial_complete'.",
        )

    current_result = job.result
    if not current_result or not isinstance(current_result, dict):
        logger.warning("Confirm failed: job %s has no result dict", job_id)
        raise HTTPException(
            status_code=400,
            detail="Job has no result to confirm.",
        )

    factors = current_result.get("confidence_factors", {}) or {}
    intake_data = {
        "human_confirmed": True,
        "missing_views": [],
        "mandatory_view_quality": {},
        "classification": factors.get("classification", 85),
        "geometry": factors.get("geometry", 70),
    }

    score, state, override_reasons = ConfidenceEngine.compute_with_modifiers(
        factors={k: float(v) for k, v in factors.items()} if factors else {"completeness": 50.0, "quality": 50.0, "visibility": 50.0, "classification": 75.0, "geometry": 60.0, "deviation_certainty": 50.0},
        intake_data=intake_data,
        degradation=[],
    )

    current_result["confidence_score"] = int(round(score))
    current_result["assessment_state"] = state
    current_result["safety_overrides"] = override_reasons

    vc = current_result.setdefault("vehicle_classification", {})
    vc["human_confirmed"] = True
    vc["type"] = body.selection
    raw_old_conf = vc.get("confidence", 0)
    if isinstance(raw_old_conf, (int, float)):
        old_conf = float(raw_old_conf)
    else:
        old_conf = 0.0
    vc["confidence"] = round(max(old_conf, 0.75), 2)

    feasibility_base = max(30, int(round(score)) - 6)
    current_result["feasibility_score"] = feasibility_base
    current_result["feasibility_label"] = (
        "feasible_with_adaptation" if score >= 60 else "conditionally_feasible"
    )

    current_result["needs_confirmation"] = False

    job.result = current_result
    job.updated_at = datetime.now(timezone.utc)
    db.commit()

    degradation = job.result.get("degradations", []) if isinstance(job.result, dict) else []

    return JobResponse(
        job_id=str(job.id),
        status=job.status,
        current_stage=job.current_stage,
        progress_pct=job.progress_pct,
        assessment_state=state,
        completed_stages=list(job.completed_stages or []),
        missing_stages=list(job.missing_stages or []),
        result=job.result,
        retry_count=job.retry_count,
        retry_available=bool(
            isinstance(job.max_retries, int)
            and job.retry_count < job.max_retries
        ),
        error_message=job.error_message,
        timed_out=False,
        infrastructure_degradation=degradation,
        created_at=_dt_iso(job.created_at),
        updated_at=_dt_iso(job.updated_at),
    )
