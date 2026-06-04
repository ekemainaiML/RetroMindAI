from core.compliance import compute_compliance_state


class TestComplianceState:
    def test_full_confidence_pass(self):
        state = compute_compliance_state(
            assessment_state="full_confidence",
            risk_state="normal",
            confidence_score=88,
        )
        assert state == "pass"

    def test_reduced_confidence_is_pass_with_caveats(self):
        state = compute_compliance_state(
            assessment_state="reduced_confidence",
            risk_state="normal",
        )
        assert state == "pass_with_caveats"

    def test_partial_assessment_is_pass_with_caveats(self):
        state = compute_compliance_state(
            assessment_state="partial_assessment",
            risk_state="normal",
        )
        assert state == "pass_with_caveats"

    def test_unsafe_to_assess_is_insufficient_evidence(self):
        state = compute_compliance_state(
            assessment_state="unsafe_to_assess",
            risk_state="critical",
        )
        assert state == "insufficient_evidence"

    def test_critical_risk_fail(self):
        state = compute_compliance_state(
            assessment_state="full_confidence",
            risk_state="critical",
            risk_counts={"critical": 1},
        )
        assert state == "fail"

    def test_critical_count_fail(self):
        state = compute_compliance_state(
            assessment_state="full_confidence",
            risk_state="normal",
            risk_counts={"critical": 1, "high": 0},
        )
        assert state == "fail"

    def test_one_high_is_pass_with_caveats(self):
        state = compute_compliance_state(
            assessment_state="full_confidence",
            risk_state="elevated",
            risk_counts={"high": 1},
        )
        assert state == "pass_with_caveats"

    def test_critical_deviations_fail(self):
        state = compute_compliance_state(
            assessment_state="full_confidence",
            risk_state="normal",
            critical_deviations=True,
        )
        assert state == "fail"

    def test_deviation_count_over_2_is_pass_with_caveats(self):
        state = compute_compliance_state(
            assessment_state="full_confidence",
            risk_state="normal",
            deviation_count=3,
        )
        assert state == "pass_with_caveats"

    def test_two_missing_mandatory_views_insufficient(self):
        state = compute_compliance_state(
            assessment_state="full_confidence",
            risk_state="normal",
            missing_views=["left_side_profile", "rear_view"],
        )
        assert state == "insufficient_evidence"

    def test_one_missing_mandatory_view_is_pass_with_caveats(self):
        state = compute_compliance_state(
            assessment_state="full_confidence",
            risk_state="normal",
            missing_views=["left_side_profile"],
        )
        assert state == "pass_with_caveats"

    def test_confidence_under_50_insufficient(self):
        state = compute_compliance_state(
            assessment_state="full_confidence",
            risk_state="normal",
            confidence_score=40,
        )
        assert state == "insufficient_evidence"
