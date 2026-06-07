import json
import logging

import numpy as np

from core.capabilities import CapabilityRegistry
from core.config import settings
from core.degradation import get_degradation_manager

logger = logging.getLogger(__name__)


class GenerativeRefiner:
    """Refines battery zones and wiring routes using an LLM backend.

    Sits on top of the template-based optimizers. If a backend is configured
    and available, refines zone/routing proposals. Falls back to pass-through
    on any failure.
    """

    def __init__(self):
        self._backend = None

    @staticmethod
    def _make_json_safe(obj):
        if isinstance(obj, dict):
            return {k: GenerativeRefiner._make_json_safe(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [GenerativeRefiner._make_json_safe(v) for v in obj]
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    def _init_backend(self):
        if self._backend is not None:
            return
        if not settings.enable_generative_design:
            self._backend = "none"
            return
        if settings.openai_api_key:
            try:
                from openai import OpenAI
                self._backend = OpenAI(api_key=settings.openai_api_key, timeout=20.0, max_retries=1)
                CapabilityRegistry.probe("genai", True, lambda: True)
                logger.info("Generative refiner using OpenAI backend")
            except ImportError:
                CapabilityRegistry.probe("genai", False, lambda: False)
                logger.warning("openai not installed — pip install retromind[genai]")
                self._backend = "none"
            except Exception:
                logger.exception("Failed to initialize OpenAI backend")
                self._backend = "none"
        elif settings.anthropic_api_key:
            try:
                from anthropic import Anthropic
                self._backend = Anthropic(api_key=settings.anthropic_api_key, timeout=20.0, max_retries=1)
                CapabilityRegistry.probe("genai", True, lambda: True)
                logger.info("Generative refiner using Anthropic backend")
            except ImportError:
                CapabilityRegistry.probe("genai", False, lambda: False)
                logger.warning("anthropic not installed — pip install retromind[genai]")
                self._backend = "none"
            except Exception:
                logger.exception("Failed to initialize Anthropic backend")
                self._backend = "none"
        else:
            self._backend = "none"

    def refine_battery_zones(self, zones: list[dict], vehicle_type: str,
                              deviations: list | None = None,
                              geometry: dict | None = None) -> list[dict]:
        self._init_backend()
        if self._backend == "none":
            return zones
        try:
            prompt = self._build_battery_prompt(zones, vehicle_type, deviations, geometry)
            response = self._call_llm(prompt)
            refined = self._parse_battery_response(response, zones)
            logger.info("Generative refiner improved battery zones for %s", vehicle_type)
            return refined
        except Exception:
            logger.exception("Generative battery refinement failed, using template zones")
            get_degradation_manager().register("genai_battery", 1, "GenAI battery refinement failed")
            return zones

    def refine_wiring_routing(self, routes: list[dict], vehicle_type: str,
                               deviations: list | None = None,
                               battery_zone: dict | None = None) -> list[dict]:
        self._init_backend()
        if self._backend == "none":
            return routes
        try:
            prompt = self._build_wiring_prompt(routes, vehicle_type, deviations, battery_zone)
            response = self._call_llm(prompt)
            refined = self._parse_wiring_response(response, routes)
            logger.info("Generative refiner improved wiring routes for %s", vehicle_type)
            return refined
        except Exception:
            logger.exception("Generative wiring refinement failed, using template routes")
            get_degradation_manager().register("genai_wiring", 1, "GenAI wiring refinement failed")
            return routes

    def _call_llm(self, prompt: str) -> str:
        if isinstance(self._backend, str):
            return ""
        backend_name = type(self._backend).__module__
        if "openai" in backend_name:
            resp = self._backend.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
            return resp.choices[0].message.content or ""
        elif "anthropic" in backend_name:
            resp = self._backend.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=2000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text if resp.content else ""
        return ""

    def _build_battery_prompt(self, zones: list[dict], vehicle_type: str,
                               deviations: list | None,
                               geometry: dict | None) -> str:
        safe = self._make_json_safe({
            "task": "refine_battery_zones",
            "vehicle_type": vehicle_type,
            "current_zones": zones,
            "deviations": deviations or [],
            "geometry": geometry or {},
            "instructions": (
                "Review these battery placement zones for a %s EV retrofit. "
                "Consider: (1) structural integrity given deviations, "
                "(2) weight distribution, (3) ground clearance, "
                "(4) thermal management. "
                "Return a JSON array where each zone has: id, priority (1-5), "
                "label, and an optional expert_note string. "
                "Adjust priorities if any zone is unsafe for the given deviation data. "
                "Do NOT add or remove zones — only reorder and annotate."
            ) % vehicle_type,
        })
        return json.dumps(safe)

    def _build_wiring_prompt(self, routes: list[dict], vehicle_type: str,
                              deviations: list | None,
                              battery_zone: dict | None) -> str:
        safe = self._make_json_safe({
            "task": "refine_wiring_routes",
            "vehicle_type": vehicle_type,
            "current_routes": routes,
            "deviations": deviations or [],
            "battery_zone": battery_zone or {},
            "instructions": (
                "Review these HV wiring routing paths for a %s EV retrofit. "
                "Consider: (1) heat zone avoidance from deviations, "
                "(2) moving parts clearance, (3) abrasion risk, "
                "(4) compatibility with selected battery zone. "
                "Return a JSON array where each route has: id, priority (1-5), "
                "label, and an optional expert_note string. "
                "Adjust priorities if any route conflicts with deviation data. "
                "Do NOT add or remove routes — only reorder and annotate."
            ) % vehicle_type,
        })
        return json.dumps(safe)

    def _parse_battery_response(self, response: str, original_zones: list[dict]) -> list[dict]:
        try:
            parsed = json.loads(response)
            if isinstance(parsed, list):
                return self._merge_zones(parsed, original_zones)
            return original_zones
        except (json.JSONDecodeError, TypeError):
            return original_zones

    def _parse_wiring_response(self, response: str, original_routes: list[dict]) -> list[dict]:
        try:
            parsed = json.loads(response)
            if isinstance(parsed, list):
                return self._merge_routes(parsed, original_routes)
            return original_routes
        except (json.JSONDecodeError, TypeError):
            return original_routes

    @staticmethod
    def _merge_zones(refined: list[dict], original: list[dict]) -> list[dict]:
        original_by_id = {z["id"]: dict(z) for z in original}
        for rz in refined:
            rz_id = rz.get("id")
            if rz_id in original_by_id:
                merged = dict(original_by_id[rz_id])
                if "priority" in rz:
                    merged["priority"] = rz["priority"]
                if "expert_note" in rz:
                    merged["expert_note"] = rz["expert_note"]
                original_by_id[rz_id] = merged
        result = sorted(original_by_id.values(), key=lambda z: z.get("priority", 99))
        return result

    @staticmethod
    def _merge_routes(refined: list[dict], original: list[dict]) -> list[dict]:
        original_by_id = {r["id"]: dict(r) for r in original}
        for rr in refined:
            rr_id = rr.get("id")
            if rr_id in original_by_id:
                merged = dict(original_by_id[rr_id])
                if "priority" in rr:
                    merged["priority"] = rr["priority"]
                if "expert_note" in rr:
                    merged["expert_note"] = rr["expert_note"]
                original_by_id[rr_id] = merged
        result = sorted(original_by_id.values(), key=lambda r: r.get("priority", 99))
        return result
