import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.fspath(PROJECT_ROOT / "gofish"))

from gofish import gui  # noqa: E402
from gofish.gui import GoFishGame  # noqa: E402


class TestGoFishGame(unittest.TestCase):
    def test_initial_deal_uses_single_deck(self) -> None:
        game = GoFishGame()
        # 52 cards, 7 each dealt.
        remaining = game.deck.remaining()
        self.assertEqual(52 - 14, remaining)
        self.assertEqual(7, len(game.player_hand))
        self.assertEqual(7, len(game.ai_hand))

    def test_ai_turn_with_empty_hand_passes_turn(self) -> None:
        game = GoFishGame()
        game.ai_hand.clear()
        game.deck._cards = []  # exhaust deck
        game.turn = "ai"
        game.ai_turn()
        self.assertEqual("player", game.turn)


if __name__ == "__main__":
    unittest.main()
