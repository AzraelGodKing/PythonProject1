"""
Basic Tkinter UI for the tic-tac-toe game logic in tic-tac-toe.py.
The UI is a thin layer over the existing logic: board state, AI moves, and scoreboard persistence.
"""

import importlib.util
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import pathlib
import tkinter as tk
import atexit
import math
from typing import Optional
from tkinter import messagebox, ttk
import options


MODULE_PATH = pathlib.Path(__file__).with_name("tic-tac-toe.py")
LOG_DIR = os.path.join("data", "logs")
SETTINGS_FILE = "gui_settings.json"
SETTINGS_BACKUP = os.path.join(LOG_DIR, "gui_settings.json.bak")
spec = importlib.util.spec_from_file_location("tictactoe_module_gui", MODULE_PATH)
module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
assert spec.loader is not None
spec.loader.exec_module(module)  # type: ignore[arg-type]

PALETTE_DEFAULT = {
    "BG": "#0f172a",
    "PANEL": "#1e293b",
    "ACCENT": "#38bdf8",
    "TEXT": "#e2e8f0",
    "MUTED": "#94a3b8",
    "BTN": "#0ea5e9",
    "O": "#f97316",
    "CELL": "#233244",
}

PALETTE_HIGH_CONTRAST = {
    "BG": "#000000",
    "PANEL": "#111111",
    "ACCENT": "#ffeb3b",
    "TEXT": "#ffffff",
    "MUTED": "#cccccc",
    "BTN": "#ff9800",
    "O": "#ff5722",
    "CELL": "#1f1f1f",
}

PALETTE_LIGHT = {
    "BG": "#f6f8fb",
    "PANEL": "#e1e7f2",
    "ACCENT": "#0077ff",
    "TEXT": "#111827",
    "MUTED": "#4b5563",
    "BTN": "#2563eb",
    "O": "#f97316",
    "CELL": "#ffffff",
}

PALETTE_PROTAN = {
    "BG": "#0f1627",
    "PANEL": "#192339",
    "ACCENT": "#f2c14e",
    "TEXT": "#e6edf5",
    "MUTED": "#c0cad8",
    "BTN": "#f08a5d",
    "O": "#00b7a8",
    "CELL": "#1f2c40",
}

PALETTE_DEUTAN = {
    "BG": "#0e1524",
    "PANEL": "#1b273a",
    "ACCENT": "#ffc857",
    "TEXT": "#edf2f7",
    "MUTED": "#cbd5e1",
    "BTN": "#ef476f",
    "O": "#06d6a0",
    "CELL": "#1f2c42",
}

PALETTE_TRITAN = {
    "BG": "#0f172a",
    "PANEL": "#1c2540",
    "ACCENT": "#f9c80e",
    "TEXT": "#e5ecf5",
    "MUTED": "#cbd5e1",
    "BTN": "#a4508b",
    "O": "#2dd4bf",
    "CELL": "#22314f",
}

PALETTE_MONO = {
    "BG": "#0f1115",
    "PANEL": "#1b1f26",
    "ACCENT": "#d1d5db",
    "TEXT": "#f3f4f6",
    "MUTED": "#9ca3af",
    "BTN": "#e5e7eb",
    "O": "#d1d5db",
    "CELL": "#222630",
}

FONTS_DEFAULT = {
    "board": ("Segoe UI", 18, "bold"),
    "text": ("Segoe UI", 11, "normal"),
    "title": ("Segoe UI", 13, "bold"),
}

FONTS_LARGE = {
    "board": ("Segoe UI", 22, "bold"),
    "text": ("Segoe UI", 13, "normal"),
    "title": ("Segoe UI", 15, "bold"),
}


class GameSession:
    def __init__(self) -> None:
        self.scoreboard = module.load_scoreboard()
        self.difficulty_key = "Easy"
        self.personality = "standard"
        self.ai_move_fn = module.ai_move_easy
        self.board = [" "] * 9
        self.game_over = False
        self.history = []
        self.moves = []
        loaded_history = module.load_session_history_from_file()
        if loaded_history:
            self.history = [(d, r, ts) for d, r, ts, _ in loaded_history]
        self.last_history_path: str = module.HISTORY_FILE

    def set_difficulty(self, level: str, personality: str = "standard") -> None:
        self.difficulty_key = level
        self.personality = personality
        if level == "Easy":
            self.ai_move_fn = module.ai_move_easy
        elif level == "Normal":
            self.ai_move_fn = module.NORMAL_PERSONALITIES.get(personality, module.ai_move_normal)
        else:
            self.ai_move_fn = module.ai_move_hard

    def reset_board(self) -> None:
        self.board = [" "] * 9
        self.game_over = False
        self.moves = []

    def label(self) -> str:
        return module.difficulty_display_label(self.difficulty_key, self.personality)

    def record_result(self, winner: str) -> None:
        if self.difficulty_key not in self.scoreboard:
            self.scoreboard[self.difficulty_key] = module.DEFAULT_SCORE.copy()
        self.scoreboard[self.difficulty_key][winner] += 1
        module.save_scoreboard(self.scoreboard)
        ts = module.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.history.append((self.label(), winner, ts))


class TicTacToeGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Tic-Tac-Toe")
        self.root.geometry("1100x800")
        self.root.minsize(900, 760)
        self.settings_path = os.environ.get("GUI_SETTINGS_PATH", SETTINGS_FILE)
        self.logger = self._init_logger()
        settings = self._load_settings()
        self.large_fonts = tk.BooleanVar(value=settings["large_fonts"])
        self.theme_var = tk.StringVar(value=settings["theme"])
        self.animations_enabled = tk.BooleanVar(value=settings["animations"])
        self.sound_enabled = tk.BooleanVar(value=settings["sound"])
        self.show_coords = tk.BooleanVar(value=settings["show_coords"])
        self.palette = self._resolve_palette(self.theme_var.get())
        self.fonts = dict(FONTS_LARGE if self.large_fonts.get() else FONTS_DEFAULT)
        self._configure_style()
        self.session = GameSession()
        self.match_length = 1
        self.match_length_var = tk.StringVar(value="1")
        self.match_target = 1
        self.match_wins = {"X": 0, "O": 0, "Draw": 0}
        self.match_over = False
        self.match_rounds = 0
        self.options_popup: Optional[tk.Toplevel] = None
        self.history_popup: Optional[tk.Toplevel] = None
        self.achievements_popup: Optional[tk.Toplevel] = None
        self.achievements_filter_earned = tk.BooleanVar(value=False)
        self.compact_sidebar = tk.BooleanVar(value=settings.get("compact_sidebar", False))
        self.match_winner = ""
        self.tooltips = []

        self.status_var = tk.StringVar(value="Choose a difficulty and start a game.")
        self.score_var = tk.StringVar()
        self.history_var = tk.StringVar(value="Recent: none")
        self.log_path_var = tk.StringVar(value=f"History file: {self.session.last_history_path}")
        self.match_var = tk.StringVar(value=self._match_score_text())
        self.quick_stats_var = tk.StringVar(value="")
        self.confirm_moves = tk.BooleanVar(value=settings["confirm_moves"])
        self.auto_start = tk.BooleanVar(value=settings["auto_start"])
        self.rotate_logs = tk.BooleanVar(value=settings["rotate_logs"])
        self.pending_ai_id: Optional[str] = None
        self.last_move_idx: Optional[int] = None
        self.hint_highlight: Optional[int] = None

        self._build_layout()
        self._refresh_scoreboard()
        self._bind_keys()
        self._apply_theme()
        atexit.register(self._shutdown_logger)
        self.root.report_callback_exception = self._handle_exception
        self.player_turn = True
        self._build_menu()
        self._apply_compact_layout()

    def _color(self, key: str) -> str:
        return self.palette[key]

    def _font(self, key: str):
        return self.fonts[key]

    def _resolve_palette(self, theme: str) -> dict:
        if theme == "high_contrast":
            return dict(PALETTE_HIGH_CONTRAST)
        if theme == "colorblind_protan":
            return dict(PALETTE_PROTAN)
        if theme == "colorblind_deutan":
            return dict(PALETTE_DEUTAN)
        if theme == "colorblind_tritan":
            return dict(PALETTE_TRITAN)
        if theme == "monochrome":
            return dict(PALETTE_MONO)
        if theme == "light":
            return dict(PALETTE_LIGHT)
        return dict(PALETTE_DEFAULT)

    def _match_score_text(self) -> str:
        base = (
            f"Bo{self.match_length} (target {self.match_target}) "
            f"| Round {self.match_rounds + 1 if not self.match_over else self.match_rounds}/{self.match_length} "
            f"| X={self.match_wins['X']}  O={self.match_wins['O']}  Draws={self.match_wins['Draw']}"
        )
        if self.match_winner:
            base += f"  | Winner: {self.match_winner}"
        return base

    def _parse_match_length(self) -> int:
        text = self.match_length_var.get().strip()
        if text.isdigit():
            val = int(text)
            if val >= 1 and val % 2 == 1:
                return val
        return 1

    def _new_match(self) -> None:
        self.match_length = self._parse_match_length()
        if self.match_length % 2 == 0:
            self.match_length += 1
        self.match_length_var.set(str(self.match_length))
        self.match_target = (self.match_length // 2) + 1
        self.match_wins = {"X": 0, "O": 0, "Draw": 0}
        self.match_over = False
        self.match_winner = ""
        self.match_rounds = 0
        self.match_var.set(self._match_score_text())
        self.start_new_game()

    def _set_match_preset(self, val: int) -> None:
        self.match_length_var.set(str(val))
        self._new_match()

    def _init_logger(self) -> logging.Logger:
        os.makedirs(LOG_DIR, exist_ok=True)
        logger = logging.getLogger("tictactoe_gui")
        logger.setLevel(logging.INFO)
        log_path = os.path.join(LOG_DIR, "app.log")
        handler = RotatingFileHandler(log_path, maxBytes=200_000, backupCount=3, encoding="utf-8", delay=True)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(fmt)
        if not logger.handlers:
            logger.addHandler(handler)
        logger.propagate = False
        return logger

    def _shutdown_logger(self) -> None:
        logger = getattr(self, "logger", None)
        if not logger:
            return
        for h in list(logger.handlers):
            try:
                h.flush()
                h.close()
            except Exception:
                pass

    def _build_layout(self) -> None:
        # Scrollable container so all controls remain reachable on smaller screens.
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        outer = ttk.Frame(self.root, style="App.TFrame")
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        canvas = tk.Canvas(outer, highlightthickness=0, bg=self._color("BG"))
        vbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        scroll_frame = ttk.Frame(canvas, padding=10, style="App.TFrame")
        window_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def _on_frame_configure(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        scroll_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        self._canvas = canvas
        container = scroll_frame
        container.columnconfigure(0, weight=3)
        container.columnconfigure(1, weight=2)

        left = ttk.Frame(container, style="App.TFrame")
        left.grid(row=0, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        right = ttk.Frame(container, style="App.TFrame")
        right.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        right.columnconfigure(0, weight=1)

        self._build_controls(left)
        self._build_board(left)
        self._build_info(right)

    def _bind_keys(self) -> None:
        for n in range(1, 10):
            self.root.bind(str(n), lambda e, idx=n - 1: self._handle_player_move(idx))
        self.root.bind("<Control-n>", lambda _e: self.start_new_game())
        self.root.bind("<Control-N>", lambda _e: self.start_new_game())
        self.root.bind("n", lambda _e: self.start_new_game())
        self.root.bind("N", lambda _e: self.start_new_game())

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        game_menu = tk.Menu(menubar, tearoff=0)
        game_menu.add_command(label="New Game", command=self.start_new_game, accelerator="Ctrl+N")
        game_menu.add_command(label="New Match", command=self._new_match)
        game_menu.add_separator()
        game_menu.add_command(label="Save History", command=self._save_history_now)
        game_menu.add_separator()
        game_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="Game", menu=game_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Achievements", command=self._show_achievements_popup)
        view_menu.add_command(label="History", command=self._view_history_popup)
        view_menu.add_command(label="Options", command=self._show_options_popup)
        menubar.add_cascade(label="View", menu=view_menu)

        self.root.config(menu=menubar)

    def _load_settings(self) -> dict:
        defaults = {
            "confirm_moves": True,
            "auto_start": False,
            "rotate_logs": True,
            "theme": "default",
            "large_fonts": False,
            "animations": True,
            "sound": True,
            "show_coords": False,
            "compact_sidebar": False,
        }
        data = None
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            # attempt backup restore
            try:
                with open(SETTINGS_BACKUP, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.status_var = getattr(self, "status_var", tk.StringVar())
                self.status_var.set("Settings restored from backup.")
            except (OSError, json.JSONDecodeError):
                self.status_var = getattr(self, "status_var", tk.StringVar())
                self.status_var.set("Settings file unreadable; using defaults.")
                return defaults

        if not isinstance(data, dict):
            return defaults
        # backward compatibility: high_contrast flag becomes theme
        theme_val = data.get("theme")
        allowed_themes = {
            "default",
            "high_contrast",
            "colorblind_protan",
            "colorblind_deutan",
            "colorblind_tritan",
            "monochrome",
            "light",
        }
        if theme_val not in allowed_themes:
            if bool(data.get("high_contrast", False)):
                theme_val = "high_contrast"
            else:
                theme_val = defaults["theme"]
        return {
            "confirm_moves": bool(data.get("confirm_moves", defaults["confirm_moves"])),
            "auto_start": bool(data.get("auto_start", defaults["auto_start"])),
            "rotate_logs": bool(data.get("rotate_logs", defaults["rotate_logs"])),
            "theme": theme_val,
            "large_fonts": bool(data.get("large_fonts", defaults["large_fonts"])),
            "animations": bool(data.get("animations", defaults["animations"])),
            "sound": bool(data.get("sound", defaults["sound"])),
            "show_coords": bool(data.get("show_coords", defaults["show_coords"])),
            "compact_sidebar": bool(data.get("compact_sidebar", defaults["compact_sidebar"])),
        }

    def _save_settings(self) -> None:
        data = {
            "confirm_moves": self.confirm_moves.get(),
            "auto_start": self.auto_start.get(),
            "rotate_logs": self.rotate_logs.get(),
            "theme": self.theme_var.get(),
            "large_fonts": self.large_fonts.get(),
            "animations": self.animations_enabled.get(),
            "sound": self.sound_enabled.get(),
            "show_coords": self.show_coords.get(),
            "compact_sidebar": self.compact_sidebar.get(),
        }
        try:
            # write backup first
            try:
                os.makedirs(LOG_DIR, exist_ok=True)
                if os.path.exists(self.settings_path):
                    with open(self.settings_path, "r", encoding="utf-8") as f:
                        current = f.read()
                    with open(SETTINGS_BACKUP, "w", encoding="utf-8") as f:
                        f.write(current)
            except OSError:
                pass
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except OSError as exc:
            # Show a non-blocking hint if settings cannot be saved.
            self.status_var.set(f"Could not save settings ({exc}).")

    def _configure_style(self) -> None:
        self.root.configure(bg=self._color("BG"))
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=self._color("BG"))
        style.configure("Panel.TFrame", background=self._color("PANEL"), relief="flat")
        style.configure("App.TLabel", background=self._color("BG"), foreground=self._color("TEXT"), font=self._font("text"))
        style.configure("Title.TLabel", background=self._color("PANEL"), foreground=self._color("TEXT"), font=self._font("title"))
        style.configure("Status.TLabel", background=self._color("BG"), foreground=self._color("ACCENT"), font=self._font("title"))
        style.configure("Muted.TLabel", background=self._color("PANEL"), foreground=self._color("MUTED"), font=self._font("text"))
        style.configure(
            "App.TCheckbutton",
            background=self._color("PANEL"),
            foreground=self._color("TEXT"),
            font=self._font("text"),
            focuscolor=self._color("PANEL"),
        )

        style.configure(
            "Panel.TButton",
            padding=8,
            background=self._color("PANEL"),
            foreground=self._color("TEXT"),
        )

        style.configure(
            "Accent.TButton",
            padding=8,
            background=self._color("BTN"),
            foreground=self._color("BG"),
        )
        style.map(
            "Accent.TButton",
            background=[("active", self._color("ACCENT"))],
            foreground=[("active", self._color("BG"))],
        )

        style.configure(
            "App.TCombobox",
            fieldbackground=self._color("PANEL"),
            background=self._color("PANEL"),
            foreground=self._color("TEXT"),
        )
        style.map(
            "App.TCombobox",
            fieldbackground=[
                ("disabled", self._color("PANEL")),
                ("readonly", self._color("PANEL")),
                ("active", self._color("PANEL")),
            ],
            background=[
                ("disabled", self._color("PANEL")),
                ("readonly", self._color("PANEL")),
                ("active", self._color("PANEL")),
            ],
            foreground=[
                ("disabled", self._color("TEXT")),
                ("readonly", self._color("TEXT")),
                ("active", self._color("TEXT")),
            ],
        )

    def _apply_theme(self) -> None:
        self.palette = self._resolve_palette(self.theme_var.get())
        self.fonts = dict(FONTS_LARGE if self.large_fonts.get() else FONTS_DEFAULT)
        self._configure_style()
        self._apply_compact_layout()
        self._apply_compact_layout()

        for row in self.buttons:
            for btn in row:
                btn.configure(
                    bg=self._color("CELL"),
                    fg=self._color("TEXT"),
                    activebackground=self._color("ACCENT"),
                    activeforeground=self._color("BG"),
                    highlightbackground=self._color("ACCENT"),
                    font=self._font("board"),
                )
                btn.default_bg = self._color("CELL")  # type: ignore[attr-defined]
                btn.default_fg = self._color("TEXT")  # type: ignore[attr-defined]
        self._refresh_board()
        # update label fonts that were set explicitly
        if hasattr(self, "status_label"):
            self.status_label.configure(font=self._font("title"))
            self.score_label.configure(font=self._font("text"))
            self.history_label.configure(font=self._font("text"))
            self.log_label.configure(font=self._font("text"))
            self.match_label.configure(font=self._font("text"))
        self._save_settings()

    def _apply_compact_layout(self) -> None:
        wrap = 230 if self.compact_sidebar.get() else 260
        if hasattr(self, "status_label"):
            self.status_label.configure(wraplength=wrap)
            self.score_label.configure(wraplength=wrap)
            self.history_label.configure(wraplength=wrap)
            self.log_label.configure(wraplength=wrap)
            self.match_label.configure(wraplength=wrap)

    def _handle_exception(self, exc_type, exc_value, exc_traceback) -> None:
        self.logger.exception("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
        messagebox.showerror("Error", "An unexpected error occurred. See data/logs/app.log for details.")

    def _copy_diagnostics(self) -> None:
        log_path = os.path.join(LOG_DIR, "app.log")
        if not os.path.exists(log_path):
            messagebox.showinfo("Diagnostics", "No log file yet.")
            return
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                data = f.read()
            self.root.clipboard_clear()
            self.root.clipboard_append(data)
            messagebox.showinfo("Diagnostics", "Copied app log to clipboard.")
        except OSError:
            messagebox.showinfo("Diagnostics", "No log file available yet.")

    def _toggle_font_size(self) -> None:
        self._apply_theme()

    def _toggle_confirm(self) -> None:
        self._save_settings()

    def _toggle_auto_start(self) -> None:
        self._save_settings()

    def _toggle_rotate_logs(self) -> None:
        self._save_settings()

    def _toggle_animations(self) -> None:
        self._save_settings()

    def _toggle_sound(self) -> None:
        self._save_settings()

    def _toggle_show_coords(self) -> None:
        self._refresh_board()
        self._save_settings()

    def _disable_motion_sound(self) -> None:
        self.animations_enabled.set(False)
        self.sound_enabled.set(False)
        self._save_settings()

    def _reset_toggles(self) -> None:
        self.confirm_moves.set(True)
        self.auto_start.set(False)
        self.rotate_logs.set(True)
        self.large_fonts.set(False)
        self.animations_enabled.set(True)
        self.sound_enabled.set(True)
        self.show_coords.set(False)
        self.compact_sidebar.set(False)
        self._save_settings()
        self._apply_compact_layout()

    def _set_status_icon(self, mode: str) -> None:
        if not hasattr(self, "status_icon"):
            return
        icon = "⏸️"
        if mode == "player":
            icon = "▶️"
        elif mode == "ai":
            icon = "⏳"
        elif mode == "done":
            icon = "✅"
        self.status_icon.configure(text=icon)

    def _on_theme_change(self, _event=None) -> None:
        self._apply_theme()
        if self.options_popup and self.options_popup.winfo_exists():
            swatch = None
            for child in self.options_popup.winfo_children():
                for grand in child.winfo_children():
                    if isinstance(grand, tk.Canvas):
                        swatch = grand
                        break
            if swatch:
                self._update_theme_swatch(swatch)

    def _update_theme_swatch(self, canvas: tk.Canvas) -> None:
        canvas.delete("all")
        colors = [self._color(k) for k in ("BG", "PANEL", "ACCENT", "TEXT", "O")]
        width = canvas.winfo_width() or 200
        segment = width // len(colors)
        for i, col in enumerate(colors):
            canvas.create_rectangle(i * segment, 0, (i + 1) * segment, 20, fill=col, outline=col)

    def _build_controls(self, parent: tk.Widget) -> None:
        top = ttk.Frame(parent, padding=8, style="App.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        for col in range(6):
            top.columnconfigure(col, weight=1)

        ttk.Label(top, text="Difficulty:", style="App.TLabel", font=self._font("title")).grid(row=0, column=0, sticky="w")
        self.diff_var = tk.StringVar(value="Easy")
        diff_menu = ttk.Combobox(
            top,
            textvariable=self.diff_var,
            state="readonly",
            values=["Easy", "Normal", "Hard"],
            width=10,
            style="App.TCombobox",
        )
        diff_menu.grid(row=0, column=1, padx=4, sticky="w")
        diff_menu.bind("<<ComboboxSelected>>", self._on_diff_change)

        ttk.Label(top, text="Personality:", style="App.TLabel", font=self._font("title")).grid(row=0, column=2, sticky="w")
        self.personality_var = tk.StringVar(value="balanced")
        self.personality_menu = ttk.Combobox(
            top,
            textvariable=self.personality_var,
            state="readonly",
            values=["balanced", "defensive", "aggressive", "misdirection", "mirror"],
            width=14,
            style="App.TCombobox",
        )
        self.personality_menu.grid(row=0, column=3, padx=4, sticky="w")
        self.personality_menu.bind("<<ComboboxSelected>>", self._on_personality_change)

        self.start_btn = ttk.Button(top, text="New Game", command=self.start_new_game, style="Accent.TButton")
        self.start_btn.grid(row=0, column=4, padx=6, sticky="w")

        self.reset_btn = ttk.Button(top, text="Reset Scoreboard", command=self._reset_scoreboard, style="Panel.TButton")
        self.reset_btn.grid(row=0, column=5, padx=4, sticky="w")

        # Second row: match controls to avoid horizontal overflow on small widths.
        match_row = ttk.Frame(top, style="App.TFrame")
        match_row.grid(row=1, column=0, columnspan=6, sticky="w", pady=(6, 0))
        ttk.Label(match_row, text="Match (best of):", style="App.TLabel", font=self._font("title")).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.match_entry = ttk.Entry(match_row, textvariable=self.match_length_var, width=6)
        self.match_entry.grid(row=0, column=1, padx=4, sticky="w")
        ttk.Button(match_row, text="New Match", style="Panel.TButton", command=self._new_match).grid(row=0, column=2, padx=4, sticky="w")
        presets = ttk.Frame(match_row, style="App.TFrame")
        presets.grid(row=0, column=3, sticky="w", padx=(4, 0))
        for i, val in enumerate((3, 5, 7)):
            btn = ttk.Button(presets, text=f"Bo{val}", style="Panel.TButton", command=lambda v=val: self._set_match_preset(v))
            btn.grid(row=0, column=i, padx=2)

    def _build_board(self, parent: tk.Widget) -> None:
        board_frame = ttk.Frame(parent, padding=10, style="Panel.TFrame")
        board_frame.grid(row=1, column=0, sticky="nsew")
        board_frame.columnconfigure((0, 1, 2), weight=1)
        board_frame.rowconfigure((1, 2, 3), weight=1)

        ttk.Label(board_frame, text="Board", style="Title.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

        self.buttons = []
        for r in range(3):
            row_buttons = []
            for c in range(3):
                idx = r * 3 + c
                btn = tk.Button(
                    board_frame,
                    text=" ",
                    command=lambda i=idx: self._handle_player_move(i),
                    width=4,
                    font=self._font("board"),
                    bg=self._color("CELL"),
                    fg=self._color("TEXT"),
                    activebackground=self._color("ACCENT"),
                    activeforeground=self._color("BG"),
                    relief="raised",
                    bd=2,
                    highlightthickness=1,
                    highlightbackground=self._color("ACCENT"),
                    cursor="hand2",
                )
                btn.default_bg = self._color("CELL")  # type: ignore[attr-defined]
                btn.default_fg = self._color("TEXT")  # type: ignore[attr-defined]
                btn.bind("<Enter>", lambda _e, b=btn: self._hover_on(b))
                btn.bind("<Leave>", lambda _e, b=btn: self._hover_off(b))
                btn.grid(row=r + 1, column=c, padx=6, pady=6, sticky="nsew")
                row_buttons.append(btn)
            self.buttons.append(row_buttons)

        # Live move log under the board.
        log_frame = ttk.Frame(board_frame, style="App.TFrame")
        log_frame.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        ttk.Label(log_frame, text="Moves", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.move_listbox = tk.Listbox(
            log_frame,
            height=3,
            bg=self._color("PANEL"),
            fg=self._color("TEXT"),
            highlightthickness=1,
            highlightbackground=self._color("ACCENT"),
            selectbackground=self._color("ACCENT"),
            activestyle="none",
            relief="flat",
        )
        self.move_listbox.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        log_frame.columnconfigure(0, weight=1)

        ttk.Label(log_frame, text="Quick stats", style="App.TLabel", font=self._font("title")).grid(row=2, column=0, sticky="w", pady=(8, 2))
        self.quick_stats_inline = ttk.Label(
            log_frame,
            textvariable=self.quick_stats_var,
            style="App.TLabel",
            font=self._font("text"),
            wraplength=600,
            justify="left",
        )
        self.quick_stats_inline.grid(row=3, column=0, sticky="ew")

    def _build_info(self, parent: tk.Widget) -> None:
        info = ttk.Frame(parent, padding=12, style="Panel.TFrame")
        info.grid(row=0, column=0, sticky="nsew")
        info.columnconfigure(0, weight=1)

        status_frame = ttk.Frame(info, style="Panel.TFrame")
        status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Label(status_frame, text="Status", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.status_icon = ttk.Label(status_frame, text="⏸️", style="Status.TLabel", font=self._font("title"))
        self.status_icon.grid(row=1, column=0, sticky="w", padx=(0, 6))
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel", font=self._font("title"), wraplength=240)
        self.status_label.grid(row=1, column=1, sticky="w", pady=(2, 6))

        ttk.Label(info, text="Scoreboard", style="Title.TLabel").grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.score_label = ttk.Label(info, textvariable=self.score_var, style="App.TLabel", font=self._font("text"), wraplength=260, justify="left")
        self.score_label.grid(row=3, column=0, sticky="w", pady=(2, 6))

        ttk.Label(info, text="Match Score", style="Title.TLabel").grid(row=4, column=0, sticky="w")
        self.match_label = ttk.Label(info, textvariable=self.match_var, style="App.TLabel", font=self._font("text"), wraplength=260, justify="left")
        self.match_label.grid(row=5, column=0, sticky="w", pady=(2, 6))

        ttk.Label(info, text="Quick Stats", style="Title.TLabel").grid(row=6, column=0, sticky="w")
        self.quick_stats_label = ttk.Label(info, textvariable=self.quick_stats_var, style="App.TLabel", font=self._font("text"), wraplength=260, justify="left")
        self.quick_stats_label.grid(row=7, column=0, sticky="w", pady=(2, 6))

        ttk.Label(info, text="Recent Results", style="Title.TLabel").grid(row=6, column=0, sticky="w")
        self.history_label = ttk.Label(info, textvariable=self.history_var, style="App.TLabel", font=self._font("text"), wraplength=260, justify="left")
        self.history_label.grid(row=8, column=0, sticky="w", pady=(2, 6))

        self.log_label = ttk.Label(info, textvariable=self.log_path_var, style="Muted.TLabel", font=self._font("text"), wraplength=260, justify="left")
        self.log_label.grid(row=9, column=0, sticky="w", pady=(4, 8))

        ttk.Label(info, text="Shortcuts", style="Title.TLabel").grid(row=10, column=0, sticky="w")
        ttk.Label(
            info,
            text="Moves: 1-9  |  New: N/Ctrl+N",
            style="Muted.TLabel",
            font=self._font("text"),
            wraplength=260,
            justify="left",
        ).grid(row=11, column=0, sticky="w", pady=(2, 8))

        btn_row = ttk.Frame(info, style="Panel.TFrame")
        btn_row.grid(row=12, column=0, sticky="ew", pady=(4, 0))
        btn_row.columnconfigure((0, 1), weight=1)
        ttk.Button(btn_row, text="Hint", style="Panel.TButton", command=self._show_hint).grid(row=0, column=0, sticky="ew", padx=3)
        ttk.Button(btn_row, text="Undo Move", style="Panel.TButton", command=self._undo_move).grid(row=0, column=1, sticky="ew", padx=3)

        records = ttk.Frame(info, style="Panel.TFrame")
        records.grid(row=13, column=0, sticky="ew", pady=(6, 2))
        records.columnconfigure((0, 1), weight=1)
        ttk.Button(records, text="View history", style="Panel.TButton", command=self._view_history_popup).grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        ttk.Button(records, text="Save history", style="Panel.TButton", command=self._save_history_now).grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        ttk.Button(records, text="Achievements", style="Panel.TButton", command=self._show_achievements_popup).grid(row=1, column=0, columnspan=2, sticky="ew", padx=2, pady=(2, 2))
        ttk.Button(records, text="Options", style="Panel.TButton", command=self._show_options_popup).grid(row=2, column=0, columnspan=2, sticky="ew", padx=2, pady=(2, 0))

    def _on_diff_change(self, _event=None) -> None:
        self._apply_selection()

    def _on_personality_change(self, _event=None) -> None:
        self._apply_selection()

    def _format_move(self, move: tuple[int, str]) -> str:
        idx, symbol = move
        r, c = divmod(idx, 3)
        return f"{symbol} \u2192 {r + 1},{c + 1}"

    def _refresh_move_log(self) -> None:
        if not hasattr(self, "move_listbox"):
            return
        self.move_listbox.delete(0, tk.END)
        for i, (idx, symbol) in enumerate(self.session.moves, start=1):
            self.move_listbox.insert(tk.END, f"{i}. {self._format_move((idx, symbol))}")
        if self.session.moves:
            self.move_listbox.see(tk.END)

    def _apply_selection(self) -> None:
        level = self.diff_var.get()
        personality = self.personality_var.get() if level == "Normal" else "standard"
        self.personality_menu.state(["!disabled"] if level == "Normal" else ["disabled"])
        self.session.set_difficulty(level, personality)
        self.status_var.set(f"Selected {self.session.label()}. Start a game.")

    def _reset_scoreboard(self) -> None:
        if messagebox.askyesno("Reset scoreboard", "Reset all scores to zero?"):
            self.session.scoreboard = module._new_scoreboard()
            module.save_scoreboard(self.session.scoreboard)
            self._refresh_scoreboard()
            self.status_var.set("Scoreboard reset.")

    def _refresh_board(self) -> None:
        for r in range(3):
            for c in range(3):
                idx = r * 3 + c
                val = self.session.board[idx]
                btn = self.buttons[r][c]
                if val == " " and self.show_coords.get():
                    btn["text"] = f"{r+1},{c+1}"
                else:
                    btn["text"] = val
                if val == "X":
                    btn.configure(fg=self._color("ACCENT"), bg=btn.default_bg)
                elif val == "O":
                    btn.configure(fg=self._color("O"), bg=btn.default_bg)
                else:
                    btn.configure(fg=self._color("TEXT"), bg=btn.default_bg)

    def _hover_on(self, btn: tk.Button) -> None:
        if not self.animations_enabled.get():
            if btn["text"] == " ":
                btn.configure(highlightbackground=self._color("ACCENT"), highlightthickness=2)
            return
        if btn["text"] == " ":
            btn.configure(bg=self._color("ACCENT"), fg=self._color("BG"), relief="solid")

    def _hover_off(self, btn: tk.Button) -> None:
        if not self.animations_enabled.get():
            btn.configure(highlightbackground=self._color("ACCENT"), highlightthickness=1)
            return
        val = btn["text"]
        if val == "X":
            btn.configure(bg=btn.default_bg, fg=self._color("ACCENT"), relief="raised")
        elif val == "O":
            btn.configure(bg=btn.default_bg, fg=self._color("O"), relief="raised")
        else:
            btn.configure(bg=btn.default_bg, fg=btn.default_fg, relief="raised")

    def _refresh_scoreboard(self) -> None:
        sb = self.session.scoreboard
        lines = []
        for diff in module.DIFFICULTIES:
            entry = sb.get(diff, module.DEFAULT_SCORE)
            lines.append(f"{diff}: X={entry['X']}  O={entry['O']}  D={entry['Draw']}")
        self.score_var.set("\n".join(lines))
        if self.session.history:
            recent = self.session.history[-3:]
            parsed = []
            for item in recent:
                if len(item) == 3:
                    d, r, ts = item
                else:
                    d, r, ts, _ = item  # type: ignore[misc]
                parsed.append(f"{d}: {r}")
            self.history_var.set("Recent: " + " | ".join(parsed))
        else:
            self.history_var.set("Recent: none")
        # Update achievements popup if open
        if self.achievements_popup and self.achievements_popup.winfo_exists():
            self._populate_achievements(self.achievements_popup)

        self._refresh_quick_stats()

    def start_new_game(self) -> None:
        if getattr(self, "match_over", False):
            self._new_match()
        if self.pending_ai_id:
            self.root.after_cancel(self.pending_ai_id)
            self.pending_ai_id = None
        self.last_move_idx = None
        self.session.reset_board()
        self._apply_selection()
        self._refresh_board()
        self._refresh_move_log()
        self.session.game_over = False
        self.status_var.set(f"{self.session.label()}: Your turn.")
        self._set_status_icon("player")
        self._refresh_scoreboard()
        self.match_var.set(self._match_score_text())
        self.player_turn = True

    def _handle_player_move(self, idx: int) -> None:
        if self.session.game_over or self.session.board[idx] != " " or not getattr(self, "player_turn", True) or getattr(self, "match_over", False):
            return

        r, c = divmod(idx, 3)
        if self.confirm_moves.get():
            if not messagebox.askyesno("Confirm move", f"Place X at row {r + 1}, column {c + 1}?"):
                return
        self.last_move_idx = idx

        if self.pending_ai_id:
            self.root.after_cancel(self.pending_ai_id)
            self.pending_ai_id = None

        self.session.board[idx] = "X"
        self.session.moves.append((idx, "X"))
        self._refresh_move_log()
        self._refresh_board()
        winner = module.check_winner(self.session.board)
        if winner or module.board_full(self.session.board):
            self._finish_round(winner or "Draw")
            return

        self.status_var.set("AI is thinking...")
        self._set_status_icon("ai")
        self.player_turn = False
        self.pending_ai_id = self.root.after(250, self._ai_move)

    def _ai_move(self) -> None:
        if self.session.game_over:
            return
        ai_idx = self.session.ai_move_fn(self.session.board)
        self.session.board[ai_idx] = "O"
        self.session.moves.append((ai_idx, "O"))
        self._refresh_move_log()
        self._refresh_board()
        self._flash_ai_move(ai_idx)
        self.pending_ai_id = None
        self.last_move_idx = None
        winner = module.check_winner(self.session.board)
        if winner or module.board_full(self.session.board):
            self._finish_round(winner or "Draw")
            return
        self.status_var.set("Your turn.")
        self._set_status_icon("player")
        self.player_turn = True

    def _update_match_progress(self, round_winner: str) -> None:
        if self.match_over:
            return

        self.match_rounds += 1
        self.match_wins[round_winner] = self.match_wins.get(round_winner, 0) + 1

        target_hit = self.match_wins["X"] >= self.match_target or self.match_wins["O"] >= self.match_target
        rounds_exhausted = self.match_rounds >= self.match_length

        if target_hit or rounds_exhausted:
            if self.match_wins["X"] > self.match_wins["O"]:
                self.match_winner = "X"
            elif self.match_wins["O"] > self.match_wins["X"]:
                self.match_winner = "O"
            else:
                self.match_winner = "Draw"
            self.match_over = True
            self.player_turn = False
            if self.match_winner == "Draw":
                self.status_var.set("Match over: draw. Start a new match.")
            else:
                self.status_var.set(f"Match over! {self.match_winner} wins the match.")
            self._set_status_icon("done")

        self.match_var.set(self._match_score_text())
        self._refresh_quick_stats()

    def _refresh_quick_stats(self) -> None:
        sb = self.session.scoreboard
        x_total = sum(sb.get(diff, {}).get("X", 0) for diff in module.DIFFICULTIES)
        o_total = sum(sb.get(diff, {}).get("O", 0) for diff in module.DIFFICULTIES)
        d_total = sum(sb.get(diff, {}).get("Draw", 0) for diff in module.DIFFICULTIES)
        games = x_total + o_total + d_total
        match_line = (
            f"Match: Bo{self.match_length}, Round {self.match_rounds + (0 if self.match_over else 1)}/{self.match_length} "
            f"| X={self.match_wins['X']} O={self.match_wins['O']} D={self.match_wins['Draw']}"
        )
        self.quick_stats_var.set(
            f"Total games: {games}\nX wins: {x_total} | O wins: {o_total} | Draws: {d_total}\n{match_line}"
        )

    def _finish_round(self, winner: str) -> None:
        self.session.game_over = True
        if winner == "Draw":
            self.status_var.set("It's a draw. Start a new game.")
        else:
            self.status_var.set(f"Player {winner} wins! Start a new game.")
        self._set_status_icon("done")
        self.session.record_result(winner)
        self._update_match_progress(winner)
        self._refresh_scoreboard()
        self._refresh_move_log()
        self.last_move_idx = None
        if self.auto_start.get() and not getattr(self, "match_over", False):
            self.root.after(600, self.start_new_game)
        self._play_sound()

    def _flash_ai_move(self, idx: int) -> None:
        if not self.animations_enabled.get():
            return
        r, c = divmod(idx, 3)
        btn = self.buttons[r][c]
        original = btn.cget("bg")
        btn.configure(bg=self._color("ACCENT"), fg=self._color("BG"), relief="solid")
        self.root.after(220, lambda: btn.configure(bg=original, fg=self._color("O"), relief="raised"))

    def _undo_move(self) -> None:
        if self.session.game_over or self.last_move_idx is None:
            return
        if self.pending_ai_id:
            self.root.after_cancel(self.pending_ai_id)
            self.pending_ai_id = None
        self.session.board[self.last_move_idx] = " "
        self.last_move_idx = None
        self._refresh_board()
        self.status_var.set("Move undone. Your turn.")

    def _show_hint(self) -> None:
        if self.session.game_over:
            return
        board_copy = self.session.board[:]
        open_spots = [i for i, v in enumerate(board_copy) if v == " "]
        if not open_spots:
            return
        hint_idx = module.ai_move_hard(board_copy)
        r, c = divmod(hint_idx, 3)
        btn = self.buttons[r][c]
        btn.configure(bg=self._color("O"), fg=self._color("BG"), relief="solid")
        self.root.after(300, lambda: self._refresh_board())
        self.status_var.set(f"Hint: consider row {r + 1}, column {c + 1}.")

    def _view_history_popup(self) -> None:
        if self.history_popup and self.history_popup.winfo_exists():
            self.history_popup.lift()
            self.history_popup.focus_set()
            return
        if not self.session.history:
            messagebox.showinfo("History", "No history yet.")
            return
        popup = tk.Toplevel(self.root)
        popup.title("Recent history")
        popup.configure(bg=self._color("BG"))
        self.history_popup = popup
        text = tk.Text(
            popup,
            width=40,
            height=10,
            bg=self._color("PANEL"),
            fg=self._color("TEXT"),
            insertbackground=self._color("TEXT"),
        )
        text.pack(fill="both", expand=True, padx=10, pady=10)
        for diff, result, ts in self.session.history[-20:]:
            text.insert("end", f"{ts} - {diff}: {result}\n")
        text.configure(state="disabled")
        def on_close() -> None:
            self.history_popup = None
            popup.destroy()
        popup.protocol("WM_DELETE_WINDOW", on_close)

    def _compute_session_achievements(self) -> list:
        # Lifetime achievements based on persisted scoreboard
        sb = self.session.scoreboard
        total_wins = sum(entry.get("X", 0) for entry in sb.values())
        total_games = sum(entry.get("X", 0) + entry.get("O", 0) + entry.get("Draw", 0) for entry in sb.values())
        total_draws = sum(entry.get("Draw", 0) for entry in sb.values())

        hard = sb.get("Hard", module.DEFAULT_SCORE)
        normal = sb.get("Normal", module.DEFAULT_SCORE)
        easy = sb.get("Easy", module.DEFAULT_SCORE)

        hard_wins = hard.get("X", 0)
        normal_wins = normal.get("X", 0)
        easy_wins = easy.get("X", 0)
        hard_draws = hard.get("Draw", 0)
        normal_draws = normal.get("Draw", 0)
        easy_draws = easy.get("Draw", 0)

        defs = [
            # Wins & games
            ("First win!", total_wins >= 1),
            ("Win 5 games lifetime.", total_wins >= 5),
            ("Win 10 games lifetime.", total_wins >= 10),
            ("Win 25 games lifetime.", total_wins >= 25),
            ("Win 50 games lifetime.", total_wins >= 50),
            ("Play 25 games lifetime.", total_games >= 25),
            ("Play 50 games lifetime.", total_games >= 50),
            # Difficulty-specific wins
            ("Easy warmup (5 wins).", easy_wins >= 5),
            ("Easy veteran (15 wins).", easy_wins >= 15),
            ("Normal contender (5 wins).", normal_wins >= 5),
            ("Normal champ (15 wins).", normal_wins >= 15),
            ("Hard cracked once.", hard_wins >= 1),
            ("Hard regular (5 wins).", hard_wins >= 5),
            ("Hard seasoned (10 wins).", hard_wins >= 10),
            # Draws
            ("Draw collector (5 draws).", total_draws >= 5),
            ("Draw connoisseur (15 draws).", total_draws >= 15),
            ("Hard stalemates (5 draws).", hard_draws >= 5),
            ("Normal stalemates (7 draws).", normal_draws >= 7),
            ("Easy stalemates (5 draws).", easy_draws >= 5),
            # Mixed goals
            ("All-rounder: wins on Easy, Normal, Hard.", hard_wins >= 1 and normal_wins >= 1 and easy_wins >= 1),
            ("Balanced player: 10+ wins on Easy and Normal.", easy_wins >= 10 and normal_wins >= 10),
        ]

        earned = [name for name, ok in defs if ok]
        locked = [f"(locked) {name}" for name, ok in defs if not ok]
        items = earned + locked
        if not items:
            items = ["(locked) Achievements will appear as you play."]
        return items

    def _populate_achievements(self, popup: tk.Toplevel) -> None:
        for child in popup.winfo_children():
            child.destroy()
        ttk.Label(popup, text="Achievements (lifetime)", style="Title.TLabel").pack(anchor="w", padx=10, pady=(8, 4))
        container = ttk.Frame(popup, style="Panel.TFrame")
        container.pack(fill="both", expand=True, padx=10, pady=4)
        canvas = tk.Canvas(container, bg=self._color("PANEL"), highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas, style="Panel.TFrame")
        frame_id = canvas.create_window((0, 0), window=frame, anchor="nw")

        def _on_configure(event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(frame_id, width=canvas.winfo_width())

        frame.bind("<Configure>", _on_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        achievements = self._compute_session_achievements()
        if self.achievements_filter_earned.get():
            achievements = [a for a in achievements if not a.startswith("(locked)")]
        for item in achievements:
            ttk.Label(frame, text=f"- {item}", style="App.TLabel", wraplength=320, justify="left").pack(anchor="w", pady=2)
        frame.update_idletasks()
        if self.achievements_popup and achievements:
            try:
                first_locked_idx = next(i for i, a in enumerate(achievements) if a.startswith("(locked)"))
                canvas = frame.nametowidget(frame.winfo_parent())
                total = len(achievements)
                if total:
                    canvas.yview_moveto(first_locked_idx / max(1, total))
            except StopIteration:
                pass

    def _show_achievements_popup(self) -> None:
        if self.achievements_popup and self.achievements_popup.winfo_exists():
            self.achievements_popup.lift()
            self.achievements_popup.focus_set()
            return
        popup = tk.Toplevel(self.root)
        popup.title("Achievements")
        popup.configure(bg=self._color("BG"))
        self.achievements_popup = popup
        popup.protocol("WM_DELETE_WINDOW", lambda: self._close_achievements_popup(popup))
        controls = ttk.Frame(popup, style="App.TFrame")
        controls.pack(fill="x", padx=10, pady=(6, 0))
        ttk.Checkbutton(
            controls,
            text="Show earned only",
            variable=self.achievements_filter_earned,
            style="App.TCheckbutton",
            command=lambda: self._populate_achievements(popup),
        ).pack(side="left")
        ttk.Button(controls, text="Jump to first locked", style="Panel.TButton", command=lambda: self._populate_achievements(popup)).pack(side="right")
        self._populate_achievements(popup)

    def _close_achievements_popup(self, popup: tk.Toplevel) -> None:
        try:
            popup.destroy()
        finally:
            self.achievements_popup = None

    def _save_history_now(self) -> None:
        if not self.session.history:
            self.status_var.set("No history to save yet.")
            return
        path = module.save_session_history_to_file(
            [(d, r, ts, 0.0) for d, r, ts in self.session.history], rotate=self.rotate_logs.get()
        )
        self.session.last_history_path = path
        self.log_path_var.set(f"History file: {path}")
        self.status_var.set("History saved.")

    def _play_sound(self) -> None:
        if not self.sound_enabled.get():
            return
        try:
            self.root.bell()
        except tk.TclError:
            pass

    def _show_options_popup(self) -> None:
        options.show_options_popup(self)



def main() -> None:
    root = tk.Tk()
    app = TicTacToeGUI(root)
    app.start_new_game()
    root.mainloop()


if __name__ == "__main__":
    main()

