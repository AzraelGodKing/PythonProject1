"""Go Fish for one player against the computer.

Rules: seven cards each. On your turn ask for a rank you hold; if the other
player has any they hand them all over and you go again. Otherwise you "go
fish" from the pond - drawing the rank you asked for also earns another
turn. Four of a kind make a book. A player with no cards draws one before
asking. The game ends when all thirteen books are made.

Events are recorded as ``(message_key, params)`` pairs so the GUI can
translate them.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field

from arcade.core.cards import RANKS, Card, full_deck

PLAYER, AI = "player", "ai"
HAND_SIZE = 7


def other(who: str) -> str:
    return AI if who == PLAYER else PLAYER


@dataclass
class GoFish:
    rng: random.Random = field(default_factory=random.Random)
    smart_ai: bool = True
    pond: list[Card] = field(default_factory=list)
    hands: dict[str, list[Card]] = field(default_factory=lambda: {PLAYER: [], AI: []})
    books: dict[str, list[str]] = field(default_factory=lambda: {PLAYER: [], AI: []})
    turn: str = PLAYER
    log: list[tuple[str, dict]] = field(default_factory=list)
    # Ranks the AI knows the player holds (the player asked for them).
    memory: set[str] = field(default_factory=set)

    @classmethod
    def deal(cls, rng: random.Random | None = None, smart_ai: bool = True) -> GoFish:
        game = cls(rng=rng or random.Random(), smart_ai=smart_ai)
        game.pond = full_deck()
        game.rng.shuffle(game.pond)
        for who in (PLAYER, AI):
            game.hands[who] = [game.pond.pop() for _ in range(HAND_SIZE)]
            game._collect_books(who)
        game._refill(PLAYER)
        return game

    @property
    def over(self) -> bool:
        return len(self.books[PLAYER]) + len(self.books[AI]) == len(RANKS)

    @property
    def winner(self) -> str | None:
        """``"player"``, ``"ai"``, ``"draw"`` or None while playing."""
        if not self.over:
            return None
        mine, theirs = len(self.books[PLAYER]), len(self.books[AI])
        return PLAYER if mine > theirs else AI if theirs > mine else "draw"

    def ranks_in_hand(self, who: str) -> list[str]:
        held = {card.rank for card in self.hands[who]}
        return [rank for rank in RANKS if rank in held]

    def _collect_books(self, who: str) -> None:
        counts = Counter(card.rank for card in self.hands[who])
        for rank, count in counts.items():
            if count == 4:
                self.hands[who] = [c for c in self.hands[who] if c.rank != rank]
                self.books[who].append(rank)
                self.memory.discard(rank)
                self.log.append(("gofish.log.book", {"who": who, "rank": rank}))

    def _refill(self, who: str) -> None:
        """A player whose hand is empty draws a card before taking their turn."""
        if not self.hands[who] and self.pond and not self.over:
            self.hands[who].append(self.pond.pop())
            self.log.append(("gofish.log.empty_draw", {"who": who}))
            self._collect_books(who)

    def _pass_turn(self) -> None:
        self.turn = other(self.turn)
        # Skip a player who can't act at all (no cards and an empty pond).
        for _ in range(2):
            self._refill(self.turn)
            if self.hands[self.turn] or self.over:
                return
            self.turn = other(self.turn)

    def ask(self, rank: str) -> bool:
        """The current player asks for ``rank``. Returns True if they go again."""
        who, target = self.turn, other(self.turn)
        if self.over or rank not in self.ranks_in_hand(who):
            raise ValueError(f"{who} cannot ask for {rank!r}")
        if who == PLAYER:
            self.memory.add(rank)
        taken = [c for c in self.hands[target] if c.rank == rank]
        again = bool(taken)
        if taken:
            self.hands[target] = [c for c in self.hands[target] if c.rank != rank]
            self.hands[who].extend(taken)
            self.log.append(("gofish.log.took", {"who": who, "count": len(taken), "rank": rank}))
            if who == AI:
                self.memory.discard(rank)
        else:
            self.log.append(("gofish.log.go_fish", {"who": who, "rank": rank}))
            if self.pond:
                drawn = self.pond.pop()
                self.hands[who].append(drawn)
                if drawn.rank == rank:
                    again = True
                    self.log.append(("gofish.log.lucky", {"who": who, "rank": rank}))
        self._collect_books(who)
        if self.over:
            return False
        if again and (self.hands[who] or self.pond):
            self._refill(who)
            return True
        self._pass_turn()
        return False

    def ai_choice(self) -> str:
        ranks = self.ranks_in_hand(AI)
        if self.smart_ai:
            remembered = [r for r in ranks if r in self.memory]
            if remembered:
                return self.rng.choice(remembered)
            # Otherwise ask for the rank it holds the most of.
            counts = Counter(c.rank for c in self.hands[AI])
            top = max(counts.values())
            return self.rng.choice([r for r in ranks if counts[r] == top])
        return self.rng.choice(ranks)

    def ai_turn(self) -> bool:
        if self.turn != AI or self.over:
            raise ValueError("not the computer's turn")
        return self.ask(self.ai_choice())
