"""Image logic, independent of the GUI."""

from __future__ import annotations

import io
import os
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageGrab

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
    exported_bytes: int | None = None  # file size of the last export
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
    if sum(clean_name(n) == name for n in all_names) > 1:
        return "Tên bị trùng"
    return None


def slugify(text: str) -> str:
    """'Đây là Tên file' -> 'day-la-ten-file'. Keeps a trailing '-' so a space being typed isn't eaten."""
    text = text.replace("đ", "d").replace("Đ", "D")
    text = "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return text.lstrip("-")


def clean_name(name: str) -> str:
    name = name.strip()
    for ext in (".jpg", ".jpeg", ".png"):
        if name.lower().endswith(ext):
            name = name[:-len(ext)]
    return slugify(name).strip("-")


AUTO_DIR_NAME = "JokamQuimedit"
AUTO_STAMP = "%Y%m%d-%H%M%S"
AUTO_KEEP_DAYS = 14


def desktop_dir() -> Path:
    """The real Desktop folder, which may be redirected (e.g. into OneDrive)."""
    if os.name == "nt":
        import ctypes
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0:  # CSIDL_DESKTOPDIRECTORY
            return Path(buf.value)
    return Path.home() / "Desktop"


def auto_root() -> Path:
    return desktop_dir() / AUTO_DIR_NAME


def clean_old_auto_dirs(root: Path, now: datetime, keep_days: int = AUTO_KEEP_DAYS) -> None:
    """Delete auto-export folders older than keep_days. Only touches folders named like a timestamp."""
    if not root.is_dir():
        return
    for d in root.iterdir():
        try:
            made = datetime.strptime(d.name, AUTO_STAMP)
        except ValueError:
            continue
        if d.is_dir() and now - made > timedelta(days=keep_days):
            shutil.rmtree(d, ignore_errors=True)


def empty_dir(path: Path) -> None:
    """Create the folder, or remove everything inside it if it already exists."""
    path.mkdir(parents=True, exist_ok=True)
    for p in path.iterdir():
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()


RELEASES_API = "https://api.github.com/repos/letuantam96/quick-edit-image/releases/latest"


def parse_version(text: str) -> tuple[int, ...] | None:
    """'v1.2.3' or '1.2.3' -> (1, 2, 3)."""
    m = re.fullmatch(r"v?(\d+(?:\.\d+)*)", text.strip())
    return tuple(map(int, m.group(1).split("."))) if m else None


def newer_release(current: str, timeout: float = 5) -> tuple[str, str] | None:
    """(tag, page url) of the latest GitHub release if it's newer than current; None otherwise or on any error."""
    import json
    import urllib.request
    try:
        req = urllib.request.Request(RELEASES_API, headers={"Accept": "application/vnd.github+json",
                                                            "User-Agent": "JokamQuimedit"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        tag, url = data["tag_name"], data["html_url"]
    except Exception:  # offline, rate-limited, repo private, ...: just stay quiet
        return None
    latest, mine = parse_version(tag), parse_version(current)
    if latest and mine and latest > mine:
        return tag, url
    return None


EXPORT_EXT = ".jpg"
MAX_BYTES = 100 * 1024
MIN_QUALITY = 30


def encode_jpeg(img: Image.Image, max_bytes: int = MAX_BYTES) -> bytes:
    """Highest JPEG quality that fits max_bytes; falls back to MIN_QUALITY if nothing fits."""
    if img.mode != "RGB":
        flat = Image.new("RGB", img.size, "white")  # JPEG has no alpha: transparent areas become white
        flat.paste(img, mask=img.getchannel("A") if img.mode == "RGBA" else None)
        img = flat

    def encode(q: int) -> bytes:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        return buf.getvalue()

    best = encode(95)
    if len(best) <= max_bytes:
        return best
    lo, hi = MIN_QUALITY, 94
    best = encode(lo)
    while lo <= hi:
        mid = (lo + hi) // 2
        data = encode(mid)
        if len(data) <= max_bytes:
            best, lo = data, mid + 1
        else:
            hi = mid - 1
    return best


def export_item(item: Item, width: int, wm: Image.Image | None, out_dir: Path,
                max_bytes: int = MAX_BYTES) -> Path:
    dst = out_dir / (clean_name(item.name) + EXPORT_EXT)
    dst.write_bytes(encode_jpeg(compose(item.resized(width), wm, item.placement), max_bytes))
    return dst
