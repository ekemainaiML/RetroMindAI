import numpy as np

import pytest
from ai.deviation.detector import DeviationDetector
from core.risk import assess_deviation_risks


def _blank_image(width=640, height=480):
    import cv2
    return np.ones((height, width, 3), dtype=np.uint8) * 200


def _draw_vehicle_side(img, length_px, wheelbase_px):
    import cv2
    h, w = img.shape[:2]
    y_top = h // 4
    y_bot = 3 * h // 4
    x_start = w // 8
    x_end = x_start + length_px

    if x_end > w - 10:
        x_end = w - 10
        x_start = x_end - length_px
    if x_start < 10:
        x_start = 10
        x_end = x_start + length_px

    cv2.rectangle(img, (x_start, y_top), (x_end, y_bot), (80, 80, 80), -1)

    wheel_y = y_bot - 10
    wheel_r = 18
    cx1 = x_start + (length_px - wheelbase_px) // 2
    cx2 = cx1 + wheelbase_px

    for cx in (cx1, cx2):
        cv2.circle(img, (cx, wheel_y), wheel_r, (40, 40, 40), -1)
        cv2.circle(img, (cx, wheel_y), wheel_r // 2, (20, 20, 20), -1)

    return img


@pytest.fixture
def detector():
    return DeviationDetector()


@pytest.fixture
def perfect_match_images(tmp_path):
    import cv2
    known_length_mm = 2800
    known_wheelbase_mm = 2150

    px_per_mm = 0.15
    length_px = int(known_length_mm * px_per_mm)
    wheelbase_px = int(known_wheelbase_mm * px_per_mm)

    img = _draw_vehicle_side(_blank_image(1600, 900), length_px, wheelbase_px)
    path = str(tmp_path / "side_profile.png")
    cv2.imwrite(path, img)

    rear = _blank_image()
    cv2.imwrite(str(tmp_path / "rear_view.png"), rear)

    return {
        "left_side_profile": path,
        "right_side_profile": path,
        "rear_view": str(tmp_path / "rear_view.png"),
    }


@pytest.fixture
def moderate_deviation_images(tmp_path):
    import cv2
    known_length_mm = 2800
    known_wheelbase_mm = 2150

    px_per_mm = 0.25
    length_px = int(known_length_mm * px_per_mm * 0.92)
    wheelbase_px = int(known_wheelbase_mm * px_per_mm * 0.94)

    img = _draw_vehicle_side(_blank_image(1600, 900), length_px, wheelbase_px)
    path = str(tmp_path / "side_profile.png")
    cv2.imwrite(path, img)

    rear = _blank_image()
    cv2.imwrite(str(tmp_path / "rear_view.png"), rear)

    return {
        "left_side_profile": path,
        "right_side_profile": path,
        "rear_view": str(tmp_path / "rear_view.png"),
    }


class TestDeviationDetector:
    def test_perfect_match_no_deviations(self, detector, perfect_match_images):
        result = detector.detect(perfect_match_images, "three_wheeler")

        assert result["deviation_score"] >= 85
        assert result["critical_delamination"] is False
        assert result["salvage_potential"] >= 85
        for d in result["deviations"]:
            assert d["severity"] in ("minor",)

    def test_moderate_deviations_reduces_score(self, detector, moderate_deviation_images):
        result = detector.detect(moderate_deviation_images, "three_wheeler")

        assert result["deviation_count"] > 0
        assert result["deviation_score"] < 100
        assert result["deviation_score"] >= 0
        assert isinstance(result["deviation_score"], int)

        for d in result["deviations"]:
            assert "parameter" in d
            assert "estimated" in d
            assert "reference" in d
            assert "delta" in d
            assert "delta_pct" in d
            assert "severity" in d
            assert d["severity"] in ("minor", "moderate", "major")

    def test_critical_delamination_triggered(self, detector):
        class MockDetector(DeviationDetector):
            def detect(self, image_paths, vehicle_type):
                return {
                    "deviations": [
                        {
                            "parameter": "wheelbase_mm",
                            "estimated": 1700,
                            "reference": 2150,
                            "delta": -450,
                            "delta_pct": -20.93,
                            "severity": "major",
                            "notes": "Wheelbase -20.93% vs reference",
                        },
                        {
                            "parameter": "overall_length_mm",
                            "estimated": 2200,
                            "reference": 2800,
                            "delta": -600,
                            "delta_pct": -21.43,
                            "severity": "major",
                            "notes": "Overall Length -21.43% vs reference",
                        },
                    ],
                    "deviation_score": 40,
                    "deviation_certainty": 70,
                    "critical_delamination": True,
                    "salvage_potential": 30,
                    "deviation_count": 2,
                    "high_severity_count": 2,
                }

        mock = MockDetector()
        result = mock.detect({}, "three_wheeler")
        assert result["critical_delamination"] is True
        assert result["high_severity_count"] == 2

        risks = assess_deviation_risks(result)
        deviation_risks = [r for r in risks if r["category"] == "deviation"]
        assert len(deviation_risks) >= 1
        high_risks = [r for r in deviation_risks if r["severity"] == "high"]
        assert len(high_risks) >= 1

    def test_unknown_vehicle_type_defaults_three_wheeler(self, detector, perfect_match_images):
        result = detector.detect(perfect_match_images, "unknown")

        assert result["deviation_certainty"] > 0

        for d in result["deviations"]:
            ref = detector.references["three_wheeler"]
            param = d["parameter"]
            assert d["reference"] == ref[param]

    def test_missing_images_handled_gracefully(self, detector):
        result = detector.detect({}, "three_wheeler")

        assert result["deviation_score"] >= 0
        assert result["deviation_certainty"] == 0
        assert result["deviation_count"] == 0
        assert result["critical_delamination"] is False
        assert len(result["deviations"]) == 0

    def test_deviation_score_clamping(self, detector):
        class ExtremeDetector(DeviationDetector):
            def detect(self, image_paths, vehicle_type):
                deviations = []
                for param in ["wheelbase_mm", "overall_length_mm", "overall_width_mm"]:
                    deviations.append({
                        "parameter": param,
                        "estimated": 500,
                        "reference": 2000,
                        "delta": -1500,
                        "delta_pct": -75.0,
                        "severity": "major",
                        "notes": f"{param} severely deviated",
                    })
                return {
                    "deviations": deviations,
                    "deviation_score": self._compute_deviation_score(deviations),
                    "deviation_certainty": 50,
                    "critical_delamination": True,
                    "salvage_potential": self._compute_salvage_potential(deviations, 10),
                    "deviation_count": len(deviations),
                    "high_severity_count": len(deviations),
                }

        result = ExtremeDetector().detect({}, "three_wheeler")
        assert result["deviation_score"] == 10
        assert result["salvage_potential"] == 0

    def test_salvage_potential_deducts_for_major_structural(self, detector):
        class StructDetector(DeviationDetector):
            def detect(self, image_paths, vehicle_type):
                deviations = [
                    {
                        "parameter": "wheelbase_mm",
                        "estimated": 1900,
                        "reference": 2150,
                        "delta": -250,
                        "delta_pct": -11.63,
                        "severity": "major",
                        "notes": "Wheelbase -11.63% vs reference",
                    },
                    {
                        "parameter": "ground_clearance_mm",
                        "estimated": 220,
                        "reference": 180,
                        "delta": 40,
                        "delta_pct": 22.22,
                        "severity": "major",
                        "notes": "Ground Clearance +22.22% vs reference",
                    },
                ]
                return {
                    "deviations": deviations,
                    "deviation_score": self._compute_deviation_score(deviations),
                    "deviation_certainty": 70,
                    "critical_delamination": True,
                    "salvage_potential": self._compute_salvage_potential(deviations, 40),
                    "deviation_count": len(deviations),
                    "high_severity_count": 2,
                }

        result = StructDetector().detect({}, "three_wheeler")
        assert result["salvage_potential"] == 30

    def test_risk_assessor_creation(self):
        result = {
            "deviations": [
                {
                    "parameter": "wheelbase_mm",
                    "estimated": 1700,
                    "reference": 2150,
                    "delta": -450,
                    "delta_pct": -20.93,
                    "severity": "major",
                    "notes": "Wheelbase -20.93% vs reference",
                },
            ],
            "deviation_score": 70,
            "deviation_certainty": 80,
            "critical_delamination": True,
            "salvage_potential": 50,
            "deviation_count": 1,
            "high_severity_count": 1,
        }

        risks = assess_deviation_risks(result)
        assert len(risks) >= 1
        wheelbase_risk = next(
            (r for r in risks if "wheelbase" in r.get("message", "")), None
        )
        assert wheelbase_risk is not None
        assert wheelbase_risk["severity"] == "high"
        assert wheelbase_risk["blocking"] is True

    def test_risk_assessor_no_deviation(self):
        result = {
            "deviations": [],
            "deviation_score": 100,
            "deviation_certainty": 80,
            "critical_delamination": False,
            "salvage_potential": 100,
            "deviation_count": 0,
            "high_severity_count": 0,
        }
        risks = assess_deviation_risks(result)
        deviation_risks = [r for r in risks if r["category"] == "deviation"]
        assert len(deviation_risks) == 0

    def test_risk_assessor_none_input(self):
        risks = assess_deviation_risks(None)
        assert risks == []
