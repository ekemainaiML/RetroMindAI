import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_workshop_obj
from core.database import get_db
from core.models import Workshop

logger = logging.getLogger(__name__)

router = APIRouter()


class NotificationPreferencesUpdate(BaseModel):
    assessment_complete: bool | None = None
    assessment_failed: bool | None = None
    key_expiring: bool | None = None
    team_invite: bool | None = None
    payment_receipt: bool | None = None
    daily_digest: bool | None = None
    portal_invite: bool | None = None


@router.get("/notifications/preferences")
def get_preferences(
    workshop: Workshop = Depends(get_current_workshop_obj),
    db: Session = Depends(get_db),
):
    from infrastructure.email.preferences import get_notification_preferences
    prefs = get_notification_preferences(db, str(workshop.id))
    return {"preferences": prefs}


@router.put("/notifications/preferences")
def update_preferences(
    body: NotificationPreferencesUpdate,
    workshop: Workshop = Depends(get_current_workshop_obj),
    db: Session = Depends(get_db),
):
    from infrastructure.email.preferences import update_notification_preferences
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No preferences to update")
    prefs = update_notification_preferences(db, str(workshop.id), updates)
    return {"preferences": prefs}


@router.post("/notifications/test")
async def test_email(
    workshop: Workshop = Depends(get_current_workshop_obj),
    db: Session = Depends(get_db),
):
    if not workshop.email:
        raise HTTPException(status_code=400, detail="Workshop has no email address")
    from infrastructure.email.sender import get_email_sender
    sender = get_email_sender()
    success = await sender.send_assessment_complete(
        to=workshop.email,
        workshop_name=workshop.name,
        job_id="test",
        report_url="http://localhost:3000/reports/test",
    )
    if success:
        return {"message": f"Test email sent to {workshop.email}"}
    raise HTTPException(status_code=502, detail="Failed to send test email")
