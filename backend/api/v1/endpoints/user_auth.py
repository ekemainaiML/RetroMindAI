import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from core.auth import (
    create_jwt,
    generate_api_key,
    get_current_workshop_obj,
    get_current_user,
    hash_api_key,
    hash_password,
    verify_password,
)
from core.database import get_db
from core.models import User, Workshop

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str


class WorkshopItem(BaseModel):
    id: str
    name: str
    api_key_prefix: str
    tier: str
    created_at: str | None


class CreateWorkshopRequest(BaseModel):
    name: str


class CreateWorkshopResponse(BaseModel):
    id: str
    name: str
    api_key: str
    api_key_prefix: str
    tier: str
    created_at: str | None


def create_workshop(
    body: CreateWorkshopRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw, key_hash, prefix = generate_api_key()
    workshop = Workshop(
        id=uuid.uuid4(),
        user_id=user.id,
        name=body.name,
        email=user.email,
        tier="standard",
        api_key_hash=key_hash,
        api_key_prefix=prefix,
        is_active=True,
    )
    db.add(workshop)
    db.commit()

    return CreateWorkshopResponse(
        id=str(workshop.id),
        name=workshop.name,
        api_key=raw,
        api_key_prefix=workshop.api_key_prefix,
        tier=workshop.tier,
        created_at=workshop.created_at.isoformat() if workshop.created_at else None,
    )


@router.post("/workshops/{workshop_id}/key")
def generate_workshop_key(
    workshop_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workshop = db.query(Workshop).filter(
        Workshop.id == workshop_id,
        Workshop.user_id == user.id,
    ).first()
    if not workshop:
        raise HTTPException(status_code=404, detail="Workshop not found")
    raw, key_hash, prefix = generate_api_key()
    workshop.api_key_hash = key_hash
    workshop.api_key_prefix = prefix
    if workshop.demo_raw_key is not None:
        workshop.demo_raw_key = raw
    db.commit()
    return {"api_key": raw, "api_key_prefix": prefix}


@router.delete("/workshops/{workshop_id}", status_code=204)
def delete_workshop(
    workshop_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workshop = db.query(Workshop).filter(
        Workshop.id == workshop_id,
        Workshop.user_id == user.id,
    ).first()
    if not workshop:
        raise HTTPException(status_code=404, detail="Workshop not found")
    db.delete(workshop)
    db.commit()
