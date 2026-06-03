import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from core.auth import get_current_workshop
from core.database import get_db
from core.models import Intake, Job

logger = logging.getLogger(__name__)

router = APIRouter()

_freecad_client = None


def _get_freecad():
    global _freecad_client
    if _freecad_client is None:
        from infrastructure.freecad_client import FreeCADClient
        _freecad_client = FreeCADClient()
        _freecad_client.check_available()
    return _freecad_client


@router.get("/cad/export/{assessment_id}")
def export_cad(
    assessment_id: str,
    format: str = "step",
    db: Session = Depends(get_db),
    workshop_id: str = Depends(get_current_workshop),
):
    """Export assessment as STEP/STL via FreeCAD worker.

    Requires X-API-Key header. Returns 503 if FreeCAD service is unavailable.
    """
    client = _get_freecad()
    if not client._available:
        raise HTTPException(
            status_code=503,
            detail="CAD export unavailable — FreeCAD service not running. "
                   "Start with: docker compose --profile freecad up",
        )

    job = (
        db.query(Job)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(Job.id == assessment_id, Intake.workshop_id == uuid.UUID(workshop_id))
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if job.status not in ("completed", "expired"):
        raise HTTPException(
            status_code=400,
            detail=f"Assessment status is '{job.status}', must be 'completed' or 'expired'",
        )

    fmt = format.lower()
    if fmt == "step":
        data = client.export_step(job.result or {})
    elif fmt == "stl":
        data = client.export_stl(job.result or {})
    else:
        raise HTTPException(status_code=400, detail="Unsupported format (use 'step' or 'stl')")

    if data is None:
        raise HTTPException(status_code=503, detail="CAD export failed")

    media_type = "application/step" if fmt == "step" else "application/sla"
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{assessment_id}.{fmt}"'},
    )
