import logging

from sqlalchemy.orm import Session

from core.models import EmailPreferences

logger = logging.getLogger(__name__)

_DEFAULT_PREFERENCES = {
    "assessment_complete": True,
    "assessment_failed": True,
    "key_expiring": True,
    "team_invite": True,
    "payment_receipt": True,
    "daily_digest": False,
    "portal_invite": True,
}


def get_notification_preferences(db: Session, workshop_id: str) -> dict:
    prefs = db.query(EmailPreferences).filter(
        EmailPreferences.workshop_id == workshop_id
    ).first()
    if prefs is None:
        return dict(_DEFAULT_PREFERENCES)
    return {**_DEFAULT_PREFERENCES, **(prefs.preferences or {})}


def update_notification_preferences(
    db: Session, workshop_id: str, updates: dict, user_id: str | None = None
) -> dict:
    prefs = db.query(EmailPreferences).filter(
        EmailPreferences.workshop_id == workshop_id
    ).first()
    if prefs is None:
        prefs = EmailPreferences(
            workshop_id=workshop_id,
            preferences=dict(_DEFAULT_PREFERENCES),
        )
        db.add(prefs)
    current = {**_DEFAULT_PREFERENCES, **(prefs.preferences or {})}
    current.update(updates)
    prefs.preferences = current
    if user_id:
        prefs.updated_by = user_id
    db.commit()
    db.refresh(prefs)
    return current
