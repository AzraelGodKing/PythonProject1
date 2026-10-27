"""Yahtzee scoring and turn flow.

Standard rules: three rolls per turn, thirteen categories each used once,
a 35 point bonus for 63+ in the upper section, and a 100 point bonus for
each extra Yahtzee once the Yahtzee box holds 50. An extra Yahtzee also
works as a joker: Full House and the straights score their full value.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

UPPER = ("ones", "twos", "threes", "fours", "fives", "sixes")
LOWER = ("three_kind", "four_kind", "full_house", "small_straight", "large_straight", "yahtzee", "chance")
CATEGORIES = UPPER + LOWER
UPPER_BONUS_THRESHOLD = 63
UPPER_BONUS = 35
YAHTZEE_BONUS = 100
ROLLS_PER_TURN = 3
FIXED = {"full_house": 25, "small_straight": 30, "large_straight": 40, "yahtzee": 50}


def is_yahtzee(dice: Sequence[int]) -> bool:
    return len(set(dice)) == 1


def score(category: str, dice: Sequence[int], *, joker: bool = False) -> int:
    """Points ``dice`` would earn in ``category``."""
    if len(dice) != 5 or any(not 1 <= d <= 6 for d in dice):
        raise ValueError("expected five dice with values 1-6")
    counts = Counter(dice)
    total = sum(dice)
    faces = set(dice)
    if category in UPPER:
        face = UPPER.index(category) + 1
        return counts[face] * face
    if category == "three_kind":
        return total if max(counts.values()) >= 3 else 0
    if category == "four_kind":
        return total if max(counts.values()) >= 4 else 0
    if category == "chance":
        return total
    if joker and category in ("full_house", "small_straight", "large_straight"):
        return FIXED[category]
    if category == "full_house":
        return FIXED[category] if sorted(counts.values()) == [2, 3] else 0
    if category == "small_straight":
        runs = ({1, 2, 3, 4}, {2, 3, 4, 5}, {3, 4, 5, 6})
        return FIXED[category] if any(run <= faces for run in runs) else 0
    if category == "large_straight":
        return FIXED[category] if faces in ({1, 2, 3, 4, 5}, {2, 3, 4, 5, 6}) else 0
    if category == "yahtzee":
        return FIXED[category] if is_yahtzee(dice) else 0
    raise KeyError(category)


@dataclass
class Yahtzee:
    rng: random.Random = field(default_factory=random.Random)
    dice: list[int] = field(default_factory=lambda: [1] * 5)
    held: list[bool] = field(default_factory=lambda: [False] * 5)
    rolls_left: int = ROLLS_PER_TURN
    card: dict[str, int | None] = field(default_factory=lambda: dict.fromkeys(CATEGORIES))
    yahtzee_bonus: int = 0

    @property
    def turn_started(self) -> bool:
        return self.rolls_left < ROLLS_PER_TURN

    @property
    def over(self) -> bool:
        return all(value is not None for value in self.card.values())

    @property
    def upper_total(self) -> int:
        return sum(self.card[c] or 0 for c in UPPER)

    @property
    def upper_bonus(self) -> int:
        return UPPER_BONUS if self.upper_total >= UPPER_BONUS_THRESHOLD else 0

    @property
    def total(self) -> int:
        return sum(v or 0 for v in self.card.values()) + self.upper_bonus + self.yahtzee_bonus

    def roll(self) -> bool:
        if self.rolls_left <= 0 or self.over:
            return False
        if not self.turn_started:
            self.held = [False] * 5
        self.dice = [d if h else self.rng.randint(1, 6) for d, h in zip(self.dice, self.held, strict=True)]
        self.rolls_left -= 1
        return True

    def toggle_hold(self, index: int) -> None:
        if self.turn_started and self.rolls_left > 0:
            self.held[index] = not self.held[index]

    def _joker(self) -> bool:
        return is_yahtzee(self.dice) and self.card["yahtzee"] is not None

    def potential(self, category: str) -> int:
        return score(category, self.dice, joker=self._joker())

    def can_score(self, category: str) -> bool:
        return self.turn_started and not self.over and self.card[category] is None

    def choose(self, category: str) -> int:
        if not self.can_score(category):
            raise ValueError(f"cannot score {category} now")
        if is_yahtzee(self.dice) and self.card["yahtzee"] == FIXED["yahtzee"]:
            self.yahtzee_bonus += YAHTZEE_BONUS
        points = self.potential(category)
        self.card[category] = points
        self.rolls_left = ROLLS_PER_TURN
        self.held = [False] * 5
        return points
