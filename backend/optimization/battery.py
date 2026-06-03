from __future__ import annotations

"""
Battery zone optimizer — computes candidate placement zones from vehicle
geometry, deviation data, and vehicle type constraints.

The optimizer maps each vehicle type to known viable zones, adjusts them
for structural deviations (asymmetry, delamination, salvage), and returns
a priority-ordered list with per-zone constraints and risk assessment.
"""

from core.config import settings

VEHICLE_ZONE_TEMPLATES: dict[str, list[dict]] = {
    "three_wheeler": [
        {
            "id": "under_seat",
            "priority": 1,
            "label": "Under-Seat Battery Tray",
            "position": "under_seat_forward",
            "description": "Battery pack housed beneath the driver seat, forward of rear axle",
            "max_dimensions_mm": {"length": 600, "width": 400, "height": 200},
            "weight_kg": 45,
            "constraints": [
                "max_width_420mm",
                "ground_clearance_min_160mm",
                "ventilation_required",
            ],
            "adaptable": False,
        },
        {
            "id": "cargo_bay",
            "priority": 2,
            "label": "Cargo Bay Floor Mount",
            "position": "cargo_bay_center",
            "description": "Battery pack mounted to the cargo floor, behind passenger cabin",
            "max_dimensions_mm": {"length": 500, "width": 500, "height": 180},
            "weight_kg": 50,
            "constraints": [
                "max_width_520mm",
                "cargo_space_reduction_30pct",
                "tie_down_points_required",
            ],
            "adaptable": True,
        },
        {
            "id": "frame_mounted",
            "priority": 3,
            "label": "Frame Rail Mount (Split Pack)",
            "position": "frame_rails_below",
            "description": "Split battery pack mounted along chassis frame rails",
            "max_dimensions_mm": {"length": 800, "width": 200, "height": 150},
            "weight_kg": 48,
            "constraints": [
                "max_width_220mm_per_rail",
                "protective_skid_plate_required",
                "waterproofing_ip67",
            ],
            "adaptable": True,
        },
    ],
    "four_wheeler": [
        {
            "id": "underfloor_center",
            "priority": 1,
            "label": "Underfloor Skateboard Pack",
            "position": "underfloor_center",
            "description": "Flat battery pack spanning the wheelbase under the cabin floor",
            "max_dimensions_mm": {"length": 1400, "width": 900, "height": 150},
            "weight_kg": 180,
            "constraints": [
                "ground_clearance_min_160mm",
                "structural_cross_members_preserved",
                "thermal_management_required",
            ],
            "adaptable": False,
        },
        {
            "id": "trunk_mount",
            "priority": 2,
            "label": "Trunk / Boot Mount",
            "position": "trunk_rear",
            "description": "Battery pack mounted in the trunk compartment, behind rear seats",
            "max_dimensions_mm": {"length": 700, "width": 900, "height": 350},
            "weight_kg": 150,
            "constraints": [
                "trunk_space_reduction_50pct",
                "ventilation_required",
                "rear_crash_structure_preserved",
            ],
            "adaptable": True,
        },
        {
            "id": "engine_bay",
            "priority": 3,
            "label": "Engine Bay Mount",
            "position": "engine_bay_forward",
            "description": "Compact battery pack mounted in the former engine compartment",
            "max_dimensions_mm": {"length": 500, "width": 600, "height": 400},
            "weight_kg": 100,
            "constraints": [
                "max_width_620mm",
                "heat_shielding_required",
                "weight_distribution_impact",
            ],
            "adaptable": True,
        },
    ],
    "motorcycle": [
        {
            "id": "under_seat_mc",
            "priority": 1,
            "label": "Under-Seat Battery Tray",
            "position": "under_seat_forward",
            "description": "Battery pack housed beneath the rider seat, above swingarm pivot",
            "max_dimensions_mm": {"length": 250, "width": 180, "height": 100},
            "weight_kg": 12,
            "constraints": [
                "seat_height_increase_max_30mm",
                "waterproofing_ip65",
                "ventilation_required",
            ],
            "adaptable": False,
        },
        {
            "id": "fuel_tank_area",
            "priority": 2,
            "label": "Fuel Tank Area (In Place of Tank)",
            "position": "fuel_tank_replacement",
            "description": "Battery pack shaped to fit the fuel tank cavity, above engine",
            "max_dimensions_mm": {"length": 300, "width": 200, "height": 150},
            "weight_kg": 15,
            "constraints": [
                "heat_shielding_required",
                "center_of_gravity_impact",
                "custom_bracket_fabrication",
            ],
            "adaptable": True,
        },
        {
            "id": "side_pannier",
            "priority": 3,
            "label": "Side Pannier Mount",
            "position": "side_pannier_left",
            "description": "Battery pack in a side-mounted pannier, offset to left",
            "max_dimensions_mm": {"length": 200, "width": 150, "height": 300},
            "weight_kg": 10,
            "constraints": [
                "side_profile_increase_max_100mm",
                "balanced_weight_required",
                "protective_cage_required",
            ],
            "adaptable": True,
        },
    ],
}


def _get_deviation_penalty(deviation_result: dict | None) -> int:
    if not deviation_result:
        return 0
    salvage = deviation_result.get("salvage_potential", 100)
    critical = deviation_result.get("critical_delamination", False)
    dscore = deviation_result.get("deviation_score", 100)

    penalty = 0
    if salvage < 40:
        penalty += 2
    elif salvage < 60:
        penalty += 1
    if critical:
        penalty += 3
    if dscore < 30:
        penalty += 2
    elif dscore < 50:
        penalty += 1
    return penalty


def _should_warn_adaptation(deviation_result: dict | None, zone: dict) -> str | None:
    if not deviation_result:
        return None
    salvage = deviation_result.get("salvage_potential", 100)
    dscore = deviation_result.get("deviation_score", 100)

    if salvage < 40 and not zone.get("adaptable"):
        return (
            f"Low salvage potential ({salvage}%) conflicts with "
            f"non-adaptable zone '{zone['id']}'"
        )
    if dscore < 50:
        return (
            f"High deviation score ({dscore}) suggests structural assessment "
            f"needed before {zone['id']} installation"
        )
    return None


def _sort_key(zone: dict) -> tuple:
    return (zone["priority"], zone["id"])


def compute_battery_zones(
    vehicle_type: str,
    deviation_result: dict | None = None,
    geometry_result: dict | None = None,
    oem_data: dict | None = None,
) -> dict:
    templates = VEHICLE_ZONE_TEMPLATES.get(vehicle_type, VEHICLE_ZONE_TEMPLATES["three_wheeler"])

    zones = []
    penalty = _get_deviation_penalty(deviation_result)

    oem_mounting_points = (oem_data or {}).get("mounting_points", [])
    if oem_mounting_points:
        battery_points = [mp for mp in oem_mounting_points if getattr(mp, "point_type", "") == "battery"]
        if battery_points:
            oem_zone = {
                "id": "oem_battery_location",
                "priority": 0,
                "label": "OEM-Recommended Battery Location",
                "position": "oem_specified",
                "description": f"Battery placement based on OEM mounting points ({battery_points[0].point_name})",
                "max_dimensions_mm": {"length": 600, "width": 400, "height": 200},
                "weight_kg": 50,
                "constraints": ["oem_specification", "factory_mounting_points_available"],
                "adaptable": False,
                "oem": True,
                "warnings": [],
                "adapted": False,
                "adaptation_reason": None,
            }
            zones.append(oem_zone)

    for template in templates:
        zone = dict(template)
        zone["priority"] = min(zone["priority"] + penalty, 5)

        chain_warnings = []
        adaptation_warning = _should_warn_adaptation(deviation_result, zone)
        if adaptation_warning:
            chain_warnings.append(adaptation_warning)

        if geometry_result:
            geo_conf = geometry_result.get("geometry_consistency", 100)
            if geo_conf < 40 and zone.get("adaptable"):
                chain_warnings.append(
                    "Low geometry consistency limits zone adaptation confidence"
                )

        zone["warnings"] = chain_warnings
        zone["adapted"] = len(chain_warnings) > 0
        zone["adaptation_reason"] = (
            chain_warnings[0] if chain_warnings else None
        )
        zones.append(zone)

    zones.sort(key=_sort_key)

    if settings.enable_generative_design:
        from ai.generative.refiner import GenerativeRefiner
        deviations = (deviation_result or {}).get("deviations", [])
        refined = GenerativeRefiner().refine_battery_zones(
            zones, vehicle_type, deviations, geometry_result,
        )
        zones = refined

    return {
        "zones": zones,
        "recommended_zone": zones[0]["id"] if zones else None,
        "zone_count": len(zones),
        "deviation_adjusted": penalty > 0,
        "deviation_penalty": penalty,
    }
