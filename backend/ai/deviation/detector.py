import logging
import os

import cv2
import numpy as np

from core.retry import with_retry

logger = logging.getLogger(__name__)

SEVERITY_THRESHOLDS = (2.0, 5.0)

_STRUCTURAL_KEYS = [
    "wheelbase_mm",
    "overall_length_mm",
    "overall_width_mm",
    "ground_clearance_mm",
    "cargo_length_mm",
]


_DEFAULT_REFERENCES = {
    "three_wheeler": {
        "wheelbase_mm": 2150,
        "overall_length_mm": 2800,
        "overall_width_mm": 1200,
        "ground_clearance_mm": 180,
        "cargo_length_mm": 1200,
    },
    "motorcycle": {
        "wheelbase_mm": 1350,
        "overall_length_mm": 2000,
        "overall_width_mm": 800,
        "ground_clearance_mm": 160,
        "cargo_length_mm": 0,
    },
    "four_wheeler": {
        "wheelbase_mm": 2500,
        "overall_length_mm": 4000,
        "overall_width_mm": 1700,
        "ground_clearance_mm": 170,
        "cargo_length_mm": 0,
    },
}


class DeviationDetector:
    def __init__(self, oem_specs: dict | None = None):
        self.references = {
            k: dict(v) for k, v in _DEFAULT_REFERENCES.items()
        }
        if oem_specs:
            vehicle_type = oem_specs.get("_vehicle_type", "three_wheeler")
            if vehicle_type not in self.references:
                vehicle_type = "three_wheeler"
            for key in _STRUCTURAL_KEYS:
                val = oem_specs.get(key)
                if val is not None:
                    self.references[vehicle_type][key] = val

    def _best_side_profile(self, images: dict) -> str | None:
        for view in ("left_side_profile", "right_side_profile"):
            path = images.get(view)
            if path and os.path.isfile(path):
                return path
        for path in images.values():
            if path and os.path.isfile(path):
                return path
        return None

    def _estimate_wheelbase(self, images: dict) -> tuple[float, float]:
        side_path = self._best_side_profile(images)
        if side_path is None:
            return 0.0, 0.0

        img = cv2.imread(side_path)
        if img is None:
            return 0.0, 0.0

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        contours, _ = cv2.findContours(
            cv2.Canny(blurred, 50, 150),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )
        if not contours:
            return 0.0, 0.0

        largest = max(contours, key=cv2.contourArea)
        bx, by, bw, bh = cv2.boundingRect(largest)

        h_img, w_img = img.shape[:2]
        coverage_ratio = (bw * bh) / (w_img * h_img)
        certainty = min(1.0, coverage_ratio * 4.0)

        wheel_roi = gray[by + bh // 2 : by + bh, bx : bx + bw]
        if wheel_roi.size == 0:
            return 0.0, certainty * 0.3

        circles = cv2.HoughCircles(
            wheel_roi,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=int(bw * 0.15),
            param1=50,
            param2=20,
            minRadius=int(max(bw, bh) * 0.02),
            maxRadius=int(max(bw, bh) * 0.2),
        )

        wheel_centers = []
        if circles is not None:
            circles = np.round(circles[0, :]).astype(int)
            for cx, cy, r in circles:
                wheel_centers.append((int(cx + bx), int(cy + by + bh // 2)))

        wheel_centers.sort(key=lambda p: p[0])

        if len(wheel_centers) < 2:
            return 0.0, certainty * 0.3

        left = np.array(wheel_centers[0])
        right = np.array(wheel_centers[-1])
        pixel_distance = float(np.linalg.norm(right - left))

        wb_ratio = pixel_distance / max(bw, 1)
        if wb_ratio < 0.1 or wb_ratio > 1.5:
            return 0.0, certainty * 0.3

        return pixel_distance, certainty

    def _estimate_dimensions(self, images: dict, vehicle_type: str) -> dict:
        ref = self.references.get(vehicle_type, self.references["three_wheeler"])
        side_path = self._best_side_profile(images)
        if side_path is None or not os.path.isfile(side_path):
            result = {k: 0.0 for k in _STRUCTURAL_KEYS}
            result["_certainty"] = 0.0
            return result

        img = cv2.imread(side_path)
        if img is None:
            result = {k: 0.0 for k in _STRUCTURAL_KEYS}
            result["_certainty"] = 0.0
            return result

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            result = {k: 0.0 for k in _STRUCTURAL_KEYS}
            result["_certainty"] = 0.1
            return result

        largest = max(contours, key=cv2.contourArea)
        bx, by, cw, ch = cv2.boundingRect(largest)

        h_img, w_img = img.shape[:2]
        coverage = (cw * ch) / (w_img * h_img)
        certainty = min(1.0, coverage * 4.0)

        known_length = ref.get("overall_length_mm", 2800)
        known_wheelbase = ref.get("wheelbase_mm", 2150)

        px_per_mm = cw / max(known_length, 1)
        estimated_length = known_length

        estimated_width = ref.get("overall_width_mm", 1200)

        wb_px, wb_certainty = self._estimate_wheelbase(images)
        if wb_px > 0 and px_per_mm > 0:
            estimated_wheelbase = wb_px / px_per_mm
        else:
            estimated_wheelbase = known_wheelbase

        estimated_wheelbase = max(500.0, estimated_wheelbase)

        ground_clearance = ref.get("ground_clearance_mm", 180)
        clearance_px_ratio = 0.0
        if ch > 10:
            bottom_region = edges[by + ch - 10 : by + ch, bx : bx + cw]
            if bottom_region.size > 0:
                clearance_px_ratio = np.count_nonzero(bottom_region) / max(
                    bottom_region.size, 1
                )
        clearance_factor = 1.0 + 0.5 * (
            1.0 - min(1.0, clearance_px_ratio * 10)
        )
        estimated_clearance = int(ground_clearance * clearance_factor)
        estimated_clearance = max(80, min(400, estimated_clearance))

        cargo_length = ref.get("cargo_length_mm", 0)
        if cargo_length > 0 and known_length > 0:
            estimated_cargo = cargo_length
        else:
            estimated_cargo = cargo_length

        avg_certainty = (certainty + wb_certainty) / 2.0

        return {
            "wheelbase_mm": round(estimated_wheelbase, 1),
            "overall_length_mm": estimated_length,
            "overall_width_mm": estimated_width,
            "ground_clearance_mm": estimated_clearance,
            "cargo_length_mm": estimated_cargo,
            "_certainty": round(avg_certainty, 4),
        }

    def _compare_to_reference(
        self, estimates: dict, vehicle_type: str
    ) -> list[dict]:
        ref = self.references.get(vehicle_type)
        if ref is None:
            ref = self.references["three_wheeler"]

        deviations = []
        for key in _STRUCTURAL_KEYS:
            estimated = estimates.get(key)
            if estimated is None or estimated == 0.0:
                continue
            reference = ref.get(key)
            if reference is None or reference == 0:
                continue
            delta = estimated - reference
            delta_pct = round((delta / reference) * 100, 2)

            if delta_pct == 0.0:
                continue

            abs_pct = abs(delta_pct)
            minor_cutoff, moderate_cutoff = SEVERITY_THRESHOLDS
            if abs_pct < minor_cutoff:
                severity = "minor"
            elif abs_pct <= moderate_cutoff:
                severity = "moderate"
            else:
                severity = "major"

            deviations.append(
                {
                    "parameter": key,
                    "estimated": int(round(estimated)),
                    "reference": int(reference),
                    "delta": int(round(delta)),
                    "delta_pct": delta_pct,
                    "severity": severity,
                    "notes": f"{key.replace('_', ' ').title()} {delta_pct:+.2f}% vs reference",
                }
            )

        return deviations

    def _compute_deviation_score(self, deviations: list) -> int:
        score = 100
        for d in deviations:
            sev = d.get("severity", "minor")
            if sev == "minor":
                score -= 5
            elif sev == "moderate":
                score -= 15
            elif sev == "major":
                score -= 30
        return max(0, min(100, score))

    def _compute_salvage_potential(
        self, deviations: list, score: int
    ) -> int:
        base = score
        for d in deviations:
            if d.get("severity") == "major" and d.get("parameter") in (
                "wheelbase_mm",
                "overall_length_mm",
                "overall_width_mm",
            ):
                base -= 10
        return max(0, min(100, base))

    @with_retry(retryable_exceptions=(RuntimeError,))
    def detect(self, image_paths: dict, vehicle_type: str) -> dict:
        if vehicle_type == "unknown" or vehicle_type not in self.references:
            vehicle_type = "three_wheeler"
            reduced_certainty = True
        else:
            reduced_certainty = False

        estimates = self._estimate_dimensions(image_paths, vehicle_type)

        if reduced_certainty:
            estimates["_certainty"] = round(
                estimates["_certainty"] * 0.6, 4
            )

        deviations = self._compare_to_reference(estimates, vehicle_type)

        deviation_score = self._compute_deviation_score(deviations)

        deviation_certainty = int(
            round(estimates.get("_certainty", 0.0) * 100)
        )

        critical_delamination = any(
            d.get("severity") == "major"
            and d.get("parameter")
            in ("wheelbase_mm", "overall_length_mm", "overall_width_mm")
            for d in deviations
        )

        salvage_potential = self._compute_salvage_potential(
            deviations, deviation_score
        )

        high_count = sum(1 for d in deviations if d["severity"] == "major")

        return {
            "deviations": deviations,
            "deviation_score": deviation_score,
            "deviation_certainty": deviation_certainty,
            "critical_delamination": critical_delamination,
            "salvage_potential": salvage_potential,
            "deviation_count": len(deviations),
            "high_severity_count": high_count,
        }
