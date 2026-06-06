from __future__ import annotations

import math
import os
import tempfile
from io import BytesIO
from typing import Any, Optional

import httpx
from PIL import Image, ImageColor, ImageDraw, ImageFont


DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_FONT_CACHE: dict[str, str] = {}


def load_image_from_bytes(payload: bytes) -> Image.Image:
    return Image.open(BytesIO(payload)).convert("RGBA")


def load_image_from_url(url: str) -> Image.Image:
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
    return load_image_from_bytes(response.content)


def ensure_rgba(img: Image.Image, width: int, height: int) -> Image.Image:
    if img.size != (width, height):
        return img.resize((width, height), Image.LANCZOS).convert("RGBA")
    return img.convert("RGBA")


def resolve_font_path(font_url: str, family_name: str) -> str:
    if font_url in _FONT_CACHE:
        return _FONT_CACHE[font_url]
    suffix = os.path.splitext(font_url.split("?")[0])[1] or ".ttf"
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(font_url)
        response.raise_for_status()
        data = response.content
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix=f"font_{family_name}_")
    tmp.write(data)
    tmp.flush()
    tmp.close()
    _FONT_CACHE[font_url] = tmp.name
    return tmp.name


def get_font(field: dict[str, Any], template_fonts: list[dict[str, Any]], font_size: int) -> ImageFont.FreeTypeFont:
    family = (field.get("fontFamily") or "").split(",")[0].strip()
    for font_info in template_fonts:
        known_family = font_info.get("family") or font_info.get("name") or ""
        font_url = font_info.get("public_url") or font_info.get("url")
        if family and known_family and family.lower() == known_family.lower() and font_url:
            try:
                return ImageFont.truetype(resolve_font_path(font_url, known_family), font_size)
            except Exception:
                pass
    try:
        return ImageFont.truetype(DEFAULT_FONT, font_size)
    except Exception:
        return ImageFont.load_default()


def text_color(field: dict[str, Any]):
    color = field.get("color") or "#ffffff"
    return ImageColor.getrgb(color)


def measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, letter_spacing: int) -> tuple[int, int]:
    if not text:
        return 0, 0
    if letter_spacing == 0:
        box = draw.textbbox((0, 0), text, font=font)
        return box[2] - box[0], box[3] - box[1]
    width = 0
    height = 0
    for index, ch in enumerate(text):
        box = draw.textbbox((0, 0), ch, font=font)
        width += box[2] - box[0]
        if index < len(text) - 1:
            width += letter_spacing
        height = max(height, box[3] - box[1])
    return width, height


def draw_text_letterspaced(draw: ImageDraw.ImageDraw, pos: tuple[float, float], text: str, font, fill, letter_spacing: int):
    x, y = pos
    for index, ch in enumerate(text):
        draw.text((x, y), ch, font=font, fill=fill)
        box = draw.textbbox((0, 0), ch, font=font)
        x += (box[2] - box[0]) + (letter_spacing if index < len(text) - 1 else 0)


def build_gradient_image(width: int, height: int, gradient: dict[str, Any]) -> Image.Image:
    angle = float(gradient.get("angle", 0))
    stops = gradient.get("stops") or [{"offset": 0, "color": "#ffffff"}, {"offset": 1, "color": "#cccccc"}]
    stops = sorted(stops, key=lambda s: float(s.get("offset", 0)))

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    px = img.load()
    rad = math.radians(angle)
    dx, dy = math.cos(rad), math.sin(rad)

    for y in range(height):
        for x in range(width):
            nx = x / max(width - 1, 1)
            ny = y / max(height - 1, 1)
            t = (nx * dx + ny * dy + 1) / 2
            t = max(0.0, min(1.0, t))
            left = stops[0]
            right = stops[-1]
            for idx in range(len(stops) - 1):
                s1, s2 = stops[idx], stops[idx + 1]
                if float(s1.get("offset", 0)) <= t <= float(s2.get("offset", 1)):
                    left, right = s1, s2
                    break
            o1, o2 = float(left.get("offset", 0)), float(right.get("offset", 1))
            mix = 0 if o2 == o1 else (t - o1) / (o2 - o1)
            c1 = ImageColor.getrgb(left.get("color", "#ffffff"))
            c2 = ImageColor.getrgb(right.get("color", "#cccccc"))
            rgb = tuple(int(c1[i] + (c2[i] - c1[i]) * mix) for i in range(3))
            px[x, y] = (*rgb, 255)
    return img


def draw_field(base: Image.Image, field: dict[str, Any], value: str, template_fonts: list[dict[str, Any]]):
    draw = ImageDraw.Draw(base)
    text = value.upper() if field.get("uppercase") else value
    size = int(field.get("fontSize", 36))
    width_limit = int(field.get("width", base.width))
    letter_spacing = int(field.get("letterSpacing", 0))
    font = get_font(field, template_fonts, size)

    w, h = measure_text(draw, text, font, letter_spacing)
    while w > width_limit and size > 12:
        size -= 1
        font = get_font(field, template_fonts, size)
        w, h = measure_text(draw, text, font, letter_spacing)

    align = field.get("align", "center")
    x = float(field.get("x", 0))
    y = float(field.get("y", 0))
    if align == "center":
        left = x - w / 2
    elif align == "right":
        left = x - w
    else:
        left = x
    top = y - h / 2

    if field.get("fillType") == "gradient" and field.get("gradient"):
        mask = Image.new("L", (max(int(w) + 4, 4), max(int(h) + 4, 4)), 0)
        mask_draw = ImageDraw.Draw(mask)
        draw_text_letterspaced(mask_draw, (2, 2), text, font, 255, letter_spacing)
        grad = build_gradient_image(mask.width, mask.height, field["gradient"])
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        overlay.paste(grad, (int(left) - 2, int(top) - 2), mask)
        composited = Image.alpha_composite(base, overlay)
        base.paste(composited)
    else:
        fill = text_color(field)
        draw_text_letterspaced(draw, (left, top), text, font, fill, letter_spacing)


def render_poster(
    *,
    template: dict[str, Any],
    text_values: dict[str, Any],
    person_image: Image.Image | None,
    background_image: Image.Image | None,
    foreground_image: Image.Image | None,
    person_x: float = 0,
    person_y: float = 0,
    person_scale: float = 1.0,
) -> Image.Image:
    canvas_cfg = template.get("canvas", {})
    width = int(canvas_cfg.get("width", 1080))
    height = int(canvas_cfg.get("height", 1350))
    result = Image.new("RGBA", (width, height), (0, 0, 0, 255))

    if background_image is not None:
        result.alpha_composite(ensure_rgba(background_image, width, height))

    if person_image is not None:
        person_rgba = person_image.convert("RGBA")
        pw = max(1, int(person_rgba.width * person_scale))
        ph = max(1, int(person_rgba.height * person_scale))
        person_resized = person_rgba.resize((pw, ph), Image.LANCZOS)
        result.alpha_composite(person_resized, (int(person_x), int(person_y)))

    if foreground_image is not None:
        result.alpha_composite(ensure_rgba(foreground_image, width, height))

    template_fonts = template.get("fonts", []) or []
    for field in template.get("textFields", []) or []:
        value = text_values.get(field.get("key"), field.get("defaultValue", ""))
        if value in (None, ""):
            continue
        draw_field(result, field, str(value), template_fonts)

    return result


def save_png_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
