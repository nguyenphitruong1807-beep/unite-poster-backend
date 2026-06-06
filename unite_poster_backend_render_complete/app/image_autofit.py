from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Optional

import cv2
import numpy as np
from PIL import Image


@dataclass
class AlphaBounds:
    x: int
    y: int
    width: int
    height: int


def load_rgba(image_bytes: bytes) -> Image.Image:
    return Image.open(BytesIO(image_bytes)).convert("RGBA")


def get_alpha_bounds(img: Image.Image) -> AlphaBounds:
    alpha = np.array(img)[:, :, 3]
    ys, xs = np.where(alpha > 20)
    if len(xs) == 0 or len(ys) == 0:
        return AlphaBounds(0, 0, img.width, img.height)
    min_x, max_x = int(xs.min()), int(xs.max())
    min_y, max_y = int(ys.min()), int(ys.max())
    return AlphaBounds(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)


def detect_face_box(img: Image.Image) -> Optional[dict]:
    rgb = np.array(img.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}


def suggest_transform(
    img: Image.Image,
    slot_x: int,
    slot_y: int,
    slot_width: int,
    slot_height: int,
    *,
    anchor_y: str = "bottom",
    fit_mode: str = "head_to_belly",
) -> dict:
    bounds = get_alpha_bounds(img)
    face = detect_face_box(img)

    scale = min(slot_width / bounds.width, slot_height / bounds.height) * 1.04
    person_x = slot_x + slot_width / 2 - (bounds.x + bounds.width / 2) * scale

    if anchor_y == "belly":
        body_anchor_ratio = 0.78
        anchor_pixel = bounds.y + bounds.height * body_anchor_ratio
        person_y = slot_y + slot_height - anchor_pixel * scale
    elif anchor_y == "center":
        person_y = slot_y + slot_height / 2 - (bounds.y + bounds.height / 2) * scale
    else:
        person_y = slot_y + slot_height - (bounds.y + bounds.height) * scale

    result = {
        "x": round(person_x, 2),
        "y": round(person_y, 2),
        "scale": round(scale, 5),
        "bounds": bounds.__dict__,
        "face_box": face,
        "fit_mode": fit_mode,
        "anchor_y": anchor_y,
        "slot": {
            "x": slot_x,
            "y": slot_y,
            "width": slot_width,
            "height": slot_height,
        },
    }
    return result
