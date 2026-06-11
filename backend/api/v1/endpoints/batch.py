import io
import logging
import os
import uuid
from zipfile import ZipFile, BadZipFile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_workshop
from core.config import settings
from core.database import get_db
from core.models import Batch, BatchJob, Intake, Job

logger = logging.getLogger(__name__)

router = APIRouter()

ALL_SLOTS = ["left_side_profile", "right_side_profile", "rear_view", "front_view", "engine_bay", "underbody"]
REQUIRED_SLOTS = ["left_side_profile", "right_side_profile", "rear_view"]
UPLOAD_DIR = settings.upload_dir


class BatchJobEntry(BaseModel):
    vehicle_name: str
    intake_id: str | None = None
    status: str
    error: str | None = None


class BatchCreateResponse(BaseModel):
    batch_id: str
    total: int
    jobs: list[BatchJobEntry]


class BatchDetailEntry(BaseModel):
    vehicle_name: str
    intake_id: str | None = None
    status: str
    error: str | None = None


class BatchDetailResponse(BaseModel):
    batch_id: str
    total: int
    completed: int
    failed: int
    avg_feasibility: int | None = None
    jobs: list[BatchDetailEntry]


ACCEPTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


def _is_image(name: str) -> bool:
    _, ext = os.path.splitext(name)
    return ext.lower() in ACCEPTED_EXTENSIONS


@router.post("/batch/intake", status_code=status.HTTP_202_ACCEPTED, response_model=BatchCreateResponse)
async def create_batch_intake(
    batch_file: UploadFile = File(...),
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    if not batch_file.filename or not batch_file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a ZIP archive")

    raw = await batch_file.read()
    try:
        zf = ZipFile(io.BytesIO(raw))
    except BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")

    vehicle_dirs: dict[str, dict[str, bytes]] = {}
    for name in zf.namelist():
        parts = name.replace("\\", "/").strip("/").split("/")
        if len(parts) < 2:
            continue
        vehicle_name = parts[0]
        slot_name = parts[-1]
        if not _is_image(slot_name):
            continue
        root, _ = os.path.splitext(slot_name)
        if root not in ALL_SLOTS:
            continue
        if vehicle_name not in vehicle_dirs:
            vehicle_dirs[vehicle_name] = {}
        vehicle_dirs[vehicle_name][root] = zf.read(name)

    if not vehicle_dirs:
        raise HTTPException(status_code=400, detail="No vehicle images found in ZIP. Expected folders per vehicle with images named left_side_profile.jpg, etc.")

    batch_id = uuid.uuid4()
    batch = Batch(id=batch_id, workshop_id=uuid.UUID(workshop_id), status="processing", total=len(vehicle_dirs))
    db.add(batch)
    db.flush()

    entries: list[BatchJobEntry] = []

    workshop_uuid = uuid.UUID(workshop_id)

    for vehicle_name, images in vehicle_dirs.items():
        missing = [s for s in REQUIRED_SLOTS if s not in images]
        if missing:
            entries.append(BatchJobEntry(vehicle_name=vehicle_name, status="validation_failed", error=f"Missing mandatory view: {', '.join(missing)}"))
            batch.failed += 1
            bj = BatchJob(workshop_id=workshop_uuid, batch_id=batch_id, vehicle_name=vehicle_name, status="failed", error_message=f"Missing mandatory view: {', '.join(missing)}")
            db.add(bj)
            continue

        intake_id = uuid.uuid4()
        intake_dir = os.path.join(UPLOAD_DIR, workshop_id, str(intake_id))
        os.makedirs(intake_dir, exist_ok=True)

        view_slots: dict[str, str | None] = {}
        for slot in ALL_SLOTS:
            data = images.get(slot)
            if data:
                ext = ".jpg"
                file_path = os.path.join(intake_dir, f"{slot}{ext}")
                try:
                    with open(file_path, "wb") as f:
                        f.write(data)
                except OSError as e:
                    logger.error("Failed to write %s: %s", file_path, e)
                    view_slots[slot] = None
                    continue
                view_slots[slot] = file_path
            else:
                view_slots[slot] = None

        attempts = {s: 1 for s in ALL_SLOTS if view_slots.get(s) is not None}
        intake_status = "ready"

        db_intake = Intake(
            id=intake_id,
            workshop_id=workshop_uuid,
            view_slots=view_slots,
            attempts=attempts,
            quality_scores={},
            low_quality_views=[],
            occluded_views=[],
            swap_detected=False,
            status=intake_status,
        )
        db.add(db_intake)
        db.flush()

        job = Job(intake_id=intake_id, status="queued", progress_pct=0, completed_stages=[], missing_stages=[], result=None)
        db.add(job)
        db.flush()

        bj = BatchJob(workshop_id=workshop_uuid, batch_id=batch_id, vehicle_name=vehicle_name, intake_id=intake_id, status="created")
        db.add(bj)

        try:
            from redis import Redis
            from rq import Queue
            from workers.assessment import run_assessment
            redis_conn = Redis.from_url(settings.redis_url, socket_connect_timeout=3)
            redis_conn.ping()
            queue = Queue("retromind-jobs", connection=redis_conn)
            queue.enqueue(run_assessment, str(intake_id))
        except Exception as e:
            logger.warning("Failed to enqueue %s: %s", vehicle_name, e)
            job.status = "failed"
            job.error_message = f"Enqueue failed: {e}"
            batch.failed += 1
            entries.append(BatchJobEntry(vehicle_name=vehicle_name, intake_id=str(intake_id), status="enqueue_failed", error=str(e)))
            continue

        batch.completed += 1
        entries.append(BatchJobEntry(vehicle_name=vehicle_name, intake_id=str(intake_id), status="created"))

    if batch.completed == 0 and batch.failed > 0:
        batch.status = "failed"
    elif batch.failed > 0:
        batch.status = "partial"
    else:
        batch.status = "completed"

    db.commit()

    return BatchCreateResponse(
        batch_id=str(batch_id),
        total=len(vehicle_dirs),
        jobs=entries,
    )


@router.get("/batch/{batch_id}", response_model=BatchDetailResponse)
async def get_batch_dashboard(
    batch_id: uuid.UUID,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    batch = db.query(Batch).filter(Batch.id == batch_id, Batch.workshop_id == uuid.UUID(workshop_id)).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    batch_jobs = db.query(BatchJob).filter(BatchJob.batch_id == batch_id).all()
    jobs_out: list[BatchDetailEntry] = []
    for bj in batch_jobs:
        jobs_out.append(BatchDetailEntry(
            vehicle_name=bj.vehicle_name,
            intake_id=str(bj.intake_id) if bj.intake_id else None,
            status=bj.status,
            error=bj.error_message,
        ))

    return BatchDetailResponse(
        batch_id=str(batch.id),
        total=batch.total,
        completed=batch.completed,
        failed=batch.failed,
        avg_feasibility=batch.avg_feasibility,
        jobs=jobs_out,
    )
