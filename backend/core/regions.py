"""Region-specific compliance rules for EV retrofitting.

Implements rule sets for ICAT (International Centre for Automotive Technology)
and ARAI (Automotive Research Association of India) based on AIS standards,
CMVR requirements, and published retrofit guidelines.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

COMPLIANCE_STATES = ["pass", "pass_with_caveats", "fail", "insufficient_evidence", "not_assessed"]


RuleResult = dict[str, Any]


def _has_constraint(zones: list[dict] | None, tag: str) -> bool:
    if not zones:
        return False
    for z in zones:
        if tag in (z.get("constraints") or []):
            return True
    return False


def _get_deviation(  # noqa: PLR0913
    deviations: list[dict] | None,
    param: str,
    severity: str = "",
) -> dict | None:
    if not deviations:
        return None
    for d in deviations:
        if d.get("parameter") == param:
            if severity and d.get("severity") != severity:
                continue
            return d
    return None


# ── Rule checkers ──────────────────────────────────────────────────────────


def _check_ground_clearance(data: dict) -> RuleResult | None:
    deviations = data.get("deviations") or []
    ground = _get_deviation(deviations, "ground_clearance_mm")
    estimated = ground.get("estimated") if ground else None
    if estimated is not None and estimated < 160:
        return {
            "rule": "CLR-001",
            "state": "fail",
            "message": f"Estimated ground clearance {estimated}mm is below minimum 160mm required by CMVR / AIS-123.",
        }
    if estimated is not None and estimated < 170:
        return {
            "rule": "CLR-002",
            "state": "pass_with_caveats",
            "message": f"Estimated ground clearance {estimated}mm is marginal (min 160mm recommended).",
        }
    return None


def _check_structural_deviations(data: dict) -> RuleResult | None:
    deviations = data.get("deviations") or []
    critical = any(d.get("severity") == "major" for d in deviations)
    if critical:
        return {
            "rule": "STR-001",
            "state": "fail",
            "message": "Critical structural deviations detected — vehicle may not be roadworthy per ICAT/ARAI guidelines.",
        }
    high_sev = sum(1 for d in deviations if d.get("severity") in ("moderate", "major"))
    if high_sev >= 2:
        return {
            "rule": "STR-002",
            "state": "pass_with_caveats",
            "message": f"{high_sev} structural deviations found — structural integrity review recommended.",
        }
    return None


def _check_battery_secured(data: dict) -> RuleResult | None:
    battery = data.get("battery_placement") or {}
    zones = battery.get("zones") or []
    if not zones:
        return {
            "rule": "BAT-001",
            "state": "insufficient_evidence",
            "message": "No battery placement data available — cannot verify mounting security.",
        }
    if not _has_constraint(zones, "tie_down_points_required"):
        return {
            "rule": "BAT-002",
            "state": "pass_with_caveats",
            "message": "Battery placement should include mechanical tie-down points per AIS-038.",
        }
    return None


def _check_wiring_conduit(data: dict) -> RuleResult | None:
    wiring = data.get("wiring_guidance") or {}
    paths = wiring.get("routing_paths") or []
    if not paths:
        return {
            "rule": "WIR-001",
            "state": "insufficient_evidence",
            "message": "No wiring routing data — cannot verify HV cable protection.",
        }
    oem = data.get("oem") or {}
    if not _has_constraint(paths, "secure_at_300mm_intervals"):
        return {
            "rule": "WIR-002",
            "state": "pass_with_caveats",
            "message": "HV wiring should be secured at max 300mm intervals per AIS-123.",
        }
    return None


def _check_oem_gvw(data: dict) -> RuleResult | None:
    oem = data.get("oem") or {}
    kerb = oem.get("kerb_weight_kg")
    gross = oem.get("gross_weight_kg")
    battery = data.get("battery_placement") or {}
    battery_weight = None
    for z in (battery.get("zones") or []):
        zw = z.get("weight_kg")
        if zw is not None:
            battery_weight = zw
            break
    if kerb and battery_weight and gross:
        estimated_total = kerb + battery_weight
        if estimated_total > gross:
            return {
                "rule": "GVW-001",
                "state": "fail",
                "message": f"Estimated total weight {estimated_total}kg exceeds OEM GVW {gross}kg per CMVR.",
            }
        if estimated_total > gross * 0.9:
            return {
                "rule": "GVW-002",
                "state": "pass_with_caveats",
                "message": f"Estimated total weight {estimated_total}kg is at {estimated_total/gross:.0%} of GVW — close to limit.",
            }
    return None


def _check_vehicle_recognized(data: dict) -> RuleResult | None:
    vc = data.get("vehicle_classification") or {}
    vtype = vc.get("type", "unknown")
    if vtype == "unknown":
        return {
            "rule": "VEH-001",
            "state": "insufficient_evidence",
            "message": "Vehicle type could not be identified — ICAT/ARAI requires known vehicle classification for homologation.",
        }
    return None


def _check_classification_confidence(data: dict) -> RuleResult | None:
    vc = data.get("vehicle_classification") or {}
    vtype = vc.get("type", "unknown")
    conf = vc.get("confidence", 0)
    if isinstance(conf, float) and conf < 0.5 and vtype != "unknown":
        return {
            "rule": "VEH-002",
            "state": "pass_with_caveats",
            "message": f"Vehicle classification confidence ({conf:.0%}) is below 50% threshold recommended for type-approval.",
        }
    return None


def _check_geometry_symmetry(data: dict) -> RuleResult | None:
    geo = data.get("geometry_extraction") or {}
    symmetry = geo.get("symmetry_deviation")
    if symmetry is not None and symmetry > 0.4:
        return {
            "rule": "GEO-001",
            "state": "pass_with_caveats",
            "message": f"Vehicle symmetry deviation ({symmetry:.2f}) exceeds 0.4 — may indicate structural damage.",
        }
    return None


def _check_structural_score(data: dict) -> RuleResult | None:
    geo = data.get("geometry_extraction") or {}
    score = geo.get("geometry_score")
    if score is not None and score < 30:
        return {
            "rule": "GEO-002",
            "state": "fail",
            "message": f"Structural geometry score ({score}) is below minimum 30 — vehicle may be unsuitable for retrofitting.",
        }
    return None


def _check_battery_waterproofing(data: dict) -> RuleResult | None:
    zones = (data.get("battery_placement") or {}).get("zones") or []
    ip67 = _has_constraint(zones, "waterproofing_ip67")
    ip65 = _has_constraint(zones, "waterproofing_ip65")
    if not (ip67 or ip65):
        return {
            "rule": "BAT-003",
            "state": "pass_with_caveats",
            "message": "Battery enclosure should meet at least IP65 (IP67 recommended) per AIS-038.",
        }
    return None


def _check_thermal_management(data: dict) -> RuleResult | None:
    zones = (data.get("battery_placement") or {}).get("zones") or []
    if _has_constraint(zones, "thermal_management_required"):
        return {
            "rule": "BAT-004",
            "state": "pass_with_caveats",
            "message": "Thermal management system required for battery — ensure active or passive cooling per AIS-038.",
        }
    return None


def _check_skid_plate(data: dict) -> RuleResult | None:
    zones = (data.get("battery_placement") or {}).get("zones") or []
    if _has_constraint(zones, "protective_skid_plate_required"):
        return {
            "rule": "BAT-005",
            "state": "pass_with_caveats",
            "message": "Protective skid plate required for underbody battery mounting per ICAT guidelines.",
        }
    return None


def _check_ventilation(data: dict) -> RuleResult | None:
    zones = (data.get("battery_placement") or {}).get("zones") or []
    if _has_constraint(zones, "ventilation_required"):
        return {
            "rule": "BAT-006",
            "state": "pass_with_caveats",
            "message": "Battery ventilation required — ensure adequate airflow per AIS-038.",
        }
    return None


def _check_weight_distribution(data: dict) -> RuleResult | None:
    zones = (data.get("battery_placement") or {}).get("zones") or []
    if _has_constraint(zones, "balanced_weight_required"):
        return {
            "rule": "BAT-007",
            "state": "pass_with_caveats",
            "message": "Battery weight distribution may be unbalanced — verify axle loading per CMVR.",
        }
    return None


def _check_cross_members(data: dict) -> RuleResult | None:
    zones = (data.get("battery_placement") or {}).get("zones") or []
    if _has_constraint(zones, "structural_cross_members_preserved"):
        return {
            "rule": "STR-003",
            "state": "pass_with_caveats",
            "message": "Structural cross members must be preserved — verify cutting/modifications per ICAT structural guidelines.",
        }
    return None


def _check_braking_compatibility(data: dict) -> RuleResult | None:
    recommendations = data.get("recommendations") or []
    regen_found = any(
        "regen" in (r.get("id") or "").lower()
        or "brake" in (r.get("title") or "").lower()
        for r in recommendations
    )
    risks = data.get("risks") or []
    brake_risk = any(
        "brake" in (r.get("message") or "").lower()
        for r in risks
    )
    if brake_risk:
        return {
            "rule": "BRK-001",
            "state": "pass_with_caveats",
            "message": "Brake system compatibility flagged — upgrade recommended per CMVR braking requirements.",
        }
    return None


def _check_salvage_potential(data: dict) -> RuleResult | None:
    deviations = data.get("deviations") or []
    sal = None
    if deviations:
        sal = data.get("deviation_result", {}).get("salvage_potential")
    if sal is not None and sal < 40:
        return {
            "rule": "VEH-003",
            "state": "pass_with_caveats",
            "message": f"Vehicle salvage potential ({sal}/100) is low — may not be economically viable for retrofitting.",
        }
    return None


# ── Rule sets per region ────────────────────────────────────────────────────

ICAT_RULES = [
    _check_ground_clearance,
    _check_structural_deviations,
    _check_battery_secured,
    _check_wiring_conduit,
    _check_battery_waterproofing,
    _check_thermal_management,
    _check_skid_plate,
    _check_ventilation,
    _check_cross_members,
    _check_geometry_symmetry,
]

ARAI_RULES = [
    _check_ground_clearance,
    _check_structural_deviations,
    _check_battery_secured,
    _check_wiring_conduit,
    _check_vehicle_recognized,
    _check_classification_confidence,
    _check_oem_gvw,
    _check_structural_score,
    _check_braking_compatibility,
    _check_salvage_potential,
    _check_weight_distribution,
]

REGION_RULES: dict[str, list] = {
    "icat": ICAT_RULES,
    "arai": ARAI_RULES,
}


def compute_region_compliance(
    region: str,
    assessment_data: dict[str, Any],
) -> tuple[str, list[RuleResult]]:
    """Evaluate region-specific compliance rules against assessment data.

    Returns (overall_compliance_state, detailed_rule_results).
    If the region is unknown or no rules apply, returns ("pass", []).
    """
    region_lower = region.lower().strip()
    rules = REGION_RULES.get(region_lower)
    if not rules:
        logger.warning("Unknown compliance region '%s' — treating as pass", region)
        return "pass", []

    results: list[RuleResult] = []
    overall = "pass"

    for rule_fn in rules:
        try:
            result = rule_fn(assessment_data)
        except Exception:
            logger.exception("Rule %s failed for region %s", rule_fn.__name__, region)
            continue
        if result is None:
            continue
        results.append(result)
        state = result.get("state", "pass")
        state_rank = {"fail": 4, "insufficient_evidence": 3, "pass_with_caveats": 2, "pass": 1}
        if state_rank.get(state, 0) > state_rank.get(overall, 0):
            overall = state

    return overall, results
