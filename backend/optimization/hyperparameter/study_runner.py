import json
import logging
from pathlib import Path

from core.capabilities import CapabilityRegistry

logger = logging.getLogger(__name__)

STUDIES_DIR = Path(__file__).resolve().parent
BEST_PARAMS_PATH = STUDIES_DIR / "best_params.json"


def _import_optuna():
    try:
        import optuna
        return optuna
    except ImportError:
        return None


def _import_tune_confidence():
    from optimization.hyperparameter.tune_confidence import tune_confidence_weights
    return tune_confidence_weights


def _import_tune_classifier():
    from optimization.hyperparameter.tune_classifier import tune_classifier_signals
    return tune_classifier_signals


def _import_tune_deviation():
    from optimization.hyperparameter.tune_deviation import tune_deviation_thresholds
    return tune_deviation_thresholds


def _import_tune_safety():
    from optimization.hyperparameter.tune_safety import tune_safety_overrides
    return tune_safety_overrides


def _import_tune_timeouts():
    from optimization.hyperparameter.tune_timeouts import tune_stage_timeouts
    return tune_stage_timeouts


class StudyRunner:
    TARGETS = {
        "confidence_weights": _import_tune_confidence,
        "classifier_signals": _import_tune_classifier,
        "deviation_thresholds": _import_tune_deviation,
        "safety_overrides": _import_tune_safety,
        "stage_timeouts": _import_tune_timeouts,
    }

    def __init__(self, n_trials: int = 100):
        self.n_trials = n_trials

    def run_all(self, db_session=None) -> dict:
        optuna = _import_optuna()
        if optuna is None:
            logger.warning("optuna not installed — install with: pip install retromind[optuna]")
            return {"status": "skipped", "reason": "optuna not installed"}

        results = {}
        for name, import_fn in self.TARGETS.items():
            try:
                objective = import_fn()
            except ImportError as e:
                logger.warning("Could not import study '%s': %s", name, e)
                continue

            study = optuna.create_study(
                direction="maximize",
                pruner=optuna.pruners.MedianPruner(),
                study_name=name,
            )
            n_trials = max(10, self.n_trials)
            study.optimize(lambda trial: objective(trial, db_session), n_trials=n_trials)

            results[name] = {
                "best_params": study.best_params,
                "best_value": round(study.best_value, 4),
                "trials": len(study.trials),
            }
            logger.info(
                "Study '%s' complete: best=%.4f (%d trials)",
                name, study.best_value, len(study.trials),
            )

        self._save_results(results)
        return results

    @staticmethod
    def _save_results(results: dict):
        BEST_PARAMS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(BEST_PARAMS_PATH, "w") as f:
            json.dump(results, f, indent=2)
        logger.info("Saved best params to %s", BEST_PARAMS_PATH)

    @staticmethod
    def load_best_params() -> dict:
        if BEST_PARAMS_PATH.exists():
            with open(BEST_PARAMS_PATH) as f:
                return json.load(f)
        return {}
