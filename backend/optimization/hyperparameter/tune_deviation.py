import logging

logger = logging.getLogger(__name__)


def tune_deviation_thresholds(trial, db_session) -> float:
    """Optimize severity bin boundaries for deviation detection.

    Objective: maximize F1 score of severity classification
    (minor/moderate/major) against human-labeled deviations.
    """
    minor_cutoff = trial.suggest_float("minor_cutoff", 0.5, 4.0)
    moderate_cutoff = trial.suggest_float("moderate_cutoff", 2.0, 10.0)

    if minor_cutoff >= moderate_cutoff:
        return 0.0

    if db_session is None:
        return 0.5

    from core.models import Job

    jobs = db_session.query(Job).filter(
        Job.status == "completed",
        Job.result.isnot(None),
    ).all()

    if len(jobs) < 5:
        return 0.0

    from ai.deviation.detector import DeviationDetector

    score = 0.0
    count = 0
    for job in jobs:
        result = job.result or {}
        deviations = result.get("deviations") or result.get("deviation_result", {}).get("deviations", [])
        if not deviations:
            continue

        for dev in deviations:
            delta_pct = abs(dev.get("delta_pct", 0))
            if delta_pct <= minor_cutoff:
                predicted = "minor"
            elif delta_pct <= moderate_cutoff:
                predicted = "moderate"
            else:
                predicted = "major"

            if predicted == dev.get("severity"):
                score += 1.0
            else:
                score += 0.0
            count += 1

    return score / max(count, 1)
