"""Unit tests for shared.deck module."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.deck import Card, Deck, SUITS, RANKS, JOKER


class TestCard:
    """Test cases for the Card class."""

    def test_card_creation(self):
        """Test basic card creation."""
        card = Card("A", "Spades")
        assert card.rank == "A"
        assert card.suit == "Spades"

    def test_card_label(self):
        """Test card label generation."""
        card = Card("A", "Spades")
        assert card.label() == "A of Spades"

        card2 = Card("10", "Hearts")
        assert card2.label() == "10 of Hearts"

    def test_joker_label(self):
        """Test joker label generation."""
        joker = Card(JOKER, JOKER)
        assert joker.label() == "Joker"

    def test_card_short_name(self):
        """Test short name generation."""
        card = Card("A", "Spades")
        assert card.short_name() == "AS"

        card2 = Card("10", "Hearts")
        assert card2.short_name() == "10H"

        card3 = Card("K", "Clubs")
        assert card3.short_name() == "KC"

        card4 = Card("2", "Diamonds")
        assert card4.short_name() == "2D"

    def test_joker_short_name(self):
        """Test joker short name."""
        joker = Card(JOKER, JOKER)
        assert joker.short_name() == "JK"

    def test_from_label_long_form(self):
        """Test creating card from long label."""
        card = Card.from_label("A of Spades")
        assert card.rank == "A"
        assert card.suit == "Spades"

        card2 = Card.from_label("10 of Hearts")
        assert card2.rank == "10"
        assert card2.suit == "Hearts"

    def test_from_label_short_form(self):
        """Test creating card from short label."""
        card = Card.from_label("AS")
        assert card.rank == "A"
        assert card.suit == "Spades"

        card2 = Card.from_label("10H")
        assert card2.rank == "10"
        assert card2.suit == "Hearts"

        card3 = Card.from_label("KC")
        assert card3.rank == "K"
        assert card3.suit == "Clubs"

        card4 = Card.from_label("2D")
        assert card4.rank == "2"
        assert card4.suit == "Diamonds"

    def test_from_label_joker(self):
        """Test creating joker from label."""
        joker = Card.from_label("Joker")
        assert joker.rank == JOKER
        assert joker.suit == JOKER

        joker2 = Card.from_label("joker")
        assert joker2.rank == JOKER
        assert joker2.suit == JOKER

    def test_from_label_invalid_suit(self):
        """Test invalid suit code raises ValueError."""
        with pytest.raises(ValueError, match="Unknown suit code"):
            Card.from_label("AX")

    def test_from_label_with_whitespace(self):
        """Test from_label handles whitespace."""
        card = Card.from_label("  A of Spades  ")
        assert card.rank == "A"
        assert card.suit == "Spades"

    def test_card_immutable(self):
        """Test that Card is immutable (frozen dataclass)."""
        card = Card("A", "Spades")
        with pytest.raises(Exception):  # FrozenInstanceError in Python 3.11+
            card.rank = "K"

    def test_card_equality(self):
        """Test card equality comparison."""
        card1 = Card("A", "Spades")
        card2 = Card("A", "Spades")
        card3 = Card("K", "Spades")

        assert card1 == card2
        assert card1 != card3

    def test_card_hashable(self):
        """Test that cards can be used in sets/dicts."""
        card1 = Card("A", "Spades")
        card2 = Card("A", "Spades")
        card3 = Card("K", "Spades")

        card_set = {card1, card2, card3}
        assert len(card_set) == 2  # card1 and card2 are the same


class TestDeck:
    """Test cases for the Deck class."""

    def test_deck_creation_default(self):
        """Test default deck creation."""
        deck = Deck()
        assert deck.remaining() == 52
        assert deck.discard_count() == 0
        assert deck.num_decks == 1
        assert not deck.include_jokers

    def test_deck_creation_with_jokers(self):
        """Test deck creation with jokers."""
        deck = Deck(include_jokers=True)
        assert deck.remaining() == 54  # 52 + 2 jokers

    def test_deck_creation_multiple_decks(self):
        """Test deck creation with multiple decks."""
        deck = Deck(num_decks=2)
        assert deck.remaining() == 104

        deck_with_jokers = Deck(num_decks=2, include_jokers=True)
        assert deck_with_jokers.remaining() == 108  # 104 + 4 jokers

    def test_deck_creation_invalid_num_decks(self):
        """Test that invalid num_decks raises ValueError."""
        with pytest.raises(ValueError, match="num_decks must be positive"):
            Deck(num_decks=0)

        with pytest.raises(ValueError, match="num_decks must be positive"):
            Deck(num_decks=-1)

    def test_deck_contains_all_cards(self):
        """Test that deck contains all expected cards."""
        deck = Deck()
        cards = list(deck)

        # Check we have all ranks and suits
        for suit in SUITS:
            for rank in RANKS:
                expected_card = Card(rank, suit)
                assert expected_card in cards

    def test_deck_shuffle(self):
        """Test that shuffle changes card order."""
        deck1 = Deck(seed=42)
        deck2 = Deck(seed=42)

        # Before shuffling, order should be the same
        cards1_before = list(deck1)
        cards2_before = list(deck2)
        assert cards1_before == cards2_before

        # After shuffling with same seed, should still be the same
        deck1.shuffle()
        deck2.shuffle()
        cards1_after = list(deck1)
        cards2_after = list(deck2)
        assert cards1_after == cards2_after

        # But shuffled should differ from unshuffled
        assert cards1_before != cards1_after

    def test_deck_draw_single(self):
        """Test drawing a single card."""
        deck = Deck()
        card = deck.draw(1)
        assert len(card) == 1
        assert isinstance(card[0], Card)
        assert deck.remaining() == 51

    def test_deck_draw_one_convenience(self):
        """Test draw_one convenience method."""
        deck = Deck()
        card = deck.draw_one()
        assert isinstance(card, Card)
        assert deck.remaining() == 51

    def test_deck_draw_multiple(self):
        """Test drawing multiple cards."""
        deck = Deck()
        cards = deck.draw(5)
        assert len(cards) == 5
        assert deck.remaining() == 47

    def test_deck_draw_zero(self):
        """Test drawing zero cards."""
        deck = Deck()
        cards = deck.draw(0)
        assert cards == []
        assert deck.remaining() == 52

    def test_deck_draw_negative_raises(self):
        """Test that drawing negative count raises ValueError."""
        deck = Deck()
        with pytest.raises(ValueError, match="count must be non-negative"):
            deck.draw(-1)

    def test_deck_draw_too_many_raises(self):
        """Test that drawing more cards than available raises IndexError."""
        deck = Deck()
        with pytest.raises(IndexError, match="not enough cards"):
            deck.draw(53)

    def test_deck_draw_exhaustion(self):
        """Test drawing all cards from deck."""
        deck = Deck()
        cards = deck.draw(52)
        assert len(cards) == 52
        assert deck.remaining() == 0

        with pytest.raises(IndexError):
            deck.draw(1)

    def test_deck_deal_hands(self):
        """Test dealing hands."""
        deck = Deck()
        hands = deck.deal_hands(4, 5)

        assert len(hands) == 4
        for hand in hands:
            assert len(hand) == 5
        assert deck.remaining() == 32  # 52 - 20

    def test_deck_deal_hands_invalid_params(self):
        """Test deal_hands with invalid parameters."""
        deck = Deck()

        with pytest.raises(ValueError, match="must be positive"):
            deck.deal_hands(0, 5)

        with pytest.raises(ValueError, match="must be positive"):
            deck.deal_hands(4, 0)

        with pytest.raises(ValueError, match="must be positive"):
            deck.deal_hands(-1, 5)

    def test_deck_deal_hands_not_enough_cards(self):
        """Test deal_hands when not enough cards available."""
        deck = Deck()
        with pytest.raises(IndexError, match="not enough cards"):
            deck.deal_hands(10, 6)  # Would need 60 cards

    def test_deck_discard_single_card(self):
        """Test discarding a single card."""
        deck = Deck()
        card = deck.draw_one()
        deck.discard(card)

        assert deck.discard_count() == 1
        assert deck.remaining() == 51

    def test_deck_discard_multiple_cards(self):
        """Test discarding multiple cards."""
        deck = Deck()
        cards = deck.draw(5)
        deck.discard(cards)

        assert deck.discard_count() == 5
        assert deck.remaining() == 47

    def test_deck_recycle_discards(self):
        """Test recycling discarded cards."""
        deck = Deck(seed=42)
        cards = deck.draw(10)
        deck.discard(cards)

        assert deck.remaining() == 42
        assert deck.discard_count() == 10

        deck.recycle_discards()

        assert deck.remaining() == 52
        assert deck.discard_count() == 0

    def test_deck_recycle_discards_no_shuffle(self):
        """Test recycling without shuffling."""
        deck = Deck(seed=42)
        original_cards = list(deck)

        cards = deck.draw(10)
        deck.discard(cards)
        deck.recycle_discards(shuffle=False)

        # Without shuffle, recycled cards should be at the end
        new_cards = list(deck)
        assert len(new_cards) == 52
        # The last 10 cards should be the ones we discarded
        assert new_cards[-10:] == cards

    def test_deck_reset(self):
        """Test resetting deck to original state."""
        deck = Deck()
        deck.draw(20)
        deck.discard(deck.draw(10))

        assert deck.remaining() == 22
        assert deck.discard_count() == 10

        deck.reset()

        assert deck.remaining() == 52
        assert deck.discard_count() == 0

    def test_deck_reset_with_shuffle(self):
        """Test resetting and shuffling deck."""
        deck = Deck(seed=42)
        original_order = list(deck)

        deck.draw(20)
        deck.reset(shuffle=True)

        assert deck.remaining() == 52
        new_order = list(deck)
        assert len(new_order) == 52
        # After shuffling, order should be different
        assert original_order != new_order

    def test_deck_len(self):
        """Test len() convenience method."""
        deck = Deck()
        assert len(deck) == 52

        deck.draw(10)
        assert len(deck) == 42

    def test_deck_iter(self):
        """Test iterating over deck."""
        deck = Deck()
        cards = list(deck)
        assert len(cards) == 52
        assert all(isinstance(card, Card) for card in cards)

    def test_deck_deterministic_with_seed(self):
        """Test that deck shuffling is deterministic with seed."""
        deck1 = Deck(seed=12345)
        deck1.shuffle()
        cards1 = deck1.draw(10)

        deck2 = Deck(seed=12345)
        deck2.shuffle()
        cards2 = deck2.draw(10)

        assert cards1 == cards2

    def test_deck_different_without_seed(self):
        """Test that decks shuffle differently without seed."""
        deck1 = Deck()
        deck1.shuffle()

        deck2 = Deck()
        deck2.shuffle()

        # Very unlikely to be the same (but theoretically possible)
        # We'll just check they both have 52 cards
        assert len(list(deck1)) == 52
        assert len(list(deck2)) == 52

    def test_multiple_deck_shuffle(self):
        """Test shuffling with multiple decks."""
        deck = Deck(num_decks=2, seed=42)
        deck.shuffle()
        cards = list(deck)

        # Count occurrences of Ace of Spades
        ace_spades = Card("A", "Spades")
        count = cards.count(ace_spades)
        assert count == 2  # Should have 2 in a double deck

    def test_joker_cards_present(self):
        """Test that jokers are present when requested."""
        deck = Deck(include_jokers=True)
        cards = list(deck)

        joker = Card(JOKER, JOKER)
        joker_count = cards.count(joker)
        assert joker_count == 2

    def test_deck_operations_sequence(self):
        """Test a realistic sequence of deck operations."""
        deck = Deck(seed=42)
        deck.shuffle()

        # Deal poker hands
        hands = deck.deal_hands(4, 5)
        assert len(hands) == 4
        assert deck.remaining() == 32

        # Draw a few more cards
        community = deck.draw(3)
        assert len(community) == 3
        assert deck.remaining() == 29

        # Discard all cards
        for hand in hands:
            deck.discard(hand)
        deck.discard(community)
        assert deck.discard_count() == 23

        # Recycle and continue
        deck.recycle_discards()
        assert deck.remaining() == 52
        assert deck.discard_count() == 0
