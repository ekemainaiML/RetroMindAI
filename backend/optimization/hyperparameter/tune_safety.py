import logging

logger = logging.getLogger(__name__)


def tune_safety_overrides(trial, db_session) -> float:
    """Optimize safety override thresholds for confidence engine.

    Searches for classification/geometry floor values that balance
    false positives (overly conservative) against false negatives
    (unsafe assessments missed).
    """
    class_floor = trial.suggest_float("class_floor", 20.0, 60.0)
    geom_floor = trial.suggest_float("geom_floor", 20.0, 60.0)
    weak_view_threshold = trial.suggest_float("weak_view_threshold", 30.0, 70.0)

    if db_session is None:
        return 0.5

    from core.models import Job

    jobs = db_session.query(Job).filter(
        Job.status.in_(["completed", "partial_complete", "timed_out"]),
        Job.result.isnot(None),
    ).all()

    if len(jobs) < 10:
        return 0.0

    score = 0.0
    count = 0
    for job in jobs:
        result = job.result or {}
        factors = result.get("confidence_factors", {})
        classification = factors.get("classification", 100.0)
        geometry = factors.get("geometry", 100.0)
        state = result.get("assessment_state", "")

        would_override = classification < class_floor and geometry < geom_floor
        actual_unsafe = state == "unsafe_to_assess"

        if would_override == actual_unsafe:
            score += 1.0
        count += 1

    return score / max(count, 1)
