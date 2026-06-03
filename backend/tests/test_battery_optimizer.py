import pytest

from optimization.battery import (
    VEHICLE_ZONE_TEMPLATES,
    compute_battery_zones,
)


class TestBatteryZoneTemplates:
    def test_all_vehicle_types_have_templates(self):
        for vtype in ("three_wheeler", "four_wheeler", "motorcycle"):
            assert vtype in VEHICLE_ZONE_TEMPLATES

    def test_each_type_has_at_least_2_zones(self):
        for vtype, zones in VEHICLE_ZONE_TEMPLATES.items():
            assert len(zones) >= 2, f"{vtype} has fewer than 2 zones"

    def test_each_zone_has_required_keys(self):
        required = {"id", "priority", "label", "position", "max_dimensions_mm", "constraints"}
        for zones in VEHICLE_ZONE_TEMPLATES.values():
            for zone in zones:
                assert required.issubset(zone.keys()), f"Zone {zone['id']} missing keys"


class TestComputeBatteryZones:
    def test_returns_recommended_zone_for_three_wheeler(self):
        result = compute_battery_zones("three_wheeler")
        assert result["recommended_zone"] == "under_seat"
        assert result["zone_count"] == 3
        assert result["deviation_adjusted"] is False

    def test_returns_recommended_zone_for_four_wheeler(self):
        result = compute_battery_zones("four_wheeler")
        assert result["recommended_zone"] == "underfloor_center"
        assert result["zone_count"] == 3

    def test_returns_recommended_zone_for_motorcycle(self):
        result = compute_battery_zones("motorcycle")
        assert result["recommended_zone"] == "under_seat_mc"
        assert result["zone_count"] == 3

    def test_defaults_to_three_wheeler_for_unknown_type(self):
        result = compute_battery_zones("unknown")
        assert result["recommended_zone"] == "under_seat"

    def test_deviation_penalty_increases_priority(self):
        clean = compute_battery_zones("three_wheeler")
        deviated = compute_battery_zones("three_wheeler", {
            "salvage_potential": 30,
            "critical_delamination": True,
            "deviation_score": 20,
            "deviations": [{"parameter": "frame_twist", "severity": "high"}],
        })
        assert deviated["deviation_adjusted"] is True
        assert deviated["deviation_penalty"] >= 3

    def test_adaptation_warning_for_low_salvage(self):
        result = compute_battery_zones("three_wheeler", {
            "salvage_potential": 25,
            "deviation_score": 60,
            "deviations": [],
        })
        for zone in result["zones"]:
            if not zone["adaptable"]:
                assert len(zone["warnings"]) > 0
                assert zone["adapted"] is True

    def test_zones_sorted_by_priority(self):
        result = compute_battery_zones("three_wheeler")
        priorities = [z["priority"] for z in result["zones"]]
        assert priorities == sorted(priorities)

    def test_zone_has_warnings_list(self):
        result = compute_battery_zones("three_wheeler")
        for zone in result["zones"]:
            assert "warnings" in zone
            assert "adapted" in zone

    def test_geometry_consistency_affects_adaptable_zones(self):
        result = compute_battery_zones(
            "three_wheeler",
            geometry_result={"geometry_consistency": 25},
        )
        adaptable = [z for z in result["zones"] if z.get("adaptable")]
        assert all(len(z["warnings"]) > 0 for z in adaptable)
