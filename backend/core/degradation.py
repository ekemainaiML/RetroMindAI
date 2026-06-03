import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class Degradation:
    __slots__ = ("tier", "reason", "timestamp")

    def __init__(self, tier: int, reason: str):
        self.tier = tier
        self.reason = reason
        self.timestamp = datetime.now(timezone.utc)


_manager_instance = None


def get_degradation_manager():
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = DegradationManager()
    return _manager_instance


def reset_degradation_manager():
    global _manager_instance
    _manager_instance = None


class DegradationManager:
    def __init__(self):
        self.degradations: dict[str, Degradation] = {}

    def register(self, component: str, tier: int, reason: str):
        self.degradations[component] = Degradation(tier, reason)
        logger.warning(
            "Degradation registered: %s (tier %d) — %s", component, tier, reason
        )

    def resolve(self, component: str):
        if component in self.degradations:
            logger.info("Degradation resolved: %s", component)
            del self.degradations[component]

    def current_tier(self) -> int:
        if not self.degradations:
            return 0
        return max(d.tier for d in self.degradations.values())

    TIER_AI_STAGES = {
        "vehicle_classification",
        "geometry_extraction",
        "deviation_detection",
        "battery_optimization",
        "wiring_generation",
        "digital_twin",
    }

    def should_skip_stage(self, stage_name: str) -> bool:
        tier = self.current_tier()
        if tier >= 2 and stage_name in self.TIER_AI_STAGES:
            logger.info(
                "Stage '%s' skipped due to degradation tier %d", stage_name, tier
            )
            return True
        return False

    def get_degradation_summary(self) -> list[dict]:
        return [
            {
                "component": name,
                "tier": d.tier,
                "reason": d.reason,
                "timestamp": d.timestamp.isoformat(),
            }
            for name, d in self.degradations.items()
        ]

    def clear(self):
        self.degradations.clear()
