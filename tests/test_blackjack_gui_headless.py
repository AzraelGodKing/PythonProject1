import os
import sys
import unittest
import tkinter as tk
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.fspath(PROJECT_ROOT / "blackjack"))


class TestBlackjackGUIHeadless(unittest.TestCase):
    def test_gui_initializes_headless(self) -> None:
        if os.environ.get("CI"):
            self.skipTest("Skip GUI headless test in CI")
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("Tk unavailable in this environment")
            return
        try:
            root.withdraw()
            import gui  # noqa: E402

            gui.BlackjackApp(root)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
