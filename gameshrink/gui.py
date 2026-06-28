import os
import time
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from builder import BuildPlan, build_dest_folder, execute_build, make_plan
from charts import ChartsTab
from heatmap import HeatmapTab
from reporter import format_size, generate_report
from scanner import ScanResult, FileEntry, largest_files, largest_folders, scan
from config import REPORTS_DIR, WORKSPACE_DIR, TOP_FILES_COUNT, TOP_FOLDERS_COUNT
from themes import load_preferences, load_theme, other_theme, save_preferences, save_theme

PRESET_EXTENSIONS = {
    "Movies (.bik)": ".bik",
    "Text files (.txt)": ".txt",
    "Logs (.log)": ".log",
}

EXT_CATEGORIES = {
    ".bik": "Video", ".mp4": "Video", ".avi": "Video", ".wmv": "Video",
    ".mp3": "Audio", ".wav": "Audio", ".ogg": "Audio",
    ".txt": "Text", ".log": "Log", ".ini": "Config", ".cfg": "Config",
    ".exe": "Executable", ".dll": "Library",
    ".pak": "Archive", ".zip": "Archive", ".rar": "Archive",
    ".dds": "Texture", ".png": "Image", ".jpg": "Image", ".tga": "Image",
}

EXT_PURPOSES = {
    ".bik": "Cutscene video", ".mp4": "Video file",
    ".mp3": "Music/SFX", ".wav": "Audio", ".ogg": "Audio",
    ".txt": "Text/Readme", ".log": "Log file", ".ini": "Config", ".cfg": "Config",
    ".exe": "Game executable", ".dll": "Runtime library",
    ".pak": "Game data archive", ".dds": "GPU texture", ".png": "Image", ".tga": "Texture",
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self._prefs = load_preferences()
        self._theme = load_theme()
        self.title("GameShrink")
        self.minsize(1040, 740)
        self._restore_geometry()
        self.resizable(True, True)
        self._result: ScanResult | None = None
        self._report_path: Path | None = None
        self._plan: BuildPlan | None = None
        self._build_dest: Path | None = None
        self._scan_start: float = 0.0
        self._last_scan_time: str = "â€”"
        self._last_scan_duration: float = 0.0
        self._last_build_size: int = 0
        self._last_space_saved: int = 0
        self._activity_lines: list[str] = []
        self._skipped_names: list[str] = []
        self._build_ui()
        self._apply_theme()


    def _restore_geometry(self):
        geometry = self._prefs.get("geometry")
        if isinstance(geometry, str) and "x" in geometry:
            try:
                self.geometry(geometry)
                return
            except tk.TclError:
                pass
        self.geometry("1180x780")

    def _save_window_state(self):
        self._prefs["geometry"] = self.geometry()
        self._prefs["last_folder"] = self._folder_var.get().strip()
        self._prefs["theme"] = self._theme["name"]
        save_preferences(self._prefs)
    def _build_ui(self):
        t = self._theme
        self._folder_var = tk.StringVar(value=self._prefs.get("last_folder", ""))
        self._status_var = tk.StringVar(value="Ready")

        self._app = ttk.Frame(self, style="App.TFrame", padding=(16, 14, 16, 10))
        self._app.pack(fill="both", expand=True)
        self._app.columnconfigure(0, weight=1)
        self._app.rowconfigure(2, weight=1)

        header = ttk.Frame(self._app, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="GameShrink", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Analyze, plan, and build smaller game folders", style="Subtle.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))
        self._theme_btn = ttk.Button(header, text=self._theme_label(), style="Tool.TButton", command=self._toggle_theme)
        self._theme_btn.grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 0))

        folder_card = ttk.Frame(self._app, style="Card.TFrame", padding=14)
        folder_card.grid(row=1, column=0, sticky="ew", pady=(14, 12))
        folder_card.columnconfigure(1, weight=1)
        ttk.Label(folder_card, text="Game folder", style="Caption.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self._folder_entry = ttk.Entry(folder_card, textvariable=self._folder_var)
        self._folder_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self._browse_btn = ttk.Button(folder_card, text="Browse...", style="Tool.TButton", command=self._browse)
        self._browse_btn.grid(row=0, column=2, padx=(0, 8))
        self._scan_btn = ttk.Button(folder_card, text="Scan Game", style="Primary.TButton", command=self._start_scan)
        self._scan_btn.grid(row=0, column=3, padx=(0, 8))
        self._report_btn = ttk.Button(folder_card, text="Open Report", style="Tool.TButton", command=self._open_report, state="disabled")
        self._report_btn.grid(row=0, column=4, padx=(0, 8))
        self._workspace_btn = ttk.Button(folder_card, text="Open Workspace", style="Tool.TButton", command=self._open_workspace)
        self._workspace_btn.grid(row=0, column=5, padx=(0, 8))
        ttk.Button(folder_card, text="Exit", style="Tool.TButton", command=self._on_close).grid(row=0, column=6)
        self._progress = ttk.Progressbar(folder_card, mode="indeterminate", style="Modern.Horizontal.TProgressbar")
        self._progress.grid(row=1, column=0, columnspan=7, sticky="ew", pady=(12, 0))

        self._main_pane = ttk.Panedwindow(self._app, orient="vertical")
        self._main_pane.grid(row=2, column=0, sticky="nsew")

        self._notebook = ttk.Notebook(self._main_pane, style="Modern.TNotebook")
        self._main_pane.add(self._notebook, weight=5)

        self._tab_dashboard = self._make_dashboard_tab()
        self._notebook.add(self._tab_dashboard, text="Dashboard")

        self._tab_files_frame, self._files_tree = self._make_tree_tab(
            ("Rank", "File", "Size"), (70, 680, 140))
        self._notebook.add(self._tab_files_frame, text="Largest Files")
        self._files_tree.bind("<<TreeviewSelect>>", lambda e: self._on_tree_select(self._files_tree, "file"))

        self._tab_folders_frame, self._folders_tree = self._make_tree_tab(
            ("Rank", "Folder", "Size"), (70, 680, 140))
        self._notebook.add(self._tab_folders_frame, text="Largest Folders")
        self._folders_tree.bind("<<TreeviewSelect>>", lambda e: self._on_tree_select(self._folders_tree, "folder"))

        self._tab_ext_frame, self._ext_tree = self._make_tree_tab(
            ("Extension", "Count", "Total Size"), (180, 160, 160))
        self._notebook.add(self._tab_ext_frame, text="Extensions")

        self._charts_tab = ChartsTab(self._notebook, self._theme)
        self._notebook.add(self._charts_tab, text="Charts")

        self._heatmap_tab = HeatmapTab(self._notebook, self._theme, on_file_select=self._on_heatmap_select)
        self._notebook.add(self._heatmap_tab, text="Heatmap")

        self._tab_details = self._make_details_tab()
        self._notebook.add(self._tab_details, text="File Details")

        self._tab_planner = self._make_planner_tab()
        self._notebook.add(self._tab_planner, text="Build Planner")

        self._tab_activity = self._make_activity_tab()
        self._notebook.add(self._tab_activity, text="Activity")

        bottom = ttk.Frame(self._main_pane, style="App.TFrame")
        bottom.columnconfigure(0, weight=1)
        bottom.rowconfigure(1, weight=1)
        self._main_pane.add(bottom, weight=1)
        ttk.Label(bottom, text="Activity Log", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        log_frame = ttk.Frame(bottom, style="Card.TFrame", padding=8)
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self._log = tk.Text(log_frame, height=4, state="disabled", wrap="word", bd=0, highlightthickness=0, font=("Consolas", 9))
        scroll = ttk.Scrollbar(log_frame, command=self._log.yview)
        self._log.configure(yscrollcommand=scroll.set)
        self._log.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self._log_frame = log_frame

        self._status_bar = ttk.Label(self, textvariable=self._status_var, anchor="w", style="Status.TLabel", padding=(14, 5))
        self._status_bar.pack(fill="x", side="bottom")

    def _theme_label(self):
        return "Moon Dark" if self._theme["name"] == "light" else "Sun Light"
    def _make_dashboard_tab(self) -> tk.Frame:
        frame = ttk.Frame(self._notebook, style="App.TFrame", padding=14)
        frame.columnconfigure((0, 1, 2, 3), weight=1, uniform="dash")
        self._dash_vars: dict[str, tk.StringVar] = {}
        fields = [
            ("Total Size", "total_size", "0 B", "Disk footprint"),
            ("Total Files", "total_files", "0", "Files scanned"),
            ("Largest File", "largest_file", "-", "Biggest single file"),
            ("Largest Folder", "largest_folder", "-", "Heaviest folder"),
            ("Last Build Size", "build_size", "-", "Latest output"),
            ("Space Saved", "space_saved", "-", "Excluded size"),
            ("Last Scan Time", "scan_time", "-", "Most recent run"),
            ("Scan Duration", "scan_duration", "-", "Elapsed time"),
        ]
        for i, (label, key, default, helper) in enumerate(fields):
            var = tk.StringVar(value=default)
            self._dash_vars[key] = var
            card = ttk.Frame(frame, style="Card.TFrame", padding=16)
            card.grid(row=i // 4, column=i % 4, sticky="nsew", padx=6, pady=6)
            card.columnconfigure(0, weight=1)
            ttk.Label(card, text=label, style="Caption.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(card, textvariable=var, style="Metric.TLabel", wraplength=210).grid(row=1, column=0, sticky="w", pady=(8, 2))
            ttk.Label(card, text=helper, style="CardSubtle.TLabel").grid(row=2, column=0, sticky="w")
        self._dashboard_empty = ttk.Frame(frame, style="Card.TFrame", padding=22)
        self._dashboard_empty.grid(row=2, column=0, columnspan=4, sticky="ew", padx=6, pady=(14, 6))
        self._dashboard_empty.columnconfigure(0, weight=1)
        ttk.Label(self._dashboard_empty, text="Select a game folder and run a scan to populate the dashboard.", style="Empty.TLabel").grid(row=0, column=0, sticky="w")
        return frame
    def _make_tree_tab(self, columns: tuple, widths: tuple) -> tuple[tk.Frame, ttk.Treeview]:
        frame = ttk.Frame(self._notebook, style="App.TFrame", padding=12)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        tree = self._make_tree(frame, columns, widths)
        tree.master.grid(row=0, column=0, sticky="nsew")
        return frame, tree
    def _make_details_tab(self) -> tk.Frame:
        t = self._theme
        frame = tk.Frame(self._notebook, bg=t["bg"])
        self._detail_vars: dict[str, tk.StringVar] = {}
        fields = ["Name", "Path", "Size", "Extension", "Category", "Last Modified", "Estimated Purpose", "Optimization Status"]
        for i, field in enumerate(fields):
            var = tk.StringVar(value="â€”")
            self._detail_vars[field] = var
            tk.Label(frame, text=field + ":", anchor="w", width=22,
                     bg=t["bg"], fg=t["fg"], font=("Segoe UI", 10, "bold")).grid(
                row=i, column=0, sticky="w", padx=20, pady=5)
            tk.Label(frame, textvariable=var, anchor="w", wraplength=580,
                     bg=t["bg"], fg=t["fg"], font=("Segoe UI", 10)).grid(
                row=i, column=1, sticky="w", padx=8)
        return frame

    def _make_planner_tab(self) -> tk.Frame:
        t = self._theme
        frame = tk.Frame(self._notebook, bg=t["bg"], padx=8, pady=8)

        exc_frame = tk.LabelFrame(frame, text="Exclude by Category", bg=t["bg"],
                                  fg=t["fg"], padx=6, pady=4)
        exc_frame.pack(fill="x", pady=(0, 6))
        self._preset_vars: dict[str, tk.BooleanVar] = {}
        for label, ext in PRESET_EXTENSIONS.items():
            var = tk.BooleanVar(value=True)
            self._preset_vars[ext] = var
            tk.Checkbutton(exc_frame, text=label, variable=var, command=self._invalidate_plan,
                           bg=t["bg"], fg=t["fg"], selectcolor=t["entry_bg"],
                           activebackground=t["bg"]).pack(side="left", padx=8)
        custom_row = tk.Frame(exc_frame, bg=t["bg"])
        custom_row.pack(side="left", padx=8)
        tk.Label(custom_row, text="Custom extensions:", bg=t["bg"], fg=t["fg"]).pack(side="left")
        self._custom_ext_var = tk.StringVar()
        self._custom_ext_var.trace_add("write", lambda *_: self._invalidate_plan())
        tk.Entry(custom_row, textvariable=self._custom_ext_var, width=20,
                 bg=t["entry_bg"], fg=t["entry_fg"],
                 insertbackground=t["entry_fg"]).pack(side="left", padx=4)

        skip_frame = tk.LabelFrame(frame, text="Skip Specific Files by Name", bg=t["bg"],
                                   fg=t["fg"], padx=6, pady=4)
        skip_frame.pack(fill="x", pady=(0, 6))
        skip_input_row = tk.Frame(skip_frame, bg=t["bg"])
        skip_input_row.pack(fill="x")
        tk.Label(skip_input_row, text="Filename:", bg=t["bg"], fg=t["fg"]).pack(side="left")
        self._skip_name_var = tk.StringVar()
        self._skip_name_entry = tk.Entry(skip_input_row, textvariable=self._skip_name_var, width=36,
                                         bg=t["entry_bg"], fg=t["entry_fg"],
                                         insertbackground=t["entry_fg"])
        self._skip_name_entry.pack(side="left", padx=4)
        self._skip_name_entry.bind("<Return>", lambda _: self._add_skip_name())
        tk.Button(skip_input_row, text="Add", command=self._add_skip_name,
                  bg=t["bg"], fg=t["fg"]).pack(side="left", padx=2)
        tk.Button(skip_input_row, text="Remove Selected", command=self._remove_skip_name,
                  bg=t["bg"], fg=t["fg"]).pack(side="left", padx=2)
        self._skip_list_box = tk.Listbox(skip_frame, height=4, selectmode="single",
                                          bg=t["entry_bg"], fg=t["entry_fg"], width=50)
        self._skip_list_box.pack(fill="x", pady=(4, 0))
        self._skip_list_box.bind("<<ListboxSelect>>", lambda _: self._invalidate_plan())

        est_frame = tk.LabelFrame(frame, text="Size Estimate", bg=t["bg"], fg=t["fg"], padx=6, pady=4)
        est_frame.pack(fill="x", pady=(0, 6))
        self._lbl_orig_size = tk.Label(est_frame, text="Original Size: â€”", bg=t["bg"], fg=t["fg"])
        self._lbl_orig_size.pack(side="left", padx=12)
        self._lbl_build_size = tk.Label(est_frame, text="Estimated Build Size: â€”", bg=t["bg"], fg=t["fg"])
        self._lbl_build_size.pack(side="left", padx=12)
        self._lbl_saved = tk.Label(est_frame, text="Space Saved: â€”", bg=t["bg"], fg=t["fg"])
        self._lbl_saved.pack(side="left", padx=12)

        count_row = tk.Frame(frame, bg=t["bg"])
        count_row.pack(fill="x", pady=(0, 4))
        self._lbl_will_copy = tk.Label(count_row, text="Files to copy: â€”", bg=t["bg"], fg=t["fg"])
        self._lbl_will_copy.pack(side="left", padx=4)
        self._lbl_will_skip = tk.Label(count_row, text="Files to skip: â€”", bg=t["bg"], fg=t["fg"])
        self._lbl_will_skip.pack(side="left", padx=16)
        self._preview_btn = tk.Button(count_row, text="Calculate Preview", command=self._calculate_plan,
                                      bg=t["bg"], fg=t["fg"])
        self._preview_btn.pack(side="left", padx=8)
        self._create_build_btn = tk.Button(count_row, text="Create Build", command=self._confirm_build,
                                           state="disabled", bg=t["bg"], fg=t["fg"])
        self._create_build_btn.pack(side="left", padx=4)
        self._open_build_btn = tk.Button(count_row, text="Open Build Folder", command=self._open_build_folder,
                                         state="disabled", bg=t["bg"], fg=t["fg"])
        self._open_build_btn.pack(side="left", padx=4)

        preview_frame = tk.LabelFrame(frame, text="Preview â€” files to be skipped",
                                      bg=t["bg"], fg=t["fg"], padx=4, pady=4)
        preview_frame.pack(fill="both", expand=True)
        self._preview_tree = self._make_tree(preview_frame, ("File", "Extension", "Size"), (440, 100, 100))
        self._preview_tree.master.pack(fill="both", expand=True)

        self._build_progress = ttk.Progressbar(frame, mode="determinate")
        self._build_progress.pack(fill="x", pady=(4, 0))
        self._lbl_build_current = tk.Label(frame, text="", anchor="w", bg=t["bg"], fg=t["fg"])
        self._lbl_build_current.pack(fill="x")

        return frame

    def _make_activity_tab(self) -> tk.Frame:
        t = self._theme
        frame = tk.Frame(self._notebook, bg=t["bg"])
        self._activity_text = tk.Text(frame, state="disabled", wrap="word",
                                      bg=t["text_bg"], fg=t["text_fg"],
                                      insertbackground=t["text_fg"], font=("Consolas", 9))
        sb = ttk.Scrollbar(frame, command=self._activity_text.yview)
        self._activity_text.configure(yscrollcommand=sb.set)
        self._activity_text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._perf_frame = tk.LabelFrame(frame, text="Performance", bg=t["bg"], fg=t["fg"], padx=8, pady=4)
        self._perf_frame.pack(side="right", fill="y", padx=4, pady=4)
        self._perf_vars: dict[str, tk.StringVar] = {}
        for key in ("Scan Speed", "Current Folder", "Files Processed", "Elapsed", "Est. Remaining"):
            var = tk.StringVar(value="â€”")
            self._perf_vars[key] = var
            tk.Label(self._perf_frame, text=key + ":", anchor="w", width=16,
                     bg=t["bg"], fg=t["fg"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
            tk.Label(self._perf_frame, textvariable=var, anchor="w",
                     bg=t["bg"], fg=t["fg"], font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 6))

        return frame

    def _make_tree(self, parent, columns: tuple, widths: tuple) -> ttk.Treeview:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=8)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=columns, show="headings", style="Modern.Treeview", selectmode="browse")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        for col, w in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, minwidth=60, anchor="w", stretch=True)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        hsb.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        tree.master = frame
        return tree
    def _apply_theme(self):
        t = self._theme
        self.configure(bg=t["bg"])
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background=t["bg"], foreground=t["fg"], fieldbackground=t["entry_bg"], bordercolor=t["border"], lightcolor=t["border"], darkcolor=t["border"], troughcolor=t["progress_bg"])
        style.configure("App.TFrame", background=t["bg"])
        style.configure("Card.TFrame", background=t["surface"], borderwidth=1, relief="solid")
        style.configure("Title.TLabel", background=t["bg"], foreground=t["fg"], font=("Segoe UI", 22, "bold"))
        style.configure("Section.TLabel", background=t["bg"], foreground=t["fg"], font=("Segoe UI", 11, "bold"))
        style.configure("Subtle.TLabel", background=t["bg"], foreground=t["muted_fg"], font=("Segoe UI", 9))
        style.configure("CardSubtle.TLabel", background=t["surface"], foreground=t["muted_fg"], font=("Segoe UI", 9))
        style.configure("Caption.TLabel", background=t["surface"], foreground=t["muted_fg"], font=("Segoe UI", 9, "bold"))
        style.configure("Metric.TLabel", background=t["surface"], foreground=t["fg"], font=("Segoe UI", 18, "bold"))
        style.configure("Value.TLabel", background=t["bg"], foreground=t["fg"], font=("Segoe UI", 10))
        style.configure("Empty.TLabel", background=t["surface"], foreground=t["muted_fg"], font=("Segoe UI", 11))
        style.configure("Status.TLabel", background=t["status_bg"], foreground=t["status_fg"], font=("Segoe UI", 9))
        style.configure("TEntry", fieldbackground=t["entry_bg"], foreground=t["entry_fg"], insertcolor=t["entry_fg"], padding=7, borderwidth=1)
        style.configure("Tool.TButton", background=t["surface_alt"], foreground=t["fg"], padding=(12, 7), borderwidth=1)
        style.map("Tool.TButton", background=[("active", t["border"]), ("disabled", t["surface_alt"])], foreground=[("disabled", t["muted_fg"])])
        style.configure("Primary.TButton", background=t["accent"], foreground=t["accent_fg"], padding=(14, 8), borderwidth=1, font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton", background=[("active", t["accent_hover"]), ("disabled", t["surface_alt"])], foreground=[("disabled", t["muted_fg"])])
        style.configure("Modern.TNotebook", background=t["bg"], borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure("Modern.TNotebook.Tab", background=t["surface_alt"], foreground=t["muted_fg"], padding=(14, 8), borderwidth=0)
        style.map("Modern.TNotebook.Tab", background=[("selected", t["surface"])], foreground=[("selected", t["fg"])])
        style.configure("Modern.Treeview", background=t["tree_bg"], foreground=t["tree_fg"], fieldbackground=t["tree_bg"], borderwidth=0, rowheight=28)
        style.map("Modern.Treeview", background=[("selected", t["tree_sel_bg"])], foreground=[("selected", t["tree_sel_fg"])])
        style.configure("Treeview.Heading", background=t["surface_alt"], foreground=t["fg"], font=("Segoe UI", 9, "bold"), padding=(8, 7), relief="flat")
        style.configure("TScrollbar", background=t["surface_alt"], troughcolor=t["bg"], bordercolor=t["border"], arrowcolor=t["fg"])
        style.configure("Modern.Horizontal.TProgressbar", troughcolor=t["progress_bg"], background=t["accent"], bordercolor=t["progress_bg"], lightcolor=t["accent"], darkcolor=t["accent"])
        style.configure("Modern.TLabelframe", background=t["bg"], foreground=t["fg"], bordercolor=t["border"])
        style.configure("Modern.TLabelframe.Label", background=t["bg"], foreground=t["fg"], font=("Segoe UI", 10, "bold"))
        style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"], focuscolor=t["bg"])
        style.map("TCheckbutton", background=[("active", t["bg"])], foreground=[("disabled", t["muted_fg"])])
        style.configure("TRadiobutton", background=t["bg"], foreground=t["fg"], focuscolor=t["bg"])
        style.map("TRadiobutton", background=[("active", t["bg"])])
        self._refresh_widget_colors()
    def _toggle_theme(self):
        self._theme = other_theme(self._theme)
        save_theme(self._theme)
        self._apply_theme()
        self._theme_btn.configure(text=self._theme_label())
        if hasattr(self, "_charts_tab"):
            self._charts_tab.update_theme(self._theme)
        if hasattr(self, "_heatmap_tab"):
            self._heatmap_tab.update_theme(self._theme)

    def _refresh_widget_colors(self):
        t = self._theme
        def recolor(widget):
            cls = widget.winfo_class()
            try:
                if cls in ("Frame", "LabelFrame"):
                    widget.configure(bg=t["bg"])
                elif cls == "Label":
                    widget.configure(bg=t["bg"], fg=t["fg"])
                elif cls in ("Checkbutton", "Radiobutton"):
                    widget.configure(bg=t["bg"], fg=t["fg"], selectcolor=t["entry_bg"], activebackground=t["bg"], activeforeground=t["fg"])
                elif cls == "Button":
                    widget.configure(bg=t["surface_alt"], fg=t["fg"], activebackground=t["border"], activeforeground=t["fg"], relief="flat", padx=10, pady=5)
                elif cls == "Entry":
                    widget.configure(bg=t["entry_bg"], fg=t["entry_fg"], insertbackground=t["entry_fg"], relief="flat")
                elif cls == "Text":
                    widget.configure(bg=t["text_bg"], fg=t["text_fg"], insertbackground=t["text_fg"], selectbackground=t["tree_sel_bg"], selectforeground=t["tree_sel_fg"])
                elif cls == "Listbox":
                    widget.configure(bg=t["entry_bg"], fg=t["entry_fg"], selectbackground=t["tree_sel_bg"], selectforeground=t["tree_sel_fg"], highlightbackground=t["border"], highlightcolor=t["accent"], relief="flat")
                elif cls == "Canvas":
                    widget.configure(bg=t["canvas_bg"], highlightthickness=0)
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                recolor(child)
        recolor(self)
        for tree_name in ("_files_tree", "_folders_tree", "_ext_tree", "_preview_tree"):
            tree = getattr(self, tree_name, None)
            if tree is not None:
                self._stripe_tree(tree)
    def _browse(self):
        folder = filedialog.askdirectory(title="Select Game Folder", initialdir=self._folder_var.get().strip() or None)
        if folder:
            self._folder_var.set(folder)
            self._prefs["last_folder"] = folder
            save_preferences(self._prefs)
    def _log_write(self, msg: str):
        self._log.configure(state="normal")
        self._log.insert("end", msg + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _activity_write(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self._activity_lines.append(line)
        self._activity_text.configure(state="normal")
        self._activity_text.insert("end", line + "\n")
        self._activity_text.see("end")
        self._activity_text.configure(state="disabled")

    def _set_status(self, text: str):
        self._status_var.set(text)

    def _start_scan(self):
        folder = self._folder_var.get().strip()
        if not folder:
            messagebox.showwarning("No Folder", "Please select a game folder first.")
            return
        path = Path(folder)
        if not path.is_dir():
            messagebox.showerror("Invalid Folder", f"Not a directory:\n{path}")
            return
        self._prefs["last_folder"] = folder
        save_preferences(self._prefs)
        self._scan_btn.configure(state="disabled")
        self._report_btn.configure(state="disabled")
        self._progress.start(10)
        self._scan_start = time.time()
        self._set_status("Scanningâ€¦")
        self._log_write(f"Scanning: {path}")
        self._activity_write(f"Started scan: {path}")
        self._perf_vars["Current Folder"].set(str(path))
        self._perf_vars["Files Processed"].set("0")
        threading.Thread(target=self._run_scan, args=(path,), daemon=True).start()

    def _run_scan(self, path: Path):
        try:
            start = time.time()
            result = scan(path)
            elapsed = time.time() - start
            report_path = generate_report(result)
            self.after(0, self._scan_done, result, report_path, elapsed)
        except Exception as e:
            self.after(0, self._scan_error, str(e))

    def _scan_done(self, result: ScanResult, report_path: Path, elapsed: float):
        self._result = result
        self._report_path = report_path
        self._last_scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._last_scan_duration = elapsed
        self._progress.stop()
        self._scan_btn.configure(state="normal")
        self._report_btn.configure(state="normal")
        self._plan = None
        self._create_build_btn.configure(state="disabled")
        speed = result.total_files / elapsed if elapsed > 0 else 0
        self._perf_vars["Scan Speed"].set(f"{speed:.0f} files/sec")
        self._perf_vars["Files Processed"].set(f"{result.total_files:,}")
        self._perf_vars["Elapsed"].set(f"{elapsed:.1f}s")
        self._perf_vars["Est. Remaining"].set("Done")
        self._activity_write(f"Scan complete: {result.total_files:,} files in {elapsed:.1f}s")
        self._activity_write(f"Generating reportâ€¦")
        self._activity_write(f"Report saved: {report_path.name}")
        self._activity_write("Finished.")
        self._set_status(f"Finished â€” {result.total_files:,} files | {format_size(int(result.total_size))} | {elapsed:.1f}s")
        self._update_dashboard(result)
        self._populate_files(result)
        self._populate_folders(result)
        self._populate_extensions(result)
        self._update_charts(result)
        self._heatmap_tab.load(
            [(e.path, e.size) for e in result.all_files],
            [(p, s) for p, s in result.folder_sizes.items()],
        )
        self._log_write(f"Done. {result.total_files:,} files | {format_size(int(result.total_size))}")
        self._log_write(f"Report: {report_path}")

    def _scan_error(self, msg: str):
        self._progress.stop()
        self._scan_btn.configure(state="normal")
        self._set_status("Error during scan.")
        self._log_write(f"ERROR: {msg}")
        self._activity_write(f"ERROR: {msg}")
        messagebox.showerror("Scan Error", msg)

    def _update_dashboard(self, result: ScanResult):
        from scanner import largest_files, largest_folders
        lf = largest_files(result, 1)
        lfold = largest_folders(result, 1)
        self._dash_vars["total_size"].set(format_size(int(result.total_size)))
        self._dash_vars["total_files"].set(f"{result.total_files:,}")
        self._dash_vars["largest_file"].set(
            f"{lf[0].path.name}  ({format_size(lf[0].size)})" if lf else "â€”")
        self._dash_vars["largest_folder"].set(
            f"{lfold[0][0].name}  ({format_size(lfold[0][1])})" if lfold else "â€”")
        self._dash_vars["build_size"].set(format_size(self._last_build_size) if self._last_build_size else "â€”")
        self._dash_vars["space_saved"].set(format_size(self._last_space_saved) if self._last_space_saved else "â€”")
        self._dash_vars["scan_time"].set(self._last_scan_time)
        self._dash_vars["scan_duration"].set(f"{self._last_scan_duration:.2f}s")
        self._dashboard_empty.grid_remove()

    def _populate_files(self, result: ScanResult):
        self._files_tree.delete(*self._files_tree.get_children())
        for i, entry in enumerate(largest_files(result, TOP_FILES_COUNT), 1):
            rel = entry.path.relative_to(result.game_folder)
            self._files_tree.insert("", "end", iid=str(entry.path),
                                    values=(i, str(rel), format_size(entry.size)))

    def _populate_folders(self, result: ScanResult):
        self._folders_tree.delete(*self._folders_tree.get_children())
        for i, (folder, size) in enumerate(largest_folders(result, TOP_FOLDERS_COUNT), 1):
            try:
                rel = folder.relative_to(result.game_folder)
            except ValueError:
                rel = folder
            self._folders_tree.insert("", "end", values=(i, str(rel), format_size(size)))

    def _populate_extensions(self, result: ScanResult):
        self._ext_tree.delete(*self._ext_tree.get_children())
        sorted_exts = sorted(result.extension_sizes.items(), key=lambda x: x[1], reverse=True)
        for ext, size in sorted_exts:
            count = result.extension_counts[ext]
            self._ext_tree.insert("", "end", values=(ext, f"{count:,}", format_size(size)))

    def _stripe_tree(self, tree: ttk.Treeview):
        t = self._theme
        tree.tag_configure("odd", background=t["tree_bg"], foreground=t["tree_fg"])
        tree.tag_configure("even", background=t["tree_alt_bg"], foreground=t["tree_fg"])

    def _update_charts(self, result: ScanResult):
        ext_data = [(ext, float(sz)) for ext, sz in
                    sorted(result.extension_sizes.items(), key=lambda x: x[1], reverse=True)[:10]]
        folder_data = [(p.name, float(sz)) for p, sz in largest_folders(result, 10)]
        file_data = [(e.path.name, float(e.size)) for e in largest_files(result, 10)]
        self._charts_tab.update(ext_data, folder_data, file_data)

    def _on_tree_select(self, tree: ttk.Treeview, kind: str):
        sel = tree.selection()
        if not sel or not self._result:
            return
        vals = tree.item(sel[0], "values")
        if kind == "file" and len(vals) >= 3:
            path_str = str(self._result.game_folder / vals[1])
            path = Path(path_str)
            size_entry = next((e for e in self._result.all_files if e.path == path), None)
            size = size_entry.size if size_entry else 0
            self._show_file_details(path, size)

    def _on_heatmap_select(self, path: Path, size: int):
        self._show_file_details(path, size)
        self._notebook.select(self._tab_details)

    def _show_file_details(self, path: Path, size: int):
        ext = path.suffix.lower()
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            mtime = "â€”"
        category = EXT_CATEGORIES.get(ext, "Unknown")
        purpose = EXT_PURPOSES.get(ext, "Unknown")
        if size > 500 * 1024 * 1024:
            opt_status = "Large â€” consider excluding from build"
        elif ext in (".log", ".txt"):
            opt_status = "Safe to exclude"
        elif ext in (".bik",):
            opt_status = "Video â€” large, exclude to save space"
        else:
            opt_status = "Required"
        self._detail_vars["Name"].set(path.name)
        self._detail_vars["Path"].set(str(path))
        self._detail_vars["Size"].set(format_size(size))
        self._detail_vars["Extension"].set(ext or "(none)")
        self._detail_vars["Category"].set(category)
        self._detail_vars["Last Modified"].set(mtime)
        self._detail_vars["Estimated Purpose"].set(purpose)
        self._detail_vars["Optimization Status"].set(opt_status)

    def _open_report(self):
        if self._report_path and self._report_path.exists():
            if os.name == "nt":
                os.startfile(self._report_path)
            else:
                os.system(f'xdg-open "{self._report_path}" &')
        else:
            messagebox.showinfo("No Report", "No report available yet.")

    def _open_workspace(self):
        WORKSPACE_DIR.mkdir(exist_ok=True)
        if os.name == "nt":
            os.startfile(WORKSPACE_DIR)
        else:
            os.system(f'xdg-open "{WORKSPACE_DIR}" &')

    def _get_excluded_extensions(self) -> set[str]:
        excluded = {ext for ext, var in self._preset_vars.items() if var.get()}
        for raw in self._custom_ext_var.get().split(","):
            ext = raw.strip().lower()
            if ext:
                excluded.add(ext if ext.startswith(".") else f".{ext}")
        return excluded

    def _add_skip_name(self):
        name = self._skip_name_var.get().strip()
        if not name:
            return
        if name.lower() not in [self._skip_list_box.get(i).lower()
                                 for i in range(self._skip_list_box.size())]:
            self._skip_list_box.insert("end", name)
            self._invalidate_plan()
        self._skip_name_var.set("")

    def _remove_skip_name(self):
        sel = self._skip_list_box.curselection()
        if sel:
            self._skip_list_box.delete(sel[0])
            self._invalidate_plan()

    def _get_skipped_names(self) -> set[str]:
        return {self._skip_list_box.get(i) for i in range(self._skip_list_box.size())}

    def _invalidate_plan(self):
        self._plan = None
        self._create_build_btn.configure(state="disabled")

    def _calculate_plan(self):
        if not self._result:
            messagebox.showwarning("No Scan", "Please scan a game folder first.")
            return
        excluded = self._get_excluded_extensions()
        skipped_names = self._get_skipped_names()
        plan = make_plan(self._result, excluded, skipped_names)
        self._plan = plan
        self._lbl_orig_size.configure(text=f"Original Size: {format_size(plan.original_size)}")
        self._lbl_build_size.configure(text=f"Estimated Build Size: {format_size(plan.copy_size)}")
        self._lbl_saved.configure(text=f"Space Saved: {format_size(plan.space_saved)}")
        self._lbl_will_copy.configure(text=f"Files to copy: {len(plan.files_to_copy):,}")
        self._lbl_will_skip.configure(text=f"Files to skip: {len(plan.files_to_skip):,}")
        self._preview_tree.delete(*self._preview_tree.get_children())
        for f in sorted(plan.files_to_skip):
            size = f.stat().st_size
            rel = f.relative_to(plan.game_folder)
            self._preview_tree.insert("", "end", values=(str(rel), f.suffix.lower(), format_size(size)))
        self._create_build_btn.configure(state="normal" if plan.files_to_copy else "disabled")

    def _confirm_build(self):
        if not self._plan:
            return
        plan = self._plan
        msg = (
            f"Create a build of '{plan.game_folder.name}'?\n\n"
            f"  Files to copy : {len(plan.files_to_copy):,}\n"
            f"  Files to skip : {len(plan.files_to_skip):,}\n"
            f"  Build size    : {format_size(plan.copy_size)}\n"
            f"  Space saved   : {format_size(plan.space_saved)}\n\n"
            "Destination: ~/Downloads/GameShrink_Build_<timestamp>\n\n"
            "Original files will never be modified."
        )
        if not messagebox.askyesno("Confirm Build", msg):
            return
        dest = build_dest_folder()
        self._build_dest = dest
        self._create_build_btn.configure(state="disabled")
        self._build_progress.configure(value=0, maximum=len(plan.files_to_copy))
        self._set_status("Buildingâ€¦")
        self._activity_write(f"Starting build â†’ {dest.name}")
        self._log_write(f"Starting build â†’ {dest}")
        threading.Thread(target=self._run_build, args=(plan, dest), daemon=True).start()

    def _run_build(self, plan: BuildPlan, dest: Path):
        try:
            def progress(i: int, total: int, name: str):
                pct = int(i / total * 100) if total else 0
                self.after(0, self._build_progress_update, i, total, name, pct)
            execute_build(plan, dest, progress_cb=progress)
            self.after(0, self._build_done, dest, plan)
        except Exception as e:
            self.after(0, self._build_error, str(e))

    def _build_progress_update(self, i: int, total: int, name: str, pct: int):
        self._build_progress.configure(value=i)
        self._lbl_build_current.configure(text=f"Copying ({i}/{total}): {name}")
        self._set_status(f"Buildingâ€¦ {pct}%")

    def _build_done(self, dest: Path, plan: BuildPlan):
        self._last_build_size = plan.copy_size
        self._last_space_saved = plan.space_saved
        self._lbl_build_current.configure(text=f"Build complete: {dest}")
        self._open_build_btn.configure(state="normal")
        self._create_build_btn.configure(state="normal")
        self._set_status(f"Build complete â€” {format_size(plan.copy_size)} | Saved {format_size(plan.space_saved)}")
        self._activity_write(f"Build complete: {dest.name}")
        self._log_write(f"Build complete â†’ {dest}")
        if self._result:
            self._update_dashboard(self._result)
        messagebox.showinfo("Build Complete", f"Build saved to:\n{dest}")

    def _build_error(self, msg: str):
        self._lbl_build_current.configure(text="Build failed.")
        self._create_build_btn.configure(state="normal")
        self._set_status("Build error.")
        self._activity_write(f"Build ERROR: {msg}")
        self._log_write(f"Build ERROR: {msg}")
        messagebox.showerror("Build Error", msg)

    def _open_build_folder(self):
        if self._build_dest and self._build_dest.exists():
            if os.name == "nt":
                os.startfile(self._build_dest)
            else:
                os.system(f'xdg-open "{self._build_dest}" &')


    def _on_close(self):
        self._save_window_state()
        self.destroy()

def launch():
    app = App()
    app.mainloop()










