import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent / "a tic-tac-toe game"
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from shared.deck import Card, Deck, JOKER, RANKS, SUITS, VERSION


def test_version_constant():
    assert VERSION == 2


def test_builds_full_deck_and_jokers():
    deck = Deck(include_jokers=True)
    assert len(deck) == 54
    assert deck.remaining() == 54
    # Two jokers should be present when requested
    joker_cards = [card for card in deck if card.rank == JOKER]
    assert len(joker_cards) == 2


def test_multiple_decks_supported():
    two_decks = Deck(num_decks=2)
    assert len(two_decks) == 52 * 2
    hand = two_decks.deal_hands(4, 5)
    assert len(hand) == 4
    assert all(len(cards) == 5 for cards in hand)
    assert two_decks.remaining() == 52 * 2 - 20


def test_draw_and_discard_cycle():
    deck = Deck(include_jokers=False, seed=123)
    deck.shuffle()
    drawn = deck.draw(3)
    assert len(drawn) == 3
    assert deck.remaining() == 49
    deck.discard(drawn[0])
    deck.discard(drawn[1:])
    assert deck.discard_count() == 3
    deck.recycle_discards(shuffle=False)
    assert deck.discard_count() == 0
    assert deck.remaining() == 52


def test_card_helpers():
    card = Card("A", "Spades")
    assert card.label() == "A of Spades"
    assert card.short_name() == "AS"
    assert Card.from_label("A of Spades") == card
    assert Card.from_label("QD") == Card("Q", "Diamonds")
    assert SUITS == ("Spades", "Hearts", "Clubs", "Diamonds")
    assert RANKS[0] == "A"
