import tkinter as tk
from tkinter import ttk
from pathlib import Path


def _color_for_size(size: int, max_size: int, colors: list[str]) -> str:
    if max_size == 0:
        return colors[0]
    ratio = min(size / max_size, 1.0)
    idx = int(ratio * (len(colors) - 1))
    return colors[idx]


def _squarify(items: list[tuple[object, float]], x: float, y: float, w: float, h: float) -> list[tuple[object, float, float, float, float]]:
    result = []
    if not items or w <= 0 or h <= 0:
        return result
    total = sum(v for _, v in items)
    if total == 0:
        return result
    items = sorted(items, key=lambda x: x[1], reverse=True)

    def layout(items, x, y, w, h):
        if not items:
            return
        if len(items) == 1:
            result.append((items[0][0], x, y, w, h))
            return
        total = sum(v for _, v in items)
        half = total / 2
        acc = 0
        split = 0
        for i, (_, v) in enumerate(items):
            acc += v
            if acc >= half:
                split = i + 1
                break
        left = items[:split]
        right = items[split:]
        left_total = sum(v for _, v in left)
        if w >= h:
            lw = w * left_total / total if total else w / 2
            layout(left, x, y, lw, h)
            layout(right, x + lw, y, w - lw, h)
        else:
            lh = h * left_total / total if total else h / 2
            layout(left, x, y, w, lh)
            layout(right, x, y + lh, w, h - lh)

    layout(items, x, y, w, h)
    return result


class Tooltip:
    def __init__(self, canvas: tk.Canvas, bg: str, fg: str):
        self._canvas = canvas
        self._bg = bg
        self._fg = fg
        self._win: tk.Toplevel | None = None

    def show(self, text: str, x: int, y: int):
        self.hide()
        self._win = tk.Toplevel(self._canvas)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        lbl = tk.Label(self._win, text=text, bg=self._bg, fg=self._fg,
                       font=("Segoe UI", 9), padx=6, pady=3, justify="left",
                       relief="solid", bd=1)
        lbl.pack()
        self._win.geometry(f"+{x+12}+{y+12}")

    def hide(self):
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None

    def update_colors(self, bg: str, fg: str):
        self._bg = bg
        self._fg = fg


def _fmt(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


class HeatmapTab(tk.Frame):
    def __init__(self, parent: ttk.Notebook, theme: dict, on_file_select=None):
        super().__init__(parent, bg=theme["bg"])
        self._theme = theme
        self._on_file_select = on_file_select
        self._rects: list[tuple[int, Path, int]] = []
        self._build()

    def _build(self):
        t = self._theme
        ctrl = ttk.Frame(self, style="App.TFrame")
        ctrl.pack(fill="x", padx=12, pady=(12, 6))
        ttk.Label(ctrl, text="View", style="Subtle.TLabel").pack(side="left", padx=(0, 8))
        self._mode = tk.StringVar(value="files")
        for text, val in (("Files", "files"), ("Folders", "folders")):
            ttk.Radiobutton(ctrl, text=text, variable=self._mode, value=val,
                            command=self._redraw).pack(side="left", padx=4)

        self._canvas = tk.Canvas(self, bg=t["canvas_bg"], cursor="crosshair", bd=0, highlightthickness=0)
        self._canvas.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._tooltip = Tooltip(self._canvas, t["tooltip_bg"], t["tooltip_fg"])
        self._canvas.bind("<Motion>", self._on_hover)
        self._canvas.bind("<Leave>", lambda _: self._tooltip.hide())
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Configure>", lambda _: self._redraw())

        self._items_files: list[tuple[Path, int]] = []
        self._items_folders: list[tuple[Path, int]] = []
    def update_theme(self, theme: dict) -> None:
        self._theme = theme
        self.configure(bg=theme["bg"])
        self._canvas.configure(bg=theme["canvas_bg"], highlightthickness=0)
        self._tooltip.update_colors(theme["tooltip_bg"], theme["tooltip_fg"])
        self._redraw()
    def load(self, files: list[tuple[Path, int]], folders: list[tuple[Path, int]]) -> None:
        self._items_files = files
        self._items_folders = folders
        self._redraw()

    def _redraw(self) -> None:
        self._canvas.delete("all")
        self._rects = []
        t = self._theme
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w < 4 or h < 4:
            return
        items = self._items_files if self._mode.get() == "files" else self._items_folders
        if not items:
            self._canvas.create_text(w // 2, h // 2, text="No data - run a scan first",
                                     fill=t["fg"], font=("Segoe UI", 11))
            return
        max_size = max(s for _, s in items)
        layout = _squarify([(p, float(s)) for p, s in items], 2, 2, w - 4, h - 4)
        for path, rx, ry, rw, rh in layout:
            if rw < 2 or rh < 2:
                continue
            size = dict(items).get(path, 0)
            fill = _color_for_size(size, max_size, t["heatmap_colors"])
            rid = self._canvas.create_rectangle(rx, ry, rx + rw, ry + rh,
                                                fill=fill, outline=t["bg"], width=1)
            self._rects.append((rid, path, size))
            if rw > 40 and rh > 16:
                name = path.name if hasattr(path, "name") else str(path)
                short = name if len(name) <= int(rw / 7) else name[:max(1, int(rw / 7))] + "..."
                self._canvas.create_text(rx + rw / 2, ry + rh / 2,
                                         text=short, fill="#ffffff",
                                         font=("Segoe UI", 8), width=rw - 4)

    def _rect_at(self, x: int, y: int) -> tuple[Path, int] | None:
        hits = self._canvas.find_overlapping(x, y, x, y)
        for rid, path, size in reversed(self._rects):
            if rid in hits:
                return path, size
        return None

    def _on_hover(self, event: tk.Event) -> None:
        hit = self._rect_at(event.x, event.y)
        if hit:
            path, size = hit
            self._tooltip.show(f"{path}\n{_fmt(size)}", event.x_root, event.y_root)
        else:
            self._tooltip.hide()

    def _on_click(self, event: tk.Event) -> None:
        hit = self._rect_at(event.x, event.y)
        if hit and self._on_file_select:
            self._on_file_select(hit[0], hit[1])


