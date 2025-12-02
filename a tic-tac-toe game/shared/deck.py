"""Utility classes for working with a standard deck of playing cards.

The deck is intentionally self contained so that future game modules can
reuse it without pulling in any GUI or tic-tac-toe specific dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterable, List


SUITS = ("Spades", "Hearts", "Clubs", "Diamonds")
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
JOKER = "Joker"


@dataclass(frozen=True)
class Card:
    """Represents a single playing card."""

    rank: str
    suit: str

    def label(self) -> str:
        """Return a human-friendly label (e.g. ``"A of Spades"``)."""

        if self.rank == JOKER:
            return self.rank
        return f"{self.rank} of {self.suit}"

    def short_name(self) -> str:
        """Return a compact representation (e.g. ``"AS"`` for Ace of Spades)."""

        if self.rank == JOKER:
            return "JK"
        return f"{self.rank}{self.suit[0].upper()}"


class Deck:
    """A standard deck that supports shuffling, drawing, and dealing cards."""

    def __init__(self, *, include_jokers: bool = False, seed: int | None = None) -> None:
        self.include_jokers = include_jokers
        self._rng = random.Random(seed)
        self._original_cards = self._build_cards()
        self._cards: List[Card] = list(self._original_cards)

    def _build_cards(self) -> List[Card]:
        cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        if self.include_jokers:
            cards.append(Card(JOKER, JOKER))
            cards.append(Card(JOKER, JOKER))
        return cards

    def shuffle(self) -> None:
        """Shuffle the deck in place."""

        self._rng.shuffle(self._cards)

    def reset(self, *, shuffle: bool = False) -> None:
        """Restore the deck to a full set of cards.

        Args:
            shuffle: When True, the deck is shuffled after being reset.
        """

        self._cards = list(self._original_cards)
        if shuffle:
            self.shuffle()

    def draw(self, count: int = 1) -> List[Card]:
        """Draw ``count`` cards from the top of the deck.

        Raises:
            ValueError: if ``count`` is negative.
            IndexError: if the deck does not have enough cards remaining.
        """

        if count < 0:
            raise ValueError("count must be non-negative")
        if count > len(self._cards):
            raise IndexError("not enough cards remaining in deck")
        drawn = self._cards[:count]
        del self._cards[:count]
        return drawn

    def deal_hands(self, num_hands: int, cards_per_hand: int) -> List[List[Card]]:
        """Deal ``num_hands`` each with ``cards_per_hand`` cards.

        Raises:
            ValueError: if either argument is non-positive.
            IndexError: if there are not enough cards available.
        """

        if num_hands <= 0 or cards_per_hand <= 0:
            raise ValueError("num_hands and cards_per_hand must be positive")
        total_required = num_hands * cards_per_hand
        if total_required > len(self._cards):
            raise IndexError("not enough cards remaining in deck")

        return [self.draw(cards_per_hand) for _ in range(num_hands)]

    def remaining(self) -> int:
        """Return the number of cards left in the deck."""

        return len(self._cards)

    def __len__(self) -> int:  # pragma: no cover - convenience alias
        return self.remaining()

    def __iter__(self) -> Iterable[Card]:  # pragma: no cover - convenience alias
        return iter(self._cards)

