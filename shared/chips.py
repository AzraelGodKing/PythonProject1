"""Lightweight chip/balance helper for games."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chips:
    balance: int = 0
    max_debt: int = 500  # allow dipping to -max_debt

    def can_bet(self, amount: int) -> bool:
        if amount <= 0:
            return False
        return (self.balance - amount) >= -self.max_debt

    def place_bet(self, amount: int) -> bool:
        """Attempt to place a bet. Returns True if deducted, False otherwise."""
        if not self.can_bet(amount):
            return False
        self.balance -= amount
        return True

    def payout_win(self, bet: int, *, blackjack: bool = False) -> None:
        """Pay winnings: normal wins pay 1:1, blackjack pays 3:2."""
        if blackjack:
            self.balance += int(bet * 2.5)
        else:
            self.balance += bet * 2

    def payout_push(self, bet: int) -> None:
        """Return the bet on a push."""
        self.balance += bet

