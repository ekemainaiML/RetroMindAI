import logging
import os

import cv2
import numpy as np

from ai.classification.preprocess import preprocess_for_classification
from ai.models.onnx_runner import ONNXRunner
from core.config import settings

logger = logging.getLogger(__name__)

CLASS_LABELS = ["three_wheeler", "motorcycle", "four_wheeler", "unknown"]
MIN_MODEL_CONFIDENCE = 0.35


class VehicleClassifier:
    SUPPORTED_CLASSES = list(CLASS_LABELS)

    def __init__(self, model_path: str = None):
        self._onnx_runner = ONNXRunner(model_path)
        self._pytorch_runner = None
        self._onnx_loaded = self._onnx_runner.load()
        self._pytorch_loaded = False
        if settings.enable_pytorch:
            self._try_load_pytorch()

    def _try_load_pytorch(self):
        try:
            from ai.models.pytorch_runner import PyTorchRunner
            self._pytorch_runner = PyTorchRunner()
            self._pytorch_loaded = self._pytorch_runner.load()
        except Exception:
            self._pytorch_loaded = False

    def classify(self, image_paths: dict[str, str]) -> dict:
        if settings.enable_pytorch:
            if not self._pytorch_loaded:
                logger.info("PyTorch flag enabled — attempting lazy load")
                self._try_load_pytorch()
            if self._pytorch_loaded:
                result = self._run_pytorch_inference(image_paths)
                if result is not None:
                    return result
                logger.warning("PyTorch inference failed, falling back to ONNX")
                self._pytorch_loaded = False
        if self._onnx_loaded:
            return self._run_model_inference(image_paths)
        return self._heuristic_classify(image_paths)

    def _find_best_image(self, image_paths: dict[str, str]) -> str | None:
        for view_name in ["left_side_profile", "right_side_profile", "rear_view"]:
            path = image_paths.get(view_name)
            if path and os.path.isfile(path):
                return path
        for path in image_paths.values():
            if path and os.path.isfile(path):
                return path
        return None

    def _heuristic_classify(self, image_paths: dict[str, str]) -> dict:
        image_path = self._find_best_image(image_paths)
        if image_path is None:
            return self._unknown_result(0.3)

        img = cv2.imread(image_path)
        if img is None or img.size == 0:
            return self._unknown_result(0.3)

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            logger.warning("No contours found in %s", os.path.basename(image_path))
            return self._unknown_result(0.4)

        largest = max(contours, key=cv2.contourArea)
        contour_area = cv2.contourArea(largest)
        hull = cv2.convexHull(largest)
        hull_area = cv2.contourArea(hull)
        solidity = contour_area / max(hull_area, 1)

        rx, ry, rw, rh = cv2.boundingRect(hull)
        hull_aspect = rh / max(rw, 1)

        rect = cv2.minAreaRect(hull)
        rect_w, rect_h = rect[1]
        if rect_w < rect_h:
            rect_w, rect_h = rect_h, rect_w
        minrect_aspect = rect_h / max(rect_w, 1)

        total_px = h * w
        area_fraction = contour_area / max(total_px, 1)

        bottom_third = edges[2 * h // 3:, :]
        top_two_thirds = edges[:2 * h // 3, :]
        edge_ratio = (np.count_nonzero(bottom_third) + 1) / max(np.count_nonzero(top_two_thirds) + 1, 1)

        circles = cv2.HoughCircles(
            blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=int(h * 0.25),
            param1=80, param2=50, minRadius=int(h * 0.04), maxRadius=int(h * 0.20)
        )
        wheel_count = len(circles[0]) if circles is not None else 0

        signals = []

        # Hull aspect ratio: cars are wide (low aspect), motorcycles are tall (high aspect)
        if hull_aspect < 0.6:
            signals.append(("four_wheeler", 0.35, "very wide hull shape"))
        elif hull_aspect < 1.0:
            # 0.6–1.0: could be a 3/4-view car or front-view three-wheeler
            signals.append(("four_wheeler", 0.20, "moderately wide hull shape"))
            signals.append(("three_wheeler", 0.15, "moderate hull aspect"))
        elif hull_aspect < 1.6:
            signals.append(("three_wheeler", 0.30, "compact hull shape"))
        else:
            signals.append(("motorcycle", 0.35, "elongated hull shape"))

        # Min-rectangle aspect ratio
        if minrect_aspect < 0.35:
            signals.append(("four_wheeler", 0.25, "very wide profile"))
        elif minrect_aspect < 0.55:
            signals.append(("three_wheeler", 0.25, "wide profile"))
        else:
            signals.append(("motorcycle", 0.25, "narrow profile"))

        # Edge distribution: heavy lower edges often = wheel wells on a car
        if edge_ratio > 1.8:
            signals.append(("four_wheeler", 0.15, "heavy lower edges"))
        elif edge_ratio < 0.6:
            signals.append(("motorcycle", 0.15, "light lower edges"))

        # Wheel count: cross-reference with hull width to avoid
        # misclassifying car side-profiles (2 visible wheels) as motorcycle
        if wheel_count >= 4:
            signals.append(("four_wheeler", 0.35, f"{wheel_count} wheels detected"))
        elif wheel_count == 3:
            signals.append(("three_wheeler", 0.30, f"{wheel_count} wheels detected"))
        elif wheel_count == 2:
            if hull_aspect < 0.8:
                signals.append(("four_wheeler", 0.20, f"{wheel_count} wheels + wide hull"))
            else:
                signals.append(("motorcycle", 0.20, f"{wheel_count} wheels detected"))

        # Solidity: cars fill their convex hull more than motorcycles
        if solidity > 0.85:
            signals.append(("four_wheeler", 0.15, "high solidity"))
        elif solidity < 0.6:
            signals.append(("motorcycle", 0.10, "low solidity"))

        # Area fraction
        if area_fraction > 0.35:
            signals.append(("four_wheeler", 0.20, "large vehicle silhouette"))
        elif area_fraction > 0.12:
            signals.append(("three_wheeler", 0.10, "moderate silhouette"))
        else:
            signals.append(("unknown", 0.30, "small silhouette"))

        scores = {"three_wheeler": 0.0, "motorcycle": 0.0, "four_wheeler": 0.0, "unknown": 0.0}
        for vtype, weight, reason in signals:
            if vtype in scores:
                scores[vtype] += weight

        total_weight = sum(w for _, w, _ in signals)
        if total_weight > 0:
            for k in scores:
                scores[k] = round(scores[k] / total_weight, 4)

        vehicle_type = max(scores, key=lambda k: scores[k])
        conf = scores[vehicle_type]

        sorted_types = sorted(scores, key=lambda k: scores[k], reverse=True)
        alt_type = sorted_types[1] if sorted_types[1] != "unknown" else sorted_types[2] if len(sorted_types) > 2 else "three_wheeler"
        alt_conf = round(max(0.05, scores.get(alt_type, 0.1)), 4)
        unknown_conf = round(max(0.05, scores.get("unknown", 0.1)), 4)

        logger.info(
            "Heuristic: %s (conf=%.4f, hull_aspect=%.2f, minrect_asp=%.2f, "
            "edge_ratio=%.2f, wheels=%d, area=%.3f, solidity=%.2f) from %s",
            vehicle_type, conf, hull_aspect, minrect_aspect,
            edge_ratio, wheel_count, area_fraction, solidity,
            os.path.basename(image_path),
        )

        return {
            "vehicle_type": vehicle_type,
            "confidence": conf,
            "alternatives": [
                {"type": alt_type, "confidence": alt_conf},
                {"type": "unknown", "confidence": unknown_conf},
            ],
            "human_confirmed": False,
            "model_loaded": False,
        }

    def _unknown_result(self, conf: float) -> dict:
        return {
            "vehicle_type": "unknown",
            "confidence": conf,
            "alternatives": [
                {"type": "three_wheeler", "confidence": 0.25},
                {"type": "motorcycle", "confidence": 0.25},
                {"type": "four_wheeler", "confidence": 0.25},
            ],
            "human_confirmed": False,
            "model_loaded": False,
            "classifier_used": "heuristic",
        }

    def _run_model_inference(self, image_paths: dict[str, str]) -> dict:
        input_tensor = None
        best_view = None

        for view_name, path in image_paths.items():
            if path and os.path.isfile(path):
                tensor = preprocess_for_classification(path)
                if tensor is not None:
                    input_tensor = tensor
                    best_view = view_name
                    break

        if input_tensor is None:
            logger.warning(
                "No valid image found among %d views — falling back to heuristic",
                len(image_paths),
            )
            return self._heuristic_classify(image_paths)

        result = self._onnx_runner.run(input_tensor)
        if result is None:
            logger.warning("ONNX inference returned None — falling back to heuristic")
            return self._heuristic_classify(image_paths)

        predicted_idx = result["predicted_class"]
        probs = result["probabilities"][0]
        confidence = round(float(probs[predicted_idx]), 4)

        if confidence < MIN_MODEL_CONFIDENCE:
            logger.warning(
                "ONNX confidence %.4f below threshold %.2f — falling back to heuristic",
                confidence, MIN_MODEL_CONFIDENCE,
            )
            return self._heuristic_classify(image_paths)

        vehicle_type = CLASS_LABELS[predicted_idx]

        alternatives = [
            {"type": CLASS_LABELS[i], "confidence": round(float(probs[i]), 4)}
            for i in range(len(CLASS_LABELS))
            if i != predicted_idx
        ]
        alternatives.sort(key=lambda x: x["confidence"], reverse=True)

        logger.info(
            "Classification result: %s (conf=%.4f) from view=%s",
            vehicle_type,
            confidence,
            best_view,
        )

        return {
            "vehicle_type": vehicle_type,
            "confidence": confidence,
            "alternatives": alternatives,
            "human_confirmed": False,
            "model_loaded": True,
            "classifier_used": "onnx",
        }

    def _run_pytorch_inference(self, image_paths: dict[str, str]) -> dict | None:
        input_tensor = None
        best_view = None

        for view_name, path in image_paths.items():
            if path and os.path.isfile(path):
                tensor = preprocess_for_classification(path)
                if tensor is not None:
                    input_tensor = tensor
                    best_view = view_name
                    break

        if input_tensor is None:
            return None

        try:
            result = self._pytorch_runner.run(input_tensor)
        except Exception:
            logger.warning("PyTorch inference raised exception")
            return None

        if result is None:
            return None

        predicted_idx = result["predicted_class"]
        probs = result["probabilities"][0]
        confidence = round(float(probs[predicted_idx]), 4)

        if confidence < MIN_MODEL_CONFIDENCE:
            logger.warning(
                "PyTorch confidence %.4f below threshold %.2f — returning None for fallback",
                confidence, MIN_MODEL_CONFIDENCE,
            )
            return None

        vehicle_type = CLASS_LABELS[predicted_idx]

        alternatives = [
            {"type": CLASS_LABELS[i], "confidence": round(float(probs[i]), 4)}
            for i in range(len(CLASS_LABELS))
            if i != predicted_idx
        ]
        alternatives.sort(key=lambda x: x["confidence"], reverse=True)

        logger.info(
            "PyTorch classification: %s (conf=%.4f) from view=%s",
            vehicle_type, confidence, best_view,
        )

        return {
            "vehicle_type": vehicle_type,
            "confidence": confidence,
            "alternatives": alternatives,
            "human_confirmed": False,
            "model_loaded": True,
            "classifier_used": "pytorch",
        }
