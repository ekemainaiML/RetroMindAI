import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)

TARGET_SIZE = (224, 224)

LOW_LIGHT_THRESHOLD = 50
OCCLUSION_STD_THRESHOLD = 15


def detect_low_light(image_path: str) -> bool:
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        return mean_brightness < LOW_LIGHT_THRESHOLD
    except Exception:
        logger.exception("Error checking low light for: %s", image_path)
        return False


def auto_enhance(image_path: str) -> str | None:
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        lightness, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        lightness = clahe.apply(lightness)
        enhanced = cv2.cvtColor(cv2.merge([lightness, a, b]), cv2.COLOR_LAB2BGR)
        enhanced_path = image_path.rsplit(".", 1)[0] + "_enhanced." + image_path.rsplit(".", 1)[1]
        cv2.imwrite(enhanced_path, enhanced)
        return enhanced_path
    except Exception:
        logger.exception("Error auto-enhancing image: %s", image_path)
        return None


def check_occlusion(image_path: str) -> dict:
    result = {"occluded": False, "std_dev": None, "coverage_pct": None}
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return result
        std_dev = float(np.std(img))
        result["std_dev"] = round(std_dev, 2)
        if std_dev < OCCLUSION_STD_THRESHOLD:
            total = img.size
            low_var = int(np.sum(img > 0))  # count non-zero pixels
            result["coverage_pct"] = round((low_var / total) * 100, 1)
            result["occluded"] = True
        return result
    except Exception:
        logger.exception("Error checking occlusion for: %s", image_path)
        return result


def preprocess_for_classification(image_path: str) -> np.ndarray | None:
    try:
        img = cv2.imread(image_path)
        if img is None:
            logger.warning("Could not read image: %s", image_path)
            return None
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, TARGET_SIZE, interpolation=cv2.INTER_LINEAR)
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        return img
    except Exception:
        logger.exception("Error preprocessing image: %s", image_path)
        return None
