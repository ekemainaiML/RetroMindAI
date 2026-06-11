import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """Tracks which optional systems are available at runtime.

    Each capability is probed once and cached. A capability is considered
    available only if its feature flag is enabled AND its check function
    returns True.

    Usage:
        ok = CapabilityRegistry.probe("pytorch", settings.enable_pytorch, lambda: True)
        if CapabilityRegistry.has("pytorch"):
            ...
    """

    _capabilities: dict[str, bool] = {}

    @classmethod
    def probe(cls, name: str, enabled: bool, check_fn: Callable[[], bool]) -> bool:
        if not enabled:
            cls._capabilities[name] = False
            return False
        try:
            available = check_fn()
        except Exception:
            logger.warning("Capability '%s' check failed", name, exc_info=True)
            available = False
        cls._capabilities[name] = available
        logger.info(
            "Capability '%s': enabled=%s, available=%s", name, enabled, available
        )
        return available

    @classmethod
    def has(cls, name: str) -> bool:
        return cls._capabilities.get(name, False)

    @classmethod
    def reset(cls):
        cls._capabilities.clear()

    @classmethod
    def all(cls) -> dict[str, bool]:
        return dict(cls._capabilities)
