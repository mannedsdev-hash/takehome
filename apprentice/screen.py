"""Screen capture and coordinate mapping.

Claude sees a downscaled screenshot and answers in that image's pixel space. pyautogui works in
logical screen points, which differ from captured pixels on HiDPI/Retina displays, so every
coordinate goes through `to_screen` before the mouse moves.
"""

import base64
import io
import math

from PIL import Image, ImageDraw

from . import config


class Screen:
    def __init__(self):
        import mss
        import pyautogui

        self._mss = mss.mss()
        self._monitor = self._mss.monitors[1]  # primary display
        self.logical_w, self.logical_h = pyautogui.size()
        phys_w, phys_h = self._monitor["width"], self._monitor["height"]
        scale = min(
            1.0,
            config.SCREENSHOT_MAX_LONG_EDGE / max(phys_w, phys_h),
            math.sqrt(config.SCREENSHOT_MAX_PIXELS / (phys_w * phys_h)),
        )
        self.sent_w, self.sent_h = int(phys_w * scale), int(phys_h * scale)

    def grab(self) -> Image.Image:
        raw = self._mss.grab(self._monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        return img.resize((self.sent_w, self.sent_h), Image.LANCZOS)

    def grab_region(self, x0: int, y0: int, x1: int, y1: int) -> Image.Image:
        """Crop a region (in sent-image coordinates) from a full-resolution capture."""
        raw = self._mss.grab(self._monitor)
        full = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        fx, fy = full.width / self.sent_w, full.height / self.sent_h
        crop = full.crop((int(x0 * fx), int(y0 * fy), int(x1 * fx), int(y1 * fy)))
        crop.thumbnail((config.SCREENSHOT_MAX_LONG_EDGE, config.SCREENSHOT_MAX_LONG_EDGE))
        return crop

    def to_screen(self, x: float, y: float) -> tuple[int, int]:
        return round(x * self.logical_w / self.sent_w), round(y * self.logical_h / self.sent_h)

    def to_sent(self, x: float, y: float) -> tuple[int, int]:
        return round(x * self.sent_w / self.logical_w), round(y * self.sent_h / self.logical_h)


def image_block(img: Image.Image, fmt: str = "PNG") -> dict:
    buf = io.BytesIO()
    if fmt == "JPEG":
        img.save(buf, "JPEG", quality=70)
        media = "image/jpeg"
    else:
        img.save(buf, "PNG", optimize=True)
        media = "image/png"
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media, "data": base64.b64encode(buf.getvalue()).decode()},
    }


def mark_click(img: Image.Image, x: int, y: int) -> Image.Image:
    """Draw a red ring where a click happened so Claude can see what was clicked in a recording."""
    img = img.copy()
    d = ImageDraw.Draw(img)
    for r, w in ((18, 4), (6, 0)):
        d.ellipse((x - r, y - r, x + r, y + r), outline=(255, 0, 0), width=w or 1, fill=None if w else (255, 0, 0))
    return img
