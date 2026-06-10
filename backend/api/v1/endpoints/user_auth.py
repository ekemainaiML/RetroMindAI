import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from core.auth import (
    create_jwt,
    generate_api_key,
    get_current_user,
    get_current_workshop_obj,
    hash_password,
    verify_password,
)
from core.database import get_db
from core.models import User, WorkspaceRole, Workshop

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


def _workshop_to_item(w: Workshop) -> WorkshopItem:
    return WorkshopItem(
        id=str(w.id),
        name=w.name,
        api_key_prefix=w.api_key_prefix,
        tier=w.tier,
        created_at=w.created_at.isoformat() if w.created_at else None,
    )


@router.post("/auth/signup", status_code=201)
def signup(
    body: SignupRequest,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.flush()

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
        api_key_expires_at=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db.add(workshop)
    db.flush()

    user.current_workshop_id = workshop.id

    role = WorkspaceRole(
        id=uuid.uuid4(),
        user_id=user.id,
        workshop_id=workshop.id,
        role="admin",
        accepted_at=datetime.now(timezone.utc),
    )
    db.add(role)
    db.commit()

    jwt = create_jwt(str(user.id), user.email, workshop.name)
    workshops = db.query(Workshop).filter(Workshop.user_id == user.id).all()

    return {
        "jwt": jwt,
        "user": {"id": str(user.id), "email": user.email, "name": workshop.name},
        "workshops": [_workshop_to_item(w) for w in workshops],
        "default_api_key": raw,
    }


@router.post("/auth/login")
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    workshops = db.query(Workshop).filter(Workshop.user_id == user.id).all()
    name = workshops[0].name if workshops else ""
    jwt = create_jwt(str(user.id), user.email, name)
    primary = workshops[0] if workshops else None

    if primary:
        if not user.current_workshop_id:
            user.current_workshop_id = primary.id

        existing_role = db.query(WorkspaceRole).filter(
            WorkspaceRole.user_id == user.id,
            WorkspaceRole.workshop_id == primary.id,
        ).first()
        if not existing_role:
            role = WorkspaceRole(
                id=uuid.uuid4(),
                user_id=user.id,
                workshop_id=primary.id,
                role="admin",
                accepted_at=datetime.now(timezone.utc),
            )
            db.add(role)

        raw, key_hash, prefix = generate_api_key()
        primary.api_key_hash = key_hash
        primary.api_key_prefix = prefix
        db.commit()

    return {
        "jwt": jwt,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": primary.name if primary else "",
        },
        "workshops": [_workshop_to_item(w) for w in workshops],
        "default_api_key": raw,
    }


@router.post("/workshops")
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
        api_key_expires_at=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db.add(workshop)
    db.flush()

    if not user.current_workshop_id:
        user.current_workshop_id = workshop.id

    role = WorkspaceRole(
        id=uuid.uuid4(),
        user_id=user.id,
        workshop_id=workshop.id,
        role="admin",
        accepted_at=datetime.now(timezone.utc),
    )
    db.add(role)
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
    workshop.api_key_expires_at = datetime.now(timezone.utc) + timedelta(days=90)
    workshop.api_key_revoked_at = None
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
    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
    if not workshop:
        raise HTTPException(status_code=404, detail="Workshop not found")

    is_owner = workshop.user_id == user.id
    is_admin = db.query(WorkspaceRole).filter(
        WorkspaceRole.workshop_id == workshop_id,
        WorkspaceRole.user_id == user.id,
        WorkspaceRole.role == "admin",
        WorkspaceRole.accepted_at.isnot(None),
    ).first() is not None

    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Only the workshop owner or admin can delete a workshop")

    db.delete(workshop)
    db.commit()


@router.get("/workshops")
def list_workshops(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owned = db.query(Workshop).filter(Workshop.user_id == user.id).all()
    member_role = (
        db.query(WorkspaceRole, Workshop)
        .join(Workshop, WorkspaceRole.workshop_id == Workshop.id)
        .filter(WorkspaceRole.user_id == user.id)
        .all()
    )
    member_workshops = [w for _, w in member_role]

    all_workshops = {w.id: w for w in owned + member_workshops}
    items = [_workshop_to_item(w) for w in all_workshops.values()]
    items.sort(key=lambda x: x.created_at or "")

    current = str(user.current_workshop_id) if user.current_workshop_id else None

    return {"workshops": items, "current_workshop_id": current}


class SelectWorkshopRequest(BaseModel):
    workshop_id: str


@router.post("/workshops/select")
def select_workshop(
    body: SelectWorkshopRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = db.query(Workshop).filter(Workshop.id == body.workshop_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Workshop not found")

    is_owner = target.user_id == user.id
    is_member = db.query(WorkspaceRole).filter(
        WorkspaceRole.user_id == user.id,
        WorkspaceRole.workshop_id == target.id,
        WorkspaceRole.accepted_at.isnot(None),
    ).first() is not None

    if not is_owner and not is_member:
        raise HTTPException(status_code=403, detail="You are not a member of this workshop")

    user.current_workshop_id = target.id
    db.commit()

    return {"workshop_id": str(target.id), "name": target.name}


class MemberItem(BaseModel):
    user_id: str
    email: str
    name: str
    role: str
    accepted_at: str | None = None
    invited_at: str | None = None


@router.get("/workshop/members")
def list_workshop_members(
    workshop: Workshop = Depends(get_current_workshop_obj),
    db: Session = Depends(get_db),
):
    members = (
        db.query(WorkspaceRole, User)
        .join(User, WorkspaceRole.user_id == User.id)
        .filter(WorkspaceRole.workshop_id == workshop.id)
        .order_by(WorkspaceRole.created_at)
        .all()
    )

    items = []
    for role, member_user in members:
        items.append(MemberItem(
            user_id=str(member_user.id),
            email=member_user.email,
            name=member_user.name,
            role=role.role,
            accepted_at=role.accepted_at.isoformat() if role.accepted_at else None,
            invited_at=role.invited_at.isoformat() if role.invited_at else None,
        ))

    return {"members": items}


class UpdateMemberRoleRequest(BaseModel):
    role: str


@router.patch("/workshop/members/{user_id}/role")
def update_member_role(
    user_id: str,
    body: UpdateMemberRoleRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.role not in {"admin", "operator", "viewer"}:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")

    current_workshop_id = user.current_workshop_id
    if not current_workshop_id:
        raise HTTPException(status_code=400, detail="No current workshop selected")

    caller_role = db.query(WorkspaceRole).filter(
        WorkspaceRole.workshop_id == current_workshop_id,
        WorkspaceRole.user_id == user.id,
        WorkspaceRole.role == "admin",
        WorkspaceRole.accepted_at.isnot(None),
    ).first()

    is_owner = db.query(Workshop).filter(
        Workshop.id == current_workshop_id,
        Workshop.user_id == user.id,
    ).first() is not None

    if not caller_role and not is_owner:
        raise HTTPException(status_code=403, detail="Only admins can update roles")

    target = db.query(WorkspaceRole).filter(
        WorkspaceRole.workshop_id == current_workshop_id,
        WorkspaceRole.user_id == user_id,
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="User is not a member of this workshop")

    target.role = body.role
    db.commit()

    return {"user_id": user_id, "role": body.role}


@router.delete("/workshop/members/{user_id}", status_code=204)
def remove_member(
    user_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_workshop_id = user.current_workshop_id
    if not current_workshop_id:
        raise HTTPException(status_code=400, detail="No current workshop selected")

    if str(user.id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    caller_role = db.query(WorkspaceRole).filter(
        WorkspaceRole.workshop_id == current_workshop_id,
        WorkspaceRole.user_id == user.id,
        WorkspaceRole.role == "admin",
        WorkspaceRole.accepted_at.isnot(None),
    ).first()

    is_owner = db.query(Workshop).filter(
        Workshop.id == current_workshop_id,
        Workshop.user_id == user.id,
    ).first() is not None

    if not caller_role and not is_owner:
        raise HTTPException(status_code=403, detail="Only admins can remove members")

    target = db.query(WorkspaceRole).filter(
        WorkspaceRole.workshop_id == current_workshop_id,
        WorkspaceRole.user_id == user_id,
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="User is not a member of this workshop")

    db.delete(target)
    db.commit()
