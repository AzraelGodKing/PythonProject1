import unittest
import tkinter as tk
import os
import json
import tempfile
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent / "tic-tac-toe"
sys.path.insert(0, os.fspath(PROJECT_ROOT))

import gui  # type: ignore  # noqa: E402


class GuiSmokeTest(unittest.TestCase):
    def test_can_instantiate_app(self) -> None:
        try:
            root = tk.Tk()
            root.withdraw()
        except tk.TclError:
            self.skipTest("Tk not available in this environment")
        app = gui.TicTacToeGUI(root)
        app.start_new_game()
        root.destroy()


class GuiSettingsTests(unittest.TestCase):
    def test_settings_persist_roundtrip(self) -> None:
        try:
            root = tk.Tk()
            root.withdraw()
        except tk.TclError:
            self.skipTest("Tk not available in this environment")

        fd, path = tempfile.mkstemp(dir=".")
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "confirm_moves": False,
                        "auto_start": True,
                        "rotate_logs": False,
                        "theme": "colorblind_protan",
                        "large_fonts": True,
                        "animations": False,
                        "sound": False,
                    },
                    f,
                )
            os.environ["GUI_SETTINGS_PATH"] = path
            app = gui.TicTacToeGUI(root)
            self.assertFalse(app.confirm_moves.get())
            self.assertTrue(app.auto_start.get())
            self.assertFalse(app.rotate_logs.get())
            self.assertEqual(app.theme_var.get(), "colorblind_protan")
            self.assertTrue(app.large_fonts.get())
            self.assertFalse(app.animations_enabled.get())
            self.assertFalse(app.sound_enabled.get())

            # Flip a toggle and ensure it saves
            app.confirm_moves.set(True)
            app.theme_var.set("light")
            app.animations_enabled.set(True)
            app.sound_enabled.set(True)
            app._save_settings()
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertTrue(saved["confirm_moves"])
            self.assertEqual(saved["theme"], "light")
            self.assertTrue(saved["animations"])
            self.assertTrue(saved["sound"])
        finally:
            root.destroy()
            os.environ.pop("GUI_SETTINGS_PATH", None)
            try:
                os.remove(path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
