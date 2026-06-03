import cv2
import numpy as np

from core.config import settings


def downscale_image(image_path: str) -> str | None:
    max_dim = settings.image_max_dimension
    if max_dim <= 0:
        return None

    img = cv2.imread(image_path)
    if img is None:
        return None

    h, w = img.shape[:2]
    if max(h, w) <= max_dim:
        return None

    scale = max_dim / float(max(h, w))
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    out_path = image_path.rsplit(".", 1)[0] + "_downscaled." + image_path.rsplit(".", 1)[1]
    cv2.imwrite(out_path, resized)
    return out_path


def downscale_if_large(image_path: str) -> str:
    result = downscale_image(image_path)
    return result if result else image_path
