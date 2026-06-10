import logging

logger = logging.getLogger(__name__)

_VEHICLE_DIMENSIONS = {
    "three_wheeler": {"length": 2800, "width": 1200, "height": 1700},
    "motorcycle": {"length": 2000, "width": 800, "height": 1100},
    "four_wheeler": {"length": 4000, "width": 1700, "height": 1500},
}

_DEVIATION_LOCATIONS = {
    "wheelbase_mm": "chassis_center",
    "overall_length_mm": "chassis_front_rear",
    "overall_width_mm": "chassis_width",
    "ground_clearance_mm": "underbody",
    "cargo_length_mm": "cargo_area",
}

_DEVIATION_3D_POSITIONS = {
    "chassis_center": {"x": 0.0, "y": 0.0, "z": 0.0},
    "chassis_front_rear": {"x": 0.0, "y": 0.0, "z": 0.0},
    "chassis_width": {"x": 0.0, "y": 0.0, "z": 0.0},
    "underbody": {"x": 0.0, "y": -0.5, "z": 0.0},
    "cargo_area": {"x": 0.0, "y": -0.1, "z": -0.5},
}

_SEVERITY_COLORS = {
    "minor": "#3b82f6",
    "moderate": "#f59e0b",
    "major": "#ef4444",
}

_COMPONENT_TEMPLATES = {
    "battery_pack_location": {
        "id": "battery_pack",
        "label": "48V LiFePO4 Battery",
        "position": {"x": 0.0, "y": -0.3, "z": 0.2},
        "color": "#10b981",
        "size": {"w": 0.6, "h": 0.2, "d": 0.4},
    },
    "motor_selection": {
        "id": "motor",
        "label": "4kW BLDC Hub Motor",
        "position": {"x": 0.0, "y": -0.2, "z": -0.6},
        "color": "#f97316",
        "size": {"w": 0.2, "h": 0.2, "d": 0.2},
    },
    "controller_and_bms": {
        "id": "controller",
        "label": "48V 100A Controller + BMS",
        "position": {"x": 0.0, "y": 0.1, "z": 0.4},
        "color": "#8b5cf6",
        "size": {"w": 0.3, "h": 0.1, "d": 0.2},
    },
    "wiring_harness": {
        "id": "wiring_harness",
        "label": "48V Wiring Harness",
        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
        "color": "#6366f1",
        "size": {"w": 0.8, "h": 0.02, "d": 0.02},
    },
    "structural_reinforcement": {
        "id": "frame_reinforcement",
        "label": "Frame Stiffening",
        "position": {"x": 0.0, "y": -0.1, "z": 0.0},
        "color": "#a855f7",
        "size": {"w": 1.0, "h": 0.05, "d": 0.05},
    },
    "regenerative_braking": {
        "id": "regenerative_braking",
        "label": "Regen Braking Controller",
        "position": {"x": 0.2, "y": 0.1, "z": 0.3},
        "color": "#06b6d4",
        "size": {"w": 0.15, "h": 0.08, "d": 0.1},
    },
}


_BATTERY_ZONE_POSITIONS = {
    "three_wheeler": {
        "under_seat_forward": {"x": 0.0, "y": -0.25, "z": 0.25},
        "under_seat_rear": {"x": 0.0, "y": -0.25, "z": -0.15},
        "underbody_center": {"x": 0.0, "y": -0.45, "z": 0.0},
        "underbody_rear": {"x": 0.0, "y": -0.40, "z": -0.35},
        "engine_bay": {"x": 0.0, "y": -0.10, "z": 0.55},
        "cargo_bay": {"x": 0.0, "y": -0.20, "z": -0.50},
        "frame_mounted_left": {"x": -0.35, "y": -0.30, "z": 0.0},
        "frame_mounted_right": {"x": 0.35, "y": -0.30, "z": 0.0},
    },
    "four_wheeler": {
        "underfloor_front": {"x": 0.0, "y": -0.30, "z": 0.35},
        "underfloor_center": {"x": 0.0, "y": -0.35, "z": 0.0},
        "underfloor_rear": {"x": 0.0, "y": -0.30, "z": -0.35},
        "trunk": {"x": 0.0, "y": -0.05, "z": -0.45},
        "engine_bay": {"x": 0.0, "y": -0.10, "z": 0.55},
        "frame_mounted_left": {"x": -0.45, "y": -0.25, "z": 0.0},
        "frame_mounted_right": {"x": 0.45, "y": -0.25, "z": 0.0},
    },
    "motorcycle": {
        "under_seat": {"x": 0.0, "y": -0.05, "z": 0.05},
        "tank_area": {"x": 0.0, "y": -0.05, "z": 0.25},
        "side_mounted_left": {"x": -0.20, "y": -0.15, "z": 0.0},
        "side_mounted_right": {"x": 0.20, "y": -0.15, "z": 0.0},
        "rear_rack": {"x": 0.0, "y": 0.0, "z": -0.30},
    },
}

_BATTERY_DEFAULT_SIZE: dict[str, dict[str, float]] = {
    "three_wheeler": {"w": 0.6, "h": 0.22, "d": 0.4},
    "four_wheeler": {"w": 0.8, "h": 0.18, "d": 0.5},
    "motorcycle": {"w": 0.3, "h": 0.12, "d": 0.2},
}

_HEAT_ZONE_DEFAULTS: dict[str, dict[str, list[dict]]] = {
    "three_wheeler": {
        "rear": [
            {"id": "exhaust_area", "label": "Exhaust / Engine Bay", "position": {"x": 0.0, "y": -0.1, "z": -0.5}, "radius": 0.35, "severity": "high", "temperature_c": 120, "source": "oem_default"},
            {"id": "motor_area", "label": "Motor Heat Zone", "position": {"x": 0.0, "y": -0.2, "z": -0.6}, "radius": 0.25, "severity": "medium", "temperature_c": 70, "source": "oem_default"},
        ],
        "front": [
            {"id": "exhaust_area", "label": "Exhaust / Engine Bay", "position": {"x": 0.0, "y": -0.1, "z": 0.5}, "radius": 0.35, "severity": "high", "temperature_c": 120, "source": "oem_default"},
            {"id": "motor_area", "label": "Motor Heat Zone", "position": {"x": 0.0, "y": -0.2, "z": 0.4}, "radius": 0.25, "severity": "medium", "temperature_c": 70, "source": "oem_default"},
        ],
        "mid": [
            {"id": "exhaust_area", "label": "Exhaust / Engine Bay", "position": {"x": 0.0, "y": -0.1, "z": 0.0}, "radius": 0.35, "severity": "high", "temperature_c": 120, "source": "oem_default"},
        ],
    },
    "four_wheeler": {
        "front": [
            {"id": "radiator", "label": "Radiator / Engine Bay", "position": {"x": 0.0, "y": -0.1, "z": 0.55}, "radius": 0.35, "severity": "high", "temperature_c": 110, "source": "oem_default"},
            {"id": "exhaust_manifold", "label": "Exhaust Manifold", "position": {"x": 0.0, "y": -0.2, "z": 0.3}, "radius": 0.25, "severity": "medium", "temperature_c": 80, "source": "oem_default"},
        ],
        "rear": [
            {"id": "exhaust_pipe", "label": "Exhaust / Muffler", "position": {"x": 0.0, "y": -0.2, "z": -0.50}, "radius": 0.3, "severity": "medium", "temperature_c": 70, "source": "oem_default"},
        ],
        "mid": [
            {"id": "catalytic_converter", "label": "Catalytic Converter", "position": {"x": 0.0, "y": -0.25, "z": 0.0}, "radius": 0.25, "severity": "high", "temperature_c": 95, "source": "oem_default"},
        ],
    },
    "motorcycle": {
        "front": [
            {"id": "engine_block", "label": "Engine Block", "position": {"x": 0.15, "y": -0.1, "z": 0.2}, "radius": 0.25, "severity": "high", "temperature_c": 115, "source": "oem_default"},
            {"id": "exhaust_header", "label": "Exhaust Header", "position": {"x": 0.1, "y": -0.15, "z": 0.0}, "radius": 0.2, "severity": "medium", "temperature_c": 85, "source": "oem_default"},
        ],
        "rear": [
            {"id": "muffler", "label": "Muffler / Silencer", "position": {"x": -0.25, "y": -0.15, "z": -0.35}, "radius": 0.2, "severity": "medium", "temperature_c": 65, "source": "oem_default"},
        ],
    },
}


_WAYPOINTS_MAP: dict[str, dict[str, list[dict[str, float]]]] = {
    "three_wheeler": {
        "under_seat_forward": [
            {"x": 0.0, "y": -0.1, "z": 0.3}, {"x": 0.0, "y": 0.05, "z": 0.2}, {"x": 0.0, "y": -0.1, "z": -0.3}, {"x": 0.0, "y": -0.2, "z": -0.6},
        ],
        "underbody_center": [
            {"x": 0.0, "y": -0.1, "z": 0.3}, {"x": 0.0, "y": -0.3, "z": 0.0}, {"x": 0.0, "y": -0.3, "z": -0.3}, {"x": 0.0, "y": -0.2, "z": -0.6},
        ],
    },
    "four_wheeler": {
        "underfloor_front_to_rear": [
            {"x": 0.0, "y": -0.1, "z": 0.5}, {"x": 0.0, "y": -0.3, "z": 0.3}, {"x": 0.0, "y": -0.35, "z": 0.0}, {"x": 0.0, "y": -0.3, "z": -0.3}, {"x": 0.0, "y": -0.1, "z": -0.5},
        ],
        "underfloor_center": [
            {"x": 0.0, "y": -0.1, "z": 0.3}, {"x": 0.0, "y": -0.35, "z": 0.0}, {"x": 0.0, "y": -0.35, "z": -0.3}, {"x": 0.0, "y": -0.1, "z": -0.5},
        ],
        "trunk_run": [
            {"x": 0.0, "y": -0.1, "z": 0.3}, {"x": 0.0, "y": -0.2, "z": 0.0}, {"x": 0.0, "y": -0.1, "z": -0.3}, {"x": 0.0, "y": 0.0, "z": -0.45},
        ],
    },
    "motorcycle": {
        "under_seat_to_motor": [
            {"x": 0.0, "y": -0.05, "z": 0.25}, {"x": 0.0, "y": 0.0, "z": 0.1}, {"x": 0.0, "y": -0.05, "z": -0.1}, {"x": 0.0, "y": -0.15, "z": -0.3},
        ],
        "frame_rail": [
            {"x": 0.0, "y": -0.05, "z": 0.3}, {"x": 0.0, "y": -0.1, "z": 0.0}, {"x": 0.0, "y": -0.1, "z": -0.2},
        ],
    },
}


class DigitalTwinDataGenerator:
    def generate(
        self, assessment_result: dict, vehicle_type: str
    ) -> dict:
        dimensions = _VEHICLE_DIMENSIONS.get(
            vehicle_type, _VEHICLE_DIMENSIONS["three_wheeler"]
        )

        deviations_3d = self._build_deviations_3d(assessment_result)
        retrofit_components = self._build_retrofit_components(assessment_result)
        battery_fitment = self._build_battery_fitment(assessment_result, vehicle_type)
        thermal_zones = self._build_thermal_zones(assessment_result, vehicle_type)
        wiring_routes = self._build_wiring_routes(assessment_result, vehicle_type)

        result = {
            "vehicle_type": vehicle_type,
            "dimensions": dict(dimensions),
            "deviations_3d": deviations_3d,
            "retrofit_components": retrofit_components,
            "battery_fitment": battery_fitment,
            "thermal_zones": thermal_zones,
            "wiring_routes": wiring_routes,
            "view_angles": {
                "default_camera": {"theta": 0.8, "phi": 0.6, "radius": 4.0}
            },
        }

        if battery_fitment is None:
            result.pop("battery_fitment")

        return result

    def _build_deviations_3d(self, assessment_result: dict) -> list[dict]:
        deviation_result = assessment_result.get("deviation_result")
        if not deviation_result:
            return []

        raw_deviations = deviation_result.get("deviations", [])
        deviations_3d = []
        for d in raw_deviations:
            parameter = d.get("parameter", "unknown")
            severity = d.get("severity", "minor")
            location_key = _DEVIATION_LOCATIONS.get(parameter, "chassis_center")
            color = _SEVERITY_COLORS.get(severity, "#3b82f6")

            deviations_3d.append({
                "parameter": parameter,
                "location": location_key,
                "severity": severity,
                "delta_pct": d.get("delta_pct", 0.0),
                "color": color,
            })

        return deviations_3d

    def _build_retrofit_components(
        self, assessment_result: dict
    ) -> list[dict]:
        recommendations = assessment_result.get("recommendations", [])
        if not recommendations:
            return []

        top_recs = recommendations[:3]
        components = []
        for rec in top_recs:
            rec_id = rec.get("id", "")
            template = _COMPONENT_TEMPLATES.get(rec_id)

            if template is None:
                category = rec.get("category", "general")
                if category == "battery":
                    template = _COMPONENT_TEMPLATES["battery_pack_location"]
                elif category == "motor":
                    template = _COMPONENT_TEMPLATES["motor_selection"]
                elif category == "controller":
                    template = _COMPONENT_TEMPLATES["controller_and_bms"]
                else:
                    template = {
                        "id": rec_id,
                        "label": rec.get("title", rec_id),
                        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "color": "#6b7280",
                        "size": {"w": 0.2, "h": 0.1, "d": 0.1},
                    }

            component = {
                "id": template["id"],
                "label": template["label"],
                "position": dict(template["position"]),  # type: ignore[arg-type]
                "color": template["color"],
                "size": dict(template["size"]),  # type: ignore[arg-type]
            }
            components.append(component)

        return components

    def _build_battery_fitment(self, assessment_result: dict, vehicle_type: str) -> dict | None:
        battery_placement = assessment_result.get("battery_placement")
        if not battery_placement:
            return None

        zones = battery_placement.get("zones", [])
        recommended_id = battery_placement.get("recommended_zone")

        recommended = next((z for z in zones if z.get("id") == recommended_id), zones[0] if zones else None)
        if not recommended:
            return None

        position = self._resolve_battery_position(recommended, vehicle_type)
        clearance = self._compute_clearance(recommended)
        confidence = battery_placement.get("confidence", 100)
        battery_size = _BATTERY_DEFAULT_SIZE.get(vehicle_type, _BATTERY_DEFAULT_SIZE["three_wheeler"])

        return {
            "zone_id": recommended.get("id", "A"),
            "label": recommended.get("label", "Battery Pack"),
            "position": position,
            "size": dict(battery_size),
            "clearance": clearance,
            "fitment_status": "tight" if confidence < 60 else "clear",
        }

    @staticmethod
    def _resolve_battery_position(zone: dict, vehicle_type: str) -> dict[str, float]:
        zone_map = _BATTERY_ZONE_POSITIONS.get(vehicle_type, _BATTERY_ZONE_POSITIONS["three_wheeler"])
        raw = zone.get("position", "") or zone.get("label", "").lower()
        for key, pos in zone_map.items():
            if key.replace("_", " ") in raw or key in raw:
                return dict(pos)
        fallback = _BATTERY_ZONE_POSITIONS["three_wheeler"]["underbody_center"]
        return dict(fallback)

    @staticmethod
    def _compute_clearance(zone: dict) -> dict[str, int]:
        constraints = zone.get("constraints") or []
        defaults = {"front": 15, "rear": 20, "left": 10, "right": 10, "top": 25, "bottom": 30}
        for c in constraints:
            for axis in ("front", "rear", "left", "right", "top", "bottom"):
                if axis in c.lower():
                    try:
                        val = int("".join(filter(str.isdigit, c)))
                        if val > 0:
                            defaults[axis] = val
                    except (ValueError, IndexError):
                        pass
        return defaults

    @staticmethod
    def _build_thermal_zones(assessment_result: dict, vehicle_type: str) -> list[dict]:
        zones: list[dict] = []

        vehicle_defaults = _HEAT_ZONE_DEFAULTS.get(vehicle_type, _HEAT_ZONE_DEFAULTS["three_wheeler"])
        geometry_result = assessment_result.get("geometry_result")
        engine_comp = (geometry_result or {}).get("engine_bay_compartment", "rear")

        defaults = vehicle_defaults.get(engine_comp, vehicle_defaults.get("front", []))
        zones.extend(defaults)

        deviations = (assessment_result.get("deviation_result") or {}).get("deviations", [])
        for d in deviations:
            notes = d.get("notes", "")
            parameter = d.get("parameter", "unknown")
            if "heat" in notes.lower() or "thermal" in notes.lower():
                location = _DEVIATION_LOCATIONS.get(parameter, "chassis_center")
                zones.append({
                    "id": f"thermal_deviation_{parameter}",
                    "label": d.get("notes", f"Heat anomaly: {parameter}"),
                    "position": dict(_DEVIATION_3D_POSITIONS.get(location, {"x": 0, "y": 0, "z": 0})),
                    "radius": 0.25,
                    "severity": "high",
                    "temperature_c": 80,
                    "source": "deviation_detection",
                })

        return zones

    @staticmethod
    def _build_wiring_routes(assessment_result: dict, vehicle_type: str) -> list[dict]:
        vehicle_waypoints = _WAYPOINTS_MAP.get(vehicle_type, _WAYPOINTS_MAP["three_wheeler"])
        wiring = assessment_result.get("wiring_guidance")
        if wiring:
            recommended_route = wiring.get("recommended_route") or (wiring.get("routes") or [None])[0]
            if recommended_route:
                route_id = recommended_route.get("id", "under_seat_forward")
                waypoints = vehicle_waypoints.get(route_id, vehicle_waypoints.get("under_seat_forward", list(vehicle_waypoints.values())[0]))
                return [
                    {
                        "id": route_id,
                        "label": recommended_route.get("label", "Primary HV Route"),
                        "waypoints": waypoints,
                        "color": "#f59e0b",
                        "caution_zones": wiring.get("caution_zones", []),
                        "confidence": wiring.get("confidence", 0.5),
                    },
                ]

        battery_placement = assessment_result.get("battery_placement")
        if battery_placement:
            zones = battery_placement.get("zones", [])
            recommended_id = battery_placement.get("recommended_zone")
            recommended = next((z for z in zones if z.get("id") == recommended_id), zones[0] if zones else None)
            if recommended:
                raw = recommended.get("position", "") or recommended.get("label", "").lower()
                route_id = next(iter(vehicle_waypoints))
                for key in vehicle_waypoints:
                    if key.replace("_", " ") in raw or key in raw:
                        route_id = key
                        break
                waypoints = vehicle_waypoints[route_id]
                return [
                    {
                        "id": route_id,
                        "label": f"HV Route ({recommended.get('label', route_id)})",
                        "waypoints": waypoints,
                        "color": "#f59e0b",
                        "caution_zones": [],
                        "confidence": 0.5,
                    },
                ]

        return []
