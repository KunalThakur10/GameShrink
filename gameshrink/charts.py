import tkinter as tk
from tkinter import ttk


def _draw_no_data(canvas: tk.Canvas, bg: str, fg: str, text: str = "No data") -> None:
    canvas.delete("all")
    canvas.configure(bg=bg, highlightthickness=0)
    w = max(1, canvas.winfo_width())
    h = max(1, canvas.winfo_height())
    canvas.create_text(w // 2, h // 2, text=text, fill=fg, font=("Segoe UI", 12, "bold"))


def draw_pie(canvas: tk.Canvas, data: list[tuple[str, float]], colors: list[str], bg: str, fg: str) -> None:
    canvas.delete("all")
    canvas.configure(bg=bg, highlightthickness=0)
    if not data:
        _draw_no_data(canvas, bg, fg, "Run a scan to view extension share")
        return
    w = max(1, canvas.winfo_width())
    h = max(1, canvas.winfo_height())
    pad = 28
    legend_w = min(240, max(160, w // 3))
    cx = max(80, (w - legend_w) // 2)
    cy = h // 2
    r = min(cx - pad, cy - pad, 150)
    if r < 20:
        return
    total = sum(v for _, v in data)
    if total == 0:
        _draw_no_data(canvas, bg, fg)
        return
    start = -90.0
    for i, (_, value) in enumerate(data):
        extent = (value / total) * 360.0
        color = colors[i % len(colors)]
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=start, extent=extent, fill=color, outline=bg, width=2)
        start += extent
    canvas.create_oval(cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2, fill=bg, outline=bg)
    canvas.create_text(cx, cy - 8, text="Total", fill=fg, font=("Segoe UI", 9))
    canvas.create_text(cx, cy + 10, text=f"{len(data)} types", fill=fg, font=("Segoe UI", 13, "bold"))
    lx = w - legend_w + 12
    ly = max(20, h // 2 - min(len(data), 10) * 11)
    for i, (label, value) in enumerate(data[:12]):
        color = colors[i % len(colors)]
        pct = (value / total * 100) if total else 0
        canvas.create_rectangle(lx, ly, lx + 12, ly + 12, fill=color, outline="")
        short = label if len(label) <= 18 else label[:16] + "..."
        canvas.create_text(lx + 20, ly + 6, text=f"{short}  {pct:.1f}%", anchor="w", fill=fg, font=("Segoe UI", 9))
        ly += 20


def draw_bar(canvas: tk.Canvas, data: list[tuple[str, float]], color: str, bg: str, fg: str, grid: str, title: str = "") -> None:
    canvas.delete("all")
    canvas.configure(bg=bg, highlightthickness=0)
    if not data:
        _draw_no_data(canvas, bg, fg, "Run a scan to view this chart")
        return
    w = max(1, canvas.winfo_width())
    h = max(1, canvas.winfo_height())
    pad_left, pad_right, pad_top, pad_bottom = 70, 24, 42, 92
    chart_w = w - pad_left - pad_right
    chart_h = h - pad_top - pad_bottom
    if chart_w < 40 or chart_h < 40:
        return
    if title:
        canvas.create_text(pad_left, 18, text=title, anchor="w", fill=fg, font=("Segoe UI", 11, "bold"))
    max_val = max(v for _, v in data) or 1
    for step in range(5):
        y = pad_top + chart_h - int(step / 4 * chart_h)
        val = max_val * step / 4
        canvas.create_line(pad_left, y, pad_left + chart_w, y, fill=grid)
        canvas.create_text(pad_left - 8, y, text=_fmt_short(val), anchor="e", fill=fg, font=("Segoe UI", 8))
    n = len(data)
    slot = chart_w / n
    bar_w = max(8, min(42, int(slot * 0.62)))
    for i, (label, value) in enumerate(data):
        bh = int((value / max_val) * chart_h)
        x0 = int(pad_left + i * slot + (slot - bar_w) / 2)
        x1 = x0 + bar_w
        y0 = pad_top + chart_h - bh
        y1 = pad_top + chart_h
        canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
        short = label if len(label) <= 13 else label[:11] + "..."
        canvas.create_text((x0 + x1) // 2, y1 + 8, text=short, anchor="n", angle=45, fill=fg, font=("Segoe UI", 8))
    canvas.create_line(pad_left, pad_top, pad_left, pad_top + chart_h, fill=grid)
    canvas.create_line(pad_left, pad_top + chart_h, pad_left + chart_w, pad_top + chart_h, fill=grid)


def _fmt_short(val: float) -> str:
    for unit in ("", "K", "M", "G", "T"):
        if val < 1024:
            return f"{val:.0f}{unit}"
        val /= 1024
    return f"{val:.0f}P"


class ChartsTab(tk.Frame):
    def __init__(self, parent: ttk.Notebook, theme: dict):
        super().__init__(parent, bg=theme["bg"])
        self._theme = theme
        self._data = ([], [], [])
        self._build()

    def _build(self):
        t = self._theme
        nb = ttk.Notebook(self, style="Modern.TNotebook")
        nb.pack(fill="both", expand=True, padx=12, pady=12)
        self._notebook = nb
        self._pie_canvas = self._add_canvas_tab("Extensions")
        self._bar_folders_canvas = self._add_canvas_tab("Largest Folders")
        self._bar_files_canvas = self._add_canvas_tab("Largest Files")
        for canvas in (self._pie_canvas, self._bar_folders_canvas, self._bar_files_canvas):
            canvas.configure(bg=t["canvas_bg"], highlightthickness=0)
            canvas.bind("<Configure>", lambda _e: self._redraw())

    def _add_canvas_tab(self, title: str) -> tk.Canvas:
        frame = tk.Frame(self._notebook, bg=self._theme["bg"], padx=12, pady=12)
        self._notebook.add(frame, text=title)
        canvas = tk.Canvas(frame, bg=self._theme["canvas_bg"], width=720, height=360, bd=0, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        return canvas

    def update_theme(self, theme: dict) -> None:
        self._theme = theme
        self.configure(bg=theme["bg"])
        for c in (self._pie_canvas, self._bar_folders_canvas, self._bar_files_canvas):
            c.master.configure(bg=theme["bg"])
            c.configure(bg=theme["canvas_bg"])
        self._redraw()

    def update(self, ext_data: list[tuple[str, float]], folder_data: list[tuple[str, float]], file_data: list[tuple[str, float]]) -> None:
        self._data = (ext_data, folder_data, file_data)
        self._redraw()

    def _redraw(self) -> None:
        ext_data, folder_data, file_data = self._data
        t = self._theme
        draw_pie(self._pie_canvas, ext_data, t["chart_colors"], t["canvas_bg"], t["fg"])
        draw_bar(self._bar_folders_canvas, folder_data, t["bar_color"], t["canvas_bg"], t["fg"], t["chart_grid"], "Largest Folders")
        draw_bar(self._bar_files_canvas, file_data, t["bar_color"], t["canvas_bg"], t["fg"], t["chart_grid"], "Largest Files")
