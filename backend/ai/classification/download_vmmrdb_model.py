"""
Download the Jordo23/vehicle-classifier model from Hugging Face.

This model (EfficientNet-B4) classifies 8,949 vehicle make/model/year classes
from the VMMRdb dataset. It's available as ONNX (~1MB) for fast inference
and comes with a class_mapping.csv.

Usage:
    python -m ai.classification.download_vmmrdb_model

Output:
    backend/ai/models/vmmrdb_classifier.onnx    (~1 MB, ONNX model)
    backend/ai/models/vmmrdb_class_mapping.csv   (class ID → make/model/year)
"""

import csv
import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
ONNX_URL = "https://huggingface.co/Jordo23/vehicle-classifier/resolve/main/vehicle_classifier.onnx"
MAPPING_URL = "https://huggingface.co/Jordo23/vehicle-classifier/resolve/main/class_mapping.csv"
ONNX_PATH = MODELS_DIR / "vmmrdb_classifier.onnx"
MAPPING_PATH = MODELS_DIR / "vmmrdb_class_mapping.csv"


def download(url: str, dest: Path, desc: str = "") -> bool:
    if dest.exists() and dest.stat().st_size > 1000:
        logger.info("%s already exists at %s (%d bytes)", desc, dest, dest.stat().st_size)
        return True
    logger.info("Downloading %s from %s ...", desc, url)
    try:
        r = requests.get(url, timeout=120, stream=True)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info("Downloaded %s to %s (%d bytes)", desc, dest, dest.stat().st_size)
        return True
    except Exception as e:
        logger.error("Failed to download %s: %s", desc, e)
        return False


def load_class_mapping() -> dict[int, str]:
    """Load class_mapping.csv → {class_id: "Make Model Year"}"""
    if not MAPPING_PATH.exists():
        logger.warning("Class mapping not found at %s", MAPPING_PATH)
        return {}
    mapping: dict[int, str] = {}
    with open(MAPPING_PATH) as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                try:
                    mapping[int(row[0])] = row[1]
                except ValueError:
                    continue
    logger.info("Loaded %d class mappings", len(mapping))
    return mapping


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    download(ONNX_URL, ONNX_PATH, "VMMRdb ONNX model")
    download(MAPPING_URL, MAPPING_PATH, "VMMRdb class mapping")
    mapping = load_class_mapping()
    print(f"Loaded {len(mapping)} classes")
    if mapping:
        for cid in list(mapping.keys())[:5]:
            print(f"  {cid}: {mapping[cid]}")
