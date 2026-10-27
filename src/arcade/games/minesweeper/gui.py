from __future__ import annotations

import sys
import time
import tkinter as tk
from tkinter import ttk

from arcade.core import scores
from arcade.core.settings import Settings
from arcade.core.ui import GameApp, ScoreSection
from arcade.games.minesweeper.logic import DIFFICULTIES, Board, State

CELL = 28


class MinesweeperApp(GameApp):
    game_id = "minesweeper"
    min_size = (560, 520)

    def __init__(self, root: tk.Tk, **kwargs) -> None:
        self.settings = Settings.named(
            "minesweeper", {"difficulty": "beginner"}, choices={"difficulty": tuple(DIFFICULTIES)}
        )
        self.board = Board.for_difficulty(self.settings["difficulty"])
        self.cursor = (0, 0)
        self.started: float | None = None
        self.finished_in: int | None = None
        self.message = ""
        super().__init__(root, **kwargs)
        self._tick()

    def best_times(self, difficulty: str) -> scores.HighScores:
        return scores.HighScores.named(f"minesweeper_{difficulty}", lower_is_better=True)

    def build(self, parent: ttk.Frame) -> None:
        top = ttk.Frame(parent)
        top.pack(fill="x")
        ttk.Label(top, text=self.t("minesweeper.name"), style="Title.TLabel").pack(side="left")
        names = list(DIFFICULTIES)
        box = ttk.Combobox(
            top, values=[self.t(f"minesweeper.difficulty.{d}") for d in names], state="readonly", width=14
        )
        box.current(names.index(self.settings["difficulty"]))
        box.pack(side="right")
        box.bind("<<ComboboxSelected>>", lambda _e: self._set_difficulty(names[box.current()]))

        info = ttk.Frame(parent)
        info.pack(fill="x", pady=(8, 0))
        self.mines_label = ttk.Label(info, style="Badge.TLabel")
        self.mines_label.pack(side="left")
        self.timer_label = ttk.Label(info, style="Badge.TLabel")
        self.timer_label.pack(side="right")
        self.best_label = ttk.Label(info, style="Muted.TLabel")
        self.best_label.pack(side="right", padx=10)

        holder = ttk.Frame(parent)
        holder.pack(fill="both", expand=True, pady=10)
        self.canvas = tk.Canvas(holder, bg=self.palette.bg, highlightthickness=0)
        self.canvas.pack(anchor="center")
        self.canvas.bind("<Button-1>", lambda e: self._click(e, "reveal"))
        # Right click is Button-3 on Windows/Linux and Button-2 on macOS.
        self.canvas.bind("<Button-2>" if sys.platform == "darwin" else "<Button-3>", lambda e: self._click(e, "flag"))
        self.canvas.bind(
            "<Button-2>" if sys.platform != "darwin" else "<Control-Button-1>", lambda e: self._click(e, "chord")
        )

        for key, delta in (("Up", (-1, 0)), ("Down", (1, 0)), ("Left", (0, -1)), ("Right", (0, 1))):
            self.root.bind(f"<{key}>", lambda _e, d=delta: self._move_cursor(*d))
        self.root.bind("<space>", lambda _e: self._act("reveal", *self.cursor))
        self.root.bind("<KeyPress-f>", lambda _e: self._act("flag", *self.cursor))

        self.status = ttk.Label(parent, style="Status.TLabel", anchor="center")
        self.status.pack(fill="x")

    def _set_difficulty(self, name: str) -> None:
        self.settings.set("difficulty", name)
        self.new_game()

    def new_game(self) -> None:
        self.board = Board.for_difficulty(self.settings["difficulty"])
        self.cursor = (0, 0)
        self.started = None
        self.finished_in = None
        self.message = ""
        self.refresh()

    # -- timer -------------------------------------------------------------------
    def elapsed(self) -> int:
        if self.finished_in is not None:
            return self.finished_in
        return int(time.monotonic() - self.started) if self.started else 0

    def _tick(self) -> None:
        if not self.root.winfo_exists():
            return
        if hasattr(self, "timer_label"):
            self.timer_label.configure(text=f"⏱ {self.elapsed():03d}")
        self.root.after(500, self._tick)

    # -- input ---------------------------------------------------------------------
    def _click(self, event: tk.Event, action: str) -> None:
        r, c = int(event.y // CELL), int(event.x // CELL)
        if 0 <= r < self.board.rows and 0 <= c < self.board.cols:
            self.cursor = (r, c)
            self._act(action, r, c)

    def _move_cursor(self, dr: int, dc: int) -> None:
        r, c = self.cursor
        self.cursor = (min(max(r + dr, 0), self.board.rows - 1), min(max(c + dc, 0), self.board.cols - 1))
        self._draw()

    def _act(self, action: str, r: int, c: int) -> None:
        board = self.board
        if board.over:
            return
        if action == "flag":
            board.toggle_flag(r, c)
        elif action == "chord" or (action == "reveal" and board.cells[r][c].revealed):
            board.chord(r, c)
        else:
            board.reveal(r, c)
        if self.started is None and board.state is not State.READY:
            self.started = time.monotonic()
        if board.over:
            self._finish()
        self.refresh()

    def _finish(self) -> None:
        self.finished_in = self.elapsed()
        if self.board.state is State.LOST:
            self.message = self.t("minesweeper.lost")
            return
        self.message = self.t("minesweeper.won", seconds=self.finished_in)
        table = self.best_times(self.settings["difficulty"])
        if table.qualifies(self.finished_in):
            name = self.ask_name()
            if name:
                rank = table.add(name, self.finished_in)
                if rank:
                    self.message += "  " + self.t("scores.ranked", rank=rank)

    # -- drawing ---------------------------------------------------------------------
    def refresh(self) -> None:
        if not hasattr(self, "canvas"):
            return
        self.canvas.configure(width=self.board.cols * CELL, height=self.board.rows * CELL)
        self.mines_label.configure(text=f"✹ {self.board.mines_left}")
        best = self.best_times(self.settings["difficulty"]).best()
        self.best_label.configure(
            text=self.t("minesweeper.best", seconds=best.score) if best else self.t("minesweeper.best_none")
        )
        self.status.configure(text=self.message or self.t("minesweeper.help"))
        self._draw()

    def _draw(self) -> None:
        c, p, board = self.canvas, self.palette, self.board
        c.delete("all")
        for r, row in enumerate(board.cells):
            for col, cell in enumerate(row):
                x, y = col * CELL, r * CELL
                show_mine = cell.mine and (board.state is State.LOST)
                if cell.revealed or show_mine:
                    fill = p.bad if (r, col) == board.exploded else p.panel
                    c.create_rectangle(x, y, x + CELL, y + CELL, fill=fill, outline=p.border)
                    if cell.mine:
                        c.create_text(x + CELL / 2, y + CELL / 2, text="✹", fill=p.text, font=(self.family, 13, "bold"))
                    elif cell.adjacent:
                        c.create_text(
                            x + CELL / 2,
                            y + CELL / 2,
                            text=str(cell.adjacent),
                            fill=p.digits[cell.adjacent - 1],
                            font=(self.family, 13, "bold"),
                        )
                else:
                    # Unopened squares look raised: a lighter top-left edge on the border colour.
                    c.create_rectangle(x, y, x + CELL, y + CELL, fill=p.border, outline=p.bg)
                    c.create_line(x + 1, y + CELL - 2, x + 1, y + 1, x + CELL - 2, y + 1, fill=p.muted)
                    if cell.flagged:
                        wrong = board.state is State.LOST and not cell.mine
                        c.create_text(
                            x + CELL / 2,
                            y + CELL / 2,
                            text="✗" if wrong else "⚑",
                            fill=p.warn,
                            font=(self.family, 13, "bold"),
                        )
        r, col = self.cursor
        c.create_rectangle(
            col * CELL + 1, r * CELL + 1, (col + 1) * CELL - 1, (r + 1) * CELL - 1, outline=p.accent, width=2
        )

    def score_sections(self) -> list[ScoreSection]:
        headers = (self.t("scores.rank"), self.t("scores.name"), self.t("scores.seconds"))
        return [
            ScoreSection(
                self.t(f"minesweeper.difficulty.{name}"),
                headers,
                [(i, e.name, e.score) for i, e in enumerate(self.best_times(name).load(), start=1)],
            )
            for name in DIFFICULTIES
        ]

    def reset_scores(self) -> None:
        for name in DIFFICULTIES:
            self.best_times(name).clear()
