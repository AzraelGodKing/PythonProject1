import random

import pytest

from arcade.games.minesweeper.logic import DIFFICULTIES, Board, State


def small(mines):
    board = Board(4, 4, len(mines) if mines else 1, rng=random.Random(0))
    board.place_mines((0, 0), positions=mines)
    return board


@pytest.mark.parametrize("name", DIFFICULTIES)
def test_first_click_is_always_safe_and_opens_an_area(name):
    for seed in range(15):
        board = Board.for_difficulty(name, random.Random(seed))
        r, c = board.rows // 2, board.cols // 2
        opened = board.reveal(r, c)
        assert board.state is State.PLAYING or board.state is State.WON
        assert len(opened) > 1
        assert sum(cell.mine for row in board.cells for cell in row) == board.mines
        assert board.cells[r][c].adjacent == 0


def test_adjacent_counts():
    board = small([(0, 0), (0, 1)])
    assert board.cells[1][0].adjacent == 2
    assert board.cells[1][2].adjacent == 1
    assert board.cells[3][3].adjacent == 0


def test_flood_fill_stops_at_numbers_and_win():
    board = small([(0, 0)])
    opened = board.reveal(3, 3)
    assert (0, 0) not in opened
    assert board.state is State.WON
    assert board.cells[0][0].flagged  # remaining mines flagged on win


def test_hitting_a_mine_loses():
    board = small([(3, 3), (0, 3)])
    board.reveal(3, 3)
    assert board.state is State.LOST
    assert board.exploded == (3, 3)
    assert board.reveal(0, 0) == []
    assert not board.toggle_flag(1, 1)


def test_flags_block_reveal_and_count():
    board = small([(3, 3), (0, 3)])
    assert board.toggle_flag(3, 3)
    assert board.mines_left == 1
    assert board.reveal(3, 3) == []
    assert board.toggle_flag(3, 3)
    assert board.flags == 0


def test_chording():
    board = small([(0, 2), (2, 2)])
    board.reveal(1, 1)
    assert board.cells[1][1].adjacent == 2
    assert board.chord(1, 1) == []  # flags don't match yet
    board.toggle_flag(0, 2)
    board.toggle_flag(2, 2)
    opened = board.chord(1, 1)
    assert (0, 0) in opened or board.cells[0][0].revealed
    assert board.state is not State.LOST


def test_wrong_flag_chord_loses():
    board = small([(0, 2), (2, 2)])
    board.reveal(1, 1)
    board.toggle_flag(0, 2)
    board.toggle_flag(0, 0)  # wrong
    board.chord(1, 1)
    assert board.state is State.LOST


def test_validation():
    with pytest.raises(ValueError):
        Board(1, 5, 1)
    with pytest.raises(ValueError):
        Board(4, 4, 8)  # 16 cells minus the 9 cell safe zone leaves room for 7
    board = Board(4, 4, 1)
    assert board.chord(0, 0) == []
    assert not board.over
