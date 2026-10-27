from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk

from arcade.core import scores
from arcade.core.settings import Settings
from arcade.core.ui import CARD_H, CARD_W, GameApp, ScoreSection, draw_card
from arcade.games.solitaire.logic import Klondike, Location

GAP = 14
FAN_DOWN, FAN_UP = 10, 26
TOP = 16


class SolitaireApp(GameApp):
    game_id = "solitaire"
    min_size = (760, 660)

    def __init__(self, root: tk.Tk, **kwargs) -> None:
        self.settings = Settings.named("solitaire", {"draw_count": 1}, choices={"draw_count": (1, 3)})
        self.stats = scores.Tally.named("solitaire_stats")
        self.times = scores.HighScores.named("solitaire_times", lower_is_better=True)
        self.game = Klondike.deal(self.settings["draw_count"])
        self.selected: Location | None = None
        self.started = time.monotonic()
        self.recorded = False
        self.final_time = 0
        self.message = ""
        super().__init__(root, **kwargs)
        self.stats.bump("games")
        self._tick()

    def build(self, parent: ttk.Frame) -> None:
        top = ttk.Frame(parent)
        top.pack(fill="x")
        ttk.Label(top, text=self.t("solitaire.name"), style="Title.TLabel").pack(side="left")
        self.info = ttk.Label(top, style="Badge.TLabel")
        self.info.pack(side="right")
        ttk.Label(top, text=self.t("solitaire.draw")).pack(side="right", padx=(0, 4))
        draw_box = ttk.Combobox(top, values=["1", "3"], state="readonly", width=3)
        draw_box.set(str(self.settings["draw_count"]))
        draw_box.pack(side="right", padx=(0, 12))
        draw_box.bind("<<ComboboxSelected>>", lambda _e: self._set_draw(int(draw_box.get())))

        self.canvas = tk.Canvas(parent, bg=self.palette.panel, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=10)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Double-Button-1>", self._on_double)
        self.canvas.bind("<Configure>", lambda _e: self._draw())

        bottom = ttk.Frame(parent)
        bottom.pack(fill="x")
        self.status = ttk.Label(bottom, style="Status.TLabel")
        self.status.pack(side="left", fill="x", expand=True)
        self.auto_btn = ttk.Button(bottom, text=self.t("solitaire.autocomplete"), command=self.autocomplete)
        self.auto_btn.pack(side="right", padx=(6, 0))
        self.undo_btn = ttk.Button(bottom, text=self.t("button.undo"), command=self.undo)
        self.undo_btn.pack(side="right", padx=(6, 0))
        ttk.Button(bottom, text=self.t("menu.new_game"), style="Accent.TButton", command=self.new_game).pack(
            side="right"
        )
        self.root.bind("<Control-z>", lambda _e: self.undo())

    def _set_draw(self, count: int) -> None:
        self.settings.set("draw_count", count)
        self.new_game()

    def new_game(self) -> None:
        self.game = Klondike.deal(self.settings["draw_count"])
        self.selected = None
        self.started = time.monotonic()
        self.recorded = False
        self.final_time = 0
        self.message = ""
        self.stats.bump("games")
        self.refresh()

    def _elapsed(self) -> int:
        return int(time.monotonic() - self.started)

    def _tick(self) -> None:
        if not self.root.winfo_exists():
            return
        if not self.game.won:
            self._update_info()
        self.root.after(1000, self._tick)

    def _update_info(self) -> None:
        minutes, seconds = divmod(self._elapsed() if not self.recorded else self.final_time, 60)
        self.info.configure(text=self.t("solitaire.info", moves=self.game.moves, time=f"{minutes}:{seconds:02d}"))

    # -- geometry -------------------------------------------------------------
    def _col_x(self, col: int) -> int:
        return GAP + col * (CARD_W + GAP)

    def _tableau_y(self, col: int, index: int) -> int:
        y = TOP + CARD_H + 30
        for i in range(index):
            y += FAN_DOWN if i < self.game.hidden[col] else FAN_UP
        return y

    def _hit(self, x: float, y: float) -> Location | str | None:
        col = int((x - GAP) // (CARD_W + GAP))
        if not 0 <= col < 7 or x - self._col_x(col) > CARD_W:
            return None
        if TOP <= y <= TOP + CARD_H:
            if col == 0:
                return "stock"
            if col == 1:
                return ("waste",)
            if col >= 3:
                return ("foundation", col - 3)
            return None
        pile = self.game.tableau[col]
        base = self._tableau_y(col, 0)
        if y < base:
            return None
        for index in range(len(pile) - 1, -1, -1):
            if y >= self._tableau_y(col, index):
                return ("tableau", col, index) if y <= self._tableau_y(col, index) + CARD_H else None
        return ("tableau", col, 0)

    # -- interaction ----------------------------------------------------------
    def _on_click(self, event: tk.Event) -> None:
        if self.game.won:
            return
        hit = self._hit(event.x, event.y)
        if hit == "stock":
            self.selected = None
            self.game.draw()
            self.play_sound()
        elif hit is None:
            self.selected = None
        elif self.selected is None:
            if self.game.cards_at(hit):
                self.selected = hit
        else:
            dst = hit
            if dst[0] == "tableau":
                dst = ("tableau", dst[1], len(self.game.tableau[dst[1]]))
            if self.game.move(self.selected, dst):
                self.play_sound()
                self.selected = None
            else:
                self.selected = hit if self.game.cards_at(hit) and hit != self.selected else None
        self._after_move()

    def _on_double(self, event: tk.Event) -> None:
        hit = self._hit(event.x, event.y)
        if isinstance(hit, tuple) and hit[0] != "foundation":
            dst = self.game.best_destination(hit)
            if dst is not None:
                self.game.move(hit, dst)
            self.selected = None
            self._after_move()

    def undo(self) -> None:
        if self.game.can_undo() and not self.game.won:
            self.game.undo()
            self.selected = None
            self.refresh()

    def autocomplete(self) -> None:
        if self.game.can_autocomplete():
            self.game.autocomplete()
            self._after_move()

    def _after_move(self) -> None:
        if self.game.won and not self.recorded:
            self.recorded = True
            self.final_time = self._elapsed()
            self.stats.bump("wins")
            self.stats.bump(f"wins_draw{self.game.draw_count}")
            rank = None
            if self.times.qualifies(self.final_time):
                name = self.ask_name()
                if name:
                    rank = self.times.add(name, self.final_time)
            self.message = self.t("solitaire.won", moves=self.game.moves)
            if rank:
                self.message += "  " + self.t("scores.ranked", rank=rank)
        self.refresh()

    # -- drawing --------------------------------------------------------------
    def refresh(self) -> None:
        if not hasattr(self, "canvas"):
            return
        self.undo_btn.state(["!disabled" if self.game.can_undo() and not self.game.won else "disabled"])
        self.auto_btn.state(["!disabled" if self.game.can_autocomplete() else "disabled"])
        self.status.configure(text=self.message or self.t("solitaire.help"))
        self._update_info()
        self._draw()

    def _draw(self) -> None:
        c, p, g = self.canvas, self.palette, self.game
        c.delete("all")
        sel = self.selected

        stock_card = g.stock[-1] if g.stock else None
        draw_card(c, self._col_x(0), TOP, stock_card, p, face_up=False)
        if not g.stock and g.waste:
            c.create_text(self._col_x(0) + CARD_W / 2, TOP + CARD_H / 2, text="↻", fill=p.muted, font=(self.family, 28))

        visible = g.waste[-g.draw_count :] if g.waste else []
        for i, card in enumerate(visible):
            top = i == len(visible) - 1
            draw_card(c, self._col_x(1) + i * 16, TOP, card, p, selected=top and sel == ("waste",))
        if not visible:
            draw_card(c, self._col_x(1), TOP, None, p)

        for i, pile in enumerate(g.foundations):
            x = self._col_x(3 + i)
            if pile:
                draw_card(c, x, TOP, pile[-1], p, selected=sel == ("foundation", i))
            else:
                draw_card(c, x, TOP, None, p)
                symbol = "♠♥♦♣"[i]
                c.create_text(x + CARD_W / 2, TOP + CARD_H / 2, text=symbol, fill=p.border, font=(self.family, 26))

        for col, pile in enumerate(g.tableau):
            x = self._col_x(col)
            if not pile:
                draw_card(c, x, self._tableau_y(col, 0), None, p)
            for index, card in enumerate(pile):
                highlighted = sel is not None and sel[0] == "tableau" and sel[1] == col and index >= sel[2]
                draw_card(
                    c, x, self._tableau_y(col, index), card, p, face_up=g.face_up(col, index), selected=highlighted
                )

    # -- scores -----------------------------------------------------------------
    def score_sections(self) -> list[ScoreSection]:
        stats = self.stats.load()
        times = [(i, e.name, f"{e.score // 60}:{e.score % 60:02d}") for i, e in enumerate(self.times.load(), start=1)]
        stat_rows = [
            (self.t("solitaire.stat.games"), stats.get("games", 0)),
            (self.t("solitaire.stat.wins"), stats.get("wins", 0)),
            (self.t("solitaire.stat.draw1"), stats.get("wins_draw1", 0)),
            (self.t("solitaire.stat.draw3"), stats.get("wins_draw3", 0)),
        ]
        return [
            ScoreSection(
                self.t("solitaire.fastest"),
                (self.t("scores.rank"), self.t("scores.name"), self.t("scores.time")),
                times,
            ),
            ScoreSection(self.t("scores.stats"), (self.t("scores.stat"), self.t("scores.value")), stat_rows),
        ]

    def reset_scores(self) -> None:
        self.stats.clear()
        self.times.clear()
