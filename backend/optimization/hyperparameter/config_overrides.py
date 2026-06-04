import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

OVERRIDE_PATH = Path(__file__).resolve().parent / "best_params.json"


class ConfigOverrides:
    @classmethod
    def apply(cls):
        if not OVERRIDE_PATH.exists():
            logger.info("No hyperparameter overrides found at %s", OVERRIDE_PATH)
            return

        with open(OVERRIDE_PATH) as f:
            params = json.load(f)

        if "confidence_weights" in params:
            cls._patch_confidence_weights(params["confidence_weights"]["best_params"])

        if "deviation_thresholds" in params:
            cls._patch_deviation_thresholds(params["deviation_thresholds"]["best_params"])

        if "stage_timeouts" in params:
            cls._patch_stage_timeouts(params["stage_timeouts"]["best_params"])

        logger.info("Applied hyperparameter overrides from %s", OVERRIDE_PATH)

    @classmethod
    def _patch_confidence_weights(cls, best_params: dict):
        from core.confidence import ConfidenceEngine
        total = sum(best_params.values())
        if total > 0:
            normalized = {k: v / total for k, v in best_params.items()}
            ConfidenceEngine.WEIGHTS.update(normalized)
            logger.info("Patched confidence weights: %s", normalized)

    @classmethod
    def _patch_deviation_thresholds(cls, best_params: dict):
        import ai.deviation.detector as det_mod

        if hasattr(det_mod, "SEVERITY_THRESHOLDS"):
            det_mod.SEVERITY_THRESHOLDS = (
                best_params.get("minor_cutoff", 2.0),
                best_params.get("moderate_cutoff", 5.0),
            )
            logger.info("Patched deviation thresholds: %s", det_mod.SEVERITY_THRESHOLDS)

    @classmethod
    def _patch_stage_timeouts(cls, best_params: dict):
        from workers.assessment import STAGE_TIMEOUTS
        mapping = {
            "classif_timeout": "vehicle_classification",
            "geometry_timeout": "geometry_extraction",
            "deviation_timeout": "deviation_detection",
            "battery_timeout": "battery_optimization",
            "wiring_timeout": "wiring_generation",
            "twin_timeout": "digital_twin",
        }
        for param_key, stage in mapping.items():
            if param_key in best_params:
                STAGE_TIMEOUTS[stage] = best_params[param_key]

        logger.info("Patched stage timeouts: %s", STAGE_TIMEOUTS)
