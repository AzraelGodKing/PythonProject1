import os
import sys
import unittest
import tkinter as tk
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent / "gofish"
sys.path.insert(0, os.fspath(PROJECT_ROOT))

import gui  # noqa: E402


class TestGoFishGUIHeadless(unittest.TestCase):
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
            app = gui.GoFishGUI(root, debug=False, headless=True)
            app._refresh()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
