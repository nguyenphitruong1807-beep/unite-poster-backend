from __future__ import annotations

from io import BytesIO

from PIL import Image
from rembg import remove


def remove_background_bytes(image_bytes: bytes) -> tuple[bytes, dict]:
    output = remove(image_bytes)
    img = Image.open(BytesIO(output)).convert("RGBA")
    meta = {"width": img.width, "height": img.height}
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), meta
