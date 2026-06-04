import logging

import httpx

from core.capabilities import CapabilityRegistry
from core.config import settings

logger = logging.getLogger(__name__)


class FreeCADClient:
    """HTTP client to FreeCAD worker container.

    Sits behind a feature flag. Returns None for every operation
    when FreeCAD is unavailable or disabled.
    """

    def __init__(self):
        self._base_url = settings.freecad_host
        self._available = False

    def check_available(self) -> bool:
        if not settings.enable_cad_export:
            return False
        if not self._base_url:
            return False
        try:
            r = httpx.get(f"{self._base_url}/health", timeout=5)
            self._available = r.status_code == 200
            if self._available:
                CapabilityRegistry.probe("freecad", True, lambda: True)
            return self._available
        except Exception:
            logger.warning("FreeCAD health check failed at %s", self._base_url)
            self._available = False
            CapabilityRegistry.probe("freecad", True, lambda: False)
            return False

    def export_step(self, assessment_result: dict) -> bytes | None:
        if not self._available:
            return None
        try:
            r = httpx.post(
                f"{self._base_url}/export",
                json={"assessment": assessment_result, "format": "step"},
                timeout=120,
            )
            if r.status_code == 200:
                logger.info("FreeCAD STEP export succeeded (%d bytes)", len(r.content))
                return r.content
            logger.warning("FreeCAD export returned %d", r.status_code)
            return None
        except Exception:
            logger.exception("FreeCAD export failed")
            return None

    def export_stl(self, assessment_result: dict) -> bytes | None:
        if not self._available:
            return None
        try:
            r = httpx.post(
                f"{self._base_url}/export",
                json={"assessment": assessment_result, "format": "stl"},
                timeout=120,
            )
            if r.status_code == 200:
                return r.content
            return None
        except Exception:
            logger.exception("FreeCAD STL export failed")
            return None
