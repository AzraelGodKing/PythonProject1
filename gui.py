"""
Basic Tkinter UI for the tic-tac-toe game logic in tic-tac-toe.py.
The UI is a thin layer over the existing logic: board state, AI moves, and scoreboard persistence.
"""

import importlib.util
import json
import os
import pathlib
import tkinter as tk
from typing import Optional
from tkinter import messagebox, ttk


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
        self.settings_path = os.environ.get("GUI_SETTINGS_PATH", SETTINGS_FILE)
        settings = self._load_settings()
        self.large_fonts = tk.BooleanVar(value=settings["large_fonts"])
        self.theme_var = tk.StringVar(value=settings["theme"])
        self.animations_enabled = tk.BooleanVar(value=settings["animations"])
        self.sound_enabled = tk.BooleanVar(value=settings["sound"])
        self.palette = self._resolve_palette(self.theme_var.get())
        self.fonts = dict(FONTS_LARGE if self.large_fonts.get() else FONTS_DEFAULT)
        self._configure_style()
        self.session = GameSession()

        self.status_var = tk.StringVar(value="Choose a difficulty and start a game.")
        self.score_var = tk.StringVar()
        self.history_var = tk.StringVar(value="Recent: none")
        self.log_path_var = tk.StringVar(value=f"History file: {self.session.last_history_path}")
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

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=10, style="App.TFrame")
        container.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
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

    def _load_settings(self) -> dict:
        defaults = {
            "confirm_moves": True,
            "auto_start": False,
            "rotate_logs": True,
            "theme": "default",
            "large_fonts": False,
            "animations": True,
            "sound": True,
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
        self._save_settings()

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

    def _on_theme_change(self, _event=None) -> None:
        self._apply_theme()

    def _build_controls(self, parent: tk.Widget) -> None:
        top = ttk.Frame(parent, padding=10, style="App.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(3, weight=1)

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
        diff_menu.grid(row=0, column=1, padx=5)
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
        self.personality_menu.grid(row=0, column=3, padx=5, sticky="w")
        self.personality_menu.bind("<<ComboboxSelected>>", self._on_personality_change)

        self.start_btn = ttk.Button(top, text="New Game", command=self.start_new_game, style="Accent.TButton")
        self.start_btn.grid(row=0, column=4, padx=10)

        self.reset_btn = ttk.Button(top, text="Reset Scoreboard", command=self._reset_scoreboard, style="Panel.TButton")
        self.reset_btn.grid(row=0, column=5, padx=5)

    def _build_board(self, parent: tk.Widget) -> None:
        board_frame = ttk.Frame(parent, padding=14, style="Panel.TFrame")
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
                    highlightthickness=2,
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

    def _build_info(self, parent: tk.Widget) -> None:
        info = ttk.Frame(parent, padding=12, style="Panel.TFrame")
        info.grid(row=0, column=0, sticky="nsew")
        info.columnconfigure(0, weight=1)

        ttk.Label(info, text="Status", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(info, textvariable=self.status_var, style="Status.TLabel", font=self._font("title"), wraplength=260)
        self.status_label.grid(row=1, column=0, sticky="w", pady=(2, 8))

        ttk.Label(info, text="Scoreboard", style="Title.TLabel").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.score_label = ttk.Label(info, textvariable=self.score_var, style="App.TLabel", font=self._font("text"), wraplength=260, justify="left")
        self.score_label.grid(row=3, column=0, sticky="w", pady=(2, 10))

        ttk.Label(info, text="Recent Results", style="Title.TLabel").grid(row=4, column=0, sticky="w")
        self.history_label = ttk.Label(info, textvariable=self.history_var, style="App.TLabel", font=self._font("text"), wraplength=260, justify="left")
        self.history_label.grid(row=5, column=0, sticky="w", pady=(2, 10))

        self.log_label = ttk.Label(info, textvariable=self.log_path_var, style="Muted.TLabel", font=self._font("text"), wraplength=260, justify="left")
        self.log_label.grid(row=6, column=0, sticky="w", pady=(4, 8))

        ttk.Label(info, text="Shortcuts", style="Title.TLabel").grid(row=7, column=0, sticky="w")
        ttk.Label(
            info,
            text="Moves: 1-9  |  New: N/Ctrl+N",
            style="Muted.TLabel",
            font=self._font("text"),
            wraplength=260,
            justify="left",
        ).grid(row=8, column=0, sticky="w", pady=(2, 8))

        btn_row = ttk.Frame(info, style="Panel.TFrame")
        btn_row.grid(row=9, column=0, sticky="ew", pady=(4, 0))
        btn_row.columnconfigure((0, 1), weight=1)
        ttk.Button(btn_row, text="Hint", style="Panel.TButton", command=self._show_hint).grid(row=0, column=0, sticky="ew", padx=3)
        ttk.Button(btn_row, text="Undo Move", style="Panel.TButton", command=self._undo_move).grid(row=0, column=1, sticky="ew", padx=3)

        ttk.Button(info, text="Options", style="Panel.TButton", command=self._show_options_popup).grid(row=10, column=0, sticky="ew", pady=(8, 2))
        ttk.Button(info, text="View history", style="Panel.TButton", command=self._view_history_popup).grid(row=11, column=0, sticky="ew", pady=(6, 2))
        ttk.Button(info, text="Save history now", style="Panel.TButton", command=self._save_history_now).grid(row=12, column=0, sticky="ew", pady=(2, 0))

    def _on_diff_change(self, _event=None) -> None:
        self._apply_selection()

    def _on_personality_change(self, _event=None) -> None:
        self._apply_selection()

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
                btn["text"] = val
                if val == "X":
                    btn.configure(fg=self._color("ACCENT"), bg=btn.default_bg)
                elif val == "O":
                    btn.configure(fg=self._color("O"), bg=btn.default_bg)
                else:
                    btn.configure(fg=self._color("TEXT"), bg=btn.default_bg)

    def _hover_on(self, btn: tk.Button) -> None:
        if not self.animations_enabled.get():
            return
        if btn["text"] == " ":
            btn.configure(bg=self._color("ACCENT"), fg=self._color("BG"), relief="solid")

    def _hover_off(self, btn: tk.Button) -> None:
        if not self.animations_enabled.get():
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
            self.history_var.set("Recent: " + " | ".join(f"{d}: {r}" for d, r, _ in recent))
        else:
            self.history_var.set("Recent: none")

    def start_new_game(self) -> None:
        if self.pending_ai_id:
            self.root.after_cancel(self.pending_ai_id)
            self.pending_ai_id = None
        self.last_move_idx = None
        self.session.reset_board()
        self._apply_selection()
        self._refresh_board()
        self.session.game_over = False
        self.status_var.set(f"{self.session.label()}: Your turn.")
        self._refresh_scoreboard()

    def _handle_player_move(self, idx: int) -> None:
        if self.session.game_over or self.session.board[idx] != " ":
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
        self._refresh_board()
        winner = module.check_winner(self.session.board)
        if winner or module.board_full(self.session.board):
            self._finish_round(winner or "Draw")
            return

        self.status_var.set("AI is thinking...")
        self.pending_ai_id = self.root.after(250, self._ai_move)

    def _ai_move(self) -> None:
        if self.session.game_over:
            return
        ai_idx = self.session.ai_move_fn(self.session.board)
        self.session.board[ai_idx] = "O"
        self._refresh_board()
        self._flash_ai_move(ai_idx)
        self.pending_ai_id = None
        self.last_move_idx = None
        winner = module.check_winner(self.session.board)
        if winner or module.board_full(self.session.board):
            self._finish_round(winner or "Draw")
            return
        self.status_var.set("Your turn.")

    def _finish_round(self, winner: str) -> None:
        self.session.game_over = True
        if winner == "Draw":
            self.status_var.set("It's a draw. Start a new game.")
        else:
            self.status_var.set(f"Player {winner} wins! Start a new game.")
        self.session.record_result(winner)
        self._refresh_scoreboard()
        self.last_move_idx = None
        if self.auto_start.get():
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
        if not self.session.history:
            messagebox.showinfo("History", "No history yet.")
            return
        popup = tk.Toplevel(self.root)
        popup.title("Recent history")
        popup.configure(bg=self._color("BG"))
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
        popup = tk.Toplevel(self.root)
        popup.title("Options")
        popup.configure(bg=self._color("BG"))
        frame = ttk.Frame(popup, padding=12, style="App.TFrame")
        frame.grid(row=0, column=0, sticky="nsew")
        popup.columnconfigure(0, weight=1)
        popup.rowconfigure(0, weight=1)

        ttk.Label(frame, text="Options", style="Title.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))

        ttk.Checkbutton(frame, text="Require confirmations", variable=self.confirm_moves, style="App.TCheckbutton", command=self._toggle_confirm).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Checkbutton(frame, text="Auto-start next game", variable=self.auto_start, style="App.TCheckbutton", command=self._toggle_auto_start).grid(row=2, column=0, sticky="w", pady=2)
        ttk.Checkbutton(frame, text="Rotate history filenames", variable=self.rotate_logs, style="App.TCheckbutton", command=self._toggle_rotate_logs).grid(row=3, column=0, sticky="w", pady=2)
        ttk.Checkbutton(frame, text="Larger fonts", variable=self.large_fonts, style="App.TCheckbutton", command=self._toggle_font_size).grid(row=4, column=0, sticky="w", pady=2)
        ttk.Checkbutton(frame, text="Animations", variable=self.animations_enabled, style="App.TCheckbutton", command=self._toggle_animations).grid(row=5, column=0, sticky="w", pady=2)
        ttk.Checkbutton(frame, text="Sound cues", variable=self.sound_enabled, style="App.TCheckbutton", command=self._toggle_sound).grid(row=6, column=0, sticky="w", pady=2)

        ttk.Label(frame, text="Theme", style="Title.TLabel").grid(row=7, column=0, sticky="w", pady=(8, 2))
        theme_box = ttk.Combobox(
            frame,
            textvariable=self.theme_var,
            state="readonly",
            values=[
                "default",
                "high_contrast",
                "colorblind_protan",
                "colorblind_deutan",
                "colorblind_tritan",
                "monochrome",
                "light",
            ],
            style="App.TCombobox",
        )
        theme_box.grid(row=8, column=0, sticky="ew", pady=(0, 4))
        theme_box.bind("<<ComboboxSelected>>", self._on_theme_change)

        ttk.Button(frame, text="Close", style="Panel.TButton", command=popup.destroy).grid(row=9, column=0, sticky="e", pady=(10, 0))


def main() -> None:
    root = tk.Tk()
    app = TicTacToeGUI(root)
    app.start_new_game()
    root.mainloop()


if __name__ == "__main__":
    main()
