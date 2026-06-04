import logging
import os

logger = logging.getLogger(__name__)


def tune_classifier_signals(trial, db_session) -> float:
    """Optimize heuristic classifier signal weights.

    Searches for weight combinations that maximize classification
    accuracy against a labeled ground-truth dataset.
    """


    from core.config import settings

    labeled_dir = os.path.join(settings.upload_dir, "eval_labels")
    if not os.path.isdir(labeled_dir):
        return 0.0


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
