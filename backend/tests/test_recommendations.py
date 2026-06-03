import pytest
from ai.recommendations.engine import RecommendationEngine


@pytest.fixture
def engine():
    return RecommendationEngine()


@pytest.fixture
def clean_three_wheeler_assessment():
    return {
        "deviation_result": {
            "deviations": [
                {
                    "parameter": "ground_clearance_mm",
                    "estimated": 190,
                    "reference": 180,
                    "delta": 10,
                    "delta_pct": 5.56,
                    "severity": "moderate",
                    "notes": "Ground Clearance +5.56% vs reference",
                },
            ],
            "deviation_score": 85,
            "deviation_certainty": 70,
            "critical_delamination": False,
            "salvage_potential": 90,
            "deviation_count": 1,
            "high_severity_count": 0,
        },
        "geometry_result": {
            "avg_structural_coverage": 0.85,
            "geometry_score": 85,
        },
    }


@pytest.fixture
def damaged_three_wheeler_assessment():
    return {
        "deviation_result": {
            "deviations": [
                {
                    "parameter": "wheelbase_mm",
                    "estimated": 1700,
                    "reference": 2150,
                    "delta": -450,
                    "delta_pct": -20.93,
                    "severity": "major",
                    "notes": "Wheelbase -20.93% vs reference",
                },
                {
                    "parameter": "overall_length_mm",
                    "estimated": 2200,
                    "reference": 2800,
                    "delta": -600,
                    "delta_pct": -21.43,
                    "severity": "major",
                    "notes": "Overall Length -21.43% vs reference",
                },
            ],
            "deviation_score": 40,
            "deviation_certainty": 70,
            "critical_delamination": True,
            "salvage_potential": 30,
            "deviation_count": 2,
            "high_severity_count": 2,
        },
        "geometry_result": {
            "avg_structural_coverage": 0.65,
            "geometry_score": 55,
        },
    }


@pytest.fixture
def motorcycle_assessment():
    return {
        "deviation_result": {
            "deviations": [
                {
                    "parameter": "ground_clearance_mm",
                    "estimated": 170,
                    "reference": 160,
                    "delta": 10,
                    "delta_pct": 6.25,
                    "severity": "moderate",
                    "notes": "Ground Clearance +6.25% vs reference",
                },
            ],
            "deviation_score": 85,
            "deviation_certainty": 70,
            "critical_delamination": False,
            "salvage_potential": 90,
            "deviation_count": 1,
            "high_severity_count": 0,
        },
        "geometry_result": {
            "avg_structural_coverage": 0.80,
            "geometry_score": 80,
        },
    }


@pytest.fixture
def low_salvage_assessment():
    return {
        "deviation_result": {
            "deviations": [
                {
                    "parameter": "overall_length_mm",
                    "estimated": 1800,
                    "reference": 2800,
                    "delta": -1000,
                    "delta_pct": -35.71,
                    "severity": "major",
                    "notes": "Overall Length -35.71% vs reference",
                },
                {
                    "parameter": "wheelbase_mm",
                    "estimated": 1400,
                    "reference": 2150,
                    "delta": -750,
                    "delta_pct": -34.88,
                    "severity": "major",
                    "notes": "Wheelbase -34.88% vs reference",
                },
                {
                    "parameter": "overall_width_mm",
                    "estimated": 900,
                    "reference": 1200,
                    "delta": -300,
                    "delta_pct": -25.00,
                    "severity": "major",
                    "notes": "Overall Width -25.00% vs reference",
                },
            ],
            "deviation_score": 10,
            "deviation_certainty": 80,
            "critical_delamination": False,
            "salvage_potential": 20,
            "deviation_count": 3,
            "high_severity_count": 3,
        },
        "geometry_result": {
            "avg_structural_coverage": 0.90,
            "geometry_score": 90,
        },
    }


class TestRecommendationEngine:
    def test_clean_three_wheeler_standard_recommendations(self, engine, clean_three_wheeler_assessment):
        result = engine.generate(
            clean_three_wheeler_assessment,
            vehicle_type="three_wheeler",
            deviation_severity="low",
            factors={"completeness": 100, "quality": 100, "visibility": 100,
                     "classification": 85, "geometry": 85, "deviation_certainty": 70},
        )

        assert len(result["recommendations"]) == 6
        assert result["feasibility_score"] >= 0
        assert result["feasibility_score"] <= 100
        assert result["estimated_total_cost_inr"]["mid"] > 0
        assert isinstance(result["tooling_required"], list)
        assert len(result["tooling_required"]) > 0
        assert result["skill_level_required"] in ("beginner", "intermediate", "advanced")
        assert result["estimated_days"] > 0

        ids = [r["id"] for r in result["recommendations"]]
        assert "battery_pack_location" in ids
        assert "motor_selection" in ids
        assert "controller_and_bms" in ids
        assert "wiring_harness" in ids
        assert "structural_reinforcement" in ids
        assert "regenerative_braking" in ids

        blocking = [r for r in result["recommendations"] if r.get("blocking")]
        assert len(blocking) == 0

        structural = next(r for r in result["recommendations"] if r["id"] == "structural_reinforcement")
        assert structural["priority"] == "medium"

    def test_structurally_damaged_three_wheeler(self, engine, damaged_three_wheeler_assessment):
        result = engine.generate(
            damaged_three_wheeler_assessment,
            vehicle_type="three_wheeler",
            deviation_severity="high",
            factors={"completeness": 100, "quality": 80, "visibility": 80,
                     "classification": 85, "geometry": 55, "deviation_certainty": 70},
        )

        structural = next(r for r in result["recommendations"] if r["id"] == "structural_reinforcement")
        assert structural["priority"] == "high"
        assert structural["blocking"] is True
        assert "Critical" in " ".join(structural["rationale"])

        blocking = [r for r in result["recommendations"] if r.get("blocking")]
        assert len(blocking) >= 1

        assert result["feasibility_score"] < 75

        motor = next(r for r in result["recommendations"] if r["id"] == "motor_selection")
        costs = motor["estimated_cost_inr"]
        orig_template = engine.templates["three_wheeler"]
        orig_motor = next(r for r in orig_template["recommendations"] if r["id"] == "motor_selection")
        assert costs["mid"] > orig_motor["estimated_cost_inr"]["mid"]

    def test_motorcycle_recommendations(self, engine, motorcycle_assessment):
        result = engine.generate(
            motorcycle_assessment,
            vehicle_type="motorcycle",
            deviation_severity="low",
        )

        assert len(result["recommendations"]) == 6

        battery = next(r for r in result["recommendations"] if r["id"] == "battery_pack_location")
        assert "36V" in battery["description"]
        assert "seat" in battery["description"]

        motor = next(r for r in result["recommendations"] if r["id"] == "motor_selection")
        assert motor["estimated_cost_inr"]["mid"] < 30000

        assert result["estimated_total_cost_inr"]["mid"] > 0

        wiring = next(r for r in result["recommendations"] if r["id"] == "wiring_harness")
        assert wiring["category"] == "wiring"
        assert wiring["priority"] == "medium"

    def test_low_salvage_reduces_feasibility_raises_skill(self, engine, low_salvage_assessment):
        result = engine.generate(
            low_salvage_assessment,
            vehicle_type="three_wheeler",
            deviation_severity="high",
        )

        assert result["feasibility_score"] < 60
        assert result["skill_level_required"] == "advanced"

    def test_cost_estimation_with_different_deviation_levels(self, engine, clean_three_wheeler_assessment):
        low_result = engine.generate(
            clean_three_wheeler_assessment,
            vehicle_type="three_wheeler",
            deviation_severity="low",
        )

        moderate_assessment = dict(clean_three_wheeler_assessment)
        result_med = engine.generate(
            moderate_assessment,
            vehicle_type="three_wheeler",
            deviation_severity="medium",
        )

        assert result_med["estimated_total_cost_inr"]["mid"] > low_result["estimated_total_cost_inr"]["mid"]

    def test_dependency_sequencing(self, engine, clean_three_wheeler_assessment):
        result = engine.generate(
            clean_three_wheeler_assessment,
            vehicle_type="three_wheeler",
            deviation_severity="low",
        )

        rec_by_id = {r["id"]: r for r in result["recommendations"]}
        wiring = rec_by_id["wiring_harness"]
        assert "controller_and_bms" in wiring["depends_on"]

        controller = rec_by_id["controller_and_bms"]
        assert "battery_pack_location" in controller["depends_on"]
        assert "motor_selection" in controller["depends_on"]

        battery = rec_by_id["battery_pack_location"]
        assert battery["depends_on"] == []

        regen = rec_by_id["regenerative_braking"]
        assert "controller_and_bms" in regen["depends_on"]

        for rec in result["recommendations"]:
            for dep in rec["depends_on"]:
                assert dep in rec_by_id

    def test_unknown_vehicle_type_defaults(self, engine, clean_three_wheeler_assessment):
        result = engine.generate(
            clean_three_wheeler_assessment,
            vehicle_type="unknown",
            deviation_severity="low",
        )

        lower_feasibility = result["feasibility_score"] < 75

        battery = next(r for r in result["recommendations"] if r["id"] == "battery_pack_location")
        assert "48V" in battery["description"]

    def test_recommendation_confidence_scores(self, engine, clean_three_wheeler_assessment):
        result = engine.generate(
            clean_three_wheeler_assessment,
            vehicle_type="three_wheeler",
            deviation_severity="low",
        )

        for rec in result["recommendations"]:
            assert 0 <= rec["confidence"] <= 100
            assert isinstance(rec["confidence"], (int, float))

    def test_estimated_days_positive(self, engine, clean_three_wheeler_assessment):
        result = engine.generate(
            clean_three_wheeler_assessment,
            vehicle_type="three_wheeler",
            deviation_severity="low",
        )
        assert result["estimated_days"] >= 1

    def test_cost_structure(self, engine, clean_three_wheeler_assessment):
        result = engine.generate(
            clean_three_wheeler_assessment,
            vehicle_type="three_wheeler",
            deviation_severity="low",
        )
        costs = result["estimated_total_cost_inr"]
        assert costs["low"] <= costs["mid"] <= costs["high"]
        assert costs["mid"] > 0

    def test_empty_assessment_no_crash(self, engine):
        result = engine.generate(
            {},
            vehicle_type="three_wheeler",
            deviation_severity="low",
        )
        assert len(result["recommendations"]) == 6
        assert result["feasibility_score"] == 75
