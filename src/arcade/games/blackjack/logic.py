"""Blackjack rules, independent of any GUI.

House rules (see :class:`Rules`): six-deck shoe, dealer hits soft 17,
blackjack pays 3:2, the dealer peeks for blackjack when showing an ace or a
ten, insurance is offered against an ace and pays 2:1, pairs of equal value
may be split up to four hands, split aces get one card each, and doubling is
allowed on any first two cards (including after a split).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from arcade.core.cards import Card, Shoe
from arcade.core.chips import Bank, InsufficientChips


def card_value(card: Card) -> int:
    if card.rank == "A":
        return 11
    if card.rank in {"J", "Q", "K"}:
        return 10
    return int(card.rank)


def hand_value(cards: list[Card]) -> tuple[int, bool]:
    """Return ``(best total, is_soft)``. Soft means an ace is still counted as 11."""
    total = sum(card_value(card) for card in cards)
    aces = sum(card.rank == "A" for card in cards)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total, aces > 0


def is_blackjack(cards: list[Card]) -> bool:
    return len(cards) == 2 and hand_value(cards)[0] == 21


class Phase(enum.Enum):
    BETTING = "betting"
    INSURANCE = "insurance"
    PLAYER = "player"
    DONE = "done"


class Action(enum.Enum):
    HIT = "hit"
    STAND = "stand"
    DOUBLE = "double"
    SPLIT = "split"


class Outcome(enum.Enum):
    BLACKJACK = "blackjack"
    WIN = "win"
    PUSH = "push"
    LOSE = "lose"
    BUST = "bust"


@dataclass(frozen=True)
class Rules:
    decks: int = 6
    dealer_hits_soft_17: bool = True
    blackjack_pays: tuple[int, int] = (3, 2)
    max_hands: int = 4
    double_after_split: bool = True
    resplit_aces: bool = False
    min_bet: int = 5


@dataclass
class Hand:
    cards: list[Card]
    bet: int
    from_split: bool = False
    doubled: bool = False
    done: bool = False
    outcome: Outcome | None = None
    payout: int = 0  # chips returned to the bank, stake included

    @property
    def total(self) -> int:
        return hand_value(self.cards)[0]

    @property
    def soft(self) -> bool:
        return hand_value(self.cards)[1]

    @property
    def busted(self) -> bool:
        return self.total > 21

    @property
    def natural(self) -> bool:
        """A two-card 21 on the original hand. A split 21 is just 21."""
        return not self.from_split and is_blackjack(self.cards)

    @property
    def split_aces(self) -> bool:
        return self.from_split and self.cards[0].rank == "A"

    @property
    def net(self) -> int:
        return self.payout - self.bet


class RuleError(Exception):
    """Raised when an action isn't allowed right now."""


@dataclass
class Blackjack:
    bank: Bank = field(default_factory=lambda: Bank(balance=500, credit=500))
    rules: Rules = field(default_factory=Rules)
    shoe: Shoe | None = None
    phase: Phase = Phase.BETTING
    hands: list[Hand] = field(default_factory=list)
    dealer: list[Card] = field(default_factory=list)
    active: int = 0
    insurance_bet: int = 0
    insurance_payout: int = 0

    def __post_init__(self) -> None:
        if self.shoe is None:
            self.shoe = Shoe(self.rules.decks)

    # -- state helpers ----------------------------------------------------
    @property
    def current(self) -> Hand | None:
        if self.phase is Phase.PLAYER and 0 <= self.active < len(self.hands):
            return self.hands[self.active]
        return None

    @property
    def dealer_up(self) -> Card | None:
        return self.dealer[0] if self.dealer else None

    @property
    def hole_revealed(self) -> bool:
        return self.phase is Phase.DONE

    @property
    def round_net(self) -> int:
        """Chips won (positive) or lost on the round just finished."""
        staked = sum(h.bet for h in self.hands) + self.insurance_bet
        returned = sum(h.payout for h in self.hands) + self.insurance_payout
        return returned - staked

    def _require(self, phase: Phase) -> None:
        if self.phase is not phase:
            raise RuleError(f"not allowed during {self.phase.value}")

    def _draw(self) -> Card:
        assert self.shoe is not None
        return self.shoe.draw()

    # -- dealing ----------------------------------------------------------
    def deal(self, bet: int) -> None:
        if self.phase not in (Phase.BETTING, Phase.DONE):
            raise RuleError("finish the current round first")
        if bet < self.rules.min_bet:
            raise RuleError(f"minimum bet is {self.rules.min_bet}")
        if not self.bank.can_afford(bet):
            raise InsufficientChips(bet)
        assert self.shoe is not None
        self.shoe.discard([c for h in self.hands for c in h.cards] + self.dealer)
        if self.shoe.needs_shuffle():
            self.shoe.reshuffle()

        self.bank.take(bet)
        player = [self._draw()]
        self.dealer = [self._draw()]
        player.append(self._draw())
        self.dealer.append(self._draw())
        self.hands = [Hand(player, bet)]
        self.active = 0
        self.insurance_bet = 0
        self.insurance_payout = 0

        if self.dealer[0].rank == "A":
            self.phase = Phase.INSURANCE
        else:
            self._after_peek_window()

    def can_insure(self) -> bool:
        return self.phase is Phase.INSURANCE and self.bank.can_afford(self.hands[0].bet // 2)

    def insurance(self, take: bool) -> None:
        self._require(Phase.INSURANCE)
        if take:
            amount = self.hands[0].bet // 2
            if amount <= 0 or not self.bank.can_afford(amount):
                raise InsufficientChips(amount)
            self.bank.take(amount)
            self.insurance_bet = amount
        self._after_peek_window()

    def _after_peek_window(self) -> None:
        dealer_bj = is_blackjack(self.dealer)
        if self.insurance_bet and dealer_bj:
            self.insurance_payout = self.insurance_bet * 3
            self.bank.pay(self.insurance_payout)
        if dealer_bj or self.hands[0].natural:
            # Dealer peeked (or the player has a natural): the round ends now.
            self.hands[0].done = True
            self._settle()
            return
        self.phase = Phase.PLAYER

    # -- player actions ---------------------------------------------------
    def available_actions(self) -> set[Action]:
        hand = self.current
        if hand is None:
            return set()
        if hand.split_aces:
            # Split aces get one card each; the only choice left is re-splitting.
            return {Action.STAND, Action.SPLIT} if self._can_split(hand) else set()
        actions = {Action.HIT, Action.STAND}
        if self._can_double(hand):
            actions.add(Action.DOUBLE)
        if self._can_split(hand):
            actions.add(Action.SPLIT)
        return actions

    def _can_double(self, hand: Hand) -> bool:
        if len(hand.cards) != 2 or (hand.from_split and not self.rules.double_after_split):
            return False
        return self.bank.can_afford(hand.bet)

    def _can_split(self, hand: Hand) -> bool:
        if len(hand.cards) != 2 or len(self.hands) >= self.rules.max_hands:
            return False
        if card_value(hand.cards[0]) != card_value(hand.cards[1]):
            return False
        if hand.split_aces and not self.rules.resplit_aces:
            return False
        return self.bank.can_afford(hand.bet)

    def _act(self, action: Action) -> Hand:
        hand = self.current
        if hand is None:
            raise RuleError("no hand in play")
        if action not in self.available_actions():
            raise RuleError(f"cannot {action.value} now")
        return hand

    def hit(self) -> None:
        hand = self._act(Action.HIT)
        hand.cards.append(self._draw())
        if hand.total >= 21:
            self._finish_hand()

    def stand(self) -> None:
        self._act(Action.STAND)
        self._finish_hand()

    def double(self) -> None:
        hand = self._act(Action.DOUBLE)
        self.bank.take(hand.bet)
        hand.bet *= 2
        hand.doubled = True
        hand.cards.append(self._draw())
        self._finish_hand()

    def split(self) -> None:
        hand = self._act(Action.SPLIT)
        self.bank.take(hand.bet)
        second = Hand([hand.cards.pop()], hand.bet, from_split=True)
        hand.from_split = True
        self.hands.insert(self.active + 1, second)
        hand.cards.append(self._draw())
        second.cards.append(self._draw())
        self._auto_finish()

    def _finish_hand(self) -> None:
        self.hands[self.active].done = True
        self.active += 1
        self._auto_finish()

    def _auto_finish(self) -> None:
        """Skip past hands that need no decision (split aces, a dealt 21)."""
        while self.active < len(self.hands):
            hand = self.hands[self.active]
            needs_choice = not hand.done and not hand.split_aces and hand.total < 21
            if needs_choice:
                return
            # A pair of split aces can still be re-split when the rules allow it.
            if hand.split_aces and not hand.done and self._can_split(hand):
                return
            hand.done = True
            self.active += 1
        self._dealer_turn()

    # -- dealer and settlement --------------------------------------------
    def dealer_should_hit(self) -> bool:
        total, soft = hand_value(self.dealer)
        return total < 17 or (total == 17 and soft and self.rules.dealer_hits_soft_17)

    def _dealer_turn(self) -> None:
        if any(not h.busted for h in self.hands):
            while self.dealer_should_hit():
                self.dealer.append(self._draw())
        self._settle()

    def _settle(self) -> None:
        dealer_total = hand_value(self.dealer)[0]
        dealer_bj = is_blackjack(self.dealer)
        num, den = self.rules.blackjack_pays
        for hand in self.hands:
            if hand.busted:
                hand.outcome = Outcome.BUST
            elif hand.natural and not dealer_bj:
                hand.outcome = Outcome.BLACKJACK
            elif dealer_bj:
                hand.outcome = Outcome.PUSH if hand.natural else Outcome.LOSE
            elif dealer_total > 21 or hand.total > dealer_total:
                hand.outcome = Outcome.WIN
            elif hand.total == dealer_total:
                hand.outcome = Outcome.PUSH
            else:
                hand.outcome = Outcome.LOSE
            hand.payout = {
                Outcome.BLACKJACK: hand.bet + hand.bet * num // den,
                Outcome.WIN: hand.bet * 2,
                Outcome.PUSH: hand.bet,
            }.get(hand.outcome, 0)
            self.bank.pay(hand.payout)
            hand.done = True
        self.active = len(self.hands)
        self.phase = Phase.DONE


def basic_strategy(hand: Hand, dealer_up: Card, actions: set[Action]) -> Action:
    """Recommend a move using standard multi-deck, dealer-hits-soft-17 basic strategy."""
    up = card_value(dealer_up)
    total, soft = hand_value(hand.cards)
    can_double = Action.DOUBLE in actions

    if Action.SPLIT in actions and card_value(hand.cards[0]) == card_value(hand.cards[1]):
        pair = card_value(hand.cards[0])
        split = {
            11: True,
            10: False,
            9: up not in (7, 10, 11),
            8: True,
            7: up <= 7,
            6: up <= 6,
            5: False,
            4: up in (5, 6),
            3: up <= 7,
            2: up <= 7,
        }[pair]
        if split:
            return Action.SPLIT

    if soft:
        if total >= 20:
            return Action.STAND
        if total == 19:
            return Action.DOUBLE if can_double and up == 6 else Action.STAND
        if total == 18:
            if 2 <= up <= 6:
                return Action.DOUBLE if can_double else Action.STAND
            return Action.STAND if up in (7, 8) else Action.HIT
        double_from = {17: 3, 16: 4, 15: 4, 14: 5, 13: 5}.get(total, 7)
        if can_double and double_from <= up <= 6:
            return Action.DOUBLE
        return Action.HIT

    if total >= 17:
        return Action.STAND
    if 13 <= total <= 16:
        return Action.STAND if up <= 6 else Action.HIT
    if total == 12:
        return Action.STAND if 4 <= up <= 6 else Action.HIT
    if total == 11:
        return Action.DOUBLE if can_double else Action.HIT
    if total == 10:
        return Action.DOUBLE if can_double and up <= 9 else Action.HIT
    if total == 9:
        return Action.DOUBLE if can_double and 3 <= up <= 6 else Action.HIT
    return Action.HIT
