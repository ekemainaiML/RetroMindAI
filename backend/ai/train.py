import logging
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

TRAINING_DATA_DIR = Path(__file__).resolve().parent / "training_data"
TRAINING_DATA_DIR.mkdir(exist_ok=True)


def extract_features(image_path: str) -> dict[str, float] | None:
    img = cv2.imread(image_path)
    if img is None or img.size == 0:
        return None

    h, w = img.shape[:2]
    aspect_ratio = w / max(h, 1)
    area = h * w

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    edge_density = float(np.count_nonzero(edges)) / max(area, 1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        ca = cv2.contourArea(largest)
        hull = cv2.convexHull(largest)
        ha = cv2.contourArea(hull)
        solidity = ca / max(ha, 1)
        x, y, cw, ch = cv2.boundingRect(largest)
        bbox_aspect = cw / max(ch, 1)
        bbox_area_ratio = (cw * ch) / max(area, 1)
    else:
        solidity = 0.5
        bbox_aspect = 1.0
        bbox_area_ratio = 0.5

    hog = cv2.HOGDescriptor()
    resized = cv2.resize(gray, (128, 128))
    hog_features = hog.compute(resized)
    hog_mean = float(np.mean(hog_features)) if hog_features is not None else 0.0
    hog_std = float(np.std(hog_features)) if hog_features is not None else 0.0

    color_hist = cv2.calcHist([img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    color_hist = cv2.normalize(color_hist, color_hist).flatten()
    color_mean = float(np.mean(color_hist))
    color_std = float(np.std(color_hist))

    return {
        "aspect_ratio": aspect_ratio,
        "edge_density": edge_density,
        "solidity": solidity,
        "bbox_aspect": bbox_aspect,
        "bbox_area_ratio": bbox_area_ratio,
        "hog_mean": hog_mean,
        "hog_std": hog_std,
        "color_mean": color_mean,
        "color_std": color_std,
    }


def _convert_to_onnx(rf_model, feature_names: list[str]) -> bytes | None:
    try:
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType

        n_features = len(feature_names)
        initial_type = [("float_input", FloatTensorType([None, n_features]))]
        onnx_model = convert_sklearn(rf_model, initial_types=initial_type, target_opset=12)
        return onnx_model.SerializeToString()
    except Exception:
        return None


def train_from_collected(images_dir: str, model_output_path: str) -> dict[str, Any]:
    from sklearn.ensemble import RandomForestClassifier

    X: list[list[float]] = []
    y: list[str] = []
    feature_names: list[str] | None = None

    for label in os.listdir(images_dir):
        label_dir = os.path.join(images_dir, label)
        if not os.path.isdir(label_dir):
            continue
        for fname in os.listdir(label_dir):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            fpath = os.path.join(label_dir, fname)
            feats = extract_features(fpath)
            if feats is None:
                continue
            if feature_names is None:
                feature_names = list(feats.keys())
            X.append([feats[k] for k in feature_names])
            y.append(label)

    if len(X) < 10:
        return {"success": False, "error": f"Not enough samples ({len(X)}). Need at least 10."}

    X_arr = np.array(X, dtype=np.float32)
    y_arr = np.array(y)

    clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    clf.fit(X_arr, y_arr)
    accuracy = float(clf.score(X_arr, y_arr))

    try:
        onnx_bytes = _convert_to_onnx(clf, feature_names or [])
        if onnx_bytes:
            os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
            with open(model_output_path, "wb") as f:
                f.write(onnx_bytes)
            logger.info("ONNX model saved to %s", model_output_path)
    except Exception:
        pass

    metadata = {
        "success": True,
        "accuracy": round(accuracy, 4),
        "samples": len(X),
        "classes": sorted(clf.classes_.tolist()),
        "feature_names": feature_names,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_path": model_output_path,
    }

    meta_path = os.path.join(os.path.dirname(model_output_path), "training_metadata.pkl")
    with open(meta_path, "wb") as f:
        pickle.dump(metadata, f)

    logger.info("Training complete: accuracy=%.4f, samples=%d", accuracy, len(X))
    return metadata


def collect_training_data(
    db_session,
    workshop_id,
    output_dir: str,
) -> dict[str, list[str]]:
    from core.models import Intake, Job

    completed_jobs = (
        db_session.query(Job)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(
            Intake.workshop_id == workshop_id,
            Job.status == "completed",
            Job.result.isnot(None),
        )
        .all()
    )

    os.makedirs(output_dir, exist_ok=True)
    counts: dict[str, int] = {}
    copied: dict[str, list[str]] = {}

    for job in completed_jobs:
        result = job.result or {}
        vc = result.get("vehicle_classification", {}) or {}
        vtype = vc.get("type", "unknown")
        slot_key = vtype.replace(" ", "_")

        intake = job.intake
        if not intake or not intake.view_slots:
            continue
        for slot_name, file_path in intake.view_slots.items():
            if file_path and os.path.isfile(file_path):
                label_dir = os.path.join(output_dir, slot_key)
                os.makedirs(label_dir, exist_ok=True)
                ext = os.path.splitext(file_path)[1]
                dest = os.path.join(label_dir, f"{slot_key}_{counts.get(slot_key, 0)}{ext}")
                try:
                    import shutil
                    shutil.copy2(file_path, dest)
                    copied.setdefault(slot_key, []).append(dest)
                    counts[slot_key] = counts.get(slot_key, 0) + 1
                except OSError:
                    continue

    return copied
