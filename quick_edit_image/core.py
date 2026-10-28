"""Image logic, independent of the GUI."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageGrab

INVALID_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


@dataclass
class Placement:
    """Watermark box relative to the image, so it survives a change of target width.

    x, y: top-left corner as a fraction of image width / height.
    scale: watermark width as a fraction of image width.
    """
    x: float = 0.70
    y: float = 0.85
    scale: float = 0.25

    def copy(self) -> "Placement":
        return Placement(self.x, self.y, self.scale)


@dataclass
class Item:
    original: Image.Image
    name: str = ""
    placement: Placement = field(default_factory=Placement)
    _resized: tuple[int, Image.Image] | None = None

    def resized(self, width: int) -> Image.Image:
        if self._resized is None or self._resized[0] != width:
            self._resized = (width, resize_to_width(self.original, width))
        return self._resized[1]


def resize_to_width(img: Image.Image, width: int) -> Image.Image:
    height = max(1, round(img.height * width / img.width))
    return img.resize((width, height), Image.Resampling.LANCZOS)


def clamp_placement(p: Placement, img_size: tuple[int, int], wm_size: tuple[int, int]) -> Placement:
    """Keep the watermark fully inside the image."""
    W, H = img_size
    aspect = wm_size[1] / wm_size[0]
    # Largest scale where the watermark still fits both horizontally and vertically.
    max_scale = min(1.0, H / (W * aspect))
    scale = min(max(p.scale, 0.02), max_scale)
    w_frac = scale
    h_frac = scale * W * aspect / H
    x = min(max(p.x, 0.0), 1.0 - w_frac)
    y = min(max(p.y, 0.0), 1.0 - h_frac)
    return Placement(x, y, scale)


def watermark_box(p: Placement, img_size: tuple[int, int], wm_size: tuple[int, int]) -> tuple[int, int, int, int]:
    """(left, top, width, height) in image pixels."""
    W, H = img_size
    w = max(1, round(p.scale * W))
    h = max(1, round(w * wm_size[1] / wm_size[0]))
    return round(p.x * W), round(p.y * H), w, h


def compose(img: Image.Image, wm: Image.Image | None, p: Placement) -> Image.Image:
    out = img.convert("RGBA")
    if wm is None:
        return out
    left, top, w, h = watermark_box(clamp_placement(p, out.size, wm.size), out.size, wm.size)
    mark = wm.resize((w, h), Image.Resampling.LANCZOS)
    out.alpha_composite(mark, (left, top))
    return out


def load_watermark(path: str | Path) -> Image.Image:
    with Image.open(path) as f:
        return f.convert("RGBA")


def grab_clipboard_images() -> list[Image.Image]:
    """Images on the clipboard: a copied bitmap, or image files copied in Explorer."""
    try:
        data = ImageGrab.grabclipboard()
    except OSError:
        return []
    if isinstance(data, Image.Image):
        return [data.convert("RGBA")]
    images = []
    if isinstance(data, list):
        for p in data:
            if Path(p).suffix.lower() in IMAGE_EXTS:
                try:
                    with Image.open(p) as f:
                        images.append(f.convert("RGBA"))
                except OSError:
                    pass
    return images


def name_problem(name: str, all_names: list[str]) -> str | None:
    """Why this file name can't be exported, or None if it's fine."""
    name = clean_name(name)
    if not name:
        return "Chưa đặt tên"
    if INVALID_NAME_CHARS.search(name):
        return 'Tên chứa ký tự không hợp lệ (< > : " / \\ | ? *)'
    if sum(clean_name(n).lower() == name.lower() for n in all_names) > 1:
        return "Tên bị trùng"
    return None


def clean_name(name: str) -> str:
    name = name.strip()
    if name.lower().endswith(".png"):
        name = name[:-4].rstrip()
    return name


def export_item(item: Item, width: int, wm: Image.Image | None, out_dir: Path) -> Path:
    dst = out_dir / (clean_name(item.name) + ".png")
    compose(item.resized(width), wm, item.placement).save(dst)
    return dst
