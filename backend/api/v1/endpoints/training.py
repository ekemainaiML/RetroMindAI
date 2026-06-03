import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_admin_user
from core.config import settings
from core.database import get_db
from core.models import Intake, Workshop

router = APIRouter()


class TrainingStatusResponse(BaseModel):
    has_trained_model: bool
    accuracy: float | None
    samples: int | None
    classes: list[str] | None
    trained_at: str | None
    model_path: str | None


class TrainingStartResponse(BaseModel):
    training_id: str
    status: str
    message: str


@router.get("/admin/training/status", response_model=TrainingStatusResponse)
async def get_training_status(
    admin: str = Depends(get_admin_user),
):
    model_path = Path(settings.ai_model_path)
    meta_path = model_path.parent / "training_metadata.pkl"

    if not model_path.exists() or not meta_path.exists():
        return TrainingStatusResponse(
            has_trained_model=False,
            accuracy=None,
            samples=None,
            classes=None,
            trained_at=None,
            model_path=str(model_path) if model_path.exists() else None,
        )

    import pickle
    try:
        with open(meta_path, "rb") as f:
            meta = pickle.load(f)
        return TrainingStatusResponse(
            has_trained_model=True,
            accuracy=meta.get("accuracy"),
            samples=meta.get("samples"),
            classes=meta.get("classes"),
            trained_at=meta.get("trained_at"),
            model_path=str(model_path),
        )
    except Exception:
        return TrainingStatusResponse(
            has_trained_model=True,
            accuracy=None,
            samples=None,
            classes=None,
            trained_at=None,
            model_path=str(model_path),
        )


@router.post("/admin/training/start", response_model=TrainingStartResponse)
async def start_training(
    workshop_id: uuid.UUID | None = None,
    admin: str = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from ai.train import collect_training_data, train_from_collected

    training_id = str(uuid.uuid4())
    training_dir = Path(settings.upload_dir) / "_training" / training_id
    training_dir.mkdir(parents=True, exist_ok=True)

    if workshop_id:
        workshops = db.query(Workshop).filter(Workshop.id == workshop_id).all()
    else:
        workshops = db.query(Workshop).filter(Workshop.is_active.is_(True)).all()

    if not workshops:
        raise HTTPException(status_code=400, detail="No workshops found to collect data from.")

    total_copied = 0
    for w in workshops:
        copied = collect_training_data(
            db,
            workshop_id=w.id,
            output_dir=str(training_dir),
        )
        for files in copied.values():
            total_copied += len(files)

    if total_copied < 10:
        import shutil
        shutil.rmtree(training_dir, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail=f"Only {total_copied} images collected. Need at least 10.",
        )

    model_output_path = settings.ai_model_path
    result = train_from_collected(
        images_dir=str(training_dir),
        model_output_path=model_output_path,
    )

    import shutil
    shutil.rmtree(training_dir, ignore_errors=True)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Training failed"))

    return TrainingStartResponse(
        training_id=training_id,
        status="completed",
        message=f"Model trained with {result['samples']} samples, accuracy={result['accuracy']:.2%}",
    )
