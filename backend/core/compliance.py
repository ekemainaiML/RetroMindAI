COMPLIANCE_STATES = ["not_assessed", "pass", "pass_with_caveats", "fail", "insufficient_evidence"]


def compute_compliance_state(
    assessment_state: str,
    risk_state: str,
    risk_counts: dict | None = None,
    missing_views: list[str] | None = None,
    critical_deviations: bool = False,
    deviation_count: int = 0,
    confidence_score: int = 100,
) -> str:
    if assessment_state == "unsafe_to_assess":
        return "insufficient_evidence"

    missing_mandatory = sum(
        1 for v in (missing_views or [])
        if v in ("left_side_profile", "right_side_profile", "rear_view")
    )
    if missing_mandatory >= 2:
        return "insufficient_evidence"

    rc = risk_counts or {}
    critical_count = rc.get("critical_count", rc.get("critical", 0))
    high_count = rc.get("high_count", rc.get("high", 0))

    if critical_deviations or critical_count > 0:
        return "fail"

    if risk_state == "critical":
        return "fail"

    if high_count >= 1:
        return "pass_with_caveats"

    if missing_mandatory >= 1:
        return "pass_with_caveats"

    if assessment_state == "partial_assessment":
        return "pass_with_caveats"

    if assessment_state == "reduced_confidence":
        return "pass_with_caveats"

    if deviation_count > 2:
        return "pass_with_caveats"

    if confidence_score < 50:
        return "insufficient_evidence"

    return "pass"
