import random

import pytest

from arcade.core.cards import Card, Shoe, cards, full_deck
from arcade.core.chips import Bank, InsufficientChips


def test_card_parse_and_properties():
    card = Card.parse("10h")
    assert card == Card("10", "hearts")
    assert card.is_red
    assert str(card) == "10♥"
    assert Card.parse("KS").rank_index == 13
    assert Card.parse("AC").rank_index == 1
    with pytest.raises(ValueError):
        Card.parse("AX")
    with pytest.raises(ValueError):
        Card("1", "spades")
    with pytest.raises(ValueError):
        Card("A", "stars")


def test_full_deck_is_unique():
    deck = full_deck()
    assert len(deck) == len(set(deck)) == 52


def test_shoe_deals_every_card_once_per_deck():
    shoe = Shoe(2, rng=random.Random(1))
    drawn = shoe.draw_many(104)
    assert len(shoe) == 0
    assert all(drawn.count(card) == 2 for card in full_deck())


def test_shoe_never_duplicates_cards_in_play():
    shoe = Shoe(1, rng=random.Random(2))
    in_play = shoe.draw_many(50)
    shoe.discard(in_play[:40])
    more = shoe.draw_many(12)  # forces a reshuffle of the discards only
    on_table = in_play[40:] + more
    assert len(on_table) == len(set(on_table))


def test_shoe_empty_raises():
    shoe = Shoe.stacked(cards("AS"))
    shoe.draw()
    with pytest.raises(IndexError):
        shoe.draw()


def test_needs_shuffle_and_validation():
    shoe = Shoe(1, rng=random.Random(3))
    assert not shoe.needs_shuffle()
    shoe.draw_many(40)
    assert shoe.needs_shuffle()
    assert not Shoe.stacked(cards("AS")).needs_shuffle()
    with pytest.raises(ValueError):
        Shoe(0)


def test_bank():
    bank = Bank(100, credit=50)
    assert bank.can_afford(150)
    assert not bank.can_afford(151)
    assert not bank.can_afford(0)
    bank.take(120)
    assert bank.balance == -20
    with pytest.raises(InsufficientChips):
        bank.take(31)
    with pytest.raises(ValueError):
        bank.take(-1)
    bank.pay(40)
    assert bank.balance == 20
    with pytest.raises(ValueError):
        bank.pay(-5)
