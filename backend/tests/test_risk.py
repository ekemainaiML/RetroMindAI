
from core.conflict import evaluate_classification_conflict
from core.risk import (
    compute_system_risk_state,
    create_risk_record,
    is_recommendation_blocked,
)


class TestComputeSystemRiskState:
    def test_any_critical(self):
        risks = [
            {"severity": "low"},
            {"severity": "critical"},
            {"severity": "high"},
        ]
        assert compute_system_risk_state(risks) == "critical"

    def test_three_or_more_high(self):
        risks = [
            {"severity": "high"},
            {"severity": "high"},
            {"severity": "high"},
        ]
        assert compute_system_risk_state(risks) == "critical"

    def test_four_high(self):
        risks = [
            {"severity": "high"},
            {"severity": "high"},
            {"severity": "high"},
            {"severity": "high"},
        ]
        assert compute_system_risk_state(risks) == "critical"

    def test_one_high(self):
        risks = [{"severity": "high"}]
        assert compute_system_risk_state(risks) == "elevated"

    def test_one_high_with_medium(self):
        risks = [
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "medium"},
        ]
        assert compute_system_risk_state(risks) == "elevated"

    def test_all_low(self):
        risks = [{"severity": "low"}, {"severity": "low"}]
        assert compute_system_risk_state(risks) == "normal"

    def test_empty_risks(self):
        assert compute_system_risk_state([]) == "normal"

    def test_mixed_no_critical_or_high(self):
        risks = [
            {"severity": "medium"},
            {"severity": "low"},
            {"severity": "medium"},
        ]
        assert compute_system_risk_state(risks) == "normal"


class TestIsRecommendationBlocked:
    def test_critical_is_blocked(self):
        assert is_recommendation_blocked("critical") is True

    def test_elevated_not_blocked(self):
        assert is_recommendation_blocked("elevated") is False

    def test_normal_not_blocked(self):
        assert is_recommendation_blocked("normal") is False

    def test_unknown_state_not_blocked(self):
        assert is_recommendation_blocked("unknown") is False


class TestCreateRiskRecord:
    def test_basic_record(self):
        record = create_risk_record(
            category="image_quality",
            severity="high",
            message="Blurry image detected",
            recommendation="Re-upload with better lighting",
            blocking=True,
            confidence=0.85,
        )
        assert record["category"] == "image_quality"
        assert record["severity"] == "high"
        assert record["message"] == "Blurry image detected"
        assert record["recommendation"] == "Re-upload with better lighting"
        assert record["blocking"] is True
        assert record["confidence"] == 0.85

    def test_confidence_rounding(self):
        record = create_risk_record(
            category="test",
            severity="low",
            message="test",
            recommendation="none",
            blocking=False,
            confidence=0.666666,
        )
        assert record["confidence"] == 0.67


class TestEvaluateClassificationConflict:
    def test_high_confidence_no_conflict(self):
        result = evaluate_classification_conflict(
            classification_conf=90,
            alternatives=[{"vehicle_type": "three_wheeler", "confidence": 0.9}],
            geometry_consistency=85,
            mandatory_view_quality={
                "left_side_profile": 90,
                "right_side_profile": 85,
                "rear_view": 80,
            },
        )
        assert result["action"] == "none"
        assert result["state"] is None

    def test_ambiguous_requires_human_confirmation(self):
        result = evaluate_classification_conflict(
            classification_conf=65,
            alternatives=[
                {"vehicle_type": "three_wheeler", "confidence": 0.65},
                {"vehicle_type": "motorcycle", "confidence": 0.30},
            ],
            geometry_consistency=80,
            mandatory_view_quality={
                "left_side_profile": 90,
                "right_side_profile": 85,
                "rear_view": 80,
            },
        )
        assert result["action"] == "human_confirmation"
        assert result["state"] is None
        assert len(result["options"]) == 2

    def test_severe_contradiction(self):
        result = evaluate_classification_conflict(
            classification_conf=35,
            alternatives=[],
            geometry_consistency=30,
            mandatory_view_quality={
                "left_side_profile": 20,
                "right_side_profile": None,
                "rear_view": 15,
            },
        )
        assert result["action"] == "unsafe_override"
        assert result["state"] == "unsafe_to_assess"
        assert result["reason"] == "severe_contradiction"

    def test_contradiction_but_good_views_no_severe(self):
        result = evaluate_classification_conflict(
            classification_conf=35,
            alternatives=[],
            geometry_consistency=30,
            mandatory_view_quality={
                "left_side_profile": 80,
                "right_side_profile": 85,
                "rear_view": 90,
            },
        )
        assert result["action"] == "partial_downgrade"
        assert result["reason"] == "unresolved_model_conflict"

    def test_unresolved_partial_downgrade(self):
        result = evaluate_classification_conflict(
            classification_conf=45,
            alternatives=[],
            geometry_consistency=90,
            mandatory_view_quality={
                "left_side_profile": 80,
                "right_side_profile": 85,
                "rear_view": 90,
            },
        )
        assert result["action"] == "partial_downgrade"
        assert result["state"] == "partial_assessment"
        assert result["reason"] == "unresolved_model_conflict"

    def test_boundary_50_requires_confirmation(self):
        result = evaluate_classification_conflict(
            classification_conf=50,
            alternatives=[{"vehicle_type": "three_wheeler", "confidence": 0.5}],
            geometry_consistency=90,
            mandatory_view_quality={
                "left_side_profile": 90,
                "right_side_profile": 85,
                "rear_view": 80,
            },
        )
        assert result["action"] == "human_confirmation"

    def test_boundary_84_requires_confirmation(self):
        result = evaluate_classification_conflict(
            classification_conf=84,
            alternatives=[{"vehicle_type": "three_wheeler", "confidence": 0.84}],
            geometry_consistency=90,
            mandatory_view_quality={
                "left_side_profile": 90,
                "right_side_profile": 85,
                "rear_view": 80,
            },
        )
        assert result["action"] == "human_confirmation"
