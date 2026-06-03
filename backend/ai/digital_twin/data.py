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


class DigitalTwinDataGenerator:
    def generate(
        self, assessment_result: dict, vehicle_type: str
    ) -> dict:
        dimensions = _VEHICLE_DIMENSIONS.get(
            vehicle_type, _VEHICLE_DIMENSIONS["three_wheeler"]
        )

        deviations_3d = self._build_deviations_3d(assessment_result)
        retrofit_components = self._build_retrofit_components(assessment_result)

        return {
            "vehicle_type": vehicle_type,
            "dimensions": dict(dimensions),
            "deviations_3d": deviations_3d,
            "retrofit_components": retrofit_components,
            "view_angles": {
                "default_camera": {"theta": 0.8, "phi": 0.6, "radius": 4.0}
            },
        }

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
            position = _DEVIATION_3D_POSITIONS.get(location_key, {"x": 0, "y": 0, "z": 0})
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
                "position": dict(template["position"]),
                "color": template["color"],
                "size": dict(template["size"]),
            }
            components.append(component)

        return components
