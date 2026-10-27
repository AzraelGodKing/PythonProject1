import random

import pytest

from arcade.games.tictactoe import logic, sim
from arcade.games.tictactoe.logic import Game, Match, Opponent


def board(text: str) -> list[str]:
    """Build a board from a 9 character string such as ``"XO.X....."``."""
    return ["" if ch == "." else ch for ch in text]


def test_winner_and_lines():
    assert logic.winner(board("XXX......")) == "X"
    assert logic.winner(board("O...O...O")) == "O"
    assert logic.winner(board("XOXXOOOXX")) is None
    assert logic.winning_line(board("..X.X.X..")) == (2, 4, 6)
    assert logic.winning_line(board(".........")) is None
    assert logic.is_over(board("XOXXOOOXX"))


def test_finishing_move_and_forks():
    assert logic.finishing_move(board("XX......."), "X") == 2
    assert logic.finishing_move(board("X..X....."), "X") == 6
    assert logic.finishing_move(board("XO......."), "X") is None
    # X in two corners with O in the middle: either free corner creates two threats.
    assert set(logic.fork_moves(board("X...O...X"), "X")) == {2, 6}
    assert logic.fork_moves(board("........."), "X") == []


def test_hard_never_loses_from_any_opening():
    rng = random.Random(0)
    hard = Opponent("hard")
    for first in range(9):
        for _ in range(3):
            game = Game(starter="X")
            game.play(first)
            while not game.over:
                if game.to_move == "O":
                    game.play(hard.move(game.board, "O", rng))
                else:
                    game.play(rng.choice(logic.open_cells(game.board)))
            assert game.result != "X"


def test_hard_vs_hard_always_draws():
    assert logic.simulate(Opponent("hard"), Opponent("hard"), 20, seed=1) == {"draw": 20}


def test_hard_takes_win_over_block():
    b = board("OO.XX....")
    assert logic.hard(b, "O", random.Random(0)) == 2


def test_negamax_prefers_faster_win():
    b = board("OO.XX.X..")
    scores = logic.move_scores(b, "O")
    assert max(scores, key=scores.get) == 2


@pytest.mark.parametrize("personality", logic.PERSONALITIES)
def test_personalities_win_and_block(personality):
    rng = random.Random(4)
    strategy = logic.NORMAL[personality]
    assert strategy(board("OO.X.X..."), "O", rng) == 2  # take the win
    assert strategy(board("XX..O...."), "O", rng) == 2  # block
    # Always returns a legal move.
    for _ in range(20):
        b = [""] * 9
        moves = rng.sample(range(9), rng.randint(0, 6))
        for i, cell in enumerate(moves):
            b[cell] = "X" if i % 2 == 0 else "O"
        if logic.is_over(b):
            continue
        assert b[strategy(b, "O", rng)] == ""


def test_easy_and_humanish_mistakes():
    rng = random.Random(9)
    assert Opponent("easy").move(board("XOXOXO..."), "X", rng) in (6, 7, 8)
    sloppy = Opponent("normal", "balanced", error_rate=1.0)
    moves = {sloppy.move(board("XX..O...."), "O", random.Random(s)) for s in range(30)}
    assert len(moves) > 1  # sometimes misses the block
    with pytest.raises(ValueError):
        Opponent("hard").move(board("XOXXOOOXX"), "X", rng)


def test_opponent_validation_and_key():
    assert Opponent("hard").key == "hard"
    assert Opponent("normal", "mirror").key == "normal:mirror"
    with pytest.raises(ValueError):
        Opponent("impossible")
    with pytest.raises(ValueError):
        Opponent("normal", "sneaky")


def test_game_flow_and_undo():
    game = Game(starter="O")
    assert game.to_move == "O"
    game.play(4)
    assert game.to_move == "X"
    with pytest.raises(ValueError):
        game.play(4)
    with pytest.raises(ValueError):
        game.play(9)
    game.undo()
    assert game.board == [""] * 9 and game.to_move == "O"
    game.undo(5)  # undoing past the start is harmless
    for cell in (0, 3, 1, 4, 2):
        game.play(cell)
    assert game.result == "O"
    with pytest.raises(ValueError):
        game.play(8)


def test_match_best_of_three():
    match = Match(3)
    assert match.target == 2
    match.record("X")
    match.record("draw")
    assert not match.over
    match.record("X")
    assert match.champion == "X"
    assert match.games_played == 3
    with pytest.raises(ValueError):
        match.record("O")
    with pytest.raises(ValueError):
        Match(2)


def test_simulate_alternates_starter():
    results = logic.simulate(Opponent("easy"), Opponent("easy"), 50, seed=3)
    assert sum(results.values()) == 50
    assert logic.play_out(Opponent("hard"), Opponent("hard"), random.Random(1), starter="O") == "draw"


def test_achievements():
    assert logic.earned_achievements({}) == set()
    stats = {"wins": 1, "best_streak": 3, "games": 10, "draws:hard": 1, "match_wins": 1}
    stats |= {f"wins:normal:{p}": 1 for p in logic.PERSONALITIES}
    assert logic.earned_achievements(stats) == set(logic.ACHIEVEMENTS)


def test_sim_cli(capsys):
    assert sim.main(["--x", "hard", "--o", "normal:mirror", "--rounds", "10", "--seed", "1"]) == 0
    out = capsys.readouterr().out
    assert "10 games" in out and "Draws" in out
    with pytest.raises(SystemExit):
        sim.main(["--rounds", "0"])
    assert sim.parse_opponent("normal:aggressive") == Opponent("normal", "aggressive")
    assert sim.parse_opponent("easy") == Opponent("easy")
