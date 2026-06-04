import logging
from copy import deepcopy

from core.capabilities import CapabilityRegistry
from core.config import settings

logger = logging.getLogger(__name__)

_STRUCTURAL_KEYS_FOR_TRIGGER = (
    "wheelbase_mm",
    "overall_length_mm",
    "overall_width_mm",
)

_TEMPLATES = {
    "three_wheeler": {
        "recommendations": [
            {
                "id": "battery_pack_location",
                "category": "battery_placement",
                "title": "Battery pack placement under cargo floor",
                "description": (
                    "Place 48V 100Ah LiFePO4 pack under the cargo floor. "
                    "This preserves cargo volume and lowers the center of gravity."
                ),
                "priority": "high",
                "rationale": [
                    "Preserves cargo volume",
                    "Lower center of gravity",
                    "Standard 3-wheeler layout",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 50000, "mid": 65000, "high": 80000},
                "confidence": 85,
                "depends_on": [],
                "structural_trigger": False,
            },
            {
                "id": "motor_selection",
                "category": "motor",
                "title": "4kW BLDC hub motor conversion",
                "description": (
                    "Install a 4kW BLDC hub motor on the rear axle. "
                    "Provides adequate torque for urban and suburban use."
                ),
                "priority": "high",
                "rationale": [
                    "Sufficient for 3-wheeler weight (~400 kg)",
                    "Hub motor simplifies drivetrain",
                    "Regen braking compatible",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 25000, "mid": 30000, "high": 35000},
                "confidence": 90,
                "depends_on": [],
                "structural_trigger": False,
            },
            {
                "id": "controller_and_bms",
                "category": "controller",
                "title": "48V 100A controller with BMS",
                "description": (
                    "Pair a 48V 100A sine-wave controller with a 48V LiFePO4 BMS. "
                    "Enables smooth throttle response and cell balancing."
                ),
                "priority": "high",
                "rationale": [
                    "Matched to 48V battery and 4kW motor",
                    "Sine-wave drive for quiet operation",
                    "BMS ensures cell longevity and safety",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 12000, "mid": 15000, "high": 18000},
                "confidence": 85,
                "depends_on": ["battery_pack_location", "motor_selection"],
                "structural_trigger": False,
            },
            {
                "id": "wiring_harness",
                "category": "wiring",
                "title": "Custom 48V wiring harness with MC4 connectors",
                "description": (
                    "Fabricate a custom 48V DC wiring harness using MC4 connectors. "
                    "Includes main power loop, motor phase wires, and accessory feeds."
                ),
                "priority": "medium",
                "rationale": [
                    "MC4 connectors handle 48V safely",
                    "Custom lengths avoid loose cabling",
                    "Fused distribution for safety",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 5000, "mid": 6500, "high": 8000},
                "confidence": 80,
                "depends_on": ["controller_and_bms"],
                "structural_trigger": False,
            },
            {
                "id": "structural_reinforcement",
                "category": "structure",
                "title": "Frame stiffening for battery weight",
                "description": (
                    "Weld cross-bracing and stiffen the chassis rails to support "
                    "the additional ~60 kg of battery pack."
                ),
                "priority": "medium",
                "rationale": [
                    "Battery adds ~60 kg to vehicle weight",
                    "Prevents chassis flex under load",
                    "Improves stability during cornering",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 8000, "mid": 11500, "high": 15000},
                "confidence": 75,
                "depends_on": [],
                "structural_trigger": True,
            },
            {
                "id": "regenerative_braking",
                "category": "controller",
                "title": "Regenerative braking controller upgrade",
                "description": (
                    "Upgrade to a regenerative braking controller to recover "
                    "energy during deceleration. Adds ~15% range."
                ),
                "priority": "low",
                "rationale": [
                    "Extends range by ~15%",
                    "Reduces brake pad wear",
                    "Optional — adds controller complexity",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 5000, "mid": 7500, "high": 10000},
                "confidence": 70,
                "depends_on": ["controller_and_bms"],
                "structural_trigger": False,
            },
        ],
        "base_feasibility": 75,
        "tooling_required": [
            "crimping_tool",
            "drill_set",
            "jack_and_stands",
            "multimeter",
            "screwdriver_set",
            "welder",
            "wrench_set",
        ],
        "skill_level_required": "intermediate",
        "estimated_days": 5,
    },
    "four_wheeler": {
        "recommendations": [
            {
                "id": "battery_pack_location",
                "category": "battery_placement",
                "title": "Battery pack in underfloor or trunk area",
                "description": (
                    "Place a 72V 120Ah LiFePO4 pack under the floor or in the trunk. "
                    "Larger capacity needed for ~1000 kg vehicle weight."
                ),
                "priority": "high",
                "rationale": [
                    "High capacity for 4-wheeler weight (~1000 kg)",
                    "Underfloor placement preserves cabin space",
                    "72V system for higher power demand",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 80000, "mid": 100000, "high": 130000},
                "confidence": 85,
                "depends_on": [],
                "structural_trigger": False,
            },
            {
                "id": "motor_selection",
                "category": "motor",
                "title": "5-7kW BLDC motor with gearbox",
                "description": (
                    "Install a 5-7kW BLDC motor coupled to the existing gearbox "
                    "via a adapter plate. Provides adequate torque for city driving."
                ),
                "priority": "high",
                "rationale": [
                    "Sufficient for 4-wheeler weight (~1000 kg)",
                    "Gearbox coupling retains reverse gear",
                    "Regen braking compatible",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 45000, "mid": 55000, "high": 70000},
                "confidence": 85,
                "depends_on": [],
                "structural_trigger": False,
            },
            {
                "id": "controller_and_bms",
                "category": "controller",
                "title": "72V 200A controller with BMS",
                "description": (
                    "Pair a 72V 200A sine-wave controller with a 72V LiFePO4 BMS. "
                    "Handles higher current draw of 4-wheeler conversion."
                ),
                "priority": "high",
                "rationale": [
                    "Matched to 72V battery and 5-7kW motor",
                    "200A rating for peak torque demand",
                    "Active cell balancing for large pack",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 18000, "mid": 22000, "high": 28000},
                "confidence": 85,
                "depends_on": ["battery_pack_location", "motor_selection"],
                "structural_trigger": False,
            },
            {
                "id": "wiring_harness",
                "category": "wiring",
                "title": "Custom 72V wiring harness with MC4 connectors",
                "description": (
                    "Fabricate a custom 72V DC wiring harness rated for 200A. "
                    "Includes main power loop, motor phase wires, and accessory feeds."
                ),
                "priority": "medium",
                "rationale": [
                    "200A-rated cables for peak current",
                    "MC4 connectors handle 72V safely",
                    "Fused distribution for safety",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 8000, "mid": 10000, "high": 13000},
                "confidence": 80,
                "depends_on": ["controller_and_bms"],
                "structural_trigger": False,
            },
            {
                "id": "structural_reinforcement",
                "category": "structure",
                "title": "Frame stiffening for battery and motor weight",
                "description": (
                    "Weld cross-bracing and reinforce suspension mounting points "
                    "to support the additional ~120 kg of EV components."
                ),
                "priority": "medium",
                "rationale": [
                    "EV components add ~120 kg",
                    "Prevents chassis flex under load",
                    "Reinforces suspension points",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 12000, "mid": 16000, "high": 22000},
                "confidence": 75,
                "depends_on": [],
                "structural_trigger": True,
            },
            {
                "id": "regenerative_braking",
                "category": "controller",
                "title": "Regenerative braking controller upgrade",
                "description": (
                    "Upgrade to a regenerative braking controller to recover "
                    "energy during deceleration. Adds ~15% range."
                ),
                "priority": "low",
                "rationale": [
                    "Extends range by ~15%",
                    "Reduces brake pad wear",
                    "Larger energy recovery on heavier vehicle",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 6000, "mid": 8500, "high": 12000},
                "confidence": 70,
                "depends_on": ["controller_and_bms"],
                "structural_trigger": False,
            },
        ],
        "base_feasibility": 70,
        "tooling_required": [
            "crimping_tool",
            "drill_set",
            "jack_and_stands",
            "multimeter",
            "screwdriver_set",
            "welder",
            "wrench_set",
        ],
        "skill_level_required": "advanced",
        "estimated_days": 7,
    },
    "motorcycle": {
        "recommendations": [
            {
                "id": "battery_pack_location",
                "category": "battery_placement",
                "title": "Battery pack under seat compartment",
                "description": (
                    "Place a 36V 60Ah LiFePO4 pack under the seat. "
                    "Fits standard motorcycle frame geometry."
                ),
                "priority": "high",
                "rationale": [
                    "Fits under standard seat",
                    "Keeps weight centered",
                    "36V is standard for 2-wheel conversions",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 30000, "mid": 40000, "high": 50000},
                "confidence": 85,
                "depends_on": [],
                "structural_trigger": False,
            },
            {
                "id": "motor_selection",
                "category": "motor",
                "title": "2kW BLDC hub motor",
                "description": (
                    "Install a 2kW BLDC hub motor on the rear wheel. "
                    "Adequate for a motorcycle weighing ~150 kg."
                ),
                "priority": "high",
                "rationale": [
                    "Lightweight and compact",
                    "Direct hub drive — no chain maintenance",
                    "2kW sufficient for city speeds",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 18000, "mid": 22000, "high": 28000},
                "confidence": 90,
                "depends_on": [],
                "structural_trigger": False,
            },
            {
                "id": "controller_and_bms",
                "category": "controller",
                "title": "36V 60A controller with BMS",
                "description": (
                    "Pair a 36V 60A sine-wave controller with a 36V LiFePO4 BMS. "
                    "Matched to the battery and motor specifications."
                ),
                "priority": "high",
                "rationale": [
                    "Matched to 36V battery and 2kW motor",
                    "Compact size fits under seat",
                    "BMS ensures safe charging",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 8000, "mid": 10000, "high": 13000},
                "confidence": 85,
                "depends_on": ["battery_pack_location", "motor_selection"],
                "structural_trigger": False,
            },
            {
                "id": "wiring_harness",
                "category": "wiring",
                "title": "Custom 36V wiring harness",
                "description": (
                    "Fabricate a custom 36V DC wiring harness. "
                    "Compact routing for motorcycle frame."
                ),
                "priority": "medium",
                "rationale": [
                    "Clean routing on motorcycle frame",
                    "Waterproof connectors",
                    "Fused main power line",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 3000, "mid": 4500, "high": 6000},
                "confidence": 80,
                "depends_on": ["controller_and_bms"],
                "structural_trigger": False,
            },
            {
                "id": "structural_reinforcement",
                "category": "structure",
                "title": "Subframe reinforcement for battery tray",
                "description": (
                    "Weld a battery tray mount and reinforce the subframe "
                    "to support the ~25 kg battery pack."
                ),
                "priority": "medium",
                "rationale": [
                    "Battery adds ~25 kg",
                    "Prevents subframe cracking",
                    "Simple weld-on solution",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 5000, "mid": 7000, "high": 10000},
                "confidence": 75,
                "depends_on": [],
                "structural_trigger": True,
            },
            {
                "id": "regenerative_braking",
                "category": "controller",
                "title": "Regenerative braking controller",
                "description": (
                    "Upgrade to a regenerative braking controller for "
                    "energy recovery. Adds ~10% range."
                ),
                "priority": "low",
                "rationale": [
                    "Extends range by ~10%",
                    "Reduces brake pad wear",
                    "Optional upgrade",
                ],
                "blocking": False,
                "estimated_cost_inr": {"low": 4000, "mid": 6000, "high": 8000},
                "confidence": 70,
                "depends_on": ["controller_and_bms"],
                "structural_trigger": False,
            },
        ],
        "base_feasibility": 80,
        "tooling_required": [
            "crimping_tool",
            "drill_set",
            "jack_and_stands",
            "multimeter",
            "screwdriver_set",
            "wrench_set",
        ],
        "skill_level_required": "intermediate",
        "estimated_days": 4,
    },
}


def _get_template(vehicle_type: str) -> dict:
    template = _TEMPLATES.get(vehicle_type)
    if template is None:
        logger.warning(
            "Unknown vehicle type '%s', defaulting to three_wheeler", vehicle_type
        )
        template = _TEMPLATES["three_wheeler"]
    return template


def _compute_feasibility(
    base_feasibility: int,
    deviation_result: dict | None,
    vehicle_type: str,
    geometry_result: dict | None,
    factors: dict[str, float] | None,
) -> int:
    score = base_feasibility
    if deviation_result:
        deviations = deviation_result.get("deviations", [])
        major_count = sum(1 for d in deviations if d.get("severity") == "major")
        score -= major_count * 5
        if deviation_result.get("critical_delamination", False):
            score -= 15
        salvage = deviation_result.get("salvage_potential", 100)
        if salvage < 50:
            score -= int((50 - salvage) / 5)
    if vehicle_type not in _TEMPLATES:
        score -= 10
    if geometry_result:
        coverage = geometry_result.get("avg_structural_coverage", 0)
        if coverage and coverage > 0.8:
            score += 5
    if factors:
        avg_confidence = sum(factors.values()) / len(factors) if factors else 0
        if avg_confidence > 80:
            score += 5
    return max(0, min(100, score))


def _compute_skill_level(base_skill: str, deviation_result: dict | None) -> str:
    if not deviation_result:
        return base_skill
    salvage = deviation_result.get("salvage_potential", 100)
    if salvage < 40:
        levels = ["beginner", "intermediate", "advanced"]
        base_idx = levels.index(base_skill) if base_skill in levels else 1
        return levels[min(base_idx + 1, len(levels) - 1)]
    return base_skill


def _adjust_recommendations(
    recommendations: list[dict],
    deviation_result: dict | None,
    deviation_severity: str,
) -> list[dict]:
    adjusted = [dict(r) for r in recommendations]
    has_structural_damage = False
    if deviation_result:
        deviations = deviation_result.get("deviations", [])
        major_structural = any(
            d.get("severity") == "major" and d.get("parameter") in _STRUCTURAL_KEYS_FOR_TRIGGER
            for d in deviations
        )
        if major_structural or deviation_result.get("critical_delamination", False):
            has_structural_damage = True

    cost_multiplier = 1.0
    if deviation_severity == "medium":
        cost_multiplier = 1.1
    elif deviation_severity == "high":
        cost_multiplier = 1.25
    if deviation_result:
        salvage = deviation_result.get("salvage_potential", 100)
        if salvage < 40:
            cost_multiplier *= 1.15

    for rec in adjusted:
        if rec.get("structural_trigger") and has_structural_damage:
            rec["priority"] = "high"
            rec["blocking"] = True
            rationale = list(rec.get("rationale", []))
            rationale.append("Critical — structural damage detected")
            rec["rationale"] = rationale
        if cost_multiplier != 1.0:
            costs = rec.get("estimated_cost_inr", {})
            rec["estimated_cost_inr"] = {
                k: int(round(v * cost_multiplier)) for k, v in costs.items()
            }
        rec.pop("structural_trigger", None)
    return adjusted


def _compute_total_costs(recommendations: list[dict]) -> dict[str, int]:
    low = sum(r["estimated_cost_inr"]["low"] for r in recommendations)
    mid = sum(r["estimated_cost_inr"]["mid"] for r in recommendations)
    high = sum(r["estimated_cost_inr"]["high"] for r in recommendations)
    return {"low": low, "mid": mid, "high": high}


def _validate_dependencies(recommendations: list[dict]) -> list[dict]:
    ids = {r["id"] for r in recommendations}
    for rec in recommendations:
        deps = rec.get("depends_on", [])
        rec["depends_on"] = [d for d in deps if d in ids]
    return recommendations


class RecommendationEngine:
    def __init__(self):
        self.templates = _TEMPLATES
        self._rl_agent = None

    def _get_rl_agent(self):
        if self._rl_agent is None:
            if not settings.enable_rl_recommendations:
                return None
            from ai.recommendations.rl_agent import RLRecommendationAgent
            agent = RLRecommendationAgent()
            agent.load()
            self._rl_agent = agent
            CapabilityRegistry.probe("rllib", agent._algorithm is not None, lambda: agent._algorithm is not None)
        return self._rl_agent

    def generate(
        self,
        assessment_result: dict,
        vehicle_type: str,
        deviation_severity: str = "low",
        factors: dict[str, float] | None = None,
        oem_info: dict | None = None,
    ) -> dict:
        template = _get_template(vehicle_type)
        deviation_result = assessment_result.get("deviation_result")

        if oem_info:
            model_name = oem_info.get("model_name", "")
            manufacturer = oem_info.get("manufacturer_name", "")
            for rec in template.get("recommendations", []):
                if model_name:
                    rec["title"] = f"{rec['title']} — {manufacturer} {model_name}" if manufacturer else f"{rec['title']} — {model_name}"
                if manufacturer and model_name:
                    existing = rec.get("rationale", [])
                    existing.insert(0, f"Based on OEM data for {manufacturer} {model_name}")
                    rec["rationale"] = existing
        geometry_result = assessment_result.get("geometry_result")

        recommendations = _adjust_recommendations(
            deepcopy(template["recommendations"]),
            deviation_result,
            deviation_severity,
        )
        recommendations = _validate_dependencies(recommendations)

        feasibility_score = _compute_feasibility(
            template["base_feasibility"],
            deviation_result,
            vehicle_type,
            geometry_result,
            factors,
        )

        tooling = template["tooling_required"]
        skill_level = _compute_skill_level(
            template["skill_level_required"], deviation_result
        )
        estimated_days = template["estimated_days"]

        rl_agent = self._get_rl_agent()
        rl_adjustments = rl_agent.generate(assessment_result) if rl_agent else None

        if rl_adjustments:
            adjusted_recs = []
            for rec in recommendations:
                r = dict(rec)
                r["priority"] = rl_adjustments.get("priority_default", r["priority"])
                if rl_adjustments.get("cost_multiplier", 1.0) != 1.0:
                    cm = rl_adjustments["cost_multiplier"]
                    costs = r.get("estimated_cost_inr", {})
                    r["estimated_cost_inr"] = {
                        k: int(round(v * cm)) for k, v in costs.items()
                    }
                adjusted_recs.append(r)
            recommendations = adjusted_recs

        return {
            "recommendations": recommendations,
            "feasibility_score": feasibility_score,
            "estimated_total_cost_inr": _compute_total_costs(recommendations),
            "tooling_required": sorted(set(tooling)),
            "skill_level_required": skill_level,
            "estimated_days": estimated_days,
        }
