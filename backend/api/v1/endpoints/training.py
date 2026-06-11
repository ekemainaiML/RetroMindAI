import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_admin_user
from core.config import settings
from core.database import get_db
from core.models import Workshop

router = APIRouter()


class TrainingInfo(BaseModel):
    has_trained_model: bool
    accuracy: float | None
    samples: int | None
    classes: list[str] | None
    trained_at: str | None
    model_path: str | None


class TrainingStatusResponse(BaseModel):
    onnx: TrainingInfo
    pytorch: TrainingInfo


class TrainingStartResponse(BaseModel):
    training_id: str
    model_type: str
    status: str
    message: str


def _read_metadata(meta_path: Path) -> dict | None:
    if not meta_path.exists():
        return None
    import pickle
    try:
        with open(meta_path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def _build_info(model_path: Path, meta_path: Path) -> TrainingInfo:
    if not model_path.exists():
        return TrainingInfo(
            has_trained_model=False, accuracy=None, samples=None,
            classes=None, trained_at=None, model_path=str(model_path),
        )
    meta = _read_metadata(meta_path) or {}
    return TrainingInfo(
        has_trained_model=True,
        accuracy=meta.get("accuracy"),
        samples=meta.get("samples"),
        classes=meta.get("classes"),
        trained_at=meta.get("trained_at"),
        model_path=str(model_path),
    )


@router.get("/admin/training/status", response_model=TrainingStatusResponse)
async def get_training_status(
    admin: str = Depends(get_admin_user),
):
    onnx_path = Path(settings.ai_model_path)
    onnx_meta = onnx_path.parent / "training_metadata.pkl"

    pt_path = Path(settings.torch_model_path)
    pt_meta = pt_path.parent / "torch_training_metadata.pkl"

    return TrainingStatusResponse(
        onnx=_build_info(onnx_path, onnx_meta),
        pytorch=_build_info(pt_path, pt_meta),
    )


@router.post("/admin/training/start", response_model=TrainingStartResponse)
async def start_training(
    model_type: str = Query("onnx", description="Model type to train: 'onnx' or 'pytorch'"),
    workshop_id: uuid.UUID | None = None,
    admin: str = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    if model_type not in ("onnx", "pytorch"):
        raise HTTPException(status_code=400, detail="model_type must be 'onnx' or 'pytorch'")

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

    if model_type == "onnx":
        model_output_path = settings.ai_model_path
        result = train_from_collected(
            images_dir=str(training_dir),
            model_output_path=model_output_path,
        )
    else:
        from ai.train_pytorch import train_pytorch
        model_output_path = settings.torch_model_path
        result = train_pytorch(
            images_dir=str(training_dir),
            model_output_path=model_output_path,
        )

    import shutil
    shutil.rmtree(training_dir, ignore_errors=True)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Training failed"))

    return TrainingStartResponse(
        training_id=training_id,
        model_type=model_type,
        status="completed",
        message=f"{model_type.upper()} model trained with {result['samples']} samples, accuracy={result['accuracy']:.2%}",
    )
