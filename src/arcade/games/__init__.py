"""The game catalogue shown by the launcher.

Each game is a subpackage with ``logic.py`` (rules, no Tkinter), ``gui.py``
(a :class:`arcade.core.ui.GameApp`) and ``__main__.py`` so it can run on its
own with ``python -m arcade.games.<id>``.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class GameInfo:
    id: str
    icon: str

    @property
    def module(self) -> str:
        return f"arcade.games.{self.id}"

    @property
    def name_key(self) -> str:
        return f"{self.id}.name"

    @property
    def description_key(self) -> str:
        return f"{self.id}.description"

    @property
    def available(self) -> bool:
        return importlib.util.find_spec(f"{self.module}.gui") is not None

    def command(self) -> list[str]:
        return [sys.executable, "-m", self.module]


GAMES: tuple[GameInfo, ...] = (
    GameInfo("tictactoe", "✕"),
    GameInfo("blackjack", "♠"),
    GameInfo("solitaire", "♥"),
    GameInfo("yahtzee", "⚄"),
    GameInfo("minesweeper", "✹"),
    GameInfo("gofish", "♣"),
)


def by_id(game_id: str) -> GameInfo:
    for game in GAMES:
        if game.id == game_id:
            return game
    raise KeyError(game_id)
