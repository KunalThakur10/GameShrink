import json
from pathlib import Path

_PREFS_FILE = Path(__file__).parent / "prefs.json"

LIGHT = {
    "name": "light",
    "bg": "#f6f8fb",
    "fg": "#172033",
    "muted_fg": "#667085",
    "surface": "#ffffff",
    "surface_alt": "#eef2f7",
    "border": "#d7dde8",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "accent_fg": "#ffffff",
    "success": "#12805c",
    "warning": "#b54708",
    "danger": "#b42318",
    "entry_bg": "#ffffff",
    "entry_fg": "#172033",
    "tree_bg": "#ffffff",
    "tree_alt_bg": "#f8fafc",
    "tree_fg": "#172033",
    "tree_sel_bg": "#dbeafe",
    "tree_sel_fg": "#0f172a",
    "frame_bg": "#f6f8fb",
    "label_bg": "#f6f8fb",
    "label_fg": "#172033",
    "text_bg": "#ffffff",
    "text_fg": "#172033",
    "status_bg": "#e9eef8",
    "status_fg": "#344054",
    "canvas_bg": "#ffffff",
    "tooltip_bg": "#111827",
    "tooltip_fg": "#f9fafb",
    "progress_bg": "#dbe4f0",
    "chart_grid": "#d7dde8",
    "chart_colors": [
        "#2563eb", "#16a34a", "#f97316", "#dc2626",
        "#7c3aed", "#0891b2", "#ca8a04", "#db2777",
        "#475569", "#65a30d",
    ],
    "bar_color": "#2563eb",
    "heatmap_colors": ["#dbeafe", "#93c5fd", "#3b82f6", "#1e3a8a"],
}

DARK = {
    "name": "dark",
    "bg": "#101828",
    "fg": "#f2f4f7",
    "muted_fg": "#98a2b3",
    "surface": "#182230",
    "surface_alt": "#202b3c",
    "border": "#344054",
    "accent": "#60a5fa",
    "accent_hover": "#93c5fd",
    "accent_fg": "#0b1220",
    "success": "#32d583",
    "warning": "#fdb022",
    "danger": "#f97066",
    "entry_bg": "#111827",
    "entry_fg": "#f2f4f7",
    "tree_bg": "#111827",
    "tree_alt_bg": "#182230",
    "tree_fg": "#f2f4f7",
    "tree_sel_bg": "#1d4ed8",
    "tree_sel_fg": "#ffffff",
    "frame_bg": "#101828",
    "label_bg": "#101828",
    "label_fg": "#f2f4f7",
    "text_bg": "#111827",
    "text_fg": "#f2f4f7",
    "status_bg": "#182230",
    "status_fg": "#d0d5dd",
    "canvas_bg": "#111827",
    "tooltip_bg": "#f2f4f7",
    "tooltip_fg": "#101828",
    "progress_bg": "#344054",
    "chart_grid": "#344054",
    "chart_colors": [
        "#60a5fa", "#34d399", "#fb923c", "#f87171",
        "#a78bfa", "#22d3ee", "#facc15", "#f472b6",
        "#cbd5e1", "#a3e635",
    ],
    "bar_color": "#60a5fa",
    "heatmap_colors": ["#1e293b", "#1d4ed8", "#0ea5e9", "#f97316"],
}


def load_preferences() -> dict:
    try:
        data = json.loads(_PREFS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_preferences(data: dict) -> None:
    try:
        _PREFS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_theme() -> dict:
    data = load_preferences()
    return DARK if data.get("theme") == "dark" else LIGHT


def save_theme(theme: dict) -> None:
    data = load_preferences()
    data["theme"] = theme["name"]
    save_preferences(data)


def other_theme(theme: dict) -> dict:
    return DARK if theme["name"] == "light" else LIGHT
