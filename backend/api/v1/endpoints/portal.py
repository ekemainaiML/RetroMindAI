import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import desc
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from core.auth import get_current_workshop_obj
from infrastructure.feedback_store import FeedbackStore
from core.config import settings
from core.database import get_db
from core.models import Intake, Job, PortalSession, Workshop
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from infrastructure.email.sender import EmailMessage, EmailSender

router = APIRouter()

ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = settings.portal_token_expiry_hours


def _generate_portal_token(session_id: str, job_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)
    payload = {
        "session_id": session_id,
        "job_id": job_id,
        "exp": expires_at,
        "type": "portal_access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def _decode_portal_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        if payload.get("type") != "portal_access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


class CreatePortalLinkRequest(BaseModel):
    job_id: str
    customer_email: str
    customer_name: str | None = None


class PortalLinkResponse(BaseModel):
    portal_url: str
    token: str
    expires_at: str


class PortalSessionStatus(BaseModel):
    status: str
    job_id: str
    customer_email: str
    customer_name: str | None
    created_at: str
    expires_at: str
    approved_at: str | None
    rejection_reason: str | None


class PortalApprovalRequest(BaseModel):
    action: str
    rejection_reason: str | None = None


@router.post("/portal/share", response_model=PortalLinkResponse)
async def create_portal_link(
    body: CreatePortalLinkRequest,
    background_tasks: BackgroundTasks,
    workshop: Workshop = Depends(get_current_workshop_obj),
    db: Session = Depends(get_db),
):
    job_uuid = uuid.UUID(body.job_id)
    job = (
        db.query(Job)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(Job.id == job_uuid, Intake.workshop_id == workshop.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Assessment must be completed before sharing")

    token = _generate_portal_token(str(uuid.uuid4()), str(job.id))

    session = PortalSession(
        workshop_id=workshop.id,
        job_id=job.id,
        token=token,
        customer_email=body.customer_email,
        customer_name=body.customer_name,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    portal_url = f"{settings.portal_base_url}/{token}"

    try:
        from infrastructure.email.sender import get_email_sender
        background_tasks.add_task(
            get_email_sender().send_portal_invite,
            to=body.customer_email,
            workshop_name=workshop.name,
            portal_url=portal_url,
            expires_hours=TOKEN_EXPIRY_HOURS,
        )
    except ImportError:
        pass

    return PortalLinkResponse(
        portal_url=portal_url,
        token=token,
        expires_at=session.expires_at.isoformat(),
    )


@router.get("/portal/view/{token}")
async def view_portal_assessment(
    token: str,
    db: Session = Depends(get_db),
):
    payload = _decode_portal_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired portal link")

    session = db.query(PortalSession).filter(PortalSession.token == token).first()
    if not session:
        raise HTTPException(status_code=401, detail="Portal session not found")
    if session.status == "expired":
        raise HTTPException(status_code=410, detail="Portal link has expired")
    if datetime.now(timezone.utc) > session.expires_at:
        session.status = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="Portal link has expired")

    job = db.query(Job).filter(Job.id == session.job_id).first()
    if not job or not job.result:
        raise HTTPException(status_code=404, detail="Assessment not found")

    result = job.result
    intake = db.query(Intake).filter(Intake.id == job.intake_id).first()

    return {
        "portal": {
            "status": session.status,
            "customer_email": session.customer_email,
            "customer_name": session.customer_name,
        },
        "assessment": {
            "job_id": str(job.id),
            "status": job.status,
            "vehicle_classification": result.get("vehicle_classification", {}),
            "compliance_state": result.get("compliance_state", "not_assessed"),
            "confidence_score": result.get("confidence_score", 0),
            "feasibility_score": result.get("feasibility_score", 0),
            "feasibility_label": result.get("feasibility_label", "unknown"),
            "recommendations": result.get("recommendations", []),
            "estimated_total_cost_inr": result.get("estimated_total_cost_inr", {}),
            "estimated_days": result.get("estimated_days", 0),
            "digital_twin": result.get("digital_twin"),
        },
    }


def _record_portal_feedback(db: Session, action: str, session: "PortalSession"):
    try:
        from core.models import RecommendationFeedback

        job = db.query(Job).filter(Job.id == session.job_id).first()
        if not job or not job.result:
            return
        recommendations = job.result.get("recommendations", [])
        if not recommendations:
            return
        vc = job.result.get("vehicle_classification", {}) or {}
        state_features = [
            {"type": vc.get("type", "unknown"), "confidence": vc.get("confidence", 0)},
        ]
        was_accepted = action == "approved"
        store = FeedbackStore(db)
        for rec in recommendations:
            store.log_feedback(
                assessment_id=str(job.id),
                state_features=state_features,
                action_taken={
                    "recommendation_id": rec.get("id", ""),
                    "title": rec.get("title", ""),
                    "priority": rec.get("priority", "medium"),
                    "cost_inr": rec.get("cost_inr", 0),
                },
                was_accepted=was_accepted,
            )
        logger.info(
            "Recorded %d feedback entries for assessment %s (action=%s)",
            len(recommendations), job.id, action,
        )
    except Exception:
        logger.exception("Failed to record portal feedback")


@router.post("/portal/{token}/respond")
async def respond_portal_assessment(
    token: str,
    body: PortalApprovalRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    payload = _decode_portal_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired portal link")

    session = db.query(PortalSession).filter(PortalSession.token == token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Portal session not found")
    if session.status != "pending":
        raise HTTPException(status_code=400, detail=f"Already {session.status}")
    if datetime.now(timezone.utc) > session.expires_at:
        session.status = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="Portal link has expired")

    if body.action not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Action must be 'approved' or 'rejected'")

    session.status = body.action
    session.approved_at = datetime.now(timezone.utc)
    if body.action == "rejected":
        session.rejection_reason = body.rejection_reason
    db.commit()
    db.refresh(session)

    _record_portal_feedback(db, body.action, session)

    workshop = db.query(Workshop).filter(Workshop.id == session.workshop_id).first()
    if workshop and workshop.email:
        action_label = "approved" if body.action == "approved" else "rejected"
        try:
            from infrastructure.email.sender import EmailMessage, get_email_sender
            background_tasks.add_task(
                get_email_sender().send,
                EmailMessage(
                    to=workshop.email,
                    subject=f"Customer {action_label} assessment — {workshop.name}",
                    template_name="assessment_complete.html",
                    context={
                        "workshop_name": workshop.name,
                        "job_id": str(session.job_id),
                        "report_url": "#",
                        "brand_name": settings.email_from_name,
                    },
                ),
            )
        except ImportError:
            pass

    return {
        "status": session.status,
        "job_id": str(session.job_id),
        "approved_at": session.approved_at.isoformat() if session.approved_at else None,
    }


@router.get("/portal/{token}/status", response_model=PortalSessionStatus)
async def get_portal_status(
    token: str,
    db: Session = Depends(get_db),
):
    payload = _decode_portal_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired portal link")

    session = db.query(PortalSession).filter(PortalSession.token == token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Portal session not found")

    now = datetime.now(timezone.utc)
    if session.status == "pending" and now > session.expires_at:
        session.status = "expired"
        db.commit()

    return PortalSessionStatus(
        status=session.status,
        job_id=str(session.job_id),
        customer_email=session.customer_email,
        customer_name=session.customer_name,
        created_at=session.created_at.isoformat(),
        expires_at=session.expires_at.isoformat(),
        approved_at=session.approved_at.isoformat() if session.approved_at else None,
        rejection_reason=session.rejection_reason,
    )


class PortalSessionSummary(BaseModel):
    id: str
    job_id: str
    customer_email: str
    customer_name: str | None
    status: str
    created_at: str
    expires_at: str
    approved_at: str | None
    rejection_reason: str | None


@router.get("/portal/sessions")
async def list_portal_sessions(
    job_id: str | None = None,
    workshop: Workshop = Depends(get_current_workshop_obj),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    query = db.query(PortalSession).filter(PortalSession.workshop_id == workshop.id)
    if job_id:
        query = query.filter(PortalSession.job_id == uuid.UUID(job_id))
    sessions = query.order_by(desc(PortalSession.created_at)).all()

    expired = False
    for s in sessions:
        if s.status == "pending" and now > s.expires_at:
            s.status = "expired"
            expired = True
    if expired:
        db.commit()

    return [
        PortalSessionSummary(
            id=str(s.id),
            job_id=str(s.job_id),
            customer_email=s.customer_email,
            customer_name=s.customer_name,
            status=s.status,
            created_at=s.created_at.isoformat(),
            expires_at=s.expires_at.isoformat(),
            approved_at=s.approved_at.isoformat() if s.approved_at else None,
            rejection_reason=s.rejection_reason,
        )
        for s in sessions
    ]
