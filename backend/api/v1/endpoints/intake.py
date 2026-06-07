import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from api.v1.models.intake import (
    AnalyzeResponse,
    IdentifyVehicleResponse,
    IntakeResponse,
    SetOemModelRequest,
    SetOemModelResponse,
    ViewSlotResponse,
)
from core.auth import get_current_workshop
from core.config import settings
from core.database import get_db
from core.degradation import get_degradation_manager
from core.models import Intake, Job
from core.validation import check_swap, compute_blur_score, is_blurry
from ai.classification.preprocess import check_occlusion

from sqlalchemy import func

logger = logging.getLogger(__name__)

router = APIRouter()


def _find_best_image(image_paths: dict[str, str]) -> str | None:
    import os
    for view_name in ["left_side_profile", "right_side_profile", "rear_view"]:
        path = image_paths.get(view_name)
        if path and os.path.isfile(path):
            return path
    for path in image_paths.values():
        if path and os.path.isfile(path):
            return path
    return None

REQUIRED_SLOTS = ["left_side_profile", "right_side_profile", "rear_view"]
OPTIONAL_SLOTS = ["front_view", "engine_bay", "underbody"]
ALL_SLOTS = REQUIRED_SLOTS + OPTIONAL_SLOTS
MAX_ATTEMPTS = 3

UPLOAD_DIR = settings.upload_dir


async def _process_uploaded_file(
    intake_dir: str, slot_name: str, file: UploadFile
) -> Optional[str]:
    ext = os.path.splitext(file.filename or ".jpg")[1]
    file_path = os.path.join(intake_dir, f"{slot_name}{ext}")
    content = await file.read()
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except OSError as e:
        if e.errno == 28:
            raise HTTPException(
                status_code=507,
                detail="Storage is full. Cannot accept uploads at this time.",
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to write file: {e}",
        )
    return file_path


def _compute_quality_scores(
    intake_dir: str, view_slots: dict
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for slot_name, file_path in view_slots.items():
        if file_path and os.path.exists(file_path):
            scores[slot_name] = compute_blur_score(file_path)
        else:
            scores[slot_name] = 0.0
    return scores


def _find_low_quality(scores: dict[str, float | None], view_slots: dict) -> list[str]:
    return [
        s for s, score in scores.items()
        if view_slots.get(s) is not None and score is not None and 0.0 < score < 100.0
    ]


def _update_intake_status(intake: Intake, db: Session):
    attempts = intake.attempts or {}
    view_slots = intake.view_slots or {}

    missing_mandatory = False
    for slot in REQUIRED_SLOTS:
        if view_slots.get(slot) is None:
            if attempts.get(slot, 0) >= MAX_ATTEMPTS:
                intake.status = "failed"
                intake.failure_reason = (
                    f"Mandatory view '{slot}' failed after {MAX_ATTEMPTS} attempts"
                )
                db.commit()
                return
            missing_mandatory = True

    if missing_mandatory:
        intake.status = "validating"
    else:
        intake.status = "ready"

    db.commit()


def _build_intake_response(intake: Intake) -> dict:
    view_slots = intake.view_slots or {}
    missing_views = [s for s in REQUIRED_SLOTS if view_slots.get(s) is None]
    quality_scores = intake.quality_scores or {}
    low_quality = _find_low_quality(quality_scores, view_slots)
    attempts = intake.attempts or {}

    return {
        "intake_id": str(intake.id),
        "status": intake.status,
        "missing_views": missing_views,
        "low_quality_views": low_quality,
        "occluded_views": list(intake.occluded_views) if intake.occluded_views else [],
        "swap_suspected": intake.swap_detected or False,
        "attempts": attempts,
        "quality_scores": quality_scores,
        "failure_reason": intake.failure_reason,
        "oem_model_id": str(intake.oem_model_id) if intake.oem_model_id else None,
    }


@router.post("/intake", status_code=status.HTTP_201_CREATED, response_model=IntakeResponse)
async def create_intake(
    workshop_id: str = Depends(get_current_workshop),
    left_side_profile: UploadFile = File(None),
    right_side_profile: UploadFile = File(None),
    rear_view: UploadFile = File(None),
    front_view: UploadFile = File(None),
    engine_bay: UploadFile = File(None),
    underbody: UploadFile = File(None),
    oem_model_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    oem_model_uuid = None
    if oem_model_id:
        try:
            oem_model_uuid = uuid.UUID(oem_model_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid oem_model_id format")
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = (
        db.query(func.count(Intake.id))
        .filter(
            Intake.workshop_id == uuid.UUID(workshop_id),
            Intake.created_at >= today_start,
        )
        .scalar()
    )
    if today_count >= settings.daily_intake_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily intake limit ({settings.daily_intake_limit}) reached. Try again tomorrow.",
        )

    intake_id = uuid.uuid4()
    intake_dir = os.path.join(UPLOAD_DIR, str(workshop_id), str(intake_id))
    os.makedirs(intake_dir, exist_ok=True)

    slots = {
        "left_side_profile": left_side_profile,
        "right_side_profile": right_side_profile,
        "rear_view": rear_view,
        "front_view": front_view,
        "engine_bay": engine_bay,
        "underbody": underbody,
    }

    view_slots: dict[str, Optional[str]] = {}
    for slot_name, file in slots.items():
        if file:
            view_slots[slot_name] = await _process_uploaded_file(intake_dir, slot_name, file)
        else:
            view_slots[slot_name] = None

    missing_views = [s for s in REQUIRED_SLOTS if view_slots.get(s) is None]

    attempts: dict[str, int] = {}
    for slot_name in ALL_SLOTS:
        if view_slots.get(slot_name) is not None:
            attempts[slot_name] = 1

    quality_scores = _compute_quality_scores(intake_dir, view_slots)
    low_quality = _find_low_quality(quality_scores, view_slots)

    occluded_views: list[str] = []
    for slot_name, path in view_slots.items():
        if path and check_occlusion(path).get("occluded"):
            occluded_views.append(slot_name)

    swap_detected = False
    if view_slots.get("left_side_profile") and view_slots.get("right_side_profile"):
        swap_detected = check_swap(
            view_slots["left_side_profile"], view_slots["right_side_profile"]
        )

    intake_status = "validating"
    if not missing_views:
        intake_status = "ready"

    db_intake = Intake(
        id=intake_id,
        workshop_id=workshop_id,
        view_slots=view_slots,
        attempts=attempts,
        quality_scores=quality_scores,
        low_quality_views=low_quality,
        occluded_views=occluded_views,
        swap_detected=swap_detected,
        status=intake_status,
        oem_model_id=oem_model_uuid,
    )
    db.add(db_intake)
    db.commit()
    db.refresh(db_intake)

    return IntakeResponse(
        intake_id=str(intake_id),
        status=intake_status,
        missing_views=missing_views,
        low_quality_views=low_quality,
        swap_suspected=swap_detected,
        attempts=attempts,
        quality_scores=quality_scores,
        failure_reason=None,
        oem_model_id=str(oem_model_uuid) if oem_model_uuid else None,
    )


@router.get("/intake/{intake_id}", response_model=IntakeResponse)
async def get_intake(
    intake_id: uuid.UUID,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    intake = db.query(Intake).filter(
        Intake.id == intake_id,
        Intake.workshop_id == uuid.UUID(workshop_id),
    ).first()
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")
    return _build_intake_response(intake)


@router.put(
    "/intake/{intake_id}/views/{view_slot}",
    status_code=status.HTTP_200_OK,
    response_model=ViewSlotResponse,
)
async def reupload_view(
    intake_id: uuid.UUID,
    view_slot: str,
    file: UploadFile = File(...),
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    if view_slot not in ALL_SLOTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid view slot '{view_slot}'. Must be one of: {', '.join(ALL_SLOTS)}",
        )

    intake = db.query(Intake).filter(
        Intake.id == intake_id,
        Intake.workshop_id == uuid.UUID(workshop_id),
    ).first()
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")

    if intake.status == "failed":
        raise HTTPException(
            status_code=400,
            detail="Intake has failed. Cannot upload more views.",
        )

    attempts = dict(intake.attempts or {})
    current_attempt = attempts.get(view_slot, 0) + 1

    if view_slot in REQUIRED_SLOTS and current_attempt > MAX_ATTEMPTS:
        intake.status = "failed"
        intake.failure_reason = (
            f"Mandatory view '{view_slot}' failed after {MAX_ATTEMPTS} attempts"
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Max attempts ({MAX_ATTEMPTS}) exceeded for mandatory view '{view_slot}'. Intake has failed.",
        )

    attempts[view_slot] = current_attempt

    active_statuses = ["queued", "running", "retrying"]
    active_jobs = (
        db.query(Job)
        .filter(Job.intake_id == intake_id, Job.status.in_(active_statuses))
        .all()
    )
    for j in active_jobs:
        j.status = "cancelled"
        j.updated_at = datetime.now(timezone.utc)
        logger.warning(
            "Cancelled active job %s due to re-upload of view '%s'",
            j.id, view_slot,
        )

    intake_dir = os.path.join(UPLOAD_DIR, str(workshop_id), str(intake_id))
    os.makedirs(intake_dir, exist_ok=True)

    file_path = await _process_uploaded_file(intake_dir, view_slot, file)

    view_slots = dict(intake.view_slots or {})
    view_slots[view_slot] = file_path

    quality_scores = dict(intake.quality_scores or {})
    quality_scores[view_slot] = compute_blur_score(file_path)  # type: ignore[arg-type]

    low_quality = _find_low_quality(quality_scores, view_slots)
    low_quality_views = list(low_quality)

    occluded_views = list(intake.occluded_views or [])
    if check_occlusion(file_path).get("occluded"):
        if view_slot not in occluded_views:
            occluded_views.append(view_slot)
    else:
        occluded_views = [v for v in occluded_views if v != view_slot]

    swap_detected = intake.swap_detected or False
    if view_slot in ("left_side_profile", "right_side_profile"):
        if view_slots.get("left_side_profile") and view_slots.get("right_side_profile"):
            swap_detected = check_swap(
                view_slots["left_side_profile"], view_slots["right_side_profile"]
            )

    intake.view_slots = view_slots
    intake.attempts = attempts
    intake.quality_scores = quality_scores
    intake.low_quality_views = low_quality_views
    intake.occluded_views = occluded_views
    intake.swap_detected = swap_detected

    failure_reason = None
    if current_attempt >= MAX_ATTEMPTS and view_slot in REQUIRED_SLOTS:
        if is_blurry(file_path):  # type: ignore[arg-type]
            intake.status = "failed"
            failure_reason = (
                f"Mandatory view '{view_slot}' failed after {MAX_ATTEMPTS} attempts"
            )
            intake.failure_reason = failure_reason
            db.commit()
            return ViewSlotResponse(
                intake_id=str(intake_id),
                view_slot=view_slot,
                status="failed",
                attempt=current_attempt,
                blurry=is_blurry(file_path),  # type: ignore[arg-type]
                occluded=view_slot in occluded_views,
                missing_views=[s for s in REQUIRED_SLOTS if view_slots.get(s) is None],
                low_quality_views=low_quality_views,
                swap_suspected=swap_detected,
                attempts=attempts,
                quality_scores=quality_scores,
                failure_reason=failure_reason,
            )

    _update_intake_status(intake, db)
    db.commit()
    db.refresh(intake)

    missing_views = [s for s in REQUIRED_SLOTS if view_slots.get(s) is None]
    blurry = is_blurry(file_path)  # type: ignore[arg-type]

    return ViewSlotResponse(
        intake_id=str(intake_id),
        view_slot=view_slot,
        status=intake.status,
        attempt=current_attempt,
        blurry=blurry,
        occluded=view_slot in occluded_views,
        missing_views=missing_views,
        low_quality_views=low_quality_views,
        swap_suspected=swap_detected,
        attempts=attempts,
        quality_scores=quality_scores,
        failure_reason=intake.failure_reason,
    )


@router.post(
    "/intake/{intake_id}/swap-views",
    status_code=status.HTTP_200_OK,
    response_model=IntakeResponse,
)
async def swap_intake_views(
    intake_id: uuid.UUID,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    intake = db.query(Intake).filter(
        Intake.id == intake_id,
        Intake.workshop_id == uuid.UUID(workshop_id),
    ).first()
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")

    view_slots = dict(intake.view_slots or {})
    quality_scores = dict(intake.quality_scores or {})
    attempts = dict(intake.attempts or {})

    left_path = view_slots.get("left_side_profile")
    right_path = view_slots.get("right_side_profile")

    view_slots["left_side_profile"] = right_path
    view_slots["right_side_profile"] = left_path

    for d in (quality_scores, attempts):
        left_val = d.get("left_side_profile")
        right_val = d.get("right_side_profile")
        d["left_side_profile"] = right_val
        d["right_side_profile"] = left_val

    intake.view_slots = view_slots
    intake.quality_scores = quality_scores
    intake.attempts = attempts
    intake.swap_detected = False

    _update_intake_status(intake, db)
    db.commit()
    db.refresh(intake)

    return _build_intake_response(intake)


@router.post(
    "/intake/{intake_id}/analyze",
    status_code=status.HTTP_201_CREATED,
    response_model=AnalyzeResponse,
)
async def analyze_intake(
    intake_id: uuid.UUID,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    intake = db.query(Intake).filter(
        Intake.id == intake_id,
        Intake.workshop_id == uuid.UUID(workshop_id),
    ).first()
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")

    if intake.status == "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot analyze intake with status '{intake.status}'. Intake has failed.",
        )

    if intake.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot analyze intake with status '{intake.status}'. Must be 'ready'.",
        )

    active_statuses = ["queued", "running", "retrying"]
    existing = (
        db.query(Job, Intake)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(
            Intake.workshop_id == uuid.UUID(workshop_id),
            Job.status.in_(active_statuses),
        )
        .first()
    )
    if existing:
        existing_job, existing_intake = existing
        raise HTTPException(
            status_code=409,
            detail={
                "message": "An assessment is already running for this workshop. Cancel it before starting a new one.",
                "existing_job_id": str(existing_job.id),
                "existing_intake_id": str(existing_intake.id),
            },
        )

    job = Job(
        intake_id=intake_id,
        status="queued",
        current_stage=None,
        progress_pct=0,
        completed_stages=[],
        missing_stages=[],
        result=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from redis import Redis
    from rq import Queue

    from workers.assessment import run_assessment

    try:
        redis_conn = Redis.from_url(settings.redis_url, socket_connect_timeout=3)
        redis_conn.ping()
        queue = Queue("retromind-jobs", connection=redis_conn)
        queue.enqueue(run_assessment, str(intake_id))
    except Exception as e:
        logger.error("Failed to enqueue job for intake %s: %s", intake_id, e)
        job.status = "failed"
        job.error_message = f"Failed to enqueue: {e}"
        db.commit()
        if "redis" not in str(e).lower():
            get_degradation_manager().register("redis", 2, f"Enqueue failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="The analysis queue is temporarily unavailable. Please retry shortly.",
        )

    return AnalyzeResponse(job_id=str(job.id), status="queued")


@router.post(
    "/intake/{intake_id}/cancel-analysis",
    status_code=status.HTTP_200_OK,
)
async def cancel_analysis(
    intake_id: uuid.UUID,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    intake = db.query(Intake).filter(
        Intake.id == intake_id,
        Intake.workshop_id == uuid.UUID(workshop_id),
    ).first()
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")

    active_statuses = ["queued", "running", "retrying"]
    active_jobs = (
        db.query(Job)
        .filter(Job.intake_id == intake_id, Job.status.in_(active_statuses))
        .all()
    )
    if not active_jobs:
        raise HTTPException(
            status_code=404,
            detail="No active assessment to cancel.",
        )

    for j in active_jobs:
        j.status = "cancelled"
        j.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"cancelled": True, "cancelled_jobs": [str(j.id) for j in active_jobs]}


@router.post(
    "/intake/{intake_id}/identify-vehicle",
    response_model=IdentifyVehicleResponse,
)
async def identify_vehicle(
    intake_id: uuid.UUID,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    intake = db.query(Intake).filter(
        Intake.id == intake_id,
        Intake.workshop_id == uuid.UUID(workshop_id),
    ).first()
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")

    view_slots = intake.view_slots or {}
    image_paths = {k: v for k, v in view_slots.items() if v}

    if not image_paths:
        raise HTTPException(
            status_code=400,
            detail="No images uploaded yet. Upload at least one view first.",
        )

    from ai.classification.classifier import VehicleClassifier
    classifier = VehicleClassifier()
    classification = classifier.classify(image_paths)

    suggestions = []
    vehicle_type = classification.get("vehicle_type")
    if vehicle_type and vehicle_type != "unknown":
        from core.models import OEMManufacturer, OEMVehicleModel
        from sqlalchemy.orm import joinedload

        query = (
            db.query(OEMVehicleModel)
            .join(OEMManufacturer)
            .options(joinedload(OEMVehicleModel.manufacturer))
            .filter(OEMVehicleModel.vehicle_type == vehicle_type, OEMVehicleModel.is_active.is_(True))
        )
        matched = query.order_by(OEMManufacturer.name, OEMVehicleModel.model_name).all()
        if matched:
            oem_dicts = [
                {
                    "id": str(m.id),
                    "manufacturer_name": m.manufacturer.name if m.manufacturer else "",
                    "model_name": m.model_name,
                    "vehicle_type": m.vehicle_type,
                }
                for m in matched
            ]
            try:
                import cv2
                from ai.classification.clip_classifier import get_clip_classifier
                clip = get_clip_classifier()
                best_path = _find_best_image(image_paths)
                if best_path:
                    img = cv2.imread(best_path)
                    if img is not None and img.size > 0:
                        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        clip_result = clip.classify(
                            img_rgb, oem_dicts,
                            vehicle_type=vehicle_type, top_k=len(oem_dicts),
                            confidence_threshold=0.01,
                        )
                        clip_scores = {s["oem_model_id"]: s["score"] for s in clip_result["all_scores"]}
                        matched.sort(
                            key=lambda m: clip_scores.get(str(m.id), 0.0),
                            reverse=True,
                        )
                        classification["clip_used"] = True
                    else:
                        classification["clip_used"] = False
                else:
                    classification["clip_used"] = False
            except Exception as e:
                logger.warning("CLIP classifier failed: %s", e)
                classification["clip_used"] = False

            suggestions = [
                {
                    "id": str(m.id),
                    "manufacturer_id": str(m.manufacturer_id),
                    "manufacturer_name": m.manufacturer.name if m.manufacturer else "",
                    "model_name": m.model_name,
                    "generation": m.generation,
                    "vehicle_type": m.vehicle_type,
                    "year_start": m.year_start,
                    "year_end": m.year_end,
                }
                for m in matched[:5]
            ]

    return IdentifyVehicleResponse(
        intake_id=str(intake_id),
        classification=classification,
        suggestions=suggestions,
    )


@router.put("/intake/{intake_id}/oem-model", response_model=SetOemModelResponse)
async def set_intake_oem_model(
    intake_id: uuid.UUID,
    body: SetOemModelRequest,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    intake = db.query(Intake).filter(
        Intake.id == intake_id,
        Intake.workshop_id == uuid.UUID(workshop_id),
    ).first()
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")

    oem_uuid = None
    if body.oem_model_id:
        try:
            oem_uuid = uuid.UUID(body.oem_model_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid oem_model_id format")

    intake.oem_model_id = oem_uuid
    db.commit()

    return SetOemModelResponse(
        intake_id=str(intake_id),
        oem_model_id=str(oem_uuid) if oem_uuid else None,
    )
