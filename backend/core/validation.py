import struct

import cv2
import numpy as np


def validate_image_bytes(data: bytes) -> bool:
    """Check that file bytes are a valid JPEG or PNG before saving."""
    if len(data) < 12:
        return False
    if data[:2] == b'\xff\xd8':
        if data[-2:] != b'\xff\xd9':
            return False
        return True
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        if data[-3:] != b'IEND':
            return False
        return True
    return False


def compute_blur_score(image_path: str) -> float:
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.0
    return float(cv2.Laplacian(img, cv2.CV_64F).var())


BLUR_THRESHOLD = 100.0


def is_blurry(image_path: str) -> bool:
    return compute_blur_score(image_path) < BLUR_THRESHOLD


def check_swap(
    left_path: str | None, right_path: str | None
) -> bool:
    if left_path is None or right_path is None:
        return False

    left_img = cv2.imread(left_path, cv2.IMREAD_GRAYSCALE)
    right_img = cv2.imread(right_path, cv2.IMREAD_GRAYSCALE)
    if left_img is None or right_img is None:
        return False

    h_left, w_left = left_img.shape[:2]
    h_right, w_right = right_img.shape[:2]
    if h_left == 0 or w_left == 0 or h_right == 0 or w_right == 0:
        return False

    left_resized = cv2.resize(left_img, (w_right, h_right))
    left_flipped = cv2.flip(left_resized, 1)

    mse = float(np.mean((left_flipped.astype(np.float32) - right_img.astype(np.float32)) ** 2))

    SIMILARITY_THRESHOLD = 500.0
    return mse < SIMILARITY_THRESHOLD
