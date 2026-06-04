import logging

logger = logging.getLogger(__name__)


def tune_confidence_weights(trial, db_session) -> float:
    """Optimize 6 confidence weights against historical human-confirmed assessments.

    Objective: maximize agreement between ConfidenceEngine score and
    human expert rating implicit in confirmation decisions.
    """
    weights = {
        "completeness": trial.suggest_float("completeness", 0.05, 0.50),
        "quality": trial.suggest_float("quality", 0.05, 0.40),
        "visibility": trial.suggest_float("visibility", 0.05, 0.40),
        "classification": trial.suggest_float("classification", 0.05, 0.30),
        "geometry": trial.suggest_float("geometry", 0.05, 0.30),
        "deviation_certainty": trial.suggest_float("deviation_certainty", 0.05, 0.30),
    }

    total = sum(weights.values())
    weights = {k: v / total for k, v in weights.items()}

    if db_session is None:
        return 0.5

    from core.confidence import ConfidenceEngine
    from core.models import Job

    jobs = db_session.query(Job).filter(
        Job.status == "completed",
        Job.result.isnot(None),
    ).all()

    if len(jobs) < 10:
        return 0.0

    original = ConfidenceEngine.WEIGHTS.copy()
    ConfidenceEngine.WEIGHTS = weights
    try:
        correct = 0
        for job in jobs:
            result = job.result or {}
            factors = result.get("confidence_factors", {})
            score = ConfidenceEngine.compute_score(factors)

            had_confirmation = result.get("needs_confirmation", False)
            human_confirmed = result.get("vehicle_classification", {}).get("human_confirmed", False)

            if score >= 75 and not had_confirmation:
                correct += 1
            elif score < 50 and had_confirmation:
                correct += 1
            elif human_confirmed and score < 50:
                correct += 0.5  # type: ignore[assignment]
    finally:
        ConfidenceEngine.WEIGHTS = original

    return correct / max(len(jobs), 1)
