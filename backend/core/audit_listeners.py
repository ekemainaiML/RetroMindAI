import json

from sqlalchemy import event
from sqlalchemy.orm import Session

from core.audit import AuditLog
from core.models import Intake, Job, User, Workshop


def _get_changes(model, old_values: dict) -> dict:
    changes = {}
    for col in model.__table__.columns:
        key = col.name
        if key in ("id", "created_at", "updated_at"):
            continue
        new_val = getattr(model, key)
        old_val = old_values.get(key)
        if new_val != old_val:
            try:
                json.dumps(new_val)
                json.dumps(old_val)
            except (TypeError, ValueError):
                new_val = str(new_val)
                old_val = str(old_val)
            changes[key] = {"old": old_val, "new": new_val}
    return changes


def _serialize_value(val):
    try:
        json.dumps(val)
        return val
    except (TypeError, ValueError):
        return str(val)


def _log_audit(
    session: Session,
    event_type: str,
    resource_type: str,
    resource_id: str,
    workshop_id: str = None,
    user_id: str = None,
    changes: dict = None,
    method: str = "SYSTEM",
    path: str = None,
    status_code: str = None,
    ip_address: str = None,
    correlation_id: str = None,
):
    log = AuditLog(
        workshop_id=workshop_id,
        user_id=user_id,
        method=method,
        path=path or f"/internal/audit/{event_type}",
        status_code=status_code or "0",
        ip_address=ip_address,
        correlation_id=correlation_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes,
    )
    session.add(log)


def _extract_workshop_id(model) -> str:
    if hasattr(model, "workshop_id") and model.workshop_id:
        return str(model.workshop_id)
    if isinstance(model, Workshop):
        return str(model.id)
    if isinstance(model, User) and hasattr(model, "current_workshop_id"):
        return str(model.current_workshop_id) if model.current_workshop_id else None
    return None


@event.listens_for(Workshop, "before_update")
def receive_workshop_before_update(mapper, connection, target):
    try:
        session = Session.object_session(target)
        if session is None:
            return
        old = {}
        for attr in session.is_modified(target, include_collections=False):
            hist = session.get_attribute_history(target, attr)
            if hist.has_changes() and hist.deleted:
                old[attr] = hist.deleted[0]
        if old:
            changes = _get_changes(target, old)
            if changes:
                _log_audit(
                    session,
                    event_type="workshop.updated",
                    resource_type="workshop",
                    resource_id=str(target.id),
                    workshop_id=str(target.id),
                    changes=changes,
                )
    except Exception:
        pass


@event.listens_for(Workshop, "after_insert")
def receive_workshop_after_insert(mapper, connection, target):
    try:
        session = Session.object_session(target)
        if session is None:
            return
        _log_audit(
            session,
            event_type="workshop.created",
            resource_type="workshop",
            resource_id=str(target.id),
            workshop_id=str(target.id),
        )
    except Exception:
        pass


@event.listens_for(Intake, "after_insert")
def receive_intake_after_insert(mapper, connection, target):
    try:
        session = Session.object_session(target)
        if session is None:
            return
        _log_audit(
            session,
            event_type="intake.created",
            resource_type="intake",
            resource_id=str(target.id),
            workshop_id=str(target.workshop_id) if target.workshop_id else None,
        )
    except Exception:
        pass


@event.listens_for(Intake, "before_update")
def receive_intake_before_update(mapper, connection, target):
    try:
        session = Session.object_session(target)
        if session is None:
            return
        old = {}
        for attr in session.is_modified(target, include_collections=False):
            hist = session.get_attribute_history(target, attr)
            if hist.has_changes() and hist.deleted:
                old[attr] = hist.deleted[0]
        if old:
            changes = _get_changes(target, old)
            if changes:
                _log_audit(
                    session,
                    event_type="intake.updated",
                    resource_type="intake",
                    resource_id=str(target.id),
                    workshop_id=str(target.workshop_id) if target.workshop_id else None,
                    changes=changes,
                )
    except Exception:
        pass


@event.listens_for(Job, "before_update")
def receive_job_before_update(mapper, connection, target):
    try:
        session = Session.object_session(target)
        if session is None:
            return
        old = {}
        for attr in session.is_modified(target, include_collections=False):
            hist = session.get_attribute_history(target, attr)
            if hist.has_changes() and hist.deleted:
                old[attr] = hist.deleted[0]
        if old:
            changes = _get_changes(target, old)
            if changes:
                _log_audit(
                    session,
                    event_type="job.updated",
                    resource_type="job",
                    resource_id=str(target.id),
                    workshop_id=str(target.intake.workshop_id) if target.intake and target.intake.workshop_id else None,
                    changes=changes,
                )
    except Exception:
        pass


@event.listens_for(Job, "after_insert")
def receive_job_after_insert(mapper, connection, target):
    try:
        session = Session.object_session(target)
        if session is None:
            return
        _log_audit(
            session,
            event_type="job.created",
            resource_type="job",
            resource_id=str(target.id),
            workshop_id=str(target.intake.workshop_id) if target.intake and target.intake.workshop_id else None,
        )
    except Exception:
        pass
