RISK_SEVERITIES = ["low", "medium", "high", "critical"]


def compute_system_risk_state(risks: list[dict]) -> str:
    counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for r in risks:
        sev = r.get("severity", "low")
        if sev in counts:
            counts[sev] += 1

    if counts["critical"] > 0:
        return "critical"
    if counts["high"] >= 3:
        return "critical"
    if counts["high"] >= 1:
        return "elevated"
    return "normal"


def is_recommendation_blocked(system_risk_state: str) -> bool:
    return system_risk_state == "critical"


def create_risk_record(
    category: str,
    severity: str,
    message: str,
    recommendation: str,
    blocking: bool,
    confidence: float,
) -> dict:
    return {
        "category": category,
        "severity": severity,
        "message": message,
        "recommendation": recommendation,
        "blocking": blocking,
        "confidence": round(confidence, 2),
    }


def assess_deviation_risks(deviation_result: dict | None) -> list[dict]:
    if deviation_result is None:
        return []

    risks: list[dict] = []

    critical_delamination = deviation_result.get("critical_delamination", False)
    deviations = deviation_result.get("deviations", [])
    high_severity_count = deviation_result.get("high_severity_count", 0)

    wheelbase_major = any(
        d.get("severity") == "major" and d.get("parameter") == "wheelbase_mm"
        for d in deviations
    )

    if critical_delamination and wheelbase_major:
        risks.append(
            create_risk_record(
                category="deviation",
                severity="high",
                message="Critical delamination detected with major wheelbase deviation",
                recommendation="Inspect frame integrity before proceeding with conversion",
                blocking=True,
                confidence=0.90,
            )
        )

    if high_severity_count > 0:
        params_summary = ", ".join(
            d["parameter"].replace("_mm", " (mm)")
            for d in deviations
            if d["severity"] == "major"
        )
        msg = f"Major structural deviations detected: {params_summary}"
        severity = "medium" if not (critical_delamination and wheelbase_major) else "high"
        risks.append(
            create_risk_record(
                category="deviation",
                severity=severity,
                message=msg,
                recommendation="Review structural measurements and consider professional inspection",
                blocking=severity == "high",
                confidence=0.85,
            )
        )

    return risks
