"""Unit tests for shared.chips module."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.chips import Chips


class TestChips:
    """Test cases for the Chips class."""

    def test_chips_creation_default(self):
        """Test default chips creation."""
        chips = Chips()
        assert chips.balance == 0
        assert chips.max_debt == 500

    def test_chips_creation_with_balance(self):
        """Test chips creation with custom balance."""
        chips = Chips(balance=1000)
        assert chips.balance == 1000
        assert chips.max_debt == 500

    def test_chips_creation_custom_max_debt(self):
        """Test chips creation with custom max debt."""
        chips = Chips(balance=500, max_debt=1000)
        assert chips.balance == 500
        assert chips.max_debt == 1000

    def test_can_bet_positive_balance(self):
        """Test can_bet with positive balance."""
        chips = Chips(balance=1000)
        assert chips.can_bet(100) is True
        assert chips.can_bet(500) is True
        assert chips.can_bet(1000) is True

    def test_can_bet_zero_amount(self):
        """Test that zero bet amount returns False."""
        chips = Chips(balance=1000)
        assert chips.can_bet(0) is False

    def test_can_bet_negative_amount(self):
        """Test that negative bet amount returns False."""
        chips = Chips(balance=1000)
        assert chips.can_bet(-100) is False

    def test_can_bet_exceeds_balance_within_debt_limit(self):
        """Test betting more than balance but within debt limit."""
        chips = Chips(balance=100, max_debt=500)
        # Can bet up to 100 + 500 = 600 total
        assert chips.can_bet(200) is True
        assert chips.can_bet(600) is True

    def test_can_bet_exceeds_debt_limit(self):
        """Test that betting beyond debt limit returns False."""
        chips = Chips(balance=100, max_debt=500)
        # Cannot bet more than 600 (balance + max_debt)
        assert chips.can_bet(601) is False
        assert chips.can_bet(1000) is False

    def test_can_bet_exact_debt_limit(self):
        """Test betting exactly to debt limit."""
        chips = Chips(balance=100, max_debt=500)
        # Betting 600 would put balance at -500 (exactly at debt limit)
        assert chips.can_bet(600) is True

    def test_can_bet_with_negative_balance(self):
        """Test can_bet when already in debt."""
        chips = Chips(balance=-200, max_debt=500)
        # Can bet up to 300 more (to reach -500)
        assert chips.can_bet(100) is True
        assert chips.can_bet(300) is True
        assert chips.can_bet(301) is False

    def test_can_bet_at_max_debt(self):
        """Test can_bet when already at max debt."""
        chips = Chips(balance=-500, max_debt=500)
        assert chips.can_bet(1) is False
        assert chips.can_bet(100) is False

    def test_place_bet_success(self):
        """Test successful bet placement."""
        chips = Chips(balance=1000)
        result = chips.place_bet(100)
        assert result is True
        assert chips.balance == 900

    def test_place_bet_multiple_bets(self):
        """Test placing multiple bets."""
        chips = Chips(balance=1000)
        assert chips.place_bet(200) is True
        assert chips.balance == 800
        assert chips.place_bet(300) is True
        assert chips.balance == 500

    def test_place_bet_into_debt(self):
        """Test placing bet that puts balance into negative."""
        chips = Chips(balance=100, max_debt=500)
        result = chips.place_bet(300)
        assert result is True
        assert chips.balance == -200

    def test_place_bet_failure_exceeds_debt(self):
        """Test bet placement failure when exceeding debt limit."""
        chips = Chips(balance=100, max_debt=500)
        result = chips.place_bet(700)
        assert result is False
        assert chips.balance == 100  # Balance unchanged

    def test_place_bet_failure_zero_amount(self):
        """Test bet placement failure with zero amount."""
        chips = Chips(balance=1000)
        result = chips.place_bet(0)
        assert result is False
        assert chips.balance == 1000

    def test_place_bet_failure_negative_amount(self):
        """Test bet placement failure with negative amount."""
        chips = Chips(balance=1000)
        result = chips.place_bet(-100)
        assert result is False
        assert chips.balance == 1000

    def test_payout_win_normal(self):
        """Test normal win payout (1:1)."""
        chips = Chips(balance=1000)
        chips.place_bet(100)
        assert chips.balance == 900

        chips.payout_win(100)
        assert chips.balance == 1100  # 900 + (100 * 2)

    def test_payout_win_blackjack(self):
        """Test blackjack win payout (3:2)."""
        chips = Chips(balance=1000)
        chips.place_bet(100)
        assert chips.balance == 900

        chips.payout_win(100, blackjack=True)
        assert chips.balance == 1150  # 900 + (100 * 2.5)

    def test_payout_win_blackjack_odd_bet(self):
        """Test blackjack payout with odd bet amount."""
        chips = Chips(balance=1000)
        chips.place_bet(50)
        assert chips.balance == 950

        chips.payout_win(50, blackjack=True)
        # 50 * 2.5 = 125, int conversion
        assert chips.balance == 1075  # 950 + 125

    def test_payout_win_blackjack_rounding(self):
        """Test blackjack payout handles integer conversion."""
        chips = Chips(balance=1000)
        chips.place_bet(15)
        assert chips.balance == 985

        chips.payout_win(15, blackjack=True)
        # 15 * 2.5 = 37.5, int(37.5) = 37
        assert chips.balance == 1022  # 985 + 37

    def test_payout_win_from_negative_balance(self):
        """Test winning while in debt."""
        chips = Chips(balance=-200, max_debt=500)
        chips.payout_win(300)
        assert chips.balance == 400  # -200 + 600

    def test_payout_push(self):
        """Test push payout (bet returned)."""
        chips = Chips(balance=1000)
        chips.place_bet(100)
        assert chips.balance == 900

        chips.payout_push(100)
        assert chips.balance == 1000  # Back to original

    def test_payout_push_multiple(self):
        """Test multiple push payouts."""
        chips = Chips(balance=1000)
        chips.place_bet(100)
        chips.place_bet(200)
        assert chips.balance == 700

        chips.payout_push(100)
        assert chips.balance == 800
        chips.payout_push(200)
        assert chips.balance == 1000

    def test_realistic_blackjack_scenario_win(self):
        """Test realistic blackjack game scenario - win."""
        chips = Chips(balance=1000)

        # Place bet
        assert chips.place_bet(100) is True
        assert chips.balance == 900

        # Win normally
        chips.payout_win(100)
        assert chips.balance == 1100

    def test_realistic_blackjack_scenario_blackjack(self):
        """Test realistic blackjack game scenario - blackjack."""
        chips = Chips(balance=1000)

        # Place bet
        assert chips.place_bet(100) is True
        assert chips.balance == 900

        # Win with blackjack
        chips.payout_win(100, blackjack=True)
        assert chips.balance == 1150

    def test_realistic_blackjack_scenario_push(self):
        """Test realistic blackjack game scenario - push."""
        chips = Chips(balance=1000)

        # Place bet
        assert chips.place_bet(100) is True
        assert chips.balance == 900

        # Push
        chips.payout_push(100)
        assert chips.balance == 1000

    def test_realistic_blackjack_scenario_loss(self):
        """Test realistic blackjack game scenario - loss."""
        chips = Chips(balance=1000)

        # Place bet
        assert chips.place_bet(100) is True
        assert chips.balance == 900

        # Loss (no payout)
        assert chips.balance == 900

    def test_realistic_blackjack_scenario_multiple_hands(self):
        """Test realistic blackjack scenario with multiple hands."""
        chips = Chips(balance=1000)

        # Hand 1: Bet and win
        chips.place_bet(100)
        chips.payout_win(100)
        assert chips.balance == 1100

        # Hand 2: Bet and lose
        chips.place_bet(200)
        assert chips.balance == 900

        # Hand 3: Bet and blackjack
        chips.place_bet(100)
        chips.payout_win(100, blackjack=True)
        assert chips.balance == 1050

        # Hand 4: Bet and push
        chips.place_bet(50)
        chips.payout_push(50)
        assert chips.balance == 1050

    def test_going_into_debt_and_recovering(self):
        """Test going into debt and recovering."""
        chips = Chips(balance=100, max_debt=500)

        # Lose several hands, go into debt
        chips.place_bet(100)
        assert chips.balance == 0

        chips.place_bet(200)
        assert chips.balance == -200

        # Win a big hand
        chips.payout_win(300)  # Win 600
        assert chips.balance == 400

        # Back in the black
        assert chips.balance > 0

    def test_debt_limit_prevents_bankruptcy(self):
        """Test that debt limit prevents excessive losses."""
        chips = Chips(balance=100, max_debt=500)

        # Can lose up to -500
        chips.place_bet(600)
        assert chips.balance == -500

        # Cannot bet anymore
        assert chips.can_bet(1) is False
        assert chips.place_bet(1) is False
        assert chips.balance == -500

    def test_zero_max_debt(self):
        """Test with zero max debt (no credit allowed)."""
        chips = Chips(balance=100, max_debt=0)

        # Can only bet up to balance
        assert chips.can_bet(100) is True
        assert chips.can_bet(101) is False

        chips.place_bet(100)
        assert chips.balance == 0

        # Cannot bet anything more
        assert chips.can_bet(1) is False

    def test_large_balance_operations(self):
        """Test with large balance amounts."""
        chips = Chips(balance=1_000_000)

        chips.place_bet(250_000)
        assert chips.balance == 750_000

        chips.payout_win(250_000)
        assert chips.balance == 1_250_000

    def test_chips_dataclass_properties(self):
        """Test that Chips is a dataclass with proper attributes."""
        chips = Chips(balance=500, max_debt=300)
        assert hasattr(chips, 'balance')
        assert hasattr(chips, 'max_debt')
        assert chips.balance == 500
        assert chips.max_debt == 300

    def test_edge_case_exactly_zero_balance(self):
        """Test operations when balance is exactly zero."""
        chips = Chips(balance=0, max_debt=100)

        assert chips.can_bet(50) is True
        assert chips.can_bet(100) is True
        assert chips.can_bet(101) is False

        chips.place_bet(50)
        assert chips.balance == -50

    def test_edge_case_max_debt_boundary(self):
        """Test operations at max debt boundary."""
        chips = Chips(balance=-499, max_debt=500)

        # Can bet 1 more
        assert chips.can_bet(1) is True
        chips.place_bet(1)
        assert chips.balance == -500

        # Now at limit
        assert chips.can_bet(1) is False
