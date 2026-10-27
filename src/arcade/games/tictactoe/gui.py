from __future__ import annotations

import random
import tkinter as tk
from tkinter import ttk

from arcade.core import scores
from arcade.core.settings import Settings
from arcade.core.ui import GameApp, ScoreSection, Toggle
from arcade.games.tictactoe import logic
from arcade.games.tictactoe.logic import DIFFICULTIES, PERSONALITIES, Game, Match, Opponent
from arcade.games.tictactoe.sim import CHOICES, parse_opponent

HUMAN, AI = "X", "O"
MATCH_LENGTHS = (1, 3, 5, 7)
AI_DELAY_MS = 350
CELL = 120


class TicTacToeApp(GameApp):
    game_id = "tictactoe"
    min_size = (820, 560)

    def __init__(self, root: tk.Tk, **kwargs) -> None:
        self.settings = Settings.named(
            "tictactoe",
            {"difficulty": "normal", "personality": "balanced", "best_of": 3, "humanish": True, "watch_x": "hard"},
            choices={
                "difficulty": DIFFICULTIES,
                "personality": PERSONALITIES,
                "best_of": MATCH_LENGTHS,
                "watch_x": CHOICES,
            },
        )
        self.stats = scores.Tally.named("tictactoe_stats")
        self.rng = random.Random()
        self.match = Match(self.settings["best_of"])
        self.game = Game(starter=HUMAN)
        self.watching = False
        self.games_started = 1
        self.hint_cell: int | None = None
        self._pending: str | None = None
        self.message = ""
        super().__init__(root, **kwargs)
        self._set_message_for_turn()

    # -- opponents ----------------------------------------------------------
    def opponent(self) -> Opponent:
        rate = logic.DEFAULT_ERROR_RATE if self.settings["humanish"] else 0.0
        return Opponent(self.settings["difficulty"], self.settings["personality"], rate)

    def _player(self, symbol: str) -> Opponent | None:
        if self.watching:
            return parse_opponent(self.settings["watch_x"]) if symbol == "X" else self.opponent()
        return None if symbol == HUMAN else self.opponent()

    # -- layout ---------------------------------------------------------------
    def build(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        ttk.Label(parent, text=self.t("tictactoe.name"), style="Title.TLabel").grid(row=0, column=0, sticky="w")

        self.canvas = tk.Canvas(parent, width=CELL * 3, height=CELL * 3, bg=self.palette.panel, highlightthickness=0)
        self.canvas.grid(row=1, column=0, pady=12)
        self.canvas.bind("<Button-1>", self._on_click)
        for n in range(9):
            self.root.bind(str(n + 1), lambda _e, i=n: self.human_move(i))

        self.status = ttk.Label(parent, style="Status.TLabel", anchor="center")
        self.status.grid(row=2, column=0, sticky="ew")

        side = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        side.grid(row=0, column=1, rowspan=3, sticky="ns", padx=(12, 0))

        def labelled_combo(row: int, label_key: str, values: list[str], current: int, on_pick) -> ttk.Combobox:
            ttk.Label(side, text=self.t(label_key), style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=3)
            box = ttk.Combobox(side, values=values, state="readonly", width=18)
            box.current(current)
            box.grid(row=row, column=1, sticky="ew", pady=3)
            box.bind("<<ComboboxSelected>>", lambda _e: on_pick(box.current()))
            return box

        labelled_combo(
            0,
            "tictactoe.difficulty",
            [self.t(f"tictactoe.difficulty.{d}") for d in DIFFICULTIES],
            DIFFICULTIES.index(self.settings["difficulty"]),
            lambda i: self._change("difficulty", DIFFICULTIES[i]),
        )
        self.personality_box = labelled_combo(
            1,
            "tictactoe.personality",
            [self.t(f"tictactoe.personality.{p}") for p in PERSONALITIES],
            PERSONALITIES.index(self.settings["personality"]),
            lambda i: self._change("personality", PERSONALITIES[i]),
        )
        labelled_combo(
            2,
            "tictactoe.best_of",
            [str(n) for n in MATCH_LENGTHS],
            MATCH_LENGTHS.index(self.settings["best_of"]),
            lambda i: self._change("best_of", MATCH_LENGTHS[i]),
        )

        buttons = ttk.Frame(side, style="Panel.TFrame")
        buttons.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 4))
        buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(buttons, text=self.t("menu.new_game"), style="Accent.TButton", command=self.new_game).grid(
            row=0, column=0, sticky="ew", padx=2, pady=2
        )
        ttk.Button(buttons, text=self.t("tictactoe.new_match"), command=self.new_match).grid(
            row=0, column=1, sticky="ew", padx=2, pady=2
        )
        self.hint_btn = ttk.Button(buttons, text=self.t("button.hint"), command=self.hint)
        self.hint_btn.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        self.undo_btn = ttk.Button(buttons, text=self.t("button.undo"), command=self.undo)
        self.undo_btn.grid(row=1, column=1, sticky="ew", padx=2, pady=2)

        ttk.Separator(side).grid(row=4, column=0, columnspan=2, sticky="ew", pady=8)
        labelled_combo(
            5,
            "tictactoe.watch_x",
            [self._choice_label(c) for c in CHOICES],
            CHOICES.index(self.settings["watch_x"]),
            lambda i: self.settings.set("watch_x", CHOICES[i]),
        )
        self.watch_btn = ttk.Button(side, command=self.toggle_watch)
        self.watch_btn.grid(row=6, column=0, columnspan=2, sticky="ew", pady=2)

        ttk.Separator(side).grid(row=7, column=0, columnspan=2, sticky="ew", pady=8)
        self.match_label = ttk.Label(side, style="Heading.TLabel")
        self.match_label.grid(row=8, column=0, columnspan=2, sticky="w")
        self.record_label = ttk.Label(side, style="Panel.TLabel", justify="left")
        self.record_label.grid(row=9, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.badges_label = ttk.Label(side, style="PanelMuted.TLabel", justify="left", wraplength=260)
        self.badges_label.grid(row=10, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _choice_label(self, choice: str) -> str:
        difficulty, _, personality = choice.partition(":")
        label = self.t(f"tictactoe.difficulty.{difficulty}")
        return f"{label} ({self.t(f'tictactoe.personality.{personality}')})" if personality else label

    def extra_options(self) -> list[Toggle]:
        var = tk.BooleanVar(value=self.settings["humanish"])
        return [Toggle("tictactoe.option.humanish", var, lambda: self.settings.set("humanish", var.get()))]

    def _change(self, key: str, value) -> None:
        self.settings.set(key, value)
        if key == "best_of":
            self.new_match()
        else:
            self.refresh()

    # -- flow -----------------------------------------------------------------
    def _cancel_pending(self) -> None:
        if self._pending is not None:
            self.root.after_cancel(self._pending)
            self._pending = None

    def new_game(self) -> None:
        self._cancel_pending()
        if self.match.over:
            self.match = Match(self.settings["best_of"])
        # Alternate who opens so the AI gets to start half the games.
        self.games_started += 1
        starter = HUMAN if self.games_started % 2 else AI
        self.game = Game(starter=starter)
        self.hint_cell = None
        self._set_message_for_turn()
        self.refresh()
        self._schedule_ai()

    def new_match(self) -> None:
        self.match = Match(self.settings["best_of"])
        self.new_game()

    def toggle_watch(self) -> None:
        self.watching = not self.watching
        self.new_match()

    def _on_click(self, event: tk.Event) -> None:
        col, row = event.x // CELL, event.y // CELL
        if 0 <= col < 3 and 0 <= row < 3:
            self.human_move(row * 3 + col)

    def human_move(self, index: int) -> None:
        if self.game.over or self._player(self.game.to_move) is not None:
            return
        if self.game.board[index]:
            return
        self.game.play(index)
        self.hint_cell = None
        self.play_sound()
        self._after_move()

    def _schedule_ai(self) -> None:
        if not self.game.over and self._player(self.game.to_move) is not None and self._pending is None:
            self._pending = self.root.after(AI_DELAY_MS, self._ai_move)

    def _ai_move(self) -> None:
        self._pending = None
        player = self._player(self.game.to_move)
        if self.game.over or player is None:
            return
        self.game.play(player.move(self.game.board, self.game.to_move, self.rng))
        self._after_move()

    def _after_move(self) -> None:
        result = self.game.result
        if result is None:
            self._set_message_for_turn()
            self.refresh()
            self._schedule_ai()
            return
        self.match.record(result)
        if not self.watching:
            self._record_stats(result)
        if result == "draw":
            self.message = self.t("tictactoe.draw")
        else:
            self.message = self.t("tictactoe.wins", player=self._symbol_name(result))
        if self.match.over and self.match.best_of > 1:
            self.message += "  " + self.t("tictactoe.match_won", player=self._symbol_name(self.match.champion or ""))
        self.refresh()
        if self.watching:
            self._pending = self.root.after(AI_DELAY_MS * 4, self._continue_watch)

    def _continue_watch(self) -> None:
        self._pending = None
        if self.watching:
            self.new_game()

    def _symbol_name(self, symbol: str) -> str:
        if self.watching:
            return symbol
        return self.t("tictactoe.you") if symbol == HUMAN else self.t("tictactoe.computer")

    def _set_message_for_turn(self) -> None:
        if self.watching:
            self.message = self.t("tictactoe.watching", player=self.game.to_move)
        elif self.game.to_move == HUMAN:
            self.message = self.t("tictactoe.your_turn")
        else:
            self.message = self.t("tictactoe.ai_thinking")

    def _record_stats(self, result: str) -> None:
        key = self.opponent().key
        outcome = {"draw": "draws", HUMAN: "wins", AI: "losses"}[result]
        counts = self.stats.bump("games", outcome, f"{outcome}:{key}")
        streak = counts.get("streak", 0) + 1 if result == HUMAN else 0
        self.stats.set("streak", streak)
        self.stats.set_max("best_streak", streak)
        if self.match.over and self.match.best_of > 1:
            self.stats.bump("match_wins" if self.match.champion == HUMAN else "match_losses")

    def hint(self) -> None:
        if self.game.over or self.watching or self.game.to_move != HUMAN:
            return
        self.hint_cell = self.rng.choice(logic.best_moves(self.game.board, HUMAN))
        self.refresh()

    def _human_has_moved(self) -> bool:
        return any(self.game.board[i] == HUMAN for i in self.game.moves)

    def undo(self) -> None:
        """Take back the player's last move and the computer's reply to it."""
        if self.watching or self.game.over or not self._human_has_moved():
            return
        self._cancel_pending()
        while self.game.moves:
            mark = self.game.board[self.game.moves[-1]]
            self.game.undo()
            if mark == HUMAN:
                break
        self.hint_cell = None
        self._set_message_for_turn()
        self.refresh()

    # -- drawing --------------------------------------------------------------
    def refresh(self) -> None:
        if not hasattr(self, "canvas"):
            return
        p, c = self.palette, self.canvas
        c.delete("all")
        for i in (1, 2):
            c.create_line(i * CELL, 8, i * CELL, CELL * 3 - 8, fill=p.border, width=3)
            c.create_line(8, i * CELL, CELL * 3 - 8, i * CELL, fill=p.border, width=3)
        line = logic.winning_line(self.game.board)
        for index, mark in enumerate(self.game.board):
            row, col = divmod(index, 3)
            cx, cy = col * CELL + CELL / 2, row * CELL + CELL / 2
            if index == self.hint_cell:
                c.create_rectangle(cx - 50, cy - 50, cx + 50, cy + 50, outline=p.accent, width=3, dash=(6, 4))
            if mark:
                colour = p.accent if mark == "X" else p.warn
                if line and index in line:
                    colour = p.good
                c.create_text(cx, cy, text=mark, fill=colour, font=(self.family, 54, "bold"))
            else:
                c.create_text(col * CELL + 12, row * CELL + 12, text=str(index + 1), fill=p.border, anchor="nw")
        self.status.configure(text=self.message)

        self.personality_box.state(["!disabled" if self.settings["difficulty"] == "normal" else "disabled"])
        human_turn = not self.watching and not self.game.over and self.game.to_move == HUMAN
        self.hint_btn.state(["!disabled" if human_turn else "disabled"])
        self.undo_btn.state(["!disabled" if human_turn and self._human_has_moved() else "disabled"])
        self.watch_btn.configure(text=self.t("tictactoe.stop_watching" if self.watching else "tictactoe.watch"))

        wins = self.match.wins
        self.match_label.configure(
            text=self.t(
                "tictactoe.match_score", x=wins["X"], o=wins["O"], draws=self.match.draws, best_of=self.match.best_of
            )
        )
        stats = self.stats.load()
        self.record_label.configure(
            text=self.t(
                "tictactoe.record",
                wins=stats.get("wins", 0),
                losses=stats.get("losses", 0),
                draws=stats.get("draws", 0),
                streak=stats.get("streak", 0),
            )
        )
        earned = logic.earned_achievements(stats)
        self.badges_label.configure(
            text=self.t("tictactoe.badges", count=len(earned), total=len(logic.ACHIEVEMENTS))
            + (
                "\n" + ", ".join(self.t(f"tictactoe.badge.{b}") for b in logic.ACHIEVEMENTS if b in earned)
                if earned
                else ""
            )
        )

    # -- scores -----------------------------------------------------------------
    def score_sections(self) -> list[ScoreSection]:
        stats = self.stats.load()
        rows = []
        for choice in CHOICES:
            w, lo, d = (stats.get(f"{k}:{choice}", 0) for k in ("wins", "losses", "draws"))
            if w or lo or d:
                rows.append((self._choice_label(choice), w, lo, d))
        earned = logic.earned_achievements(stats)
        badges = [(self.t(f"tictactoe.badge.{b}"), "✓" if b in earned else "—") for b in logic.ACHIEVEMENTS]
        return [
            ScoreSection(
                self.t("tictactoe.by_opponent"),
                (self.t("tictactoe.opponent"), self.t("scores.wins"), self.t("scores.losses"), self.t("scores.draws")),
                rows,
            ),
            ScoreSection(self.t("tictactoe.achievements"), (self.t("tictactoe.badge"), "✓"), badges),
        ]

    def reset_scores(self) -> None:
        self.stats.clear()
