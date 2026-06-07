def evaluate_classification_conflict(
    classification_conf: float,
    alternatives: list[dict],
    geometry_consistency: float,
    mandatory_view_quality: dict[str, float | None],
) -> dict:
    if classification_conf >= 85:
        return {"action": "none", "state": None}

    weak_views = any(
        q is None or q < 50 for q in mandatory_view_quality.values()
    )

    fallback = None
    if classification_conf < 40 and geometry_consistency < 40 and weak_views:
        fallback = "unsafe_override"
    elif classification_conf < 50:
        fallback = "partial_downgrade"

    return {
        "action": "human_confirmation",
        "options": list(alternatives),
        "fallback": fallback,
    }
