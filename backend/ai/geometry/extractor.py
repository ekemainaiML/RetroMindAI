import logging
import os

import cv2
import numpy as np

from core.retry import with_retry

logger = logging.getLogger(__name__)

_CENTER_CROP_FRACTION = 0.6

_THREE_WHEELER_LENGTH_MM = 2800
_THREE_WHEELER_WIDTH_MM = 1200
_MOTORCYCLE_LENGTH_MM = 2200
_MOTORCYCLE_WIDTH_MM = 800
_FOUR_WHEELER_LENGTH_MM = 4200
_FOUR_WHEELER_WIDTH_MM = 1700

_VEHICLE_DIMS = {
    "three_wheeler": (_THREE_WHEELER_LENGTH_MM, _THREE_WHEELER_WIDTH_MM),
    "motorcycle": (_MOTORCYCLE_LENGTH_MM, _MOTORCYCLE_WIDTH_MM),
    "four_wheeler": (_FOUR_WHEELER_LENGTH_MM, _FOUR_WHEELER_WIDTH_MM),
}

_STRUCTURAL_VIEW_ORDER = [
    "left_side_profile",
    "right_side_profile",
    "rear_view",
    "front_view",
]

_MANDATORY_VIEWS = ["left_side_profile", "right_side_profile", "rear_view"]


class GeometryExtractor:
    def estimate_structural_coverage(self, image_path: str) -> float:
        img = cv2.imread(image_path)
        if img is None:
            logger.warning("Could not read image: %s", image_path)
            return 0.0

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        h, w = edges.shape
        cx, cy = w // 2, h // 2
        cw = int(w * _CENTER_CROP_FRACTION)
        ch = int(h * _CENTER_CROP_FRACTION)
        x1 = max(0, cx - cw // 2)
        x2 = min(w, cx + cw // 2)
        y1 = max(0, cy - ch // 2)
        y2 = min(h, cy + ch // 2)

        centre = edges[y1:y2, x1:x2]
        if centre.size == 0:
            return 0.0

        centre_edges = np.count_nonzero(centre)
        centre_pixels = centre.size
        centre_density = centre_edges / max(centre_pixels, 1)

        score = min(1.0, centre_density * 10.0)
        return round(score, 4)

    def compute_symmetry_deviation(
        self, left_path: str, right_path: str
    ) -> float:
        left = cv2.imread(left_path)
        right = cv2.imread(right_path)
        if left is None or right is None:
            return 1.0

        target_size = (224, 224)
        left = cv2.resize(left, target_size)
        right = cv2.resize(right, target_size)

        left_gray = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY)
        right_gray = cv2.cvtColor(right, cv2.COLOR_BGR2GRAY)
        left_edges = cv2.Canny(left_gray, 50, 150)
        right_edges = cv2.Canny(right_gray, 50, 150)

        mse = np.mean(
            (left_edges.astype(np.float32) - right_edges.astype(np.float32))
            ** 2
        )

        normalized = min(1.0, mse / 65025.0)
        return round(normalized, 4)  # type: ignore[call-overload]

    def _find_largest_contour_rect(self, image_path: str):
        img = cv2.imread(image_path)
        if img is None:
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return None
        largest = max(contours, key=cv2.contourArea)
        return cv2.boundingRect(largest)

    def estimate_frame_proportions(
        self, image_paths: dict, vehicle_type: str = "three_wheeler"
    ) -> dict:
        img_path = None
        for view in _STRUCTURAL_VIEW_ORDER:
            path = image_paths.get(view)
            if path and os.path.isfile(path):
                img_path = path
                break
        if img_path is None:
            for path in image_paths.values():
                if path and os.path.isfile(path):
                    img_path = path
                    break

        if img_path is None:
            return {
                "aspect_ratio": 0.0,
                "estimated_length_mm": 0,
                "estimated_width_mm": 0,
            }

        rect = self._find_largest_contour_rect(img_path)
        if rect:
            _, _, cw, ch = rect
        else:
            img = cv2.imread(img_path)
            if img is None:
                return {
                    "aspect_ratio": 0.0,
                    "estimated_length_mm": 0,
                    "estimated_width_mm": 0,
                }
            h, w = img.shape[:2]
            cw, ch = w, h

        aspect_ratio = cw / max(ch, 1)

        known_length, known_width = _VEHICLE_DIMS.get(
            vehicle_type, (_THREE_WHEELER_LENGTH_MM, _THREE_WHEELER_WIDTH_MM)
        )
        known_aspect = known_length / max(known_width, 1)

        if aspect_ratio > 1:
            ratio = aspect_ratio / known_aspect if known_aspect > 0 else 1.0
            est_length = int(known_length * ratio)
            est_width = known_width
        else:
            est_length = known_length
            est_width = int(known_width * aspect_ratio) if aspect_ratio > 0 else known_width

        est_length = max(1500, min(4000, est_length))
        est_width = max(600, min(2000, est_width))

        return {
            "aspect_ratio": round(aspect_ratio, 4),
            "estimated_length_mm": est_length,
            "estimated_width_mm": est_width,
        }

    @with_retry(retryable_exceptions=(RuntimeError,))
    def extract(
        self, image_paths: dict[str, str], vehicle_type: str
    ) -> dict:
        structural_coverage = {}
        for view_name in _STRUCTURAL_VIEW_ORDER:
            path = image_paths.get(view_name)
            if path and os.path.isfile(path):
                structural_coverage[view_name] = self.estimate_structural_coverage(path)
            else:
                structural_coverage[view_name] = None  # type: ignore[assignment]

        symmetry_deviation = None
        left_path = image_paths.get("left_side_profile")
        right_path = image_paths.get("right_side_profile")
        if left_path and right_path and os.path.isfile(left_path) and os.path.isfile(right_path):
            symmetry_deviation = self.compute_symmetry_deviation(left_path, right_path)

        frame_approximation = self.estimate_frame_proportions(image_paths, vehicle_type)

        available_coverages = [
            v for v in structural_coverage.values() if v is not None
        ]

        if not available_coverages:
            score = 0
            geometry_conflict = False
        else:
            score = 70

            if all(c >= 0.6 for c in available_coverages):
                score += 15

            if symmetry_deviation is not None and symmetry_deviation < 0.2:
                score += 15

            for view in _MANDATORY_VIEWS:
                cov = structural_coverage.get(view)
                if cov is not None and cov < 0.3:
                    score -= 20

            geometry_conflict = False
            if symmetry_deviation is not None and symmetry_deviation > 0.4:
                geometry_conflict = True
                score -= 15

        score = max(0, min(100, score))

        avg_coverage = (
            sum(available_coverages) / len(available_coverages)
            if available_coverages
            else 0.0
        )

        return {
            "geometry_score": score,
            "structural_coverage": structural_coverage,
            "symmetry_deviation": symmetry_deviation,
            "geometry_conflict": geometry_conflict,
            "frame_approximation": frame_approximation,
            "avg_structural_coverage": round(avg_coverage, 4),
        }
