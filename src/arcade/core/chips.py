"""A chip bank for betting games."""

from __future__ import annotations

from dataclasses import dataclass


class InsufficientChips(ValueError):
    pass


@dataclass
class Bank:
    """Player chips. ``credit`` lets the balance dip below zero by that much."""

    balance: int = 500
    credit: int = 0

    def can_afford(self, amount: int) -> bool:
        return amount > 0 and self.balance - amount >= -self.credit

    def take(self, amount: int) -> None:
        """Remove a stake from the bank or raise :class:`InsufficientChips`."""
        if amount <= 0:
            raise ValueError("amount must be positive")
        if not self.can_afford(amount):
            raise InsufficientChips(amount)
        self.balance -= amount

    def pay(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("amount must not be negative")
        self.balance += amount
