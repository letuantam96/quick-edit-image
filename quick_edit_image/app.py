"""Tkinter GUI: paste images, auto-resize, place a shared PNG watermark, export."""

from __future__ import annotations

import json
import os
import re
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageTk

from . import __version__
from .core import (AUTO_STAMP, Item, Placement, auto_root, clamp_placement, clean_old_auto_dirs, compose,
                   empty_dir, export_item, grab_clipboard_images, load_watermark, name_problem, watermark_box,
                   clean_name, slugify, EXPORT_EXT, MAX_BYTES)

CONFIG_PATH = Path.home() / ".quick_edit_image.json"
ASSETS = Path(__file__).parent / "assets"
DEFAULT_WIDTH = 700
THUMB = (120, 90)
HANDLE = 6  # half size of the corner handles, in screen px
ACCENT = "#2f6fdf"
ERROR_BG = "#f8d0d0"
SELECTED_BG = "#dce8fb"
ROW_BG = "#ffffff"


def trash_icon(color: str, size: int = 18) -> ImageTk.PhotoImage:
    # Drawn at 4x and downsampled for smooth edges.
    k = 4
    s = size * k
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = 2 * k
    d.rectangle((7 * k, 1 * k, 11 * k, 3 * k), outline=color, width=w // 2)   # handle
    d.line((2 * k, 4 * k, 16 * k, 4 * k), fill=color, width=w)               # lid
    d.rounded_rectangle((4 * k, 6 * k, 14 * k, 17 * k), radius=k, outline=color, width=w)  # can
    for x in (7, 9, 11):
        d.line((x * k, 8 * k, x * k, 15 * k), fill=color, width=k)
    return ImageTk.PhotoImage(img.resize((size, size), Image.Resampling.LANCZOS))


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("JokamQuimedit - JOKAM Quick Image Edit for Thanh Hằng")
        self.minsize(860, 560)
        if os.name == "nt":
            self.iconbitmap(default=str(ASSETS / "icon.ico"))
        else:
            self.iconphoto(True, tk.PhotoImage(file=str(ASSETS / "icon.png")))

        cfg = self._load_config()
        self.window_geom = cfg.get("window", "")
        if self._on_screen(self.window_geom):
            self.geometry(self.window_geom)
        else:  # first run, or the screen it was on is gone
            self._center(1250, 800)
        if cfg.get("maximized"):
            self.state("zoomed")
        self.items: list[Item] = []
        self.selected: int | None = None
        self.last_placement = Placement(**cfg.get("placement", {}))
        self.width_var = tk.StringVar(value=str(cfg.get("width", DEFAULT_WIDTH)))
        self.kb_var = tk.StringVar(value=str(cfg.get("max_kb", MAX_BYTES // 1024)))
        self.max_kb = self._parse_max_kb() or MAX_BYTES // 1024
        self.target_width = self._parse_width() or DEFAULT_WIDTH
        self.wm_path = tk.StringVar(value=cfg.get("watermark", ""))
        self.wm: Image.Image | None = None
        self.wm_preview: Image.Image | None = None  # downsized copy for fast redraw while dragging
        self.out_dir = tk.StringVar(value=cfg.get("out_dir", ""))
        # One auto-export folder per session: the app opening, or "Xoá tất cả ảnh".
        self.auto_dir_var = tk.StringVar()
        self.new_auto_session()
        self.name_var = tk.StringVar()
        self.status = tk.StringVar()

        # Canvas state
        self.view: tuple[float, float, float] | None = None  # (offset_x, offset_y, display scale)
        self.base_tk: ImageTk.PhotoImage | None = None
        self.mark_tk: ImageTk.PhotoImage | None = None
        self.drag: dict | None = None
        self.rows: list[dict] = []
        self.flashing: set[int] = set()
        self.trash_icons = (trash_icon("#8a8a8a"), trash_icon("#d03030"))  # normal, hover

        self._build_ui()
        if self.wm_path.get():
            self._set_watermark(self.wm_path.get(), quiet=True)
        self._refresh_wm_label()

        self.bind_all("<Control-v>", self.on_paste)
        self.bind_all("<Control-V>", self.on_paste)
        self.bind("<Delete>", lambda e: None if isinstance(e.widget, (tk.Entry, ttk.Entry)) else self.delete_item(self.selected))
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_all()
        self.after(200, self.bring_to_front)

    def _center(self, w: int, h: int) -> None:
        """Open centered on the screen (without a position, Windows cascades each launch)."""
        left, top, right, bottom = 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()
        if os.name == "nt":  # the work area leaves out the taskbar
            import ctypes
            from ctypes import wintypes
            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rect), 0):  # SPI_GETWORKAREA
                left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
        title_bar = 31  # frame around Tk's client area, which geometry() sizes
        w = min(w, right - left - 16)
        h = min(h, bottom - top - title_bar - 8)
        x = left + (right - left - w) // 2
        y = top + max(0, (bottom - top - h - title_bar) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _on_screen(self, geom: str) -> bool:
        """Is the title bar of a saved 'WxH+X+Y' window on some monitor, so it can be dragged?"""
        m = re.fullmatch(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", geom)
        if not m:
            return False
        w, h, x, y = map(int, m.groups())
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
            user32.MonitorFromPoint.restype = ctypes.c_void_p
            return bool(user32.MonitorFromPoint(wintypes.POINT(x + w // 2, y + 10), 0))  # MONITOR_DEFAULTTONULL
        return 0 <= x + w // 2 < self.winfo_screenwidth() and 0 <= y < self.winfo_screenheight()

    def _sharp_taskbar_icon(self) -> None:
        """The taskbar shrinks Tk's 32 px icon to 24 px, which blurs it. Hand it the 24 px frame instead."""
        import ctypes
        user32 = ctypes.windll.user32
        user32.LoadImageW.restype = ctypes.c_void_p
        user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        size = user32.GetSystemMetrics(49) * 3 // 2  # SM_CXSMICON * 1.5 = taskbar icon size
        icon = user32.LoadImageW(None, str(ASSETS / "icon.ico"), 1, size, size, 0x10)  # IMAGE_ICON, LR_LOADFROMFILE
        if icon:
            user32.SendMessageW(int(self.wm_frame(), 16), 0x80, 1, icon)  # WM_SETICON, ICON_BIG

    def bring_to_front(self) -> None:
        # Launched from a .bat via pythonw, Windows won't give us focus and the
        # window opens behind Explorer; briefly going topmost pulls it forward.
        self.deiconify()
        if os.name == "nt":
            self._sharp_taskbar_icon()  # only sticks once the window is mapped
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()
        self.after(300, lambda: self.attributes("-topmost", False))

    # ---------- config ----------

    def _load_config(self) -> dict:
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def save_config(self) -> None:
        p = self.last_placement
        maximized = self.state() == "zoomed"
        if self.state() == "normal" and self.winfo_ismapped():  # keep the last normal size, so un-maximizing next time restores it
            self.window_geom = self.geometry()
        cfg = {"width": self.target_width, "max_kb": self.max_kb, "watermark": self.wm_path.get(), "out_dir": self.out_dir.get(),
               "placement": {"x": p.x, "y": p.y, "scale": p.scale},
               "window": self.window_geom, "maximized": maximized}
        try:
            CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    # ---------- layout ----------

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=(10, 8))
        top.pack(fill="x")
        ttk.Label(top, text="Chiều rộng").pack(side="left")
        width_entry = ttk.Entry(top, textvariable=self.width_var, width=7, justify="right")
        width_entry.pack(side="left", padx=(6, 2))
        width_entry.bind("<Return>", lambda _: self.apply_width())
        width_entry.bind("<FocusOut>", lambda _: self.apply_width())
        ttk.Label(top, text="px").pack(side="left")
        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=12)
        ttk.Label(top, text="Dung lượng tối ưu").pack(side="left")
        kb_entry = ttk.Entry(top, textvariable=self.kb_var, width=6, justify="right")
        kb_entry.pack(side="left", padx=(6, 2))
        kb_entry.bind("<Return>", lambda _: self.apply_max_kb())
        kb_entry.bind("<FocusOut>", lambda _: self.apply_max_kb())
        ttk.Label(top, text="KB").pack(side="left")
        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=12)
        ttk.Label(top, text="Watermark").pack(side="left")
        self.wm_label = ttk.Label(top, width=28, relief="groove", padding=(6, 2))
        self.wm_label.pack(side="left", padx=6)
        self.wm_thumb_label = ttk.Label(top)
        self.wm_thumb_label.pack(side="left", padx=(0, 6))
        ttk.Button(top, text="Đổi…", command=self.pick_watermark).pack(side="left")
        ttk.Label(top, text=f"v{__version__}", foreground="#666").pack(side="right")

        ttk.Separator(self).pack(fill="x")
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        # Left: pasted images
        left = ttk.Frame(body, width=440, padding=8)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        header = ttk.Frame(left)
        header.pack(fill="x")
        self.count_lbl = ttk.Label(header, foreground="#666")
        self.count_lbl.pack(side="left")
        ttk.Button(header, text="Xoá tất cả ảnh", command=self.clear_all).pack(side="right")
        holder = ttk.Frame(left)
        holder.pack(fill="both", expand=True, pady=6)
        self.list_canvas = tk.Canvas(holder, highlightthickness=0, background=ROW_BG)
        sb = ttk.Scrollbar(holder, orient="vertical", command=self.list_canvas.yview)
        self.list_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.list_canvas.pack(side="left", fill="both", expand=True)
        self.list_frame = tk.Frame(self.list_canvas, background=ROW_BG)
        self.list_window = self.list_canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.list_frame.bind("<Configure>", lambda _: self._update_list_scroll())
        self.list_canvas.bind("<Configure>", lambda e: (
            self.list_canvas.itemconfigure(self.list_window, width=e.width), self._update_list_scroll()))
        self.list_canvas.bind("<MouseWheel>", self._on_list_wheel)
        self.list_frame.bind("<MouseWheel>", self._on_list_wheel)
        ttk.Style(self).configure("Paste.TButton", padding=(0, 8))
        ttk.Button(left, text="Paste ảnh từ bộ nhớ", style="Paste.TButton",
                   command=self.on_paste).pack(fill="x")
        ttk.Label(left, text="hoặc ấn Ctrl + V để thêm ảnh", foreground="#888").pack(pady=(4, 0))

        ttk.Separator(body, orient="vertical").pack(side="left", fill="y")

        # Right: name bar + editor
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        name_bar = ttk.Frame(right, padding=(10, 8))
        name_bar.pack(fill="x")
        self.name_lbl = tk.Label(name_bar, text="Tên file")
        self.name_lbl.pack(side="left")
        self.name_entry = tk.Entry(name_bar, textvariable=self.name_var, relief="solid", borderwidth=1)
        self.name_entry.pack(side="left", fill="x", expand=True, padx=6, ipady=3)
        ttk.Label(name_bar, text=EXPORT_EXT).pack(side="left")
        self.name_var.trace_add("write", lambda *_: self.on_name_change())

        self.canvas = tk.Canvas(right, background="#e9e9e9", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self.render())
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Motion>", self.on_hover)

        ttk.Separator(self).pack(fill="x")
        bottom = ttk.Frame(self, padding=(10, 6))
        bottom.pack(fill="x")
        ttk.Label(bottom, text="Xuất vào:", foreground="#666").pack(side="left")
        ttk.Label(bottom, textvariable=self.out_dir).pack(side="left", padx=6)
        ttk.Button(bottom, text="Chọn thư mục…", command=self.pick_out_dir).pack(side="left")
        ttk.Button(bottom, text="Xuất vào thư mục", command=self.export_all).pack(side="left", padx=(6, 0))
        ttk.Button(bottom, text="Xuất tự động", command=lambda: self.export_all(auto=True)).pack(side="right")
        ttk.Label(bottom, textvariable=self.auto_dir_var).pack(side="right", padx=6)
        ttk.Label(bottom, text="Xuất vào:", foreground="#666").pack(side="right")
        ttk.Label(bottom, textvariable=self.status, foreground="#666").pack(side="left", padx=(12, 0))

    def _list_fits(self) -> bool:
        return self.list_frame.winfo_reqheight() <= self.list_canvas.winfo_height()

    def _update_list_scroll(self) -> None:
        # A scrollregion smaller than the canvas still lets Tk scroll the rows
        # around, so pin it to at least the visible height.
        height = max(self.list_frame.winfo_reqheight(), self.list_canvas.winfo_height())
        self.list_canvas.configure(scrollregion=(0, 0, self.list_canvas.winfo_width(), height))
        if self._list_fits():
            self.list_canvas.yview_moveto(0)

    def _on_list_wheel(self, e) -> None:
        if not self._list_fits():
            self.list_canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")

    # ---------- list ----------

    def refresh_all(self) -> None:
        self.rebuild_list()
        self.load_selected_into_fields()
        self.render()

    def rebuild_list(self) -> None:
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.rows = []
        for i, item in enumerate(self.items):
            row = tk.Frame(self.list_frame, background=ROW_BG, highlightthickness=1,
                           highlightbackground="#ddd", padx=4, pady=4)
            row.pack(fill="x", pady=2, padx=1)
            r = item.resized(self.target_width)
            thumb_base = r.copy()
            thumb_base.thumbnail(THUMB)
            tl = tk.Label(row, width=THUMB[0], height=THUMB[1], background=ROW_BG)
            tl.pack(side="left")
            side = tk.Frame(row, background=ROW_BG)
            side.pack(side="right", padx=4)
            trash = tk.Label(side, image=self.trash_icons[0], background=ROW_BG, cursor="hand2")
            trash.pack()
            index = tk.Label(side, text=f"{i + 1}/{len(self.items)}", foreground="#888", background=ROW_BG)
            index.pack(pady=(4, 0))
            trash.bind("<Button-1>", lambda _, i=i: self.delete_item(i))
            trash.bind("<Enter>", lambda _, t=trash: t.configure(image=self.trash_icons[1]))
            trash.bind("<Leave>", lambda _, t=trash: t.configure(image=self.trash_icons[0]))
            text = tk.Frame(row, background=ROW_BG)
            text.pack(side="left", fill="x", expand=True, padx=6)
            name = tk.Label(text, anchor="w", background=ROW_BG)
            name.pack(fill="x")
            size = tk.Label(text, text=f"{r.width} × {r.height}", anchor="w", foreground="#888", background=ROW_BG)
            size.pack(fill="x")
            file_size = tk.Label(text, anchor="w", background=ROW_BG)
            file_size.pack(fill="x")
            entry = {"row": row, "widgets": [row, tl, text, name, size, file_size, side, index, trash],
                     "name": name, "file_size": file_size, "thumb_label": tl, "thumb_base": thumb_base,
                     "thumb": None}
            self.rows.append(entry)
            for w in entry["widgets"]:
                if w is not trash:
                    w.bind("<Button-1>", lambda _, i=i: self.select(i))
                w.bind("<MouseWheel>", self._on_list_wheel)
            self.update_thumb(i)
            self.update_row(i)
        self.count_lbl.config(text=f"Ảnh đã paste ({len(self.items)})")
        self.after_idle(self._update_list_scroll)

    def update_thumb(self, i: int) -> None:
        if i is None or i >= len(self.rows):
            return
        entry = self.rows[i]
        thumb = compose(entry["thumb_base"], self.wm_preview, self.items[i].placement)
        entry["thumb"] = ImageTk.PhotoImage(thumb)
        entry["thumb_label"].configure(image=entry["thumb"])

    def update_row(self, i: int) -> None:
        if i >= len(self.rows):
            return
        item, entry = self.items[i], self.rows[i]
        bg = ERROR_BG if i in self.flashing else SELECTED_BG if i == self.selected else ROW_BG
        for w in entry["widgets"]:
            w.configure(background=bg)
        entry["row"].configure(highlightbackground=ACCENT if i == self.selected else "#ddd")
        name = clean_name(item.name)
        entry["name"].configure(text=name or "(chưa đặt tên)", foreground="#222" if name else "#c0392b")
        if item.exported_bytes is None:
            entry["file_size"].configure(text="")
        else:
            over = item.exported_bytes > self.max_kb * 1024
            entry["file_size"].configure(text=f"Đã xuất: {item.exported_bytes / 1024:.1f} KB",
                                         foreground="#c0392b" if over else "#2e8b57")

    def forget_exported(self, indices=None) -> None:
        """The last export no longer matches what's on screen, so stop showing its file size."""
        for i in range(len(self.items)) if indices is None else indices:
            if self.items[i].exported_bytes is not None:
                self.items[i].exported_bytes = None
                self.update_row(i)

    def select(self, i: int | None) -> None:
        old = self.selected
        self.selected = i
        for j in (old, i):
            if j is not None:
                self.update_row(j)
        self.load_selected_into_fields()
        self.render()
        if i is not None and i < len(self.rows):
            self.after_idle(lambda: self._scroll_into_view(i))

    def _scroll_into_view(self, i: int | None) -> None:
        if i is None or i >= len(self.rows):  # list changed before this idle callback ran
            return
        row = self.rows[i]["row"]
        total = max(1, self.list_frame.winfo_height())
        top, bottom = row.winfo_y() / total, (row.winfo_y() + row.winfo_height()) / total
        first, last = self.list_canvas.yview()
        if top < first:
            self.list_canvas.yview_moveto(top)
        elif bottom > last:
            self.list_canvas.yview_moveto(bottom - (last - first))

    def load_selected_into_fields(self) -> None:
        self._loading_name = True
        item = self.current()
        self.name_var.set(item.name if item else "")
        self.name_entry.configure(state="normal" if item else "disabled")
        self._loading_name = False
        self._paint_name_field()

    def current(self) -> Item | None:
        return self.items[self.selected] if self.selected is not None else None

    def on_name_change(self) -> None:
        item = self.current()
        if getattr(self, "_loading_name", False) or item is None:
            return
        text = self.name_var.get()
        slug = slugify(re.sub(r"\.(jpe?g|png)$", "", text, flags=re.IGNORECASE))
        if slug != text:
            # Rewrite as "day-la-ten-file", keeping the cursor after the same character.
            cursor = self.name_entry.index("insert")
            self.name_var.set(slug)  # Tk doesn't re-fire the trace from inside it
            self.name_entry.icursor(min(len(slug), len(slugify(text[:cursor]))))
            text = slug
        item.name = text
        self.flashing.discard(self.selected)
        self.update_row(self.selected)
        self._paint_name_field()

    def _paint_name_field(self) -> None:
        bad = self.selected in self.flashing
        self.name_entry.configure(background=ERROR_BG if bad else "white")
        self.name_lbl.configure(foreground="#c0392b" if bad else "black")

    # ---------- actions ----------

    def on_paste(self, event=None):
        images = grab_clipboard_images()
        if not images:
            if isinstance(getattr(event, "widget", None), (tk.Entry, ttk.Entry)):
                return None  # normal text paste into the field
            self.status.set("Clipboard không có ảnh.")
            return "break"
        for img in images:
            self.items.append(Item(original=img, placement=self.last_placement.copy()))
        self.selected = len(self.items) - 1
        self.refresh_all()
        self.after_idle(lambda: self._scroll_into_view(self.selected))
        self.name_entry.focus_set()
        return "break"

    def clear_all(self) -> None:
        if not self.items:
            return
        if not messagebox.askyesno("Xoá tất cả ảnh", f"Xoá hết {len(self.items)} ảnh trong danh sách?",
                                   icon="warning", default="no"):
            return
        self.items.clear()
        self.flashing.clear()
        self.selected = None
        self.refresh_all()
        self.new_auto_session()

    def new_auto_session(self) -> None:
        """Start a fresh auto-export folder named by the current time."""
        now = datetime.now()
        root = auto_root()
        self.auto_dir = root / now.strftime(AUTO_STAMP)
        self.auto_dir_var.set(self.auto_dir.as_posix())
        clean_old_auto_dirs(root, now)

    def delete_item(self, i: int | None) -> None:
        if i is None or i >= len(self.items):
            return
        del self.items[i]
        self.flashing = {j - (j > i) for j in self.flashing if j != i}
        if self.selected is not None and (self.selected > i or self.selected >= len(self.items)):
            self.selected -= 1
        if not self.items:
            self.selected = None
        self.refresh_all()

    def _parse_width(self) -> int | None:
        try:
            w = int(self.width_var.get().strip())
        except ValueError:
            return None
        return w if 16 <= w <= 20000 else None

    def apply_width(self) -> None:
        w = self._parse_width()
        if w is None:
            messagebox.showwarning("Chiều rộng không hợp lệ", "Nhập số pixel từ 16 đến 20000.")
            self.width_var.set(str(self.target_width))
            return
        if w != self.target_width:
            self.target_width = w
            for item in self.items:
                item.exported_bytes = None
            self.rebuild_list()
            self.render()
            self.save_config()

    def _parse_max_kb(self) -> int | None:
        try:
            kb = int(self.kb_var.get().strip())
        except ValueError:
            return None
        return kb if 10 <= kb <= 50000 else None

    def apply_max_kb(self) -> None:
        kb = self._parse_max_kb()
        if kb is None:
            messagebox.showwarning("Dung lượng không hợp lệ", "Nhập số KB từ 10 đến 50000.")
            self.kb_var.set(str(self.max_kb))
            return
        if kb != self.max_kb:
            self.max_kb = kb
            self.save_config()
            self.forget_exported()

    def pick_watermark(self) -> None:
        p = filedialog.askopenfilename(title="Chọn watermark (PNG)", filetypes=[("PNG", "*.png")])
        if p:
            self._set_watermark(p)

    def _set_watermark(self, path: str, quiet: bool = False) -> None:
        try:
            wm = load_watermark(path)
        except OSError as e:
            if not quiet:
                messagebox.showerror("Không mở được watermark", str(e))
            self.wm_path.set("")
            self.wm = self.wm_preview = None
            self._refresh_wm_label()
            return
        self.wm = wm
        self.wm_preview = wm.copy()
        self.wm_preview.thumbnail((800, 800))
        self.wm_path.set(path)
        self._refresh_wm_label()
        self.render()
        for i in range(len(self.rows)):
            self.update_thumb(i)
        self.forget_exported()
        self.save_config()

    def _refresh_wm_label(self) -> None:
        p = self.wm_path.get()
        self.wm_label.configure(text=Path(p).name if p else "(chưa chọn)")
        if self.wm is None:
            self.wm_thumb = None
            self.wm_thumb_label.configure(image="")
            return
        # Checkerboard behind the logo so transparent / white marks stay visible.
        box = (48, 24)
        mark = self.wm.copy()
        mark.thumbnail(box, Image.Resampling.LANCZOS)
        bg = Image.new("RGBA", box, "#ffffff")
        draw = ImageDraw.Draw(bg)
        for y in range(0, box[1], 6):
            for x in range(0, box[0], 6):
                if (x + y) // 6 % 2:
                    draw.rectangle((x, y, x + 5, y + 5), fill="#d8d8d8")
        bg.alpha_composite(mark, ((box[0] - mark.width) // 2, (box[1] - mark.height) // 2))
        self.wm_thumb = ImageTk.PhotoImage(bg)
        self.wm_thumb_label.configure(image=self.wm_thumb)

    def pick_out_dir(self) -> None:
        d = filedialog.askdirectory(title="Thư mục xuất ảnh", initialdir=self.out_dir.get() or None)
        if d:
            self.out_dir.set(d)
            self.save_config()

    def export_all(self, auto: bool = False) -> None:
        """auto: export into this session's folder on the Desktop, wiping it first, then open it."""
        self.apply_width()
        self.apply_max_kb()
        if not self.items:
            messagebox.showinfo("Chưa có ảnh", "Copy ảnh rồi nhấn Ctrl+V để thêm.")
            return
        names = [it.name for it in self.items]
        problems = {i: p for i, it in enumerate(self.items) if (p := name_problem(it.name, names))}
        if problems:
            self.flash(set(problems))
            first = min(problems)
            self.select(first)
            self.name_entry.focus_set()
            lines = [f"Ảnh {i + 1}: {p}" for i, p in sorted(problems.items())]
            self.status.set(f"{len(problems)} ảnh cần sửa tên.")
            messagebox.showwarning("Cần sửa tên ảnh", "\n".join(lines[:15]))
            return
        if self.wm is None and not messagebox.askyesno("Chưa có watermark", "Chưa chọn watermark. Vẫn xuất ảnh?"):
            return
        if auto:
            out = self.auto_dir
        else:
            if not self.out_dir.get():
                self.pick_out_dir()
                if not self.out_dir.get():
                    return
            out = Path(self.out_dir.get())
            out.mkdir(parents=True, exist_ok=True)
            existing = [clean_name(it.name) + EXPORT_EXT for it in self.items
                        if (out / (clean_name(it.name) + EXPORT_EXT)).exists()]
            if existing and not messagebox.askyesno(
                    "Ghi đè?", f"{len(existing)} file đã có trong thư mục, ví dụ {existing[0]}.\nGhi đè?"):
                return
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            if auto:
                empty_dir(out)
            too_big = 0
            max_bytes = self.max_kb * 1024
            for i, item in enumerate(self.items, 1):
                self.status.set(f"Đang xuất {i}/{len(self.items)}…")
                self.update_idletasks()
                item.exported_bytes = export_item(item, self.target_width, self.wm, out, max_bytes).stat().st_size
                too_big += item.exported_bytes > max_bytes
                self.update_row(i - 1)
        except OSError as e:
            messagebox.showerror("Lỗi khi xuất", str(e))
            return
        finally:
            self.configure(cursor="")
        note = f" ({too_big} ảnh > {self.max_kb}KB)" if too_big else ""
        self.status.set(f"Đã xuất {len(self.items)} ảnh.{note}")
        if auto or messagebox.askyesno("Xong", f"Đã xuất {len(self.items)} ảnh JPG.\nMở thư mục?"):
            os.startfile(out)  # type: ignore[attr-defined]

    def flash(self, rows: set[int], times: int = 6) -> None:
        """Blink the given rows red, then leave them red until their name is fixed."""
        self.flashing = set(rows)

        def step(n: int) -> None:
            on = n % 2 == 0 or n >= times
            for i in rows:
                if i in self.flashing and i < len(self.rows):
                    bg = ERROR_BG if on else ROW_BG
                    for w in self.rows[i]["widgets"]:
                        w.configure(background=bg)
            self.name_lbl.configure(foreground="#c0392b" if on and self.selected in self.flashing else "black")
            if n < times:
                self.after(180, step, n + 1)
            else:
                for i in range(len(self.rows)):
                    self.update_row(i)
                self._paint_name_field()

        step(0)
        self._paint_name_field()

    # ---------- editor canvas ----------

    def render(self) -> None:
        c = self.canvas
        c.delete("all")
        cw, ch = c.winfo_width(), c.winfo_height()
        item = self.current()
        if item is None:
            self.view = None
            c.create_text(cw // 2, ch // 2, fill="#888", font=("Segoe UI", 12),
                          text="Copy ảnh rồi nhấn Ctrl+V để thêm")
            return
        img = item.resized(self.target_width)
        pad = 24
        scale = min((cw - 2 * pad) / img.width, (ch - 2 * pad) / img.height)
        scale = max(scale, 0.01)
        dw, dh = max(1, round(img.width * scale)), max(1, round(img.height * scale))
        ox, oy = (cw - dw) / 2, (ch - dh) / 2
        self.view = (ox, oy, scale)
        self.base_tk = ImageTk.PhotoImage(img.resize((dw, dh), Image.Resampling.BILINEAR))
        c.create_image(ox, oy, image=self.base_tk, anchor="nw")
        c.create_rectangle(ox, oy, ox + dw, oy + dh, outline="#bbb")
        self.render_mark()

    def render_mark(self) -> None:
        c = self.canvas
        c.delete("mark")
        item, wm = self.current(), self.wm_preview
        if item is None or wm is None or self.view is None:
            return
        # A placement carried over from an image with another aspect ratio may not fit this one.
        item.placement = clamp_placement(item.placement, item.resized(self.target_width).size, self.wm.size)
        x0, y0, x1, y1 = self.mark_rect()
        w, h = max(1, round(x1 - x0)), max(1, round(y1 - y0))
        self.mark_tk = ImageTk.PhotoImage(wm.resize((w, h), Image.Resampling.BILINEAR))
        c.create_image(x0, y0, image=self.mark_tk, anchor="nw", tags="mark")
        c.create_rectangle(x0, y0, x1, y1, outline=ACCENT, dash=(4, 3), tags="mark")
        for hx, hy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            c.create_rectangle(hx - HANDLE, hy - HANDLE, hx + HANDLE, hy + HANDLE,
                               fill="white", outline=ACCENT, width=2, tags="mark")

    def mark_rect(self) -> tuple[float, float, float, float]:
        item = self.current()
        img = item.resized(self.target_width)
        ox, oy, s = self.view
        left, top, w, h = watermark_box(item.placement, img.size, self.wm.size)
        return ox + left * s, oy + top * s, ox + (left + w) * s, oy + (top + h) * s

    def hit(self, x: float, y: float) -> str | None:
        if self.current() is None or self.wm is None or self.view is None:
            return None
        x0, y0, x1, y1 = self.mark_rect()
        for name, (hx, hy) in {"nw": (x0, y0), "ne": (x1, y0), "sw": (x0, y1), "se": (x1, y1)}.items():
            if abs(x - hx) <= HANDLE + 3 and abs(y - hy) <= HANDLE + 3:
                return name
        if x0 <= x <= x1 and y0 <= y <= y1:
            return "move"
        return None

    def on_hover(self, e) -> None:
        h = self.hit(e.x, e.y)
        cursor = {"nw": "size_nw_se", "se": "size_nw_se", "ne": "size_ne_sw", "sw": "size_ne_sw",
                  "move": "fleur"}.get(h, "")
        self.canvas.configure(cursor=cursor)

    def on_press(self, e) -> None:
        h = self.hit(e.x, e.y)
        if h is None:
            self.drag = None
            return
        x0, y0, x1, y1 = self.mark_rect()
        # The corner opposite the grabbed handle stays fixed while resizing.
        anchor = {"nw": (x1, y1), "ne": (x0, y1), "sw": (x1, y0), "se": (x0, y0)}.get(h)
        self.drag = {"mode": h, "dx": e.x - x0, "dy": e.y - y0, "anchor": anchor}

    def on_drag(self, e) -> None:
        if not self.drag:
            return
        item = self.current()
        img = item.resized(self.target_width)
        ox, oy, s = self.view
        W, H = img.size
        aspect = self.wm.height / self.wm.width
        mode = self.drag["mode"]
        if mode == "move":
            left = (e.x - self.drag["dx"] - ox) / s
            top = (e.y - self.drag["dy"] - oy) / s
            p = Placement(left / W, top / H, item.placement.scale)
        else:
            ax, ay = self.drag["anchor"]
            # Width follows whichever axis the mouse moved further along, keeping aspect ratio.
            w_screen = max(abs(e.x - ax), abs(e.y - ay) / aspect, 8)
            sign_x = -1 if mode in ("nw", "sw") else 1
            sign_y = -1 if mode in ("nw", "ne") else 1
            # Limit growth so the box stays inside the image on the dragged side.
            img_left, img_top = ox, oy
            img_right, img_bottom = ox + W * s, oy + H * s
            room_x = (img_right - ax) if sign_x > 0 else (ax - img_left)
            room_y = (img_bottom - ay) if sign_y > 0 else (ay - img_top)
            w_screen = min(w_screen, room_x, room_y / aspect)
            h_screen = w_screen * aspect
            left_screen = ax if sign_x > 0 else ax - w_screen
            top_screen = ay if sign_y > 0 else ay - h_screen
            p = Placement((left_screen - ox) / s / W, (top_screen - oy) / s / H, w_screen / s / W)
        item.placement = clamp_placement(p, img.size, self.wm.size)
        self.render_mark()
        self.update_thumb(self.selected)

    def on_release(self, _e) -> None:
        if self.drag and self.current():
            self.last_placement = self.current().placement.copy()
            self.save_config()
            self.forget_exported([self.selected])
        self.drag = None

    def on_close(self) -> None:
        if self.items and not messagebox.askyesno("Thoát?", "Ảnh đã paste sẽ mất nếu chưa xuất. Thoát?"):
            return
        self.save_config()
        self.destroy()


def main() -> None:
    if os.name == "nt":
        # Own taskbar group, so Windows shows our icon instead of python's.
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("JokamQuimedit")
    App().mainloop()
