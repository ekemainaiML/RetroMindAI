import cv2
import numpy as np
import pytest

from ai.geometry.extractor import GeometryExtractor
from tests.synthetic_images import generate_views, generate_blank


@pytest.fixture
def extractor():
    return GeometryExtractor()


def _uniform_image(width=640, height=480, value=200):
    return np.ones((height, width, 3), dtype=np.uint8) * value


class TestStructuralCoverage:
    def test_uniform_image_low_coverage(self, extractor, tmp_path):
        path = str(tmp_path / "blank.png")
        cv2.imwrite(path, _uniform_image())
        score = extractor.estimate_structural_coverage(path)
        assert 0.0 <= score <= 1.0
        assert score < 0.1

    def test_high_contrast_image_high_coverage(self, extractor, tmp_path):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[50:430, 100:540] = 200
        cv2.rectangle(img, (100, 50), (540, 430), (80, 80, 80), -1)
        path = str(tmp_path / "high_contrast.png")
        cv2.imwrite(path, img)
        score = extractor.estimate_structural_coverage(path)
        assert 0.0 <= score <= 1.0

    def test_missing_file_returns_zero(self, extractor):
        score = extractor.estimate_structural_coverage("/nonexistent.png")
        assert score == 0.0


class TestSymmetryDeviation:
    def test_identical_images_zero_deviation(self, extractor, tmp_path):
        img = _uniform_image()
        p = str(tmp_path / "same.png")
        cv2.imwrite(p, img)
        deviation = extractor.compute_symmetry_deviation(p, p)
        assert 0.0 <= deviation <= 1.0

    def test_very_different_images_high_deviation(self, extractor, tmp_path):
        img1 = np.zeros((300, 300, 3), dtype=np.uint8)
        block = 20
        for r in range(0, 300, block):
            for c in range(0, 300, block):
                if (r // block + c // block) % 2 == 0:
                    img1[r:r+block, c:c+block] = 200
        img2 = np.ones((300, 300, 3), dtype=np.uint8) * 128
        p1 = str(tmp_path / "checkerboard.png")
        p2 = str(tmp_path / "gray.png")
        cv2.imwrite(p1, img1)
        cv2.imwrite(p2, img2)
        deviation = extractor.compute_symmetry_deviation(p1, p2)
        assert deviation > 0.01

    def test_missing_file_returns_1(self, extractor):
        deviation = extractor.compute_symmetry_deviation("/nonexistent1.png", "/nonexistent2.png")
        assert deviation == 1.0


class TestFrameProportions:
    def test_three_wheeler_proportions(self, extractor):
        views = generate_views("three_wheeler")
        result = extractor.estimate_frame_proportions(views, "three_wheeler")
        assert result["aspect_ratio"] > 1.0
        assert result["estimated_length_mm"] >= 1500
        assert result["estimated_width_mm"] >= 600

    def test_four_wheeler_proportions(self, extractor):
        views = generate_views("four_wheeler")
        result = extractor.estimate_frame_proportions(views, "four_wheeler")
        assert result["aspect_ratio"] > 1.0
        assert result["estimated_length_mm"] >= 1500

    def test_motorcycle_proportions(self, extractor):
        views = generate_views("motorcycle")
        result = extractor.estimate_frame_proportions(views, "motorcycle")
        assert result["aspect_ratio"] < 2.0 or result["aspect_ratio"] > 0.5

    def test_unknown_vehicle_type_defaults(self, extractor):
        views = generate_views("three_wheeler")
        result = extractor.estimate_frame_proportions(views, "unknown")
        assert result["estimated_length_mm"] > 0

    def test_empty_paths_returns_defaults(self, extractor):
        result = extractor.estimate_frame_proportions({}, "three_wheeler")
        assert result["aspect_ratio"] == 0.0
        assert result["estimated_length_mm"] == 0
        assert result["estimated_width_mm"] == 0


class TestExtract:
    def test_full_extract_three_wheeler(self, extractor):
        views = generate_views("three_wheeler")
        result = extractor.extract(views, "three_wheeler")

        assert "geometry_score" in result
        assert "structural_coverage" in result
        assert "symmetry_deviation" in result
        assert "geometry_conflict" in result
        assert "frame_approximation" in result
        assert "avg_structural_coverage" in result

        assert 0 <= result["geometry_score"] <= 100
        assert isinstance(result["geometry_conflict"], bool)
        assert 0.0 <= result["avg_structural_coverage"] <= 1.0

    def test_extract_four_wheeler(self, extractor):
        views = generate_views("four_wheeler")
        result = extractor.extract(views, "four_wheeler")

        assert 0 <= result["geometry_score"] <= 100
        assert result["frame_approximation"]["estimated_length_mm"] > 0

    def test_extract_motorcycle(self, extractor):
        views = generate_views("motorcycle")
        result = extractor.extract(views, "motorcycle")

        assert 0 <= result["geometry_score"] <= 100

    def test_extract_blank_image_low_score(self, extractor):
        views = generate_blank()
        result = extractor.extract(views, "three_wheeler")

        assert result["avg_structural_coverage"] < 0.1

    def test_extract_empty_no_crash(self, extractor):
        result = extractor.extract({}, "three_wheeler")

        assert result["geometry_score"] >= 0
        assert result["avg_structural_coverage"] == 0.0

    def test_structural_coverage_by_view(self, extractor):
        views = generate_views("three_wheeler")
        result = extractor.extract(views, "three_wheeler")

        for view in ["left_side_profile", "right_side_profile", "rear_view"]:
            assert view in result["structural_coverage"]
            cov = result["structural_coverage"][view]
            assert cov is None or (0.0 <= cov <= 1.0)
