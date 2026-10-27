"""Klondike solitaire.

Locations are tuples: ``("waste",)``, ``("foundation", i)`` and
``("tableau", column, card_index)``. A tableau source moves the card at
``card_index`` and everything stacked on it.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field

from arcade.core.cards import SUITS, Card, full_deck

Location = tuple


def _alternates(lower: Card, upper: Card) -> bool:
    """True if ``lower`` can be placed on ``upper`` in the tableau."""
    return lower.is_red != upper.is_red and lower.rank_index == upper.rank_index - 1


@dataclass
class Klondike:
    draw_count: int = 1
    stock: list[Card] = field(default_factory=list)  # top card is last
    waste: list[Card] = field(default_factory=list)
    foundations: list[list[Card]] = field(default_factory=lambda: [[] for _ in SUITS])
    tableau: list[list[Card]] = field(default_factory=lambda: [[] for _ in range(7)])
    hidden: list[int] = field(default_factory=lambda: [0] * 7)  # face-down cards per column
    moves: int = 0
    passes: int = 0
    _history: list[dict] = field(default_factory=list, repr=False)

    @classmethod
    def deal(cls, draw_count: int = 1, rng: random.Random | None = None) -> Klondike:
        if draw_count not in (1, 3):
            raise ValueError("draw_count must be 1 or 3")
        deck = full_deck()
        (rng or random.Random()).shuffle(deck)
        game = cls(draw_count=draw_count)
        for col in range(7):
            game.tableau[col] = [deck.pop() for _ in range(col + 1)]
            game.hidden[col] = col
        game.stock = deck
        return game

    # -- undo ---------------------------------------------------------------
    _STATE = ("stock", "waste", "foundations", "tableau", "hidden", "moves", "passes")

    def _snapshot(self) -> None:
        self._history.append({name: copy.deepcopy(getattr(self, name)) for name in self._STATE})
        del self._history[:-200]

    def can_undo(self) -> bool:
        return bool(self._history)

    def undo(self) -> None:
        if self._history:
            for name, value in self._history.pop().items():
                setattr(self, name, value)

    # -- queries ------------------------------------------------------------
    @property
    def won(self) -> bool:
        return all(len(pile) == 13 for pile in self.foundations)

    def face_up(self, col: int, index: int) -> bool:
        return index >= self.hidden[col]

    def cards_at(self, src: Location) -> list[Card]:
        kind = src[0]
        if kind == "waste":
            return self.waste[-1:]
        if kind == "foundation":
            return self.foundations[src[1]][-1:]
        if kind == "tableau":
            col, index = src[1], src[2]
            if 0 <= index < len(self.tableau[col]) and self.face_up(col, index):
                return self.tableau[col][index:]
        return []

    def can_move(self, src: Location, dst: Location) -> bool:
        moving = self.cards_at(src)
        if not moving or src[:2] == dst[:2]:
            return False
        lead = moving[0]
        if dst[0] == "foundation":
            if len(moving) != 1:
                return False
            pile = self.foundations[dst[1]]
            if lead.suit != SUITS[dst[1]]:
                return False
            return lead.rank_index == len(pile) + 1
        if dst[0] == "tableau":
            pile = self.tableau[dst[1]]
            if not pile:
                return lead.rank == "K"
            return _alternates(lead, pile[-1])
        return False

    def foundation_for(self, card: Card) -> int:
        return SUITS.index(card.suit)

    # -- actions --------------------------------------------------------------
    def draw(self) -> bool:
        """Turn cards from the stock, or recycle the waste when the stock is empty."""
        if not self.stock and not self.waste:
            return False
        self._snapshot()
        if self.stock:
            for _ in range(min(self.draw_count, len(self.stock))):
                self.waste.append(self.stock.pop())
        else:
            self.stock = self.waste[::-1]
            self.waste = []
            self.passes += 1
        self.moves += 1
        return True

    def move(self, src: Location, dst: Location) -> bool:
        if not self.can_move(src, dst):
            return False
        self._snapshot()
        count = len(self.cards_at(src))
        if src[0] == "waste":
            moving = [self.waste.pop()]
        elif src[0] == "foundation":
            moving = [self.foundations[src[1]].pop()]
        else:
            col = src[1]
            moving = self.tableau[col][-count:]
            del self.tableau[col][-count:]
            if self.hidden[col] >= len(self.tableau[col]) and self.hidden[col] > 0:
                self.hidden[col] = len(self.tableau[col]) - 1  # flip the newly exposed card
        if dst[0] == "foundation":
            self.foundations[dst[1]].extend(moving)
        else:
            self.tableau[dst[1]].extend(moving)
        self.moves += 1
        return True

    def to_foundation(self, src: Location) -> bool:
        """Send the card at ``src`` to its foundation if that is legal."""
        cards = self.cards_at(src)
        if len(cards) != 1:
            return False
        return self.move(src, ("foundation", self.foundation_for(cards[0])))

    def best_destination(self, src: Location) -> Location | None:
        """Pick a sensible target for a one-click move: foundation first, then tableau."""
        cards = self.cards_at(src)
        if not cards:
            return None
        foundation = ("foundation", self.foundation_for(cards[0]))
        if self.can_move(src, foundation):
            return foundation
        for col in range(7):
            dst = ("tableau", col, len(self.tableau[col]))
            if self.can_move(src, dst) and not (cards[0].rank == "K" and src[0] == "tableau" and src[2] == 0):
                return dst
        return None

    def can_autocomplete(self) -> bool:
        return not self.stock and not self.waste and not any(self.hidden) and not self.won

    def autocomplete(self) -> int:
        """Move every card to the foundations once nothing is hidden. Returns moves made."""
        made = 0
        progress = True
        while progress and not self.won:
            progress = False
            sources: list[Location] = [("waste",)] + [
                ("tableau", c, len(self.tableau[c]) - 1) for c in range(7) if self.tableau[c]
            ]
            for src in sources:
                if self.to_foundation(src):
                    made += 1
                    progress = True
        return made
