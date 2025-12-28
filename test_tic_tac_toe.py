import json
import os
import pathlib
import tempfile
import unittest
import sys
import io
import contextlib
from typing import List
from unittest.mock import patch


PROJECT_ROOT = pathlib.Path(__file__).resolve().parent / "tic-tac-toe"
sys.path.insert(0, os.fspath(PROJECT_ROOT))

import tictactoe as module  # type: ignore  # noqa: E402


class QuietTestCase(unittest.TestCase):
    """Suppress stdout chatter from the CLI-oriented module during tests."""

    def setUp(self) -> None:
        self._stdout = io.StringIO()
        self._redirect = contextlib.redirect_stdout(self._stdout)
        self._redirect.__enter__()

    def tearDown(self) -> None:
        self._redirect.__exit__(None, None, None)


class AiBehaviorTests(QuietTestCase):
    def test_easy_ai_chooses_open_spot(self) -> None:
        board = ["X", "O", "X", " ", " ", "O", "X", " ", " "]
        for _ in range(10):
            move = module.ai_move_easy(board)
            self.assertEqual(board[move], " ")

    def test_normal_ai_blocks_player_win(self) -> None:
        board = ["X", "X", " ", " ", "O", " ", " ", " ", "O"]
        move = module.ai_move_normal(board)
        self.assertEqual(move, 2)

    def test_hard_ai_wins_when_available(self) -> None:
        board = ["O", "O", " ", "X", "X", " ", " ", " ", " "]
        move = module.ai_move_hard(board)
        self.assertEqual(move, 2)

    def test_hard_ai_blocks_immediate_threat(self) -> None:
        board = ["X", "X", " ", " ", "O", " ", " ", " ", "O"]
        move = module.ai_move_hard(board)
        self.assertEqual(move, 2)


class HintTests(QuietTestCase):
    def test_hint_blocks_threat(self) -> None:
        board = ["X", "X", " ", "O", " ", " ", " ", "O", " "]
        hint = module.best_player_hint(board)
        self.assertEqual(hint, 2)

    def test_hint_picks_available_spot(self) -> None:
        board = ["X", "O", "X", "O", "X", "O", " ", " ", " "]
        hint = module.best_player_hint(board)
        self.assertIn(hint, {6, 7, 8})


class AiVarietyTests(QuietTestCase):
    def test_misdirection_chooses_fork(self) -> None:
        # O can fork uniquely by playing at index 2
        board = ["O", " ", " ", " ", "X", " ", " ", " ", "O"]
        move = module.ai_move_misdirection(board)
        self.assertEqual(move, 2)

    def test_mirror_mirrors_player(self) -> None:
        board = ["X", " ", " ", " ", " ", " ", " ", " ", " "]
        move = module.ai_move_mirror(board)
        self.assertEqual(move, 8)

    def test_mirror_blocks_opposite_corners(self) -> None:
        board = ["X", " ", " ", " ", "O", " ", " ", " ", "X"]
        move = module.ai_move_mirror(board)
        self.assertIn(move, {1, 3, 5, 7})

    def test_misdirection_blocks_opposite_corners(self) -> None:
        board = ["X", " ", " ", " ", "O", " ", " ", " ", "X"]
        move = module.ai_move_misdirection(board)
        self.assertIn(move, {1, 3, 5, 7})


class ParseMoveTests(QuietTestCase):
    def test_parse_single_digit(self) -> None:
        self.assertEqual(module.parse_move("5"), (2, 2))
        self.assertEqual(module.parse_move("9"), (3, 3))

    def test_parse_invalid_single_digit(self) -> None:
        self.assertIsNone(module.parse_move("0"))
        self.assertIsNone(module.parse_move("11"))

    def test_parse_row_col(self) -> None:
        self.assertEqual(module.parse_move("1 3"), (1, 3))
        self.assertEqual(module.parse_move("2,2"), (2, 2))


class ScoreboardValidationTests(QuietTestCase):
    def _write_scoreboard_file(self, payload: object, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)

    def test_load_scoreboard_with_tampered_hash_resets(self) -> None:
        fd, path = tempfile.mkstemp(dir=".")
        os.close(fd)
        try:
            tampered_payload = {
                "data": {"Easy": {"X": 99, "O": 99, "Draw": 99}},
                "hash": "notreal",
            }
            self._write_scoreboard_file(tampered_payload, path)
            scoreboard = module.load_scoreboard(file_path=path)
            for diff in module.DIFFICULTIES:
                self.assertEqual(scoreboard[diff], module.DEFAULT_SCORE)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def test_load_scoreboard_with_previous_restores(self) -> None:
        fd, path = tempfile.mkstemp(dir=".")
        os.close(fd)
        try:
            valid_score = module.new_scoreboard()
            valid_score["Easy"]["X"] = 2
            payload = {
                "data": {"Easy": {"X": 999}},  # corrupted current data
                "hash": "bad",
                "previous": {
                    "data": valid_score,
                    "hash": module.scoreboard._compute_score_hash(valid_score),
                },
            }
            self._write_scoreboard_file(payload, path)
            scoreboard = module.load_scoreboard(file_path=path)
            self.assertEqual(scoreboard["Easy"]["X"], 2)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass


class PlayRoundFlowTests(QuietTestCase):
    def test_quit_mid_round_returns_none(self) -> None:
        def ai_noop(board: List[str]) -> int:
            return next(idx for idx, cell in enumerate(board) if cell == " ")

        inputs = iter(["q"])
        with patch("builtins.input", side_effect=lambda prompt="": next(inputs)):
            result = module.play_round(ai_noop, "Easy")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
