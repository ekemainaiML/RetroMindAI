import os
import tempfile

import cv2
import numpy as np


_BG = 200
_BODY = 80
_WHEEL = 30

_VEHICLE_PROTOTYPES = {
    "three_wheeler": {
        "img_w": 480, "img_h": 480,
        "body_x": 90, "body_y": 80, "body_w": 300, "body_h": 260,
        "wheels": [(140, 380, 32), (240, 380, 32), (340, 380, 32)],
    },
    "four_wheeler": {
        "img_w": 700, "img_h": 420,
        "body_x": 30, "body_y": 80, "body_w": 640, "body_h": 280,
        "wheels": [(80, 360, 28), (230, 360, 28), (470, 360, 28), (620, 360, 28)],
    },
    "motorcycle": {
        "img_w": 300, "img_h": 400,
        "body_x": 120, "body_y": 60, "body_w": 60, "body_h": 280,
        "wheels": [(140, 340, 35), (160, 340, 35)],
    },
}


def _render_vehicle(prototype: dict) -> np.ndarray:
    img = np.ones((prototype["img_h"], prototype["img_w"], 3), dtype=np.uint8) * _BG
    cv2.rectangle(
        img,
        (prototype["body_x"], prototype["body_y"]),
        (prototype["body_x"] + prototype["body_w"], prototype["body_y"] + prototype["body_h"]),
        (_BODY, _BODY, _BODY),
        -1,
    )
    for cx, cy, r in prototype["wheels"]:
        cv2.circle(img, (cx, cy), r, (_WHEEL, _WHEEL, _WHEEL), -1)
    return img


def generate_views(vehicle_type: str, target_dir: str | None = None) -> dict[str, str]:
    prototype = _VEHICLE_PROTOTYPES.get(vehicle_type)
    if prototype is None:
        raise ValueError(f"Unknown vehicle type: {vehicle_type}. Choose from: {list(_VEHICLE_PROTOTYPES.keys())}")

    if target_dir is None:
        target_dir = tempfile.mkdtemp(prefix=f"syn_{vehicle_type}_")

    img = _render_vehicle(prototype)
    paths = {}
    for view in ("left_side_profile", "right_side_profile", "rear_view"):
        path = os.path.join(target_dir, f"{view}.png")
        cv2.imwrite(path, img)
        paths[view] = path
    return paths


def generate_blank(target_dir: str | None = None) -> dict[str, str]:
    if target_dir is None:
        target_dir = tempfile.mkdtemp(prefix="syn_blank_")
    img = np.ones((400, 600, 3), dtype=np.uint8) * 240
    paths = {}
    for view in ("left_side_profile", "right_side_profile", "rear_view"):
        path = os.path.join(target_dir, f"{view}.png")
        cv2.imwrite(path, img)
        paths[view] = path
    return paths
