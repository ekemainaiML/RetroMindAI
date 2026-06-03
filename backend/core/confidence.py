class ConfidenceEngine:
    WEIGHTS = {
        "completeness": 0.30,
        "quality": 0.20,
        "visibility": 0.20,
        "classification": 0.10,
        "geometry": 0.10,
        "deviation_certainty": 0.10,
    }

    THRESHOLDS = [
        ("full_confidence", 85, 100),
        ("reduced_confidence", 70, 84),
        ("partial_assessment", 50, 69),
        ("unsafe_to_assess", 0, 49),
    ]

    MANDATORY_VIEWS = ["left_side_profile", "right_side_profile", "rear_view"]

    @classmethod
    def compute_score(cls, factors: dict[str, float]) -> float:
        score = sum(
            factors.get(key, 0.0) * weight
            for key, weight in cls.WEIGHTS.items()
        )
        return max(0.0, min(100.0, score))

    @classmethod
    def get_state(cls, score: float) -> str:
        for state_name, lower, upper in cls.THRESHOLDS:
            if lower <= score <= upper:
                return state_name
        return "unsafe_to_assess"

    @classmethod
    def apply_safety_overrides(
        cls, state: str, intake_data: dict
    ) -> str:
        missing_views = intake_data.get("missing_views", [])

        if len(missing_views) >= 2:
            return "unsafe_to_assess"

        if len(missing_views) == 1:
            return "partial_assessment"

        classification = intake_data.get("classification", 100.0)
        geometry = intake_data.get("geometry", 100.0)
        mandatory_view_quality = intake_data.get("mandatory_view_quality", {})

        weak_views = any(
            quality is None or quality < 50
            for quality in mandatory_view_quality.values()
        )

        if classification < 40 and geometry < 40 and weak_views:
            return "unsafe_to_assess"

        return state

    @classmethod
    def compute_with_modifiers(
        cls,
        factors: dict[str, float],
        intake_data: dict,
        degradation: list[str],
    ) -> tuple[float, str, list[str]]:
        modified = dict(factors)
        reasons: list[str] = []

        if intake_data.get("human_confirmed"):
            current_class = modified.get("classification", 0.0)
            if current_class < 75:
                modified["classification"] = 75.0
                reasons.append("Human confirmation boosted classification to 75")

        for factor in degradation:
            if factor in modified:
                modified[factor] *= 0.5
                reasons.append(f"Factor '{factor}' halved due to degradation")

        score = cls.compute_score(modified)
        state = cls.get_state(score)
        final_state = cls.apply_safety_overrides(state, intake_data)

        if final_state != state:
            if len(missing := intake_data.get("missing_views", [])) >= 2:
                reasons.append("Missing >= 2 mandatory views: unsafe_to_assess")
            elif len(missing) == 1:
                reasons.append("Missing 1 mandatory view: partial_assessment")
            else:
                reasons.append("Severe contradiction with weak views: unsafe_to_assess")

        return score, final_state, reasons
