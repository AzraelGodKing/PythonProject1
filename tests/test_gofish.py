import random

import pytest

from arcade.core.cards import RANKS, cards
from arcade.games.gofish.logic import AI, PLAYER, GoFish


def make(player: str, ai: str, pond: str = "", **kw) -> GoFish:
    game = GoFish(rng=random.Random(0), **kw)
    game.hands = {PLAYER: cards(player), AI: cards(ai)}
    game.pond = cards(pond)
    return game


def test_deal():
    game = GoFish.deal(random.Random(1))
    held = len(game.hands[PLAYER]) + len(game.hands[AI])
    booked = 4 * (len(game.books[PLAYER]) + len(game.books[AI]))
    assert held + booked + len(game.pond) == 52


def test_initial_books_are_counted():
    game = make("AS AH AD AC 2S", "3S")
    game._collect_books(PLAYER)
    assert game.books[PLAYER] == ["A"]
    assert game.hands[PLAYER] == cards("2S")


def test_successful_ask_takes_all_and_goes_again():
    game = make("5S 9C", "5H 5D KC", "2C")
    assert game.ask("5")
    assert game.turn == PLAYER
    assert sorted(c.rank for c in game.hands[PLAYER]) == ["5", "5", "5", "9"]
    assert game.hands[AI] == cards("KC")
    assert game.log[-1] == ("gofish.log.took", {"who": PLAYER, "count": 2, "rank": "5"})


def test_failed_ask_fishes_and_passes_turn():
    game = make("5S", "KC", "2C")
    assert not game.ask("5")
    assert game.turn == AI
    assert cards("2C")[0] in game.hands[PLAYER]
    assert "5" in game.memory


def test_fishing_the_asked_rank_earns_another_turn():
    game = make("5S", "KC", "5D")
    assert game.ask("5")
    assert game.turn == PLAYER
    assert game.log[-1][0] == "gofish.log.lucky"


def test_cannot_ask_for_a_rank_you_do_not_hold():
    game = make("5S", "KC")
    with pytest.raises(ValueError):
        game.ask("K")


def test_book_completion_and_game_end():
    game = make("7S 7H 7D", "7C")
    game.books = {PLAYER: [r for r in RANKS if r not in ("7",)][:6], AI: [r for r in RANKS if r != "7"][6:]}
    game.ask("7")
    assert game.over
    assert game.winner == PLAYER
    assert game.books[PLAYER][-1] == "7"


def test_empty_hand_draws_before_turn():
    game = make("4S", "4H 9D", "QS QC")
    game.ask("4")  # takes the 4, no book; still has cards
    game.hands[PLAYER] = []
    game._refill(PLAYER)
    assert len(game.hands[PLAYER]) == 1
    assert game.log[-1][0] == "gofish.log.empty_draw"


def test_turn_skips_player_with_nothing_to_do():
    game = make("3S", "4H", "")
    game.books = {PLAYER: list(RANKS[:6]), AI: list(RANKS[6:12])}
    game.hands[AI] = []
    game.ask("3")  # no 3s, pond empty: the AI can't move, so it comes straight back
    assert game.turn == PLAYER


def test_smart_ai_uses_memory():
    game = make("9S 2C", "9H 4D 4C", "")
    game.memory = {"9"}
    game.turn = AI
    assert game.ai_choice() == "9"
    game.memory = set()
    assert game.ai_choice() == "4"  # most cards of that rank
    game.ai_turn()  # no 4s in the player's hand and an empty pond: turn passes
    assert game.turn == PLAYER
    with pytest.raises(ValueError):
        game.ai_turn()


def test_random_ai_only_asks_for_ranks_it_holds():
    game = make("9S", "4D KC", "", smart_ai=False)
    game.turn = AI
    for _ in range(10):
        assert game.ai_choice() in ("4", "K")


def test_full_random_games_terminate():
    for seed in range(20):
        game = GoFish.deal(random.Random(seed))
        rng = random.Random(seed + 100)
        for _ in range(500):
            if game.over:
                break
            if game.turn == PLAYER:
                game.ask(rng.choice(game.ranks_in_hand(PLAYER)))
            else:
                game.ai_turn()
        assert game.over
        assert len(game.books[PLAYER]) + len(game.books[AI]) == 13
        assert game.winner in (PLAYER, AI, "draw")
