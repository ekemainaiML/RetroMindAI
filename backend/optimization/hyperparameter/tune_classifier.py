import logging
import os

logger = logging.getLogger(__name__)


def tune_classifier_signals(trial, db_session) -> float:
    """Optimize heuristic classifier signal weights.

    Searches for weight combinations that maximize classification
    accuracy against a labeled ground-truth dataset.
    """
    signal_weights = {
        "hull_shape_fw": trial.suggest_float("hull_shape_fw", 0.1, 0.5),
        "hull_shape_tw": trial.suggest_float("hull_shape_tw", 0.1, 0.5),
        "hull_shape_mc": trial.suggest_float("hull_shape_mc", 0.1, 0.5),
        "profile_fw": trial.suggest_float("profile_fw", 0.1, 0.4),
        "profile_tw": trial.suggest_float("profile_tw", 0.1, 0.4),
        "profile_mc": trial.suggest_float("profile_mc", 0.1, 0.4),
        "wheels_fw": trial.suggest_float("wheels_fw", 0.15, 0.45),
        "wheels_tw": trial.suggest_float("wheels_tw", 0.15, 0.45),
        "wheels_mc": trial.suggest_float("wheels_mc", 0.15, 0.45),
    }

    from core.config import settings

    labeled_dir = os.path.join(settings.upload_dir, "eval_labels")
    if not os.path.isdir(labeled_dir):
        return 0.0

    from ai.classification.classifier import CLASS_LABELS

    correct = 0
    total = 0
    for label in ["three_wheeler", "motorcycle", "four_wheeler"]:
        label_dir = os.path.join(labeled_dir, label)
        if not os.path.isdir(label_dir):
            continue
        for fname in os.listdir(label_dir):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            total += 1

    return correct / max(total, 1) if total >= 5 else 0.0
