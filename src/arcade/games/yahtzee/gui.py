from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from arcade.core import scores
from arcade.core.ui import GameApp, ScoreSection
from arcade.games.yahtzee.logic import CATEGORIES, ROLLS_PER_TURN, UPPER_BONUS_THRESHOLD, Yahtzee

PIPS = {
    1: [(1, 1)],
    2: [(0, 0), (2, 2)],
    3: [(0, 0), (1, 1), (2, 2)],
    4: [(0, 0), (0, 2), (2, 0), (2, 2)],
    5: [(0, 0), (0, 2), (1, 1), (2, 0), (2, 2)],
    6: [(0, 0), (1, 0), (2, 0), (0, 2), (1, 2), (2, 2)],
}
DIE = 64
ROLL_FRAMES = 6


class YahtzeeApp(GameApp):
    game_id = "yahtzee"
    min_size = (820, 640)

    def __init__(self, root: tk.Tk, **kwargs) -> None:
        self.game = Yahtzee()
        self.leaderboard = scores.HighScores.named("yahtzee")
        self.message = ""
        self._animating = 0
        super().__init__(root, **kwargs)

    def build(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)
        ttk.Label(parent, text=self.t("yahtzee.name"), style="Title.TLabel").grid(row=0, column=0, sticky="nw")

        dice_panel = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        dice_panel.grid(row=1, column=0, sticky="nsew", pady=10)
        self.dice_canvas = tk.Canvas(
            dice_panel, width=5 * (DIE + 16), height=DIE + 30, bg=self.palette.panel, highlightthickness=0
        )
        self.dice_canvas.pack()
        self.dice_canvas.bind("<Button-1>", self._on_die_click)
        for n in range(5):
            self.root.bind(str(n + 1), lambda _e, i=n: self.toggle(i))
        self.roll_btn = ttk.Button(dice_panel, style="Accent.TButton", command=self.roll)
        self.roll_btn.pack(pady=(10, 0))
        self.root.bind("<space>", lambda _e: self.roll())
        self.status = ttk.Label(dice_panel, style="Status.TLabel", anchor="center", wraplength=420)
        self.status.pack(fill="x", pady=(10, 0))

        card = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        card.grid(row=0, column=1, rowspan=3, sticky="ns", padx=(12, 0))
        self.category_buttons: dict[str, ttk.Button] = {}
        self.category_values: dict[str, ttk.Label] = {}
        row = 0
        for category in CATEGORIES:
            if category == "three_kind":
                self.bonus_label = ttk.Label(card, style="PanelMuted.TLabel")
                self.bonus_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(2, 8))
                row += 1
            btn = ttk.Button(
                card, text=self.t(f"yahtzee.cat.{category}"), width=18, command=lambda c=category: self.score(c)
            )
            btn.grid(row=row, column=0, sticky="ew", pady=1)
            value = ttk.Label(card, style="Panel.TLabel", width=6, anchor="e")
            value.grid(row=row, column=1, sticky="e", padx=(8, 0))
            self.category_buttons[category] = btn
            self.category_values[category] = value
            row += 1
        self.total_label = ttk.Label(card, style="Heading.TLabel")
        self.total_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def new_game(self) -> None:
        self.game = Yahtzee()
        self.message = ""
        self.refresh()

    def roll(self) -> None:
        if self._animating or not self.game.roll():
            return
        self.play_sound()
        self._animating = ROLL_FRAMES
        self._animate()

    def _animate(self) -> None:
        if not self.root.winfo_exists():
            return
        self._animating -= 1
        if self._animating > 0:
            self._draw_dice(scramble=True)
            self.root.after(45, self._animate)
        else:
            self.refresh()

    def toggle(self, index: int) -> None:
        self.game.toggle_hold(index)
        self.refresh()

    def _on_die_click(self, event: tk.Event) -> None:
        index = int(event.x // (DIE + 16))
        if 0 <= index < 5:
            self.toggle(index)

    def score(self, category: str) -> None:
        if self._animating or not self.game.can_score(category):
            return
        points = self.game.choose(category)
        self.message = self.t("yahtzee.scored", points=points, category=self.t(f"yahtzee.cat.{category}"))
        if self.game.over:
            self._finish()
        self.refresh()

    def _finish(self) -> None:
        total = self.game.total
        self.message = self.t("yahtzee.final", total=total)
        if self.leaderboard.qualifies(total):
            name = self.ask_name()
            if name:
                rank = self.leaderboard.add(name, total)
                if rank:
                    self.message += "  " + self.t("scores.ranked", rank=rank)

    # -- drawing --------------------------------------------------------------
    def refresh(self) -> None:
        if not hasattr(self, "dice_canvas"):
            return
        g = self.game
        self._draw_dice()
        if g.over:
            self.roll_btn.configure(text=self.t("menu.new_game"), command=self.new_game)
            self.roll_btn.state(["!disabled"])
        else:
            self.roll_btn.configure(
                text=self.t("yahtzee.roll", left=g.rolls_left, total=ROLLS_PER_TURN), command=self.roll
            )
            self.roll_btn.state(["!disabled" if g.rolls_left else "disabled"])
        hint = self.t("yahtzee.hold_hint") if g.turn_started and g.rolls_left else self.t("yahtzee.pick_hint")
        self.status.configure(text=self.message or (hint if g.turn_started else self.t("yahtzee.roll_hint")))
        for category in CATEGORIES:
            scored = g.card[category]
            btn, label = self.category_buttons[category], self.category_values[category]
            if scored is not None:
                btn.state(["disabled"])
                label.configure(text=str(scored), style="Panel.TLabel")
            elif g.can_score(category):
                btn.state(["!disabled"])
                label.configure(text=str(g.potential(category)), style="Good.TLabel")
            else:
                btn.state(["disabled"])
                label.configure(text="", style="Panel.TLabel")
        self.bonus_label.configure(
            text=self.t("yahtzee.upper", total=g.upper_total, target=UPPER_BONUS_THRESHOLD, bonus=g.upper_bonus)
        )
        total = self.t("yahtzee.total", total=g.total)
        if g.yahtzee_bonus:
            total += "  " + self.t("yahtzee.bonus", bonus=g.yahtzee_bonus)
        self.total_label.configure(text=total)

    def _draw_dice(self, scramble: bool = False) -> None:
        c, p, g = self.dice_canvas, self.palette, self.game
        c.delete("all")
        for i, value in enumerate(g.dice):
            if scramble and not g.held[i]:
                value = g.rng.randint(1, 6)
            x, y = 8 + i * (DIE + 16), 8
            held = g.held[i]
            c.create_rectangle(
                x, y, x + DIE, y + DIE, fill=p.card_face, outline=p.accent if held else p.border, width=4 if held else 1
            )
            if not g.turn_started:
                continue
            step = DIE / 4
            for row, col in PIPS[value]:
                cx, cy = x + step * (col + 1), y + step * (row + 1)
                c.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=p.suit_black, outline="")
            if held:
                c.create_text(x + DIE / 2, y + DIE + 12, text=self.t("yahtzee.held"), fill=p.accent)

    def score_sections(self) -> list[ScoreSection]:
        rows = [(i, e.name, e.score) for i, e in enumerate(self.leaderboard.load(), start=1)]
        return [
            ScoreSection(
                self.t("yahtzee.high_scores"),
                (self.t("scores.rank"), self.t("scores.name"), self.t("scores.score")),
                rows,
            )
        ]

    def reset_scores(self) -> None:
        self.leaderboard.clear()
