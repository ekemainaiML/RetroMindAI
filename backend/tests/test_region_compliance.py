"""Tests for region-specific compliance rules (ICAT, ARAI)."""

from __future__ import annotations

import pytest
from core.regions import compute_region_compliance, COMPLIANCE_STATES
from core.compliance import compute_compliance_state, compute_compliance_detail


def _make_assessment(**overrides) -> dict:
    return {
        "vehicle_classification": {"type": "four_wheeler", "confidence": 0.92},
        "geometry_extraction": {"symmetry_deviation": 0.15, "geometry_score": 85},
        "deviation_result": {"critical_delamination": False, "deviation_count": 0, "salvage_potential": 80},
        "deviations": [],
        "risks": [],
        "recommendations": [],
        "battery_placement": {
            "zones": [{
                "id": "underfloor_center",
                "weight_kg": 150,
                "constraints": [
                    "ground_clearance_min_160mm",
                    "waterproofing_ip67",
                    "tie_down_points_required",
                    "structural_cross_members_preserved",
                    "ventilation_required",
                    "protective_skid_plate_required",
                    "balanced_weight_required",
                    "thermal_management_required",
                ],
                "max_dimensions_mm": {"length": 800, "width": 400, "height": 200},
            }],
            "recommended_zone": "underfloor_center",
            "zone_count": 1,
        },
        "wiring_guidance": {
            "routing_paths": [{
                "id": "chassis_rail_right",
                "constraints": ["secure_at_300mm_intervals", "ground_clearance_min_160mm"],
                "length_estimate_mm": 2500,
                "caution_zones": [],
            }],
            "recommended_path": "chassis_rail_right",
        },
        "oem": {"kerb_weight_kg": 1200, "gross_weight_kg": 1600, "ground_clearance_mm": 180},
        **overrides,
    }


# ── ICAT Tests ─────────────────────────────────────────────────────────────


class TestICATCompliance:
    def test_icat_pass_with_caveats(self):
        state, rules = compute_region_compliance("icat", _make_assessment())
        assert state == "pass_with_caveats"
        assert len(rules) > 0

    def test_icat_ground_clearance_fail(self):
        data = _make_assessment()
        data["deviations"] = [{
            "parameter": "ground_clearance_mm",
            "estimated": 140,
            "reference": 180,
            "delta": -40,
            "severity": "major",
        }]
        state, rules = compute_region_compliance("icat", data)
        assert state == "fail"
        assert any(r["rule"] == "CLR-001" for r in rules)

    def test_icat_ground_clearance_marginal(self):
        data = _make_assessment()
        data["deviations"] = [{
            "parameter": "ground_clearance_mm",
            "estimated": 165,
            "reference": 180,
            "delta": -15,
            "severity": "minor",
        }]
        state, rules = compute_region_compliance("icat", data)
        assert state == "pass_with_caveats"
        assert any(r["rule"] == "CLR-002" for r in rules)

    def test_icat_structural_deviation_fail(self):
        data = _make_assessment()
        data["deviations"] = [
            {"parameter": "wheelbase_mm", "estimated": 2200, "reference": 2500, "delta": -300, "severity": "major"},
            {"parameter": "ground_clearance_mm", "estimated": 170, "reference": 180, "delta": -10, "severity": "minor"},
        ]
        state, rules = compute_region_compliance("icat", data)
        assert state == "fail"
        assert any(r["rule"] == "STR-001" for r in rules)

    def test_icat_missing_battery_tie_down(self):
        data = _make_assessment()
        data["battery_placement"]["zones"][0]["constraints"] = [
            "ground_clearance_min_160mm", "waterproofing_ip67",
        ]
        state, rules = compute_region_compliance("icat", data)
        assert state == "pass_with_caveats"
        assert any(r["rule"] == "BAT-002" for r in rules)

    def test_icat_no_battery_data(self):
        data = _make_assessment()
        data["battery_placement"] = {}
        state, rules = compute_region_compliance("icat", data)
        assert state == "insufficient_evidence"
        assert any(r["rule"] == "BAT-001" for r in rules)

    def test_icat_missing_wiring_conduit(self):
        data = _make_assessment()
        data["wiring_guidance"]["routing_paths"][0]["constraints"] = []
        state, rules = compute_region_compliance("icat", data)
        assert state == "pass_with_caveats"
        assert any(r["rule"] == "WIR-002" for r in rules)

    def test_icat_no_wiring_data(self):
        data = _make_assessment()
        data["wiring_guidance"] = {}
        state, rules = compute_region_compliance("icat", data)
        assert state == "insufficient_evidence"
        assert any(r["rule"] == "WIR-001" for r in rules)

    def test_icat_missing_waterproofing(self):
        data = _make_assessment()
        data["battery_placement"]["zones"][0]["constraints"] = [
            "ground_clearance_min_160mm", "tie_down_points_required",
        ]
        state, rules = compute_region_compliance("icat", data)
        assert state == "pass_with_caveats"
        assert any(r["rule"] == "BAT-003" for r in rules)

    def test_icat_thermal_management(self):
        data = _make_assessment()
        data["battery_placement"]["zones"][0]["constraints"] = [
            "thermal_management_required",
        ]
        state, rules = compute_region_compliance("icat", data)
        assert state == "pass_with_caveats"
        assert any(r["rule"] == "BAT-004" for r in rules)

    def test_icat_skid_plate(self):
        data = _make_assessment()
        data["battery_placement"]["zones"][0]["constraints"] = [
            "protective_skid_plate_required",
        ]
        state, rules = compute_region_compliance("icat", data)
        assert state == "pass_with_caveats"
        assert any(r["rule"] == "BAT-005" for r in rules)

    def test_icat_symmetry_issue(self):
        data = _make_assessment()
        data["geometry_extraction"]["symmetry_deviation"] = 0.55
        state, rules = compute_region_compliance("icat", data)
        assert state == "pass_with_caveats"
        assert any(r["rule"] == "GEO-001" for r in rules)

    def test_icat_multiple_violations_worst_wins(self):
        data = _make_assessment()
        data["deviations"] = [
            {"parameter": "ground_clearance_mm", "estimated": 140, "reference": 180, "delta": -40, "severity": "major"},
        ]
        data["battery_placement"] = {}
        state, rules = compute_region_compliance("icat", data)
        assert state == "fail"
        assert any(r["rule"] == "CLR-001" for r in rules)
        assert any(r["rule"] == "BAT-001" for r in rules)

    def test_icat_invalid_region_fallback(self):
        state, rules = compute_region_compliance("invalid_region", _make_assessment())
        assert state == "pass"
        assert rules == []


# ── ARAI Tests ─────────────────────────────────────────────────────────────


class TestARAICOMPLIANCE:
    def test_arai_pass_with_caveats(self):
        state, rules = compute_region_compliance("arai", _make_assessment())
        assert state == "pass_with_caveats"
        assert len(rules) > 0

    def test_arai_ground_clearance_fail(self):
        data = _make_assessment()
        data["deviations"] = [
            {"parameter": "ground_clearance_mm", "estimated": 140, "reference": 180, "delta": -40, "severity": "major"},
        ]
        state, rules = compute_region_compliance("arai", data)
        assert state == "fail"
        assert any(r["rule"] == "CLR-001" for r in rules)

    def test_arai_unknown_vehicle(self):
        data = _make_assessment()
        data["vehicle_classification"]["type"] = "unknown"
        state, rules = compute_region_compliance("arai", data)
        assert state == "insufficient_evidence"
        assert any(r["rule"] == "VEH-001" for r in rules)

    def test_arai_low_confidence(self):
        data = _make_assessment()
        data["vehicle_classification"]["confidence"] = 0.35
        state, rules = compute_region_compliance("arai", data)
        assert state == "pass_with_caveats"
        assert any(r["rule"] == "VEH-002" for r in rules)

    def test_arai_gvw_exceeded(self):
        data = _make_assessment()
        data["oem"] = {"kerb_weight_kg": 1200, "gross_weight_kg": 1300}
        data["battery_placement"]["zones"][0]["weight_kg"] = 200
        state, rules = compute_region_compliance("arai", data)
        assert state == "fail"
        assert any(r["rule"] == "GVW-001" for r in rules)

    def test_arai_gvw_near_limit(self):
        data = _make_assessment()
        data["oem"] = {"kerb_weight_kg": 1200, "gross_weight_kg": 1500}
        data["battery_placement"]["zones"][0]["weight_kg"] = 200
        state, rules = compute_region_compliance("arai", data)
        assert state == "pass_with_caveats"
        assert any(r["rule"] == "GVW-002" for r in rules)

    def test_arai_low_structural_score(self):
        data = _make_assessment()
        data["geometry_extraction"]["geometry_score"] = 25
        state, rules = compute_region_compliance("arai", data)
        assert state == "fail"
        assert any(r["rule"] == "GEO-002" for r in rules)

    def test_arai_brake_compatibility(self):
        data = _make_assessment()
        data["risks"] = [
            {"category": "deviation", "severity": "high", "message": "Brake system may be incompatible"},
        ]
        state, rules = compute_region_compliance("arai", data)
        assert state == "pass_with_caveats"
        assert any(r["rule"] == "BRK-001" for r in rules)

    def test_arai_low_salvage_potential(self):
        data = _make_assessment()
        data["deviation_result"]["salvage_potential"] = 30
        data["deviations"] = [
            {"parameter": "wheelbase_mm", "estimated": 2400, "reference": 2500, "delta": -100, "severity": "moderate"},
        ]
        state, rules = compute_region_compliance("arai", data)
        assert state == "pass_with_caveats"
        assert any(r["rule"] == "VEH-003" for r in rules)

    def test_arai_weight_distribution(self):
        data = _make_assessment()
        data["battery_placement"]["zones"][0]["constraints"] = ["balanced_weight_required"]
        state, rules = compute_region_compliance("arai", data)
        assert state == "pass_with_caveats"
        assert any(r["rule"] == "BAT-007" for r in rules)


# ── Integration: compute_compliance_state with region ──────────────────────


class TestComplianceStateWithRegion:
    def test_generic_no_region_unchanged(self):
        state = compute_compliance_state(
            assessment_state="full_confidence",
            risk_state="normal",
            confidence_score=88,
        )
        assert state == "pass"

    def test_icat_region_escalates(self):
        data = _make_assessment()
        data["deviations"] = [
            {"parameter": "ground_clearance_mm", "estimated": 140, "reference": 180, "delta": -40, "severity": "major"},
        ]
        state = compute_compliance_state(
            assessment_state="full_confidence",
            risk_state="normal",
            confidence_score=88,
            region="icat",
            assessment_data=data,
        )
        assert state == "fail"

    def test_arai_region_escalates(self):
        data = _make_assessment()
        data["vehicle_classification"]["type"] = "unknown"
        state = compute_compliance_state(
            assessment_state="full_confidence",
            risk_state="normal",
            confidence_score=88,
            region="arai",
            assessment_data=data,
        )
        assert state == "insufficient_evidence"

    def test_generic_ignores_region_rules(self):
        data = _make_assessment()
        data["deviations"] = [
            {"parameter": "ground_clearance_mm", "estimated": 140, "reference": 180, "delta": -40, "severity": "major"},
        ]
        state = compute_compliance_state(
            assessment_state="full_confidence",
            risk_state="normal",
            confidence_score=88,
            region="generic",
            assessment_data=data,
        )
        assert state == "pass"

    def test_compliance_detail_returns_rules(self):
        data = _make_assessment()
        data["deviations"] = [
            {"parameter": "ground_clearance_mm", "estimated": 140, "reference": 180, "delta": -40, "severity": "major"},
        ]
        detail = compute_compliance_detail(
            assessment_state="full_confidence",
            risk_state="normal",
            confidence_score=88,
            region="icat",
            assessment_data=data,
        )
        assert detail["compliance_state"] == "fail"
        assert detail["compliance_region"] == "icat"
        assert len(detail["compliance_rules"]) > 0

    def test_compliance_detail_generic_no_rules(self):
        detail = compute_compliance_detail(
            assessment_state="full_confidence",
            risk_state="normal",
            confidence_score=88,
            region="generic",
        )
        assert detail["compliance_state"] == "pass"
        assert "compliance_rules" not in detail
