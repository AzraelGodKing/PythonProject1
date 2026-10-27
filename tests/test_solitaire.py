import random

import pytest

from arcade.core.cards import Card, cards
from arcade.games.solitaire.logic import Klondike


def test_deal_layout():
    game = Klondike.deal(1, random.Random(1))
    assert [len(col) for col in game.tableau] == [1, 2, 3, 4, 5, 6, 7]
    assert game.hidden == [0, 1, 2, 3, 4, 5, 6]
    assert len(game.stock) == 24
    every = game.stock + [c for col in game.tableau for c in col]
    assert len(set(every)) == 52
    with pytest.raises(ValueError):
        Klondike.deal(2)


def test_draw_one_and_three_and_recycle():
    game = Klondike.deal(3, random.Random(2))
    game.draw()
    assert len(game.waste) == 3
    for _ in range(7):
        game.draw()
    assert not game.stock and len(game.waste) == 24
    top_before = game.waste[0]
    game.draw()  # recycle
    assert game.passes == 1 and not game.waste and game.stock[-1] == top_before
    empty = Klondike()
    assert not empty.draw()


def test_foundation_rules():
    game = Klondike()
    game.waste = cards("AH")
    assert not game.can_move(("waste",), ("foundation", 0))  # spades pile
    assert game.to_foundation(("waste",))
    assert game.foundations[1] == cards("AH")
    game.waste = cards("3H")
    assert not game.to_foundation(("waste",))
    game.waste = cards("2H")
    assert game.to_foundation(("waste",))


def test_tableau_alternating_colours_and_kings_on_empty():
    game = Klondike()
    game.tableau[0] = cards("8S")
    game.waste = cards("7H")
    assert game.can_move(("waste",), ("tableau", 0, 1))
    game.waste = cards("7C")
    assert not game.can_move(("waste",), ("tableau", 0, 1))
    game.waste = cards("QD")
    assert not game.can_move(("waste",), ("tableau", 1, 0))
    game.waste = cards("KD")
    assert game.can_move(("waste",), ("tableau", 1, 0))


def test_moving_a_stack_flips_the_exposed_card():
    game = Klondike()
    game.tableau[0] = cards("2C 9S 8H")
    game.hidden[0] = 1  # 2C face down
    game.tableau[1] = cards("10H")
    assert game.move(("tableau", 0, 1), ("tableau", 1, 1))
    assert game.tableau[1] == cards("10H 9S 8H")
    assert game.tableau[0] == cards("2C")
    assert game.hidden[0] == 0
    assert not game.cards_at(("tableau", 0, 5))


def test_face_down_cards_cannot_move():
    game = Klondike()
    game.tableau[0] = cards("QH 2C")
    game.hidden[0] = 1
    game.tableau[1] = cards("KS")
    assert not game.can_move(("tableau", 0, 0), ("tableau", 1, 1))
    assert not game.can_move(("tableau", 0, 1), ("tableau", 0, 2))  # same column


def test_undo_restores_state():
    game = Klondike.deal(1, random.Random(5))
    before = (list(game.stock), list(game.waste), game.moves)
    game.draw()
    assert game.can_undo()
    game.undo()
    assert (game.stock, game.waste, game.moves) == before
    assert not game.can_undo()
    game.undo()  # no-op


def test_best_destination_and_autocomplete_win():
    game = Klondike()
    for i, suit in enumerate(("spades", "hearts", "diamonds", "clubs")):
        game.foundations[i] = [Card(r, suit) for r in ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J")]
    game.tableau[0] = cards("KS QH")
    game.tableau[1] = cards("KH QS")
    game.tableau[2] = cards("KD QC")
    game.tableau[3] = cards("KC QD")
    assert game.best_destination(("tableau", 0, 1)) == ("foundation", 1)
    assert game.can_autocomplete()
    assert game.autocomplete() == 8
    assert game.won
    assert not game.can_autocomplete()


def test_best_destination_prefers_tableau_and_skips_pointless_king_moves():
    game = Klondike()
    game.tableau[0] = cards("KS")
    game.tableau[1] = cards("10C")
    game.tableau[2] = cards("9H")
    assert game.best_destination(("tableau", 2, 0)) == ("tableau", 1, 1)
    assert game.best_destination(("tableau", 0, 0)) is None  # king already at the bottom
    assert game.best_destination(("waste",)) is None
