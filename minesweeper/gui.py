"""A lightweight Minesweeper GUI using Tkinter."""

from __future__ import annotations

import argparse
import os
import random
import sys
import time
import json
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.options import PALETTES
from shared import settings, single_instance
from shared.theme_manager import ThemedApp

LOCK_DIR = PROJECT_ROOT / "data" / "locks"
LOCK_FILE = LOCK_DIR / "minesweeper.lock"
ACTIVE_GAME_LOCK = LOCK_DIR / "active_game.lock"
SETTINGS_FILE = PROJECT_ROOT / "data" / "minesweeper_settings.json"
LOCALES_DIR = PROJECT_ROOT / "shared" / "locales"

DIFFICULTIES = {
    "beginner": (9, 9, 10),
    "intermediate": (16, 16, 40),
    "expert": (16, 24, 75),
}


@dataclass
class Cell:
    mine: bool = False
    revealed: bool = False
    flagged: bool = False
    adjacent: int = 0


class MinesweeperApp(ThemedApp):
    def __init__(self, root: tk.Tk, *, headless: bool = False) -> None:
        self.root = root
        defaults = {
            "difficulty": "beginner",
            "theme": "default",
            "mode": "classic",
            "best_times": {"beginner": None, "intermediate": None, "expert": None},
            "best_times_by_mode": {
                "classic": {"beginner": None, "intermediate": None, "expert": None},
                "challenge": {"beginner": None, "intermediate": None, "expert": None},
                "puzzle": {"beginner": None, "intermediate": None, "expert": None},
            },
        }
        self.settings = settings.load_settings(Path(SETTINGS_FILE), defaults)
        self.difficulty = self.settings.get("difficulty", "beginner")
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "default"))
        self.best_times: Dict[str, Optional[float]] = self.settings.get("best_times", defaults["best_times"])
        self.best_times_by_mode: Dict[str, Dict[str, Optional[float]]] = self.settings.get(
            "best_times_by_mode", defaults["best_times_by_mode"]
        )
        self.best_time_var = tk.StringVar(value="")
        self.mode_var = tk.StringVar(value=self.settings.get("mode", "classic"))
        self.language = os.environ.get("GAME_LANGUAGE", "en")
        self.translations: Dict[str, str] = {}
        self._load_translations(self.language)

        # Initialize ThemedApp parent class
        super().__init__(root, self.theme_var, self.theme_var.get())

        self.root.title(self._t("minesweeper.title", "Minesweeper"))
        self.root.geometry("900x720")
        self.root.minsize(720, 600)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
        self.headless = headless
        if headless:
            self.root.withdraw()

        self.rows, self.cols, self.mines_total = DIFFICULTIES.get(self.difficulty, DIFFICULTIES["beginner"])
        self.cells: list[list[Cell]] = []
        self.buttons: list[list[tk.Button]] = []
        self.button_coords: dict[tk.Button, tuple[int, int]] = {}
        self.first_click = True
        self.game_over = False
        self.cursor = (0, 0)
        self.flags_left = self.mines_total
        self.start_time: Optional[float] = None
        self.timer_job: Optional[str] = None

        self.status_var = tk.StringVar()
        self.timer_var = tk.StringVar(value="00:00")
        self.flags_var = tk.StringVar(value=f"{self.mines_total} F")

        self._build_ui()
        self._new_game(reset_timer=False)

    # Translation helpers
    def _load_translations(self, lang: str) -> None:
        fallback = LOCALES_DIR / "en.json"
        lang_file = LOCALES_DIR / f"{lang}.json"
        data: Dict[str, str] = {}
        for path in (fallback, lang_file):
            if not path.exists():
                continue
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    data.update(loaded)
            except Exception:
                continue
        self.translations = data

    def _t(self, key: str, default: str) -> str:
        return self.translations.get(key, default)

    # UI
    def _build_ui(self) -> None:
        self._apply_theme()
        menubar = tk.Menu(self.root)
        menubar.add_command(label=self._t("minesweeper.menu.new", "New Game"), command=self._new_game)
        menubar.add_command(label=self._t("minesweeper.menu.options", "Options"), command=self._show_options)
        self.root.config(menu=menubar)

        header = ttk.Frame(self.root, padding=14, style="Hero.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text=self._t("minesweeper.title", "Minesweeper"), style="HeroTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )
        ttk.Label(
            header,
            text=self._t("minesweeper.subtitle", "Clear every safe tile without triggering a mine."),
            style="HeroMuted.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, sticky="w")

        controls = ttk.Frame(header, style="Hero.TFrame")
        controls.grid(row=2, column=0, sticky="ew", pady=(10, 2))
        controls.columnconfigure(6, weight=1)

        ttk.Label(controls, text=self._t("minesweeper.difficulty", "Difficulty:"), style="Subtitle.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        diff_box = ttk.Combobox(
            controls,
            values=["beginner", "intermediate", "expert"],
            state="readonly",
            width=14,
        )
        diff_box.set(self.difficulty)
        diff_box.grid(row=0, column=1, sticky="w", padx=(0, 12))
        diff_box.bind("<<ComboboxSelected>>", lambda e: self._change_difficulty(diff_box.get()))

        ttk.Label(controls, text=self._t("minesweeper.mode", "Mode:"), style="Subtitle.TLabel").grid(
            row=0, column=2, sticky="w", padx=(0, 6)
        )
        mode_box = ttk.Combobox(
            controls,
            values=["classic", "challenge", "puzzle"],
            state="readonly",
            width=12,
            textvariable=self.mode_var,
        )
        mode_box.grid(row=0, column=3, sticky="w", padx=(0, 12))
        mode_box.bind("<<ComboboxSelected>>", lambda e: self._change_mode(mode_box.get()))

        ttk.Label(controls, textvariable=self.flags_var, style="Badge.TLabel").grid(row=0, column=4, sticky="w", padx=4)
        ttk.Label(controls, textvariable=self.timer_var, style="BadgeMuted.TLabel").grid(row=0, column=5, sticky="w", padx=4)
        ttk.Label(controls, textvariable=self.best_time_var, style="BadgeMuted.TLabel").grid(row=0, column=6, sticky="w", padx=4)
        ttk.Button(
            controls,
            text=self._t("minesweeper.reset", "Reset"),
            style="Accent.TButton",
            command=self._new_game,
            width=10,
        ).grid(row=0, column=5, padx=(10, 0))

        self.status_label = ttk.Label(header, textvariable=self.status_var, style="Subtitle.TLabel", wraplength=760, justify="left")
        self.status_label.grid(row=3, column=0, sticky="w", pady=(10, 0))

        self.board_frame = ttk.Frame(self.root, padding=12)
        self.board_frame.grid(row=2, column=0, sticky="nsew")
        self.board_frame.columnconfigure(0, weight=1)
        self.board_frame.rowconfigure(0, weight=1)
        # Keyboard bindings
        self.root.bind("<Up>", lambda e: self._move_cursor(-1, 0))
        self.root.bind("<Down>", lambda e: self._move_cursor(1, 0))
        self.root.bind("<Left>", lambda e: self._move_cursor(0, -1))
        self.root.bind("<Right>", lambda e: self._move_cursor(0, 1))
        self.root.bind("<space>", lambda e: self._on_left_click(*self.cursor))
        self.root.bind("<Return>", lambda e: self._on_left_click(*self.cursor))
        self.root.bind("f", lambda e: self._on_right_click(*self.cursor))
        self.root.bind("F", lambda e: self._on_right_click(*self.cursor))

    def _apply_theme(self, theme_name=None) -> None:
        """Apply theme using parent class and add game-specific customizations."""
        # Call parent to handle standard theme configuration
        super()._apply_theme(theme_name)

        # Cache palette for quick access
        self.palette = PALETTES.get(self.theme_var.get(), PALETTES["default"])

    def _customize_styles(self) -> None:
        """Minesweeper-specific style customizations."""
        # Get current theme colors
        bg = self._color("BG")
        panel = self._color("PANEL")
        text = self._color("TEXT")
        muted = self._color("MUTED")
        accent = self._color("ACCENT")
        btn = self._color("BTN")
        border = self._color("BORDER")

        # Configure Minesweeper-specific ttk styles
        self.style.theme_use("clam")
        self.style.configure("TFrame", background=bg)
        self.style.configure("Hero.TFrame", background=panel)
        self.style.configure("HeroTitle.TLabel", font=("Segoe UI", 20, "bold"), background=panel, foreground=text)
        self.style.configure("HeroMuted.TLabel", font=("Segoe UI", 10), background=panel, foreground=muted)
        self.style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), background=bg, foreground=text)
        self.style.configure("Subtitle.TLabel", font=("Segoe UI", 10), background=bg, foreground=muted)
        self.style.configure("Badge.TLabel", background=accent, foreground=bg, font=("Segoe UI", 10, "bold"), padding=(10, 4))
        self.style.configure("BadgeMuted.TLabel", background=border, foreground=text, font=("Segoe UI", 10), padding=(10, 4))
        self.style.configure("Accent.TButton", padding=(10, 6), background=accent, foreground=bg, relief="flat")
        self.style.map("Accent.TButton", background=[("active", btn)], foreground=[("active", bg)])
        self.style.configure("Cell.TButton", background=panel, foreground=text, padding=(4, 2), relief="flat")
        self.style.map("Cell.TButton", background=[("active", btn)])

        # Set up cell colors for game rendering
        self._cell_colors = {
            "hidden": panel,
            "hover": self.palette.get("HOVER", btn),
            "revealed": bg,
            "flag": border,
            "mine": "#ef4444",
        }

    # Game state
    def _change_difficulty(self, key: str) -> None:
        if key not in DIFFICULTIES:
            return
        self.difficulty = key
        self.rows, self.cols, self.mines_total = DIFFICULTIES[key]
        self.flags_left = self.mines_total
        self._new_game()

    def _change_mode(self, mode: str) -> None:
        if mode not in {"classic", "challenge", "puzzle"}:
            return
        self.mode_var.set(mode)
        self._new_game()

    def _new_game(self, reset_timer: bool = True) -> None:
        if reset_timer:
            self._stop_timer()
            self.timer_var.set("00:00")
            self.start_time = None
        self.first_click = True
        self.game_over = False
        self.flags_left = self.mines_total
        self.flags_var.set(f"{self.flags_left} F")
        self.cursor = (0, 0)
        self._refresh_best_time_label()
        self.status_var.set(self._t("minesweeper.status.ready", "Click any cell to start."))
        self._build_board()

    def _build_board(self) -> None:
        for child in self.board_frame.winfo_children():
            child.destroy()
        grid = tk.Frame(self.board_frame, bg=self.palette.get("PANEL", "#142039"))
        grid.grid(row=0, column=0, sticky="nsew")
        for r in range(self.rows):
            grid.rowconfigure(r, weight=1, minsize=32)
        for c in range(self.cols):
            grid.columnconfigure(c, weight=1, minsize=32)

        self.cells = [[Cell() for _ in range(self.cols)] for _ in range(self.rows)]
        self.buttons = []
        self.button_coords = {}
        for r in range(self.rows):
            row_btns: list[tk.Button] = []
            for c in range(self.cols):
                btn = tk.Button(
                    grid,
                    width=3,
                    height=1,
                    text="",
                    relief="flat",
                    bd=0,
                    bg=self._cell_colors["hidden"],
                    fg=self.palette.get("TEXT", "#f8fafc"),
                    activebackground=self._cell_colors["hover"],
                    command=lambda r=r, c=c: self._on_left_click(r, c),
                )
                btn.grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
                btn.bind("<Button-3>", lambda e, r=r, c=c: self._on_right_click(r, c))
                btn.bind("<Button-2>", lambda e, r=r, c=c: self._try_chord(r, c))
                btn.bind("<Double-Button-1>", lambda e, r=r, c=c: self._try_chord(r, c))
                btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self._cell_colors["hover"]))
                btn.bind("<Leave>", lambda e, b=btn: self._restore_button_bg(b))
                row_btns.append(btn)
                self.button_coords[btn] = (r, c)
            self.buttons.append(row_btns)
        self._update_cursor_highlight()

    def _on_left_click(self, r: int, c: int) -> None:
        if self.game_over:
            return
        cell = self.cells[r][c]
        if cell.flagged:
            return
        if self.first_click:
            self._place_mines(safe_r=r, safe_c=c)
            self.first_click = False
            self._start_timer()
        if cell.mine:
            self._reveal_all()
            self.game_over = True
            self._stop_timer()
            self.status_var.set(self._t("minesweeper.status.lose", "Boom! You hit a mine."))
            return
        self._flood_fill(r, c)
        if self._check_win():
            self.game_over = True
            elapsed = self._stop_timer()
            new_best = self._update_best_time()
            self.status_var.set(self._t("minesweeper.status.win", "Cleared! You win."))
            self._show_win_dialog(elapsed, new_best)
        self._render_cells()

    def _try_chord(self, r: int, c: int) -> None:
        if self.game_over or self.first_click:
            return
        cell = self.cells[r][c]
        if not cell.revealed or cell.adjacent == 0:
            return
        flagged = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols and self.cells[nr][nc].flagged:
                    flagged += 1
        if flagged != cell.adjacent:
            return
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    neighbor = self.cells[nr][nc]
                    if not neighbor.flagged and not neighbor.revealed:
                        self._on_left_click(nr, nc)

    def _on_right_click(self, r: int, c: int) -> None:
        if self.game_over:
            return
        cell = self.cells[r][c]
        if cell.revealed:
            return
        if cell.flagged:
            cell.flagged = False
            self.flags_left += 1
        else:
            if self.flags_left <= 0:
                return
            cell.flagged = True
            self.flags_left -= 1
        self.flags_var.set(f"{self.flags_left} F")
        self._render_cells()

    def _place_mines(self, *, safe_r: int, safe_c: int) -> None:
        positions = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        # Avoid placing on the first click and its neighbors for a fair start
        neighbors = {(safe_r + dr, safe_c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)}
        positions = [(r, c) for (r, c) in positions if (r, c) not in neighbors]
        mines = random.sample(positions, k=self.mines_total)
        for r, c in mines:
            self.cells[r][c].mine = True
        # Compute adjacency
        for r in range(self.rows):
            for c in range(self.cols):
                if self.cells[r][c].mine:
                    continue
                self.cells[r][c].adjacent = self._count_adjacent_mines(r, c)

    def _count_adjacent_mines(self, r: int, c: int) -> int:
        count = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols and self.cells[nr][nc].mine:
                    count += 1
        return count

    def _flood_fill(self, r: int, c: int) -> None:
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            cell = self.cells[cr][cc]
            if cell.revealed or cell.flagged:
                continue
            cell.revealed = True
            if cell.adjacent == 0:
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            neighbor = self.cells[nr][nc]
                            if not neighbor.revealed and not neighbor.flagged and not neighbor.mine:
                                stack.append((nr, nc))

    def _reveal_all(self) -> None:
        for r in range(self.rows):
            for c in range(self.cols):
                self.cells[r][c].revealed = True
        self._render_cells()

    def _render_cells(self) -> None:
        palette = self.palette
        colors = {
            0: palette.get("PANEL", "#142039"),
            1: "#38bdf8",
            2: "#22c55e",
            3: "#ef4444",
            4: "#a855f7",
            5: "#f59e0b",
            6: "#0ea5e9",
            7: "#f472b6",
            8: "#e5e7eb",
        }
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                btn = self.buttons[r][c]
                if cell.flagged and not cell.revealed:
                    btn.config(text="F", relief="raised", bg=palette.get("PANEL", "#142039"))
                    continue
                if not cell.revealed:
                    btn.config(text="", relief="raised", bg=palette.get("PANEL", "#142039"))
                    continue
                if cell.mine:
                    btn.config(text="*", bg="#ef4444", relief="sunken", fg="#0f172a")
                    continue
                btn.config(
                    text=str(cell.adjacent) if cell.adjacent > 0 else "",
                    bg=self._cell_colors["revealed"],
                    fg=colors.get(cell.adjacent, palette.get("TEXT", "#f8fafc")),
                    relief="flat",
                )
        self._update_cursor_highlight()

    def _check_win(self) -> bool:
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                if not cell.mine and not cell.revealed:
                    return False
        return True

    def _restore_button_bg(self, btn: tk.Button) -> None:
        # Re-render to restore original coloring; cheap enough for this size.
        self._render_cells()

    def _move_cursor(self, dr: int, dc: int) -> None:
        if self.game_over:
            return
        r, c = self.cursor
        r = max(0, min(self.rows - 1, r + dr))
        c = max(0, min(self.cols - 1, c + dc))
        self.cursor = (r, c)
        self._update_cursor_highlight()

    def _update_cursor_highlight(self) -> None:
        accent = self.palette.get("ACCENT", "#22c55e")
        for r in range(self.rows):
            for c in range(self.cols):
                btn = self.buttons[r][c]
                if (r, c) == self.cursor:
                    btn.configure(highlightthickness=2, highlightbackground=accent, highlightcolor=accent)
                else:
                    btn.configure(highlightthickness=0)

    def _start_timer(self) -> None:
        self.start_time = time.time()
        self._tick_timer()

    def _tick_timer(self) -> None:
        if self.game_over or self.start_time is None:
            return
        elapsed = int(time.time() - self.start_time)
        self.timer_var.set(f"{elapsed // 60:02d}:{elapsed % 60:02d}")
        self.timer_job = self.root.after(1000, self._tick_timer)

    def _stop_timer(self) -> None:
        if self.timer_job:
            try:
                self.root.after_cancel(self.timer_job)
            except Exception:
                pass
        self.timer_job = None
        if self.start_time is None:
            return None
        return int(time.time() - self.start_time)

    def _update_best_time(self) -> bool:
        if self.start_time is None:
            return False
        elapsed = int(time.time() - self.start_time)
        mode = self.mode_var.get() or "classic"
        per_mode = self.best_times_by_mode.setdefault(mode, {}).setdefault(
            self.difficulty, self.best_times.get(self.difficulty)
        )
        best = per_mode
        if best is None or elapsed < best:
            self.best_times[self.difficulty] = elapsed
            self.best_times_by_mode.setdefault(mode, {})[self.difficulty] = elapsed
            settings.save_settings(
                Path(SETTINGS_FILE),
                {
                    "difficulty": self.difficulty,
                    "theme": self.theme_var.get(),
                    "best_times": self.best_times,
                    "best_times_by_mode": self.best_times_by_mode,
                    "mode": mode,
                },
            )
            self._refresh_best_time_label()
            return True
        self._refresh_best_time_label()
        return False

    def _refresh_best_time_label(self) -> None:
        mode = self.mode_var.get() or "classic"
        best = self.best_times_by_mode.get(mode, {}).get(self.difficulty)
        if isinstance(best, (int, float)):
            m, s = divmod(int(best), 60)
            self.best_time_var.set(f"{self._t('minesweeper.best', 'Best')}: {m:02d}:{s:02d}")
        else:
            self.best_time_var.set(self._t("minesweeper.best.none", "Best: —"))

    def _show_win_dialog(self, elapsed: Optional[int], new_best: bool) -> None:
        if self.headless:
            return
        if elapsed is None:
            elapsed = 0
        minutes, seconds = divmod(elapsed, 60)
        best = self.best_times.get(self.difficulty)
        best_text = f"{best // 60:02d}:{best % 60:02d}" if isinstance(best, int) else "—"
        body = "\n".join(
            [
                f"Difficulty: {self.difficulty.title()}",
                f"Time: {minutes:02d}:{seconds:02d}",
                f"Best: {best_text}" + ("  (New best!)" if new_best else ""),
                "",
                "Play again?",
            ]
        )
        try:
            if messagebox.askyesno(self._t("minesweeper.status.win", "Cleared! You win."), body):
                self._new_game()
        except tk.TclError:
            print(body, file=sys.stderr)

    def _show_options(self) -> None:
        popup = tk.Toplevel(self.root)
        popup.title(self._t("minesweeper.menu.options", "Options"))
        popup.configure(bg=self.palette.get("BG", "#0f172a"))
        popup.resizable(False, False)
        ttk.Label(popup, text=self._t("minesweeper.theme", "Theme"), style="Title.TLabel").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )
        box = ttk.Combobox(popup, values=list(PALETTES.keys()), state="readonly", textvariable=self.theme_var, width=18)
        box.grid(row=1, column=0, sticky="ew", padx=12)
        box.bind("<<ComboboxSelected>>", lambda e: self._on_theme_change())
        ttk.Button(popup, text=self._t("minesweeper.reset_times", "Reset best times"), command=self._reset_times).grid(
            row=2, column=0, sticky="w", padx=12, pady=(10, 0)
        )
        ttk.Button(popup, text=self._t("minesweeper.close", "Close"), command=popup.destroy).grid(
            row=3, column=0, sticky="e", padx=12, pady=12
        )
        popup.columnconfigure(0, weight=1)

    def _reset_times(self) -> None:
        self.best_times = {"beginner": None, "intermediate": None, "expert": None}
        self._save_settings()

    def _on_theme_change(self) -> None:
        self._apply_theme()
        self._render_cells()
        self._save_settings()

    def _save_settings(self) -> None:
        settings.save_settings(
            Path(SETTINGS_FILE),
            {"difficulty": self.difficulty, "theme": self.theme_var.get(), "best_times": self.best_times},
        )


def _notify_already_running() -> None:
    message = "Minesweeper is already running. Close the other window before starting a new session."
    try:
        tmp = tk.Tk()
        tmp.withdraw()
        messagebox.showinfo("Already running", message)
        tmp.destroy()
    except tk.TclError:
        print(message, file=sys.stderr)


def _notify_other_game_running(holder: Optional[str]) -> None:
    name = holder or "another game"
    message = f"{name} is already running. Close it before starting Minesweeper."
    try:
        tmp = tk.Tk()
        tmp.withdraw()
        messagebox.showinfo("Another game is running", message)
        tmp.destroy()
    except tk.TclError:
        print(message, file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Minesweeper GUI")
    parser.add_argument("--headless", action="store_true", help="Run without showing the window (for tests).")
    args = parser.parse_args()
    if not single_instance.try_acquire_lock(ACTIVE_GAME_LOCK, "Minesweeper"):
        _notify_other_game_running(single_instance.lock_holder(ACTIVE_GAME_LOCK))
        return
    if not single_instance.try_acquire_lock(LOCK_FILE, "Minesweeper"):
        single_instance.release_lock(ACTIVE_GAME_LOCK)
        _notify_already_running()
        return
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"Could not start Tkinter: {exc}", file=sys.stderr)
        single_instance.release_lock(LOCK_FILE)
        single_instance.release_lock(ACTIVE_GAME_LOCK)
        return
    MinesweeperApp(root, headless=args.headless)
    root.mainloop()


if __name__ == "__main__":
    main()






