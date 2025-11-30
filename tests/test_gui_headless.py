import os
import tempfile
import unittest
import tkinter as tk

import tictactoe as game


class TestGuiHeadless(unittest.TestCase):
    def test_gui_initializes_headless_with_safe_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["GUI_SETTINGS_PATH"] = os.path.join(tmp, "gui_settings.json")
            history_path = os.path.join(tmp, "history.log")
            game.set_safe_mode(True)
            game.configure_history_file(history_path)
            game.save_badges({})

            import gui  # noqa: WPS433

            try:
                root = tk.Tk()
            except tk.TclError:
                self.skipTest("Tk unavailable in headless environment")
                return

            root.withdraw()
            try:
                app = gui.TicTacToeGUI(root)
                app.start_new_game()
                app._save_settings()
            finally:
                root.destroy()
            self.assertTrue(os.path.exists(os.environ["GUI_SETTINGS_PATH"]))


if __name__ == "__main__":
    unittest.main()
