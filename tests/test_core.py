import os
import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent / "tic-tac-toe"
sys.path.insert(0, os.fspath(PROJECT_ROOT))

import tictactoe as game


class TestCoreLogic(unittest.TestCase):
    def test_check_winner_detects_rows_and_diagonals(self) -> None:
        row_win = ["X", "X", "X", " ", " ", " ", " ", " ", " "]
        diag_win = ["O", "X", " ", "X", "O", " ", " ", " ", "O"]
        no_win = ["X", "O", "X", "X", "O", "O", "O", "X", "X"]

        self.assertEqual(game.check_winner(row_win), "X")
        self.assertEqual(game.check_winner(diag_win), "O")
        self.assertIsNone(game.check_winner(no_win))

    def test_ai_move_hard_wins_or_blocks(self) -> None:
        # Should take the winning move when available.
        winning_board = ["O", "O", " ", "X", "X", " ", " ", " ", " "]
        self.assertEqual(game.ai_move_hard(winning_board), 2)

        # Should block an imminent player win.
        blocking_board = ["X", "X", " ", " ", "O", " ", " ", " ", " "]
        self.assertEqual(game.ai_move_hard(blocking_board), 2)


if __name__ == "__main__":
    unittest.main()
