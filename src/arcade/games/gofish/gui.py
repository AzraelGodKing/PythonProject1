from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from arcade.core import scores
from arcade.core.cards import Card
from arcade.core.settings import Settings
from arcade.core.ui import CARD_H, CARD_W, GameApp, ScoreSection, Toggle, draw_card
from arcade.games.gofish.logic import AI, PLAYER, GoFish

AI_DELAY_MS = 800
LOG_LINES = 200


class GoFishApp(GameApp):
    game_id = "gofish"
    min_size = (900, 640)

    def __init__(self, root: tk.Tk, **kwargs) -> None:
        self.settings = Settings.named("gofish", {"smart_ai": True})
        self.stats = scores.Tally.named("gofish_stats")
        self.game = GoFish.deal(smart_ai=self.settings["smart_ai"])
        self._pending: str | None = None
        self._recorded = False
        self._card_boxes: list[tuple[float, float, float, float, str]] = []
        super().__init__(root, **kwargs)

    def build(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        ttk.Label(parent, text=self.t("gofish.name"), style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.canvas = tk.Canvas(parent, bg=self.palette.panel, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", pady=10)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Configure>", lambda _e: self._draw())

        side = ttk.Frame(parent, style="Panel.TFrame", padding=10)
        side.grid(row=0, column=1, rowspan=3, sticky="ns", padx=(12, 0))
        ttk.Label(side, text=self.t("gofish.log"), style="Heading.TLabel").pack(anchor="w")
        self.log_box = tk.Listbox(
            side,
            width=38,
            height=24,
            bg=self.palette.bg,
            fg=self.palette.text,
            highlightthickness=0,
            selectbackground=self.palette.button,
            selectforeground=self.palette.button_text,
            borderwidth=0,
        )
        self.log_box.pack(fill="both", expand=True, pady=(6, 0))
        ttk.Button(side, text=self.t("menu.new_game"), style="Accent.TButton", command=self.new_game).pack(
            fill="x", pady=(10, 0)
        )

        self.status = ttk.Label(parent, style="Status.TLabel", anchor="center")
        self.status.grid(row=2, column=0, sticky="ew")

    def extra_options(self) -> list[Toggle]:
        var = tk.BooleanVar(value=self.settings["smart_ai"])

        def changed() -> None:
            self.settings.set("smart_ai", var.get())
            self.game.smart_ai = var.get()

        return [Toggle("gofish.option.smart_ai", var, changed)]

    def new_game(self) -> None:
        if self._pending:
            self.root.after_cancel(self._pending)
            self._pending = None
        self.game = GoFish.deal(smart_ai=self.settings["smart_ai"])
        self._recorded = False
        self.refresh()

    # -- play -----------------------------------------------------------------
    def _on_click(self, event: tk.Event) -> None:
        if self.game.turn != PLAYER or self.game.over:
            return
        for x0, y0, x1, y1, rank in reversed(self._card_boxes):
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                self.ask(rank)
                return

    def ask(self, rank: str) -> None:
        if self.game.turn != PLAYER or self.game.over or rank not in self.game.ranks_in_hand(PLAYER):
            return
        self.game.ask(rank)
        self.play_sound()
        self._after_move()

    def _ai_step(self) -> None:
        self._pending = None
        if self.game.turn == AI and not self.game.over:
            self.game.ai_turn()
            self._after_move()

    def _after_move(self) -> None:
        if self.game.over and not self._recorded:
            self._recorded = True
            result = self.game.winner
            self.stats.bump("games", {PLAYER: "wins", AI: "losses"}.get(result or "", "draws"))
        elif self.game.turn == AI and self._pending is None:
            self._pending = self.root.after(AI_DELAY_MS, self._ai_step)
        self.refresh()

    # -- drawing --------------------------------------------------------------
    def _describe(self, key: str, params: dict) -> str:
        # Each event has a "you" and a "computer" wording so translations can differ.
        return self.t(f"{key}.{params['who']}", **params)

    def refresh(self) -> None:
        if not hasattr(self, "canvas"):
            return
        self.log_box.delete(0, "end")
        for key, params in self.game.log[-LOG_LINES:]:
            self.log_box.insert("end", self._describe(key, params))
        self.log_box.see("end")
        g = self.game
        if g.over:
            outcome = {PLAYER: "gofish.won", AI: "gofish.lost"}.get(g.winner or "", "gofish.tie")
            text = self.t(outcome, mine=len(g.books[PLAYER]), theirs=len(g.books[AI]))
        elif g.turn == PLAYER:
            text = self.t("gofish.your_turn")
        else:
            text = self.t("gofish.ai_turn")
        self.status.configure(text=text)
        self._draw()

    def _draw(self) -> None:
        c, p, g = self.canvas, self.palette, self.game
        c.delete("all")
        width = max(c.winfo_width(), 500)
        bold = (self.family, 11, "bold")

        c.create_text(
            16, 14, anchor="w", fill=p.muted, font=bold, text=self.t("gofish.computer_hand", count=len(g.hands[AI]))
        )
        step = min(24, (width - 120) / max(len(g.hands[AI]), 1))
        for i in range(len(g.hands[AI])):
            draw_card(
                c, 16 + i * step, 30, Card("A", "spades"), p, face_up=False, width=CARD_W - 16, height=CARD_H - 24
            )
        self._draw_books(AI, 30 + CARD_H)

        pond_x = width - CARD_W - 20
        draw_card(c, pond_x, 30, Card("A", "spades") if g.pond else None, p, face_up=False)
        c.create_text(pond_x + CARD_W / 2, 40 + CARD_H, fill=p.muted, text=self.t("gofish.pond", count=len(g.pond)))

        base = 30 + CARD_H + 110
        c.create_text(16, base - 14, anchor="w", fill=p.muted, font=bold, text=self.t("gofish.your_hand"))
        hand = sorted(g.hands[PLAYER], key=lambda card: (card.rank_index, card.suit))
        step = min(CARD_W + 4, (width - CARD_W - 32) / max(len(hand) - 1, 1))
        self._card_boxes = []
        active = g.turn == PLAYER and not g.over
        for i, card in enumerate(hand):
            x = 16 + i * step
            draw_card(c, x, base, card, p)
            self._card_boxes.append((x, base, x + CARD_W, base + CARD_H, card.rank))
        if active and hand:
            c.create_text(16, base + CARD_H + 16, anchor="w", fill=p.accent, text=self.t("gofish.click_hint"))
        self._draw_books(PLAYER, base + CARD_H + 36)

    def _draw_books(self, who: str, y: float) -> None:
        books = self.game.books[who]
        label = self.t("gofish.books", count=len(books))
        text = label + ("  " + " ".join(books) if books else "")
        self.canvas.create_text(16, y + 12, anchor="w", fill=self.palette.text, font=(self.family, 11), text=text)

    def score_sections(self) -> list[ScoreSection]:
        stats = self.stats.load()
        rows = [(self.t(f"scores.{key}"), stats.get(key, 0)) for key in ("games", "wins", "losses", "draws")]
        return [ScoreSection(self.t("scores.stats"), (self.t("scores.stat"), self.t("scores.value")), rows)]

    def reset_scores(self) -> None:
        self.stats.clear()
