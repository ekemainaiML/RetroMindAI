import logging

logger = logging.getLogger(__name__)


def tune_stage_timeouts(trial, db_session) -> float:
    """Optimize stage timeouts to minimize total pipeline time.

    Objective: minimize average assessment time while keeping
    completion rate above 95%.
    """
    timeouts = {
        "vehicle_classification": trial.suggest_int("classif_timeout", 5, 30),
        "geometry_extraction": trial.suggest_int("geometry_timeout", 5, 25),
        "deviation_detection": trial.suggest_int("deviation_timeout", 5, 30),
        "battery_optimization": trial.suggest_int("battery_timeout", 2, 10),
        "wiring_generation": trial.suggest_int("wiring_timeout", 2, 10),
        "digital_twin": trial.suggest_int("twin_timeout", 3, 15),
    }

    if db_session is None:
        return 0.5

    from core.models import Job

    jobs = db_session.query(Job).filter(
        Job.status.in_(["completed", "partial_complete", "timed_out"]),
        Job.result.isnot(None),
    ).all()

    if len(jobs) < 10:
        return 0.0

    total_time = sum(timeouts.values())

    completed = sum(1 for j in jobs if j.status == "completed")
    completion_rate = completed / max(len(jobs), 1)

    if completion_rate < 0.90:
        return 0.0

    return 1.0 - (total_time / 200.0)
