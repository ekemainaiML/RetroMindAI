import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from core.auth import (
    generate_api_key,
    get_current_workshop_obj,
)
from core.database import get_db
from core.models import Intake, Job, Workshop

router = APIRouter()


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr


class RegisterResponse(BaseModel):
    workshop_id: str
    api_key: str
    api_key_prefix: str


class RenewResponse(BaseModel):
    api_key: str
    api_key_prefix: str


class WorkshopProfile(BaseModel):
    name: str
    email: str | None
    tier: str
    api_key_prefix: str
    created_at: str | None
    intake_count: int
    job_count: int


@router.post("/auth/register", status_code=201, response_model=RegisterResponse)
async def register_workshop(
    body: RegisterRequest,
    db: Session = Depends(get_db),
):
    existing = db.query(Workshop).filter(Workshop.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A workshop with this email already exists.",
        )

    raw, key_hash, prefix = generate_api_key()
    workshop = Workshop(
        id=uuid.uuid4(),
        name=body.name,
        email=body.email,
        tier="standard",
        api_key_hash=key_hash,
        api_key_prefix=prefix,
        is_active=True,
    )
    db.add(workshop)
    db.commit()

    return RegisterResponse(
        workshop_id=str(workshop.id),
        api_key=raw,
        api_key_prefix=prefix,
    )


@router.post("/auth/renew", response_model=RenewResponse)
async def renew_api_key(
    workshop: Workshop = Depends(get_current_workshop_obj),
    db: Session = Depends(get_db),
):
    raw, key_hash, prefix = generate_api_key()
    workshop.api_key_hash = key_hash
    workshop.api_key_prefix = prefix
    if workshop.demo_raw_key is not None:
        workshop.demo_raw_key = raw
    db.commit()

    return RenewResponse(
        api_key=raw,
        api_key_prefix=prefix,
    )


@router.get("/workshop/profile", response_model=WorkshopProfile)
async def get_workshop_profile(
    workshop: Workshop = Depends(get_current_workshop_obj),
    db: Session = Depends(get_db),
):
    intake_count = (
        db.query(Intake)
        .filter(Intake.workshop_id == workshop.id)
        .count()
    )
    job_count = (
        db.query(Job)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(Intake.workshop_id == workshop.id)
        .count()
    )

    return WorkshopProfile(
        name=workshop.name,
        email=workshop.email,
        tier=workshop.tier,
        api_key_prefix=workshop.api_key_prefix,
        created_at=workshop.created_at.isoformat() if workshop.created_at else None,
        intake_count=intake_count,
        job_count=job_count,
    )


@router.get("/workshop/export")
async def export_workshop_data(
    workshop: Workshop = Depends(get_current_workshop_obj),
    db: Session = Depends(get_db),
):
    intakes = (
        db.query(Intake)
        .filter(Intake.workshop_id == workshop.id)
        .order_by(Intake.created_at)
        .all()
    )

    intake_ids = [i.id for i in intakes]
    jobs = (
        db.query(Job)
        .filter(Job.intake_id.in_(intake_ids))
        .order_by(Job.created_at)
        .all()
    ) if intake_ids else []

    export = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "workshop": {
            "id": str(workshop.id),
            "name": workshop.name,
            "email": workshop.email,
            "tier": workshop.tier,
            "created_at": workshop.created_at.isoformat() if workshop.created_at else None,
        },
        "intakes": [
            {
                "id": str(i.id),
                "status": i.status,
                "view_slots": i.view_slots,
                "quality_scores": i.quality_scores,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in intakes
        ],
        "jobs": [
            {
                "id": str(j.id),
                "intake_id": str(j.intake_id),
                "status": j.status,
                "result": j.result,
                "error_message": j.error_message,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "updated_at": j.updated_at.isoformat() if j.updated_at else None,
            }
            for j in jobs
        ],
    }

    return Response(
        content=json.dumps(export, default=str, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="retromind-export-{workshop.id}.json"'},
    )


class CapabilityFlag(BaseModel):
    name: str
    label: str
    description: str
    env_value: bool
    runtime_override: bool | None
    effective: bool
    dep_installed: bool
    dep: str


@router.get("/workshop/capabilities")
def list_workshop_capabilities(
    workshop: Workshop = Depends(get_current_workshop_obj),
):
    from core.feature_flags import FeatureFlagStore
    return {"capabilities": FeatureFlagStore.all_flags()}


class CapabilityToggleRequest(BaseModel):
    value: bool


@router.put("/workshop/capabilities/{name}")
def toggle_workshop_capability(
    name: str,
    body: CapabilityToggleRequest,
    workshop: Workshop = Depends(get_current_workshop_obj),
):
    from core.feature_flags import FeatureFlagStore
    ok = FeatureFlagStore.set_override(name, body.value)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Unknown capability '{name}'")
    return {"name": name, "effective": FeatureFlagStore.get_effective(name)}
