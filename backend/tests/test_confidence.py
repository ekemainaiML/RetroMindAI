
from core.confidence import ConfidenceEngine


class TestComputeScore:
    def test_all_factors_max(self):
        factors = {
            "completeness": 100,
            "quality": 100,
            "visibility": 100,
            "classification": 100,
            "geometry": 100,
            "deviation_certainty": 100,
        }
        score = ConfidenceEngine.compute_score(factors)
        assert score == 100.0

    def test_all_factors_min(self):
        factors = {
            "completeness": 0,
            "quality": 0,
            "visibility": 0,
            "classification": 0,
            "geometry": 0,
            "deviation_certainty": 0,
        }
        score = ConfidenceEngine.compute_score(factors)
        assert score == 0.0

    def test_mixed_factors(self):
        factors = {
            "completeness": 66,
            "quality": 67,
            "visibility": 50,
            "classification": 85,
            "geometry": 70,
            "deviation_certainty": 65,
        }
        score = ConfidenceEngine.compute_score(factors)
        expected = (
            66 * 0.30 + 67 * 0.20 + 50 * 0.20 + 85 * 0.10 + 70 * 0.10 + 65 * 0.10
        )
        assert score == expected

    def test_clamps_above_100(self):
        factors = dict.fromkeys(ConfidenceEngine.WEIGHTS, 200)
        score = ConfidenceEngine.compute_score(factors)
        assert score == 100.0

    def test_clamps_below_0(self):
        factors = dict.fromkeys(ConfidenceEngine.WEIGHTS, -50)
        score = ConfidenceEngine.compute_score(factors)
        assert score == 0.0

    def test_missing_factors_default_to_zero(self):
        score = ConfidenceEngine.compute_score({"completeness": 100})
        assert score == 30.0


class TestGetState:
    def test_full_confidence(self):
        assert ConfidenceEngine.get_state(85) == "full_confidence"
        assert ConfidenceEngine.get_state(92) == "full_confidence"
        assert ConfidenceEngine.get_state(100) == "full_confidence"

    def test_reduced_confidence(self):
        assert ConfidenceEngine.get_state(70) == "reduced_confidence"
        assert ConfidenceEngine.get_state(78) == "reduced_confidence"
        assert ConfidenceEngine.get_state(84) == "reduced_confidence"

    def test_partial_assessment(self):
        assert ConfidenceEngine.get_state(50) == "partial_assessment"
        assert ConfidenceEngine.get_state(60) == "partial_assessment"
        assert ConfidenceEngine.get_state(69) == "partial_assessment"

    def test_unsafe_to_assess(self):
        assert ConfidenceEngine.get_state(0) == "unsafe_to_assess"
        assert ConfidenceEngine.get_state(25) == "unsafe_to_assess"
        assert ConfidenceEngine.get_state(49) == "unsafe_to_assess"

    def test_boundary_values(self):
        assert ConfidenceEngine.get_state(85) == "full_confidence"
        assert ConfidenceEngine.get_state(84) == "reduced_confidence"
        assert ConfidenceEngine.get_state(70) == "reduced_confidence"
        assert ConfidenceEngine.get_state(69) == "partial_assessment"
        assert ConfidenceEngine.get_state(50) == "partial_assessment"
        assert ConfidenceEngine.get_state(49) == "unsafe_to_assess"


class TestApplySafetyOverrides:
    def test_missing_two_views(self):
        result = ConfidenceEngine.apply_safety_overrides(
            "full_confidence",
            {
                "missing_views": ["left_side_profile", "rear_view"],
                "mandatory_view_quality": {},
                "classification": 90,
                "geometry": 85,
            },
        )
        assert result == "unsafe_to_assess"

    def test_missing_three_views(self):
        result = ConfidenceEngine.apply_safety_overrides(
            "full_confidence",
            {
                "missing_views": [
                    "left_side_profile",
                    "right_side_profile",
                    "rear_view",
                ],
                "mandatory_view_quality": {},
                "classification": 90,
                "geometry": 85,
            },
        )
        assert result == "unsafe_to_assess"

    def test_missing_one_view(self):
        result = ConfidenceEngine.apply_safety_overrides(
            "full_confidence",
                {
                "missing_views": ["left_side_profile"],
                "mandatory_view_quality": {},
                "classification": 90,
                "geometry": 85,
            },
        )
        assert result == "partial_assessment"

    def test_severe_contradiction(self):
        result = ConfidenceEngine.apply_safety_overrides(
            "reduced_confidence",
            {
                "missing_views": [],
                "mandatory_view_quality": {
                    "left_side_profile": 30,
                    "right_side_profile": 45,
                    "rear_view": None,
                },
                "classification": 35,
                "geometry": 30,
            },
        )
        assert result == "unsafe_to_assess"

    def test_no_overrides(self):
        result = ConfidenceEngine.apply_safety_overrides(
            "full_confidence",
            {
                "missing_views": [],
                "mandatory_view_quality": {
                    "left_side_profile": 85,
                    "right_side_profile": 90,
                    "rear_view": 80,
                },
                "classification": 90,
                "geometry": 85,
            },
        )
        assert result == "full_confidence"


class TestComputeWithModifiers:
    def test_human_confirmed_boosts_classification(self):
        factors = {
            "completeness": 100,
            "quality": 100,
            "visibility": 100,
            "classification": 58,
            "geometry": 100,
            "deviation_certainty": 100,
        }
        score, state, reasons = ConfidenceEngine.compute_with_modifiers(
            factors=factors,
            intake_data={"human_confirmed": True, "missing_views": [], "mandatory_view_quality": {}, "classification": 58, "geometry": 100},
            degradation=[],
        )
        assert "Human confirmation boosted classification to 75" in reasons
        expected = (
            100 * 0.30 + 100 * 0.20 + 100 * 0.20 + 75 * 0.10 + 100 * 0.10 + 100 * 0.10
        )
        assert score == expected

    def test_degradation_halves_factor(self):
        factors = {
            "completeness": 100,
            "quality": 60,
            "visibility": 100,
            "classification": 100,
            "geometry": 100,
            "deviation_certainty": 100,
        }
        score, state, reasons = ConfidenceEngine.compute_with_modifiers(
            factors=factors,
            intake_data={"missing_views": [], "mandatory_view_quality": {}, "classification": 100, "geometry": 100},
            degradation=["quality"],
        )
        assert "Factor 'quality' halved due to degradation" in reasons
        expected = (
            100 * 0.30 + 30 * 0.20 + 100 * 0.20 + 100 * 0.10 + 100 * 0.10 + 100 * 0.10
        )
        assert score == expected

    def test_full_pipeline(self):
        factors = {
            "completeness": 100,
            "quality": 100,
            "visibility": 100,
            "classification": 85,
            "geometry": 100,
            "deviation_certainty": 100,
        }
        score, state, reasons = ConfidenceEngine.compute_with_modifiers(
            factors=factors,
            intake_data={
                "missing_views": ["left_side_profile"],
                "mandatory_view_quality": {"left_side_profile": None, "right_side_profile": 90, "rear_view": 85},
                "classification": 85,
                "geometry": 100,
            },
            degradation=[],
        )
        assert state == "partial_assessment"
        assert "Missing 1 mandatory view" in reasons[0]
