"""Version 2: shared playing card helpers for future game modules.

This module provides a small, dependency-free API for working with playing
cards. It is intentionally self contained so future game modules can import
the deck helpers without pulling in GUI or Tic-Tac-Toe specific code.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterable, Iterator, List, Sequence


SUITS = ("Spades", "Hearts", "Clubs", "Diamonds")
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
JOKER = "Joker"
VERSION = 2


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

    @classmethod
    def from_label(cls, label: str) -> "Card":
        """Create a :class:`Card` from either ``label`` or ``short_name``.

        Examples
        --------
        >>> Card.from_label("A of Spades")
        Card(rank='A', suit='Spades')
        >>> Card.from_label("10H")
        Card(rank='10', suit='Hearts')
        """

        normalized = label.strip()
        if normalized.lower() == JOKER.lower():
            return cls(JOKER, JOKER)

        if " of " in normalized:
            rank, suit = normalized.split(" of ", maxsplit=1)
        else:
            rank, suit_code = normalized[:-1], normalized[-1].upper()
            suit_lookup = {"S": "Spades", "H": "Hearts", "C": "Clubs", "D": "Diamonds"}
            suit = suit_lookup.get(suit_code)
            if suit is None:
                raise ValueError(f"Unknown suit code '{suit_code}' in '{label}'")
        return cls(rank.strip(), suit.strip())


class Deck:
    """A standard deck that supports shuffling, drawing, and dealing cards."""

    def __init__(
        self,
        *,
        include_jokers: bool = False,
        num_decks: int = 1,
        seed: int | None = None,
    ) -> None:
        if num_decks <= 0:
            raise ValueError("num_decks must be positive")

        self.include_jokers = include_jokers
        self.num_decks = num_decks
        self._rng = random.Random(seed)
        self._original_cards = self._build_cards()
        self._cards: List[Card] = list(self._original_cards)
        self._discards: List[Card] = []

    def _build_cards(self) -> List[Card]:
        cards: List[Card] = []
        for _ in range(self.num_decks):
            cards.extend(Card(rank, suit) for suit in SUITS for rank in RANKS)
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
        self._discards.clear()
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
        if count == 0:
            return []
        if count > len(self._cards):
            raise IndexError("not enough cards remaining in deck")
        drawn = self._cards[:count]
        del self._cards[:count]
        return drawn

    def draw_one(self) -> Card:
        """Draw a single card for convenience."""

        return self.draw(1)[0]

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

    def discard(self, cards: Sequence[Card] | Card) -> None:
        """Place cards into a discard pile for optional reuse later."""

        if isinstance(cards, Card):
            self._discards.append(cards)
        else:
            self._discards.extend(cards)

    def recycle_discards(self, *, shuffle: bool = True) -> None:
        """Return discarded cards to the deck."""

        self._cards.extend(self._discards)
        self._discards.clear()
        if shuffle:
            self.shuffle()

    def remaining(self) -> int:
        """Return the number of cards left in the deck."""

        return len(self._cards)

    def discard_count(self) -> int:
        """Return the number of cards in the discard pile."""

        return len(self._discards)

    def __len__(self) -> int:  # pragma: no cover - convenience alias
        return self.remaining()

    def __iter__(self) -> Iterator[Card]:  # pragma: no cover - convenience alias
        return iter(self._cards)

