from __future__ import annotations

"""
Wiring router — computes HV harness routing paths from battery zone placement,
vehicle geometry, and deviation data.

The router maps each vehicle type to known safe routing paths along chassis
rails and identifies caution zones from deviation data (heat sources, moving
parts, structural compromise areas).
"""

from core.config import settings  # noqa: E402

ROUTING_TEMPLATES: dict[str, list[dict]] = {
    "three_wheeler": [
        {
            "id": "chassis_rail_right",
            "priority": 1,
            "label": "Right Chassis Rail",
            "description": "Route along the right-side chassis rail from battery to motor controller",
            "path_type": "chassis_rail",
            "length_estimate_mm": 1800,
            "conduit_required": True,
            "constraints": [
                "secure_at_300mm_intervals",
                "avoid_exhaust_routing",
                "grommet_at_frame_pass_through",
            ],
        },
        {
            "id": "chassis_rail_left",
            "priority": 2,
            "label": "Left Chassis Rail",
            "description": "Route along the left-side chassis rail from battery to motor controller",
            "path_type": "chassis_rail",
            "length_estimate_mm": 1900,
            "conduit_required": True,
            "constraints": [
                "secure_at_300mm_intervals",
                "avoid_brake_lines",
                "grommet_at_frame_pass_through",
            ],
        },
        {
            "id": "underbody_center",
            "priority": 3,
            "label": "Underbody Centre Tunnel",
            "description": "Route through the central underbody tunnel, best protection",
            "path_type": "underbody_tunnel",
            "length_estimate_mm": 1600,
            "conduit_required": True,
            "constraints": [
                "protective_skid_plate_recommended",
                "ground_clearance_min_160mm",
                "drainage_grommets_required",
            ],
        },
    ],
    "four_wheeler": [
        {
            "id": "underbody_tunnel",
            "priority": 1,
            "label": "Underbody Centre Tunnel",
            "description": "Route through the transmission tunnel under the cabin floor",
            "path_type": "underbody_tunnel",
            "length_estimate_mm": 2500,
            "conduit_required": True,
            "constraints": [
                "secure_at_300mm_intervals",
                "avoid_heat_shield_contact",
                "grommet_at_bulkhead_pass_through",
            ],
        },
        {
            "id": "chassis_rail_driver",
            "priority": 2,
            "label": "Driver-Side Chassis Rail",
            "description": "Route along the driver-side chassis rail from battery to front controller",
            "path_type": "chassis_rail",
            "length_estimate_mm": 2800,
            "conduit_required": True,
            "constraints": [
                "secure_at_300mm_intervals",
                "avoid_fuel_line_route",
                "protective_loom_required",
            ],
        },
    ],
    "motorcycle": [
        {
            "id": "frame_spine",
            "priority": 1,
            "label": "Frame Spine (Top Tube)",
            "description": "Route along the frame spine / top tube from battery to controller",
            "path_type": "frame_spine",
            "length_estimate_mm": 800,
            "conduit_required": True,
            "constraints": [
                "secure_at_150mm_intervals",
                "abrasion_protection_at_clamps",
                "minimal_exposure_to_elements",
            ],
        },
        {
            "id": "frame_down_tube",
            "priority": 2,
            "label": "Frame Down Tube",
            "description": "Route along the frame down tube, shielded by forks",
            "path_type": "down_tube",
            "length_estimate_mm": 700,
            "conduit_required": True,
            "constraints": [
                "avoid_exhaust_heat_zone",
                "secure_with_p-clips",
                "waterproof_connectors",
            ],
        },
    ],
}


def _identify_caution_zones(
    routing: dict, deviation_result: dict | None
) -> list[dict]:
    zones: list[dict] = []
    if not deviation_result:
        return zones

    deviations = deviation_result.get("deviations", [])
    for dev in deviations:
        param = (dev.get("parameter") or "").lower()
        loc = (dev.get("location") or "").lower()
        severity = dev.get("severity", "low")
        delta = abs(dev.get("delta_pct", 0))

        if "wheel" in param or "suspension" in param:
            if delta > 5:
                zones.append({
                    "zone_id": "wheel_well",
                    "label": "Wheel Well Proximity",
                    "risk": "moving_part_contact",
                    "severity": severity,
                    "message": f"{param} deviation ({delta:.0f}%) — increased clearance needed",
                })
        if "frame" in param or "chassis" in loc:
            if severity in ("high", "critical"):
                zones.append({
                    "zone_id": "frame_rail_damage",
                    "label": "Frame Rail Deformation",
                    "risk": "structural_compromise",
                    "severity": severity,
                    "message": f"Frame deviation at {loc} — routing path may need offset",
                })
        if "engine" in loc or "motor" in param:
            zones.append({
                "zone_id": "heat_zone",
                "label": "Engine / Motor Heat Zone",
                "risk": "thermal_damage",
                "severity": severity,
                "message": "Route harness with heat shielding through this area",
            })
        if "brake" in param or "fuel" in param:
            zones.append({
                "zone_id": "hazard_proximity",
                "label": "Brake/Fuel Line Proximity",
                "risk": "cross_contamination",
                "severity": severity,
                "message": f"Maintain {150 if severity == 'high' else 75}mm separation from {param}",
            })

    return zones


def _compute_confidence(
    routing: dict, caution_zones: list[dict], deviation_result: dict | None
) -> tuple[str, str]:
    high_risk_zones = [z for z in caution_zones if z.get("severity") in ("high", "critical")]
    if len(high_risk_zones) > 2:
        return "low", "Multiple high-risk caution zones identified along routing path"
    if high_risk_zones:
        return "partial", f"{len(high_risk_zones)} high-severity caution zone(s) along path"
    if deviation_result and deviation_result.get("salvage_potential", 100) < 50:
        return "partial", "Structural condition limits routing confidence"
    return "high", "No conflicts detected along routing path"


def compute_routing(
    vehicle_type: str,
    battery_zone_id: str | None = None,
    deviation_result: dict | None = None,
    geometry_result: dict | None = None,
    oem_data: dict | None = None,
) -> dict:
    templates = list(ROUTING_TEMPLATES.get(vehicle_type, ROUTING_TEMPLATES["three_wheeler"]))

    oem_paths = (oem_data or {}).get("routing_paths", [])
    if oem_paths:
        for path in oem_paths:
            templates.insert(0, {
                "id": f"oem_{getattr(path, 'path_name', 'unknown')}",
                "priority": 0,
                "label": f"OEM: {getattr(path, 'path_name', 'Unknown Path')}",
                "description": f"OEM-specified routing path: {getattr(path, 'path_type', 'chassis_rail')}",
                "path_type": getattr(path, "path_type", "chassis_rail"),
                "length_estimate_mm": getattr(path, "length_estimate_mm", 0) or 2000,
                "conduit_required": True,
                "constraints": list(getattr(path, "constraints", {}).keys() or []),
                "oem": True,
            })

    routings = []
    for template in templates:
        routing = dict(template)
        caution_zones = _identify_caution_zones(routing, deviation_result)
        confidence, reason = _compute_confidence(routing, caution_zones, deviation_result)

        routing["caution_zones"] = caution_zones
        routing["confidence"] = confidence
        routing["confidence_reason"] = reason
        routings.append(routing)

    routings.sort(key=lambda r: r["priority"])

    recommended = routings[0] if routings else None

    if settings.enable_generative_design:
        from ai.generative.refiner import GenerativeRefiner
        deviations = (deviation_result or {}).get("deviations", [])
        battery_zone = {"id": battery_zone_id} if battery_zone_id else None
        refined = GenerativeRefiner().refine_wiring_routing(
            routings, vehicle_type, deviations, battery_zone,
        )
        routings = refined

    return {
        "routing_paths": routings,
        "recommended_path": recommended["id"] if recommended else None,
        "path_count": len(routings),
        "primary_routing_path": recommended["label"] if recommended else None,
        "routing_path": recommended["id"] if recommended else None,
        "caution_zones": recommended["caution_zones"] if recommended else [],
        "confidence": recommended["confidence"] if recommended else "low",
        "confidence_reason": recommended["confidence_reason"] if recommended else "No routing available",
    }
