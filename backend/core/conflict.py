def evaluate_classification_conflict(
    classification_conf: float,
    alternatives: list[dict],
    geometry_consistency: float,
    mandatory_view_quality: dict[str, float | None],
) -> dict:
    if classification_conf >= 85:
        return {"action": "none", "state": None}

    if classification_conf >= 50:
        return {
            "action": "human_confirmation",
            "state": None,
            "options": list(alternatives),
        }

    weak_views = any(
        q is None or q < 50 for q in mandatory_view_quality.values()
    )
    if classification_conf < 40 and geometry_consistency < 40 and weak_views:
        return {
            "action": "unsafe_override",
            "state": "unsafe_to_assess",
            "reason": "severe_contradiction",
        }

    return {
        "action": "partial_downgrade",
        "state": "partial_assessment",
        "reason": "unresolved_model_conflict",
    }
