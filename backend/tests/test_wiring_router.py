import pytest

from optimization.wiring import (
    ROUTING_TEMPLATES,
    compute_routing,
)


class TestWiringTemplates:
    def test_all_vehicle_types_have_templates(self):
        for vtype in ("three_wheeler", "four_wheeler", "motorcycle"):
            assert vtype in ROUTING_TEMPLATES

    def test_each_type_has_at_least_2_routes(self):
        for vtype, routes in ROUTING_TEMPLATES.items():
            assert len(routes) >= 2, f"{vtype} has fewer than 2 routes"

    def test_each_route_has_required_keys(self):
        required = {"id", "priority", "label", "path_type", "constraints"}
        for routes in ROUTING_TEMPLATES.values():
            for route in routes:
                assert required.issubset(route.keys()), f"Route {route['id']} missing keys"


class TestComputeRouting:
    def test_returns_recommended_path_for_three_wheeler(self):
        result = compute_routing("three_wheeler")
        assert result["recommended_path"] == "chassis_rail_right"
        assert result["path_count"] == 3
        assert result["confidence"] in ("high", "partial", "low")

    def test_returns_recommended_path_for_four_wheeler(self):
        result = compute_routing("four_wheeler")
        assert result["recommended_path"] == "underbody_tunnel"

    def test_returns_recommended_path_for_motorcycle(self):
        result = compute_routing("motorcycle")
        assert result["recommended_path"] == "frame_spine"

    def test_defaults_to_three_wheeler_for_unknown_type(self):
        result = compute_routing("unknown")
        assert result["recommended_path"] == "chassis_rail_right"

    def test_confidence_drops_with_deviations(self):
        clean = compute_routing("three_wheeler")
        degraded = compute_routing(
            "three_wheeler",
            deviation_result={
                "salvage_potential": 30,
                "deviation_score": 25,
                "deviations": [
                    {"parameter": "frame_twist", "location": "chassis", "severity": "critical", "delta_pct": 12},
                    {"parameter": "wheel_alignment", "location": "wheel", "severity": "high", "delta_pct": 8},
                    {"parameter": "brake_line", "location": "engine_bay", "severity": "high", "delta_pct": 5},
                ],
            },
        )
        assert degraded["confidence"] in ("partial", "low")

    def test_caution_zones_from_wheel_deviations(self):
        result = compute_routing(
            "three_wheeler",
            deviation_result={
                "salvage_potential": 80,
                "deviation_score": 70,
                "deviations": [
                    {"parameter": "wheel_alignment", "location": "wheel", "severity": "medium", "delta_pct": 6},
                ],
            },
        )
        assert len(result["caution_zones"]) > 0
        assert any(z["zone_id"] == "wheel_well" for z in result["caution_zones"])

    def test_caution_zones_from_frame_deviations(self):
        result = compute_routing(
            "three_wheeler",
            deviation_result={
                "salvage_potential": 80,
                "deviation_score": 70,
                "deviations": [
                    {"parameter": "frame_rail", "location": "chassis", "severity": "high", "delta_pct": 10},
                ],
            },
        )
        assert any(z["zone_id"] == "frame_rail_damage" for z in result["caution_zones"])

    def test_caution_zones_from_heat_source(self):
        result = compute_routing(
            "three_wheeler",
            deviation_result={
                "salvage_potential": 80,
                "deviation_score": 80,
                "deviations": [
                    {"parameter": "motor_mount", "location": "engine_bay", "severity": "medium", "delta_pct": 3},
                ],
            },
        )
        assert any(z["zone_id"] == "heat_zone" for z in result["caution_zones"])

    def test_routing_paths_sorted_by_priority(self):
        result = compute_routing("three_wheeler")
        priorities = [r["priority"] for r in result["routing_paths"]]
        assert priorities == sorted(priorities)

    def test_each_routing_has_confidence_and_caution_zones(self):
        result = compute_routing("three_wheeler")
        for route in result["routing_paths"]:
            assert "confidence" in route
            assert "caution_zones" in route
            assert "confidence_reason" in route
