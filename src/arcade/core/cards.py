"""Playing cards and a shoe that never hands out the same physical card twice."""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass

SUITS = ("spades", "hearts", "diamonds", "clubs")
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
SUIT_SYMBOLS = {"spades": "♠", "hearts": "♥", "diamonds": "♦", "clubs": "♣"}
RED_SUITS = frozenset({"hearts", "diamonds"})
SUIT_CODES = {"S": "spades", "H": "hearts", "D": "diamonds", "C": "clubs"}


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    def __post_init__(self) -> None:
        if self.rank not in RANKS:
            raise ValueError(f"Unknown rank: {self.rank!r}")
        if self.suit not in SUITS:
            raise ValueError(f"Unknown suit: {self.suit!r}")

    @classmethod
    def parse(cls, code: str) -> Card:
        """Build a card from a short code such as ``"AS"`` or ``"10h"``."""
        code = code.strip().upper()
        rank, suit = code[:-1], SUIT_CODES.get(code[-1:])
        if suit is None:
            raise ValueError(f"Unknown suit in {code!r}")
        return cls(rank, suit)

    @property
    def is_red(self) -> bool:
        return self.suit in RED_SUITS

    @property
    def symbol(self) -> str:
        return SUIT_SYMBOLS[self.suit]

    @property
    def rank_index(self) -> int:
        """1 for an ace up to 13 for a king."""
        return RANKS.index(self.rank) + 1

    def __str__(self) -> str:
        return f"{self.rank}{self.symbol}"


def cards(codes: str) -> list[Card]:
    """Parse a space separated list of codes, handy in tests: ``cards("AS 10H")``."""
    return [Card.parse(code) for code in codes.split()]


def full_deck() -> list[Card]:
    return [Card(rank, suit) for suit in SUITS for rank in RANKS]


class Shoe:
    """One or more decks dealt from the top, with a discard tray.

    Cards in play are never put back until :meth:`discard` is called, so a
    reshuffle in the middle of a round can't duplicate a card on the table.
    """

    def __init__(self, decks: int = 1, *, rng: random.Random | None = None) -> None:
        if decks < 1:
            raise ValueError("decks must be at least 1")
        self.decks = decks
        self.rng = rng or random.Random()
        self._cards: list[Card] = [card for _ in range(decks) for card in full_deck()]
        self._discards: list[Card] = []
        self.auto_shuffle = True
        self.shuffle()

    @classmethod
    def stacked(cls, top: Iterable[Card]) -> Shoe:
        """A shoe whose next draws are ``top`` in order (for tests and demos)."""
        shoe = cls(rng=random.Random(0))
        shoe._cards = list(top)
        shoe.auto_shuffle = False
        return shoe

    def __len__(self) -> int:
        return len(self._cards)

    @property
    def total(self) -> int:
        return self.decks * 52

    def shuffle(self) -> None:
        self.rng.shuffle(self._cards)

    def draw(self) -> Card:
        if not self._cards:
            self.reshuffle()
        if not self._cards:
            raise IndexError("the shoe is empty")
        return self._cards.pop(0)

    def draw_many(self, count: int) -> list[Card]:
        return [self.draw() for _ in range(count)]

    def discard(self, played: Iterable[Card]) -> None:
        self._discards.extend(played)

    def reshuffle(self) -> None:
        """Return the discard tray to the shoe and shuffle."""
        self._cards.extend(self._discards)
        self._discards.clear()
        self.shuffle()

    def needs_shuffle(self, penetration: float = 0.75) -> bool:
        return self.auto_shuffle and len(self._cards) < self.total * (1 - penetration)
