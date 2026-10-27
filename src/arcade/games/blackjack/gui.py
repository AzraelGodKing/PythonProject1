from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from arcade.core import scores
from arcade.core.chips import Bank, InsufficientChips
from arcade.core.settings import Settings
from arcade.core.ui import CARD_H, CARD_W, GameApp, ScoreSection, Toggle, draw_card
from arcade.games.blackjack.logic import Action, Blackjack, Outcome, Phase, RuleError, basic_strategy, hand_value

STARTING_BANK = 500
CREDIT = 500
CHIP_VALUES = (5, 25, 100)


class BlackjackApp(GameApp):
    game_id = "blackjack"
    min_size = (900, 680)

    def __init__(self, root: tk.Tk, **kwargs) -> None:
        self.settings = Settings.named(
            "blackjack", {"bank": STARTING_BANK, "bet": 25, "show_totals": True, "show_hints": False}
        )
        self.table = Blackjack(bank=Bank(self.settings["bank"], credit=CREDIT))
        self.leaderboard = scores.HighScores.named("blackjack_bankroll")
        self.stats = scores.Tally.named("blackjack_stats")
        self.bet_var = tk.IntVar(value=self.settings["bet"])
        self.show_totals = tk.BooleanVar(value=self.settings["show_totals"])
        self.show_hints = tk.BooleanVar(value=self.settings["show_hints"])
        self.message = ""
        super().__init__(root, **kwargs)
        self.message = self.t("blackjack.place_bet")
        self.refresh()

    # -- layout -----------------------------------------------------------
    def build(self, parent: ttk.Frame) -> None:
        top = ttk.Frame(parent)
        top.pack(fill="x")
        ttk.Label(top, text=self.t("blackjack.name"), style="Title.TLabel").pack(side="left")
        self.bank_label = ttk.Label(top, style="Badge.TLabel")
        self.bank_label.pack(side="right")

        self.canvas = tk.Canvas(parent, bg=self.palette.panel, highlightthickness=0, height=400)
        self.canvas.pack(fill="both", expand=True, pady=10)
        self.canvas.bind("<Configure>", lambda _e: self._draw_table())

        self.status = ttk.Label(parent, style="Status.TLabel", anchor="w", justify="left")
        self.status.pack(fill="x")

        controls = ttk.Frame(parent)
        controls.pack(fill="x", pady=(10, 0))
        bet_box = ttk.Frame(controls)
        bet_box.pack(side="left")
        ttk.Label(bet_box, text=self.t("blackjack.bet")).pack(side="left", padx=(0, 6))
        self.bet_spin = ttk.Spinbox(
            bet_box, from_=self.table.rules.min_bet, to=10_000, increment=5, textvariable=self.bet_var, width=7
        )
        self.bet_spin.pack(side="left")
        for value in CHIP_VALUES:
            ttk.Button(bet_box, text=f"+{value}", width=5, command=lambda v=value: self._add_bet(v)).pack(
                side="left", padx=2
            )
        self.deal_btn = ttk.Button(bet_box, text=self.t("blackjack.deal"), style="Accent.TButton", command=self.deal)
        self.deal_btn.pack(side="left", padx=(8, 0))

        actions = ttk.Frame(controls)
        actions.pack(side="right")
        self.action_buttons: dict[Action, ttk.Button] = {}
        for action, key in ((Action.HIT, "h"), (Action.STAND, "s"), (Action.DOUBLE, "d"), (Action.SPLIT, "p")):
            btn = ttk.Button(actions, text=self.t(f"blackjack.{action.value}"), command=lambda a=action: self.act(a))
            btn.pack(side="left", padx=2)
            self.action_buttons[action] = btn
            self.root.bind(f"<KeyPress-{key}>", lambda _e, a=action: self.act(a))
        self.hint_btn = ttk.Button(actions, text=self.t("button.hint"), command=self.hint)
        self.hint_btn.pack(side="left", padx=(8, 2))

        self.insurance_row = ttk.Frame(parent)
        ttk.Label(self.insurance_row, text=self.t("blackjack.insurance_offer")).pack(side="left")
        self.insure_yes = ttk.Button(self.insurance_row, text=self.t("button.yes"), command=lambda: self.insure(True))
        self.insure_yes.pack(side="left", padx=4)
        ttk.Button(self.insurance_row, text=self.t("button.no"), command=lambda: self.insure(False)).pack(side="left")

        bottom = ttk.Frame(parent)
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Button(bottom, text=self.t("blackjack.cash_out"), command=self.cash_out).pack(side="right")
        self.root.bind("<Return>", lambda _e: self.deal())

    def extra_options(self) -> list[Toggle]:
        return [
            Toggle("blackjack.option.totals", self.show_totals, self._save_toggles),
            Toggle("blackjack.option.hints", self.show_hints, self._save_toggles),
        ]

    def _save_toggles(self) -> None:
        self.settings.set("show_totals", self.show_totals.get())
        self.settings.set("show_hints", self.show_hints.get())
        self.refresh()

    # -- actions ----------------------------------------------------------
    def _add_bet(self, amount: int) -> None:
        self.bet_var.set(self._bet() + amount)

    def _bet(self) -> int:
        try:
            return max(0, int(self.bet_var.get()))
        except (tk.TclError, ValueError):
            return 0

    def new_game(self) -> None:
        in_play = self.table.phase in (Phase.INSURANCE, Phase.PLAYER)
        if in_play and not messagebox.askyesno(
            self.t("menu.new_game"), self.t("blackjack.forfeit_confirm"), parent=self.root
        ):
            return
        self.table = Blackjack(bank=self.table.bank)
        self.message = self.t("blackjack.place_bet")
        self.refresh()

    def deal(self) -> None:
        if self.table.phase in (Phase.INSURANCE, Phase.PLAYER):
            return
        bet = self._bet()
        try:
            self.table.deal(bet)
        except InsufficientChips:
            self.message = self.t("blackjack.no_chips", credit=CREDIT)
        except RuleError:
            self.message = self.t("blackjack.min_bet", amount=self.table.rules.min_bet)
        else:
            self.settings.set("bet", bet)
            self.play_sound()
            self._after_move()
        self.refresh()

    def insure(self, take: bool) -> None:
        if self.table.phase is not Phase.INSURANCE:
            return
        try:
            self.table.insurance(take)
        except InsufficientChips:
            self.message = self.t("blackjack.no_chips", credit=CREDIT)
        self._after_move()
        self.refresh()

    def act(self, action: Action) -> None:
        if action not in self.table.available_actions():
            return
        {
            Action.HIT: self.table.hit,
            Action.STAND: self.table.stand,
            Action.DOUBLE: self.table.double,
            Action.SPLIT: self.table.split,
        }[action]()
        self._after_move()
        self.refresh()

    def hint(self) -> None:
        hand, up = self.table.current, self.table.dealer_up
        if hand is None or up is None:
            return
        advice = basic_strategy(hand, up, self.table.available_actions())
        self.message = self.t("blackjack.hint", action=self.t(f"blackjack.{advice.value}"))
        self.refresh()

    def cash_out(self) -> None:
        if self.table.phase in (Phase.INSURANCE, Phase.PLAYER):
            return
        balance = self.table.bank.balance
        if balance > 0 and self.leaderboard.qualifies(balance):
            name = self.ask_name()
            if name:
                rank = self.leaderboard.add(name, balance)
                if rank:
                    self.message = self.t("scores.ranked", rank=rank)
        self.table = Blackjack(bank=Bank(STARTING_BANK, credit=CREDIT))
        self.settings.set("bank", STARTING_BANK)
        self.refresh()

    def _after_move(self) -> None:
        table = self.table
        if table.phase is Phase.INSURANCE:
            self.message = self.t("blackjack.insurance_offer")
        elif table.phase is Phase.PLAYER:
            hand = table.current
            assert hand is not None
            prefix = self.t("blackjack.hand_n", n=table.active + 1) + " " if len(table.hands) > 1 else ""
            self.message = prefix + self.t("blackjack.your_move")
        elif table.phase is Phase.DONE:
            self._record_round()

    def _record_round(self) -> None:
        table = self.table
        lines = []
        for i, hand in enumerate(table.hands, start=1):
            assert hand.outcome is not None
            label = self.t("blackjack.hand_n", n=i) + ": " if len(table.hands) > 1 else ""
            lines.append(label + self.t(f"blackjack.outcome.{hand.outcome.value}", amount=abs(hand.net)))
            self.stats.bump("hands")
            key = {
                Outcome.BLACKJACK: "blackjacks",
                Outcome.WIN: "wins",
                Outcome.PUSH: "pushes",
            }.get(hand.outcome, "losses")
            self.stats.bump(key)
        if table.insurance_bet:
            won = table.insurance_payout > 0
            lines.append(self.t("blackjack.insurance_won" if won else "blackjack.insurance_lost"))
        self.message = "\n".join(lines)
        self.stats.set_max("peak_bank", table.bank.balance)
        self.settings.set("bank", table.bank.balance)

    # -- drawing ----------------------------------------------------------
    def refresh(self) -> None:
        if not hasattr(self, "canvas"):
            return
        table = self.table
        self.bank_label.configure(text=self.t("blackjack.bank", amount=table.bank.balance))
        betting = table.phase in (Phase.BETTING, Phase.DONE)
        self.deal_btn.state(["!disabled" if betting else "disabled"])
        self.bet_spin.state(["!disabled" if betting else "disabled"])
        available = table.available_actions()
        for action, btn in self.action_buttons.items():
            btn.state(["!disabled" if action in available else "disabled"])
        self.hint_btn.state(["!disabled" if available else "disabled"])
        if table.phase is Phase.INSURANCE:
            self.insurance_row.pack(fill="x", pady=(8, 0))
            self.insure_yes.state(["!disabled" if table.can_insure() else "disabled"])
        else:
            self.insurance_row.pack_forget()
        message = self.message
        if self.show_hints.get() and table.current is not None and table.dealer_up is not None:
            advice = basic_strategy(table.current, table.dealer_up, available)
            message += "  " + self.t("blackjack.hint", action=self.t(f"blackjack.{advice.value}"))
        self.status.configure(text=message)
        self._draw_table()

    def _draw_table(self) -> None:
        c, p, table = self.canvas, self.palette, self.table
        c.delete("all")
        width = max(c.winfo_width(), 600)
        reveal = table.hole_revealed
        c.create_text(20, 16, text=self.t("blackjack.dealer"), anchor="w", fill=p.muted, font=(self.family, 11, "bold"))
        for i, card in enumerate(table.dealer):
            draw_card(c, 20 + i * (CARD_W + 8), 32, card, p, face_up=reveal or i == 0)
        if table.dealer and self.show_totals.get():
            shown = table.dealer if reveal else table.dealer[:1]
            c.create_text(
                30 + len(table.dealer) * (CARD_W + 8),
                32 + CARD_H / 2,
                anchor="w",
                fill=p.text,
                text=self._total_text(shown),
                font=(self.family, 12, "bold"),
            )

        y = 32 + CARD_H + 50
        c.create_text(
            20, y - 16, text=self.t("blackjack.you"), anchor="w", fill=p.muted, font=(self.family, 11, "bold")
        )
        slot = max(len(table.hands), 1)
        slot_width = (width - 20) / slot
        for index, hand in enumerate(table.hands):
            x0 = 20 + index * slot_width
            active = table.phase is Phase.PLAYER and index == table.active
            step = min(CARD_W + 8, (slot_width - CARD_W - 20) / max(len(hand.cards) - 1, 1))
            for j, card in enumerate(hand.cards):
                draw_card(c, x0 + j * step, y, card, p, selected=active)
            label = self.t("blackjack.bet_amount", amount=hand.bet)
            if self.show_totals.get():
                label = f"{self._total_text(hand.cards)}   {label}"
            if hand.outcome is not None:
                label += "   " + self.t(f"blackjack.result.{hand.outcome.value}")
            colour = p.accent if active else p.text
            if hand.outcome in (Outcome.WIN, Outcome.BLACKJACK):
                colour = p.good
            elif hand.outcome in (Outcome.LOSE, Outcome.BUST):
                colour = p.bad
            c.create_text(x0, y + CARD_H + 16, text=label, anchor="w", fill=colour, font=(self.family, 11, "bold"))

    def _total_text(self, cards) -> str:
        total, soft = hand_value(cards)
        return self.t("blackjack.soft_total", total=total) if soft and total < 21 else str(total)

    # -- scores -----------------------------------------------------------
    def score_sections(self) -> list[ScoreSection]:
        stats = self.stats.load()
        stat_rows = [
            (self.t(f"blackjack.stat.{key}"), stats.get(key, 0))
            for key in ("hands", "wins", "blackjacks", "pushes", "losses", "peak_bank")
        ]
        return [
            ScoreSection(
                self.t("blackjack.best_bankrolls"),
                (self.t("scores.rank"), self.t("scores.name"), self.t("blackjack.chips")),
                [(i, e.name, e.score) for i, e in enumerate(self.leaderboard.load(), start=1)],
            ),
            ScoreSection(self.t("scores.stats"), (self.t("scores.stat"), self.t("scores.value")), stat_rows),
        ]

    def reset_scores(self) -> None:
        self.leaderboard.clear()
        self.stats.clear()
