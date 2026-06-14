COMPLIANCE_STATES = ["not_assessed", "pass", "pass_with_caveats", "fail", "insufficient_evidence"]


def compute_compliance_state(
    assessment_state: str,
    risk_state: str,
    risk_counts: dict | None = None,
    missing_views: list[str] | None = None,
    critical_deviations: bool = False,
    deviation_count: int = 0,
    confidence_score: int = 100,
    region: str = "generic",
    assessment_data: dict | None = None,
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

    base = "pass"

    if region in ("icat", "arai") and assessment_data:
        from core.regions import compute_region_compliance
        region_state, _ = compute_region_compliance(region, assessment_data)
        state_rank = {"fail": 4, "insufficient_evidence": 3, "pass_with_caveats": 2, "pass": 1}
        if state_rank.get(region_state, 0) > state_rank.get(base, 0):
            base = region_state

    return base


def compute_compliance_detail(
    assessment_state: str,
    risk_state: str,
    risk_counts: dict | None = None,
    missing_views: list[str] | None = None,
    critical_deviations: bool = False,
    deviation_count: int = 0,
    confidence_score: int = 100,
    region: str = "generic",
    assessment_data: dict | None = None,
) -> dict:
    """Like compute_compliance_state but returns full detail dict with rule results."""
    state = compute_compliance_state(
        assessment_state=assessment_state,
        risk_state=risk_state,
        risk_counts=risk_counts,
        missing_views=missing_views,
        critical_deviations=critical_deviations,
        deviation_count=deviation_count,
        confidence_score=confidence_score,
        region=region,
        assessment_data=assessment_data,
    )
    result: dict = {"compliance_state": state}

    if region in ("icat", "arai") and assessment_data:
        from core.regions import compute_region_compliance
        _, rules = compute_region_compliance(region, assessment_data)
        result["compliance_region"] = region
        result["compliance_rules"] = rules

    return result
