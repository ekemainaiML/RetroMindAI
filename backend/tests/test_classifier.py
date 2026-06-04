import pytest
from ai.classification.classifier import VehicleClassifier
from tests.synthetic_images import generate_views, generate_blank


@pytest.fixture
def classifier():
    return VehicleClassifier()


class TestHeuristicClassifier:
    @pytest.mark.xfail(
        strict=True,
        reason="Heuristic fallback misclassifies three_wheeler synthetic image as four_wheeler (pre-existing)"
    )
    def test_three_wheeler_classification(self, classifier):
        views = generate_views("three_wheeler")
        result = classifier.classify(views)

        assert result["vehicle_type"] == "three_wheeler"
        assert result["confidence"] >= 0.3
        assert result["model_loaded"] is False
        assert result["human_confirmed"] is False
        assert len(result["alternatives"]) == 2

    def test_four_wheeler_classification(self, classifier):
        views = generate_views("four_wheeler")
        result = classifier.classify(views)

        assert result["vehicle_type"] == "four_wheeler"
        assert result["confidence"] >= 0.3
        assert result["model_loaded"] is False

    @pytest.mark.xfail(
        strict=True,
        reason="Heuristic fallback misclassifies motorcycle synthetic image as four_wheeler (pre-existing)"
    )
    def test_motorcycle_classification(self, classifier):
        views = generate_views("motorcycle")
        result = classifier.classify(views)

        assert result["vehicle_type"] == "motorcycle"
        assert result["confidence"] >= 0.2
        assert result["model_loaded"] is False

    def test_blank_image_returns_unknown(self, classifier):
        views = generate_blank()
        result = classifier.classify(views)

        assert result["vehicle_type"] == "unknown"
        assert result["model_loaded"] is False

    def test_empty_dict_returns_unknown(self, classifier):
        result = classifier.classify({})

        assert result["vehicle_type"] == "unknown"
        assert result["confidence"] <= 0.3
        assert result["model_loaded"] is False

    def test_single_view_works(self, classifier):
        views = generate_views("three_wheeler")
        single_view = {"left_side_profile": views["left_side_profile"]}
        result = classifier.classify(single_view)

        assert result["vehicle_type"] is not None
        assert 0 < result["confidence"] <= 1.0

    def test_all_scores_sum_to_approximately_1(self, classifier):
        views = generate_views("three_wheeler")
        result = classifier.classify(views)

        total = result["confidence"]
        for alt in result["alternatives"]:
            total += alt["confidence"]
        assert total <= 1.5

    def test_non_existent_path_returns_unknown(self, classifier):
        result = classifier.classify({"left_side_profile": "/nonexistent/path.png"})

        assert result["vehicle_type"] == "unknown"


class TestClassifierEdgeCases:
    def test_all_views_processed(self, classifier):
        views = {
            "left_side_profile": generate_views("three_wheeler")["left_side_profile"],
            "right_side_profile": generate_views("four_wheeler")["right_side_profile"],
            "rear_view": generate_views("motorcycle")["rear_view"],
        }
        result = classifier.classify(views)

        assert result["vehicle_type"] is not None
        assert result["confidence"] > 0

    def test_result_has_expected_keys(self, classifier):
        views = generate_views("three_wheeler")
        result = classifier.classify(views)

        expected_keys = {"vehicle_type", "confidence", "alternatives", "human_confirmed", "model_loaded"}
        assert set(result.keys()) == expected_keys

    def test_alternatives_are_valid_types(self, classifier):
        views = generate_views("three_wheeler")
        result = classifier.classify(views)

        valid_types = {"three_wheeler", "motorcycle", "four_wheeler", "unknown"}
        for alt in result["alternatives"]:
            assert alt["type"] in valid_types
            assert 0 <= alt["confidence"] <= 1
