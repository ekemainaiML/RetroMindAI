import logging

import numpy as np

from core.capabilities import CapabilityRegistry
from core.config import settings
from core.degradation import get_degradation_manager

logger = logging.getLogger(__name__)


class RLRecommendationAgent:
    """RL-powered recommendation adjustment layer.

    Sits on top of the template engine. If loaded, adjusts recommendation
    priorities, cost multipliers, and safety levels based on assessment state.
    Falls back gracefully to pass-through on any failure.
    """

    def __init__(self, checkpoint_path: str = None):  # type: ignore[assignment]
        self._algorithm = None
        self._checkpoint_path = checkpoint_path or settings.rllib_checkpoint_path

    def load(self) -> bool:
        if not settings.enable_rl_recommendations:
            logger.debug("RL recommendations disabled via feature flag")
            return False
        if not self._checkpoint_path:
            logger.debug("No RL checkpoint path configured")
            return False
        try:
            from ray.rllib.algorithms.ppo import PPO
            self._algorithm = PPO.from_checkpoint(self._checkpoint_path)
            CapabilityRegistry.probe("rllib", True, lambda: True)
            logger.info("RL agent loaded from %s", self._checkpoint_path)
            return True
        except ImportError:
            CapabilityRegistry.probe("rllib", False, lambda: False)
            logger.warning("ray[rllib] not installed — pip install retromind[rllib]")
            return False
        except Exception:
            logger.exception("Failed to load RL checkpoint from %s", self._checkpoint_path)
            CapabilityRegistry.probe("rllib", False, lambda: False)
            return False

    def generate(self, assessment_result: dict) -> dict | None:
        """Generate recommendation adjustments from RL policy.

        Returns None if RL is unavailable (triggers template fallback).
        """
        if self._algorithm is None:
            return None
        try:
            state = self._build_state(assessment_result)
            action = self._algorithm.compute_single_action(state)
            return self._action_to_adjustments(action, assessment_result)
        except Exception:
            logger.warning("RL recommendation failed, falling back to template")
            get_degradation_manager().register("rl_engine", 1, "RL inference failed")
            return None

    def _build_state(self, result: dict) -> np.ndarray:
        vc = result.get("vehicle_classification", {}) or {}
        vtype_str = vc.get("type", "unknown")
        vtype_map = {"three_wheeler": 0, "motorcycle": 1, "four_wheeler": 2, "unknown": 3}
        vtype = vtype_map.get(vtype_str, 3)

        confidence = vc.get("confidence", 0.0)
        factors = result.get("confidence_factors", {}) or {}
        avg_factor = sum(factors.values()) / max(len(factors), 1)

        dr = result.get("deviation_result", {}) or {}
        deviation_severity = 0
        for d in dr.get("deviations", []):
            sev = d.get("severity", "minor")
            if sev == "major":
                deviation_severity = max(deviation_severity, 3)
            elif sev == "moderate":
                deviation_severity = max(deviation_severity, 2)
            elif sev == "minor":
                deviation_severity = max(deviation_severity, 1)

        degs = result.get("degradations", [])
        degradation_tier = max((d.get("tier", 0) for d in degs), default=0)

        return np.array([
            float(vtype),
            confidence,
            avg_factor,
            float(deviation_severity),
            float(degradation_tier),
        ], dtype=np.float32)

    def _action_to_adjustments(self, action, result: dict) -> dict:
        action = np.asarray(action)
        if action.ndim == 0:
            action = action.reshape(1)
        action = action.flatten()

        priority_shift = int(action[0]) if len(action) > 0 else 0
        cost_multiplier = float(action[1]) if len(action) > 1 else 1.0
        safety_escalation = int(action[2]) if len(action) > 2 else 0

        cost_multiplier = max(0.8, min(1.5, cost_multiplier))

        priority_map = {0: "low", 1: "medium", 2: "high"}
        default_priority = priority_map.get(min(priority_shift, 2), "medium")

        return {
            "rl_adjusted": True,
            "priority_default": default_priority,
            "cost_multiplier": cost_multiplier,
            "safety_escalation": safety_escalation,
            "generated_by": "rl_agent",
        }

    @staticmethod
    def record_feedback(feedback_store, assessment_id: str, accepted: bool,
                        state: np.ndarray, action: dict):
        try:
            feedback_store.log_feedback(
                assessment_id=assessment_id,
                state_features=state.tolist() if hasattr(state, 'tolist') else list(state),
                action_taken=action,
                was_accepted=accepted,
            )
        except Exception:
            logger.warning("Failed to record RL feedback")
