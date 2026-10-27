import random

import pytest

from arcade.games.yahtzee.logic import CATEGORIES, UPPER, Yahtzee, score


@pytest.mark.parametrize(
    ("category", "dice", "points"),
    [
        ("ones", [1, 1, 2, 3, 1], 3),
        ("sixes", [6, 6, 6, 2, 1], 18),
        ("three_kind", [3, 3, 3, 4, 5], 18),
        ("three_kind", [3, 3, 2, 4, 5], 0),
        ("four_kind", [2, 2, 2, 2, 6], 14),
        ("four_kind", [5, 5, 5, 5, 5], 25),
        ("full_house", [2, 2, 3, 3, 3], 25),
        ("full_house", [4, 4, 4, 4, 4], 0),
        ("small_straight", [1, 2, 3, 4, 6], 30),
        ("small_straight", [3, 4, 5, 6, 6], 30),
        ("small_straight", [1, 2, 3, 5, 6], 0),
        ("large_straight", [2, 3, 4, 5, 6], 40),
        ("large_straight", [1, 2, 3, 4, 6], 0),
        ("yahtzee", [4, 4, 4, 4, 4], 50),
        ("yahtzee", [4, 4, 4, 4, 3], 0),
        ("chance", [1, 2, 3, 4, 6], 16),
    ],
)
def test_scoring(category, dice, points):
    assert score(category, dice) == points


def test_joker_scoring_and_validation():
    assert score("large_straight", [3, 3, 3, 3, 3], joker=True) == 40
    assert score("full_house", [3, 3, 3, 3, 3], joker=True) == 25
    with pytest.raises(ValueError):
        score("ones", [1, 2, 3])
    with pytest.raises(ValueError):
        score("ones", [0, 1, 2, 3, 4])
    with pytest.raises(KeyError):
        score("bogus", [1, 1, 1, 1, 1])


def test_turn_flow():
    game = Yahtzee(rng=random.Random(1))
    assert not game.turn_started
    assert not game.can_score("chance")
    game.toggle_hold(0)  # ignored before the first roll
    assert game.held == [False] * 5
    assert game.roll()
    game.toggle_hold(0)
    kept = game.dice[0]
    game.roll()
    game.roll()
    assert game.dice[0] == kept
    assert not game.roll()  # three rolls max
    game.toggle_hold(1)  # can't hold with no rolls left
    assert not game.held[1]
    points = game.choose("chance")
    assert points == sum(game.dice)
    assert game.rolls_left == 3 and game.held == [False] * 5
    with pytest.raises(ValueError):
        game.choose("chance")


def test_upper_bonus_and_total():
    game = Yahtzee()
    for face, cat in enumerate(UPPER, start=1):
        game.card[cat] = face * 3
    assert game.upper_total == 63
    assert game.upper_bonus == 35
    assert game.total == 63 + 35


def test_yahtzee_bonus_and_joker():
    game = Yahtzee()
    game.card["yahtzee"] = 50
    game.dice = [6] * 5
    game.rolls_left = 2
    assert game.potential("large_straight") == 40
    game.choose("large_straight")
    assert game.yahtzee_bonus == 100

    zeroed = Yahtzee()
    zeroed.card["yahtzee"] = 0  # scratched: joker yes, bonus no
    zeroed.dice = [2] * 5
    zeroed.rolls_left = 2
    zeroed.choose("full_house")
    assert zeroed.yahtzee_bonus == 0
    assert zeroed.card["full_house"] == 25


def test_full_game_ends():
    game = Yahtzee(rng=random.Random(3))
    for category in CATEGORIES:
        game.roll()
        game.choose(category)
    assert game.over
    assert not game.roll()
    assert not game.can_score("chance")
    assert game.total >= 0
