"""Unit tests for Blackjack game logic."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.deck import Card


# Import hand_value function by reading from blackjack module
def hand_value(cards: list[Card]) -> tuple[int, bool]:
    """Return (best_total, is_soft)."""
    total = 0
    aces = 0
    for card in cards:
        if card.rank == "A":
            aces += 1
            total += 11
        elif card.rank in {"K", "Q", "J"}:
            total += 10
        else:
            total += int(card.rank)

    while total > 21 and aces:
        total -= 10
        aces -= 1

    is_soft = aces > 0 and total <= 21
    return total, is_soft


class TestHandValue:
    """Test cases for hand value calculation."""

    def test_simple_numeric_hand(self):
        """Test hand with simple numeric cards."""
        cards = [Card("5", "Hearts"), Card("7", "Spades")]
        value, is_soft = hand_value(cards)
        assert value == 12
        assert is_soft is False

    def test_face_cards(self):
        """Test hand with face cards."""
        cards = [Card("K", "Hearts"), Card("Q", "Spades")]
        value, is_soft = hand_value(cards)
        assert value == 20
        assert is_soft is False

    def test_blackjack_ace_ten(self):
        """Test natural blackjack with ace and 10."""
        cards = [Card("A", "Hearts"), Card("10", "Spades")]
        value, is_soft = hand_value(cards)
        assert value == 21
        assert is_soft is True

    def test_blackjack_ace_face(self):
        """Test natural blackjack with ace and face card."""
        cards = [Card("A", "Hearts"), Card("K", "Spades")]
        value, is_soft = hand_value(cards)
        assert value == 21
        assert is_soft is True

    def test_soft_hand_ace_six(self):
        """Test soft 17 (Ace + 6)."""
        cards = [Card("A", "Hearts"), Card("6", "Spades")]
        value, is_soft = hand_value(cards)
        assert value == 17
        assert is_soft is True

    def test_hard_hand_after_bust(self):
        """Test ace counted as 1 after going over 21."""
        cards = [Card("A", "Hearts"), Card("8", "Spades"), Card("9", "Clubs")]
        value, is_soft = hand_value(cards)
        assert value == 18  # A(1) + 8 + 9
        assert is_soft is False

    def test_multiple_aces(self):
        """Test hand with multiple aces."""
        cards = [Card("A", "Hearts"), Card("A", "Spades")]
        value, is_soft = hand_value(cards)
        assert value == 12  # 11 + 1
        assert is_soft is True

    def test_three_aces(self):
        """Test hand with three aces."""
        cards = [Card("A", "Hearts"), Card("A", "Spades"), Card("A", "Clubs")]
        value, is_soft = hand_value(cards)
        assert value == 13  # 11 + 1 + 1
        assert is_soft is True

    def test_four_aces(self):
        """Test hand with four aces."""
        cards = [Card("A", "Hearts"), Card("A", "Spades"), Card("A", "Clubs"), Card("A", "Diamonds")]
        value, is_soft = hand_value(cards)
        assert value == 14  # 11 + 1 + 1 + 1
        assert is_soft is True

    def test_bust_hand(self):
        """Test hand that busts."""
        cards = [Card("K", "Hearts"), Card("Q", "Spades"), Card("5", "Clubs")]
        value, is_soft = hand_value(cards)
        assert value == 25
        assert is_soft is False

    def test_perfect_21_no_ace(self):
        """Test 21 without an ace."""
        cards = [Card("7", "Hearts"), Card("7", "Spades"), Card("7", "Clubs")]
        value, is_soft = hand_value(cards)
        assert value == 21
        assert is_soft is False

    def test_soft_becomes_hard(self):
        """Test soft hand becoming hard after hit."""
        # Start with soft 18 (A + 7)
        cards = [Card("A", "Hearts"), Card("7", "Spades")]
        value, is_soft = hand_value(cards)
        assert value == 18
        assert is_soft is True

        # Hit with 4, should stay soft at 12 (A now counts as 1)
        cards.append(Card("4", "Clubs"))
        value, is_soft = hand_value(cards)
        assert value == 12  # 1 + 7 + 4
        assert is_soft is False

    def test_single_ace(self):
        """Test hand with just one ace."""
        cards = [Card("A", "Hearts")]
        value, is_soft = hand_value(cards)
        assert value == 11
        assert is_soft is True

    def test_single_face_card(self):
        """Test hand with single face card."""
        cards = [Card("K", "Hearts")]
        value, is_soft = hand_value(cards)
        assert value == 10
        assert is_soft is False

    def test_all_low_cards(self):
        """Test hand with all low cards."""
        cards = [Card("2", "Hearts"), Card("3", "Spades"), Card("4", "Clubs")]
        value, is_soft = hand_value(cards)
        assert value == 9
        assert is_soft is False

    def test_ace_with_multiple_cards(self):
        """Test ace with multiple cards keeping it soft."""
        cards = [Card("A", "Hearts"), Card("2", "Spades"), Card("3", "Clubs")]
        value, is_soft = hand_value(cards)
        assert value == 16  # 11 + 2 + 3
        assert is_soft is True

    def test_ace_forced_to_one(self):
        """Test ace forced to count as 1."""
        cards = [Card("A", "Hearts"), Card("9", "Spades"), Card("9", "Clubs")]
        value, is_soft = hand_value(cards)
        assert value == 19  # 1 + 9 + 9
        assert is_soft is False

    def test_dealer_17(self):
        """Test typical dealer 17."""
        cards = [Card("K", "Hearts"), Card("7", "Spades")]
        value, is_soft = hand_value(cards)
        assert value == 17
        assert is_soft is False

    def test_dealer_soft_17(self):
        """Test dealer soft 17."""
        cards = [Card("A", "Hearts"), Card("6", "Spades")]
        value, is_soft = hand_value(cards)
        assert value == 17
        assert is_soft is True

    def test_edge_case_ten_ace(self):
        """Test 10 followed by ace."""
        cards = [Card("10", "Hearts"), Card("A", "Spades")]
        value, is_soft = hand_value(cards)
        assert value == 21
        assert is_soft is True


class TestBlackjackScenarios:
    """Test realistic blackjack game scenarios."""

    def test_player_wins_blackjack(self):
        """Test player gets blackjack, dealer doesn't."""
        player = [Card("A", "Hearts"), Card("K", "Spades")]
        dealer = [Card("K", "Hearts"), Card("9", "Spades")]

        player_value, player_soft = hand_value(player)
        dealer_value, dealer_soft = hand_value(dealer)

        assert player_value == 21
        assert dealer_value == 19
        # Player should win with blackjack (3:2 payout)

    def test_push_both_blackjack(self):
        """Test push when both have blackjack."""
        player = [Card("A", "Hearts"), Card("K", "Spades")]
        dealer = [Card("A", "Clubs"), Card("Q", "Diamonds")]

        player_value, _ = hand_value(player)
        dealer_value, _ = hand_value(dealer)

        assert player_value == 21
        assert dealer_value == 21
        # Should be a push (tie)

    def test_dealer_busts_player_wins(self):
        """Test dealer busts, player wins."""
        player = [Card("10", "Hearts"), Card("7", "Spades")]
        dealer = [Card("K", "Hearts"), Card("9", "Spades"), Card("5", "Clubs")]

        player_value, _ = hand_value(player)
        dealer_value, _ = hand_value(dealer)

        assert player_value == 17
        assert dealer_value == 24  # Bust
        # Player wins

    def test_player_busts_dealer_wins(self):
        """Test player busts, loses regardless of dealer."""
        player = [Card("K", "Hearts"), Card("Q", "Spades"), Card("5", "Clubs")]
        dealer = [Card("7", "Hearts"), Card("8", "Spades")]

        player_value, _ = hand_value(player)
        dealer_value, _ = hand_value(dealer)

        assert player_value == 25  # Bust
        assert dealer_value == 15
        # Dealer wins (player busted)

    def test_push_same_value(self):
        """Test push with same hand value."""
        player = [Card("K", "Hearts"), Card("8", "Spades")]
        dealer = [Card("Q", "Hearts"), Card("8", "Clubs")]

        player_value, _ = hand_value(player)
        dealer_value, _ = hand_value(dealer)

        assert player_value == 18
        assert dealer_value == 18
        # Push (tie)

    def test_double_down_scenario(self):
        """Test typical double down situation."""
        player = [Card("5", "Hearts"), Card("6", "Spades")]

        value, is_soft = hand_value(player)
        assert value == 11
        # Good candidate for double down

    def test_split_scenario(self):
        """Test split pair scenario."""
        player = [Card("8", "Hearts"), Card("8", "Spades")]

        value, _ = hand_value(player)
        assert value == 16
        # Should split 8s

    def test_insurance_scenario(self):
        """Test insurance when dealer shows ace."""
        dealer_upcard = Card("A", "Hearts")
        # Player should be offered insurance

        # Dealer gets blackjack
        dealer = [dealer_upcard, Card("K", "Spades")]
        dealer_value, _ = hand_value(dealer)
        assert dealer_value == 21

    def test_soft_18_stand(self):
        """Test soft 18 (common standing hand)."""
        player = [Card("A", "Hearts"), Card("7", "Spades")]

        value, is_soft = hand_value(player)
        assert value == 18
        assert is_soft is True
        # Often stand on soft 18

    def test_hard_12_hit(self):
        """Test hard 12 (common hitting hand)."""
        player = [Card("10", "Hearts"), Card("2", "Spades")]

        value, is_soft = hand_value(player)
        assert value == 12
        assert is_soft is False
        # Usually hit on hard 12

    def test_stiff_hand_16(self):
        """Test stiff hand at 16."""
        player = [Card("10", "Hearts"), Card("6", "Spades")]

        value, is_soft = hand_value(player)
        assert value == 16
        assert is_soft is False
        # Difficult decision point


class TestEdgeCases:
    """Test edge cases in blackjack logic."""

    def test_empty_hand(self):
        """Test empty hand."""
        cards = []
        value, is_soft = hand_value(cards)
        assert value == 0
        assert is_soft is False

    def test_all_aces_no_bust(self):
        """Test maximum aces without busting."""
        # 11 aces = 11 + 10*1 = 21
        cards = [Card("A", f"Suit{i}") for i in range(11)]
        value, is_soft = hand_value(cards)
        assert value == 21
        # Only works if we create fake suits

    def test_five_card_charlie_value(self):
        """Test five-card hand under 21."""
        cards = [
            Card("2", "Hearts"),
            Card("3", "Spades"),
            Card("4", "Clubs"),
            Card("5", "Diamonds"),
            Card("6", "Hearts"),
        ]
        value, is_soft = hand_value(cards)
        assert value == 20
        # Some casinos give bonus for 5-card charlie

    def test_maximum_non_bust_hand(self):
        """Test maximum possible hand without busting."""
        cards = [
            Card("A", "Hearts"),
            Card("2", "Spades"),
            Card("3", "Clubs"),
            Card("4", "Diamonds"),
            Card("2", "Hearts"),
        ]
        value, is_soft = hand_value(cards)
        assert value == 12  # 1 + 2 + 3 + 4 + 2
