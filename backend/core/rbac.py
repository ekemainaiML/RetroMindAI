import logging
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.auth import get_current_workshop_obj, get_current_user
from core.database import get_db
from core.models import User, WorkspaceRole, Workshop

logger = logging.getLogger(__name__)

ALLOWED_ROLES = {"admin", "operator", "viewer"}

ROLE_HIERARCHY = {
    "viewer": 0,
    "operator": 1,
    "admin": 2,
}


def get_role(workshop_id: str, user_id: str, db: Session) -> str | None:
    role = (
        db.query(WorkspaceRole)
        .filter(
            WorkspaceRole.workshop_id == workshop_id,
            WorkspaceRole.user_id == user_id,
            WorkspaceRole.accepted_at.isnot(None),
        )
        .first()
    )
    return role.role if role else None


def require_role(min_role: str):
    if min_role not in ALLOWED_ROLES:
        raise ValueError(f"Invalid role: {min_role}. Must be one of {ALLOWED_ROLES}")

    def dependency(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        workshop_id = user.current_workshop_id
        if not workshop_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No current workshop selected. Select a workshop first.",
            )

        actual_role = get_role(str(workshop_id), str(user.id), db)
        if actual_role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this workshop.",
            )

        if ROLE_HIERARCHY.get(actual_role, -1) < ROLE_HIERARCHY[min_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{actual_role}' insufficient. Required: '{min_role}'.",
            )

        return user

    return dependency


def require_workshop_role(workshop_id: str, min_role: str, user: User, db: Session) -> str:
    if min_role not in ALLOWED_ROLES:
        raise ValueError(f"Invalid role: {min_role}")

    actual_role = get_role(workshop_id, str(user.id), db)
    if actual_role is None:
        owner = db.query(Workshop).filter(
            Workshop.id == workshop_id,
            Workshop.user_id == user.id,
        ).first()
        if owner:
            return "admin"

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workshop.",
        )

    if ROLE_HIERARCHY.get(actual_role, -1) < ROLE_HIERARCHY[min_role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{actual_role}' insufficient. Required: '{min_role}'.",
        )

    return actual_role


def get_current_workshop_with_role(
    min_role: str = "operator",
    workshop_obj: Workshop = Depends(get_current_workshop_obj),
    db: Session = Depends(get_db),
) -> Workshop:
    return workshop_obj


def require_admin(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    return require_role("admin").dependency(user=user, db=db)
