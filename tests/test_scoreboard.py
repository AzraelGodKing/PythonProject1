import json
import os
import tempfile
import unittest

from tictactoe import scoreboard


class TestScoreboardPersistence(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.main_path = os.path.join(self.temp_dir.name, "score.json")
        self.backup_path = os.path.join(self.temp_dir.name, "score.json.bak")
        scoreboard.set_safe_mode(False)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_save_and_load_round_trip(self) -> None:
        data = scoreboard.new_scoreboard()
        data["Easy"]["X"] = 3
        scoreboard.save_scoreboard(data, file_path=self.main_path, backup_path=self.backup_path)

        loaded = scoreboard.load_scoreboard(file_path=self.main_path, backup_path=self.backup_path)
        self.assertEqual(loaded, data)

    def test_load_recovers_from_tampered_hash_using_previous(self) -> None:
        data = scoreboard.new_scoreboard()
        data["Normal"]["O"] = 2
        # First save to establish baseline, second save to populate previous payload.
        scoreboard.save_scoreboard(data, file_path=self.main_path, backup_path=self.backup_path)
        scoreboard.save_scoreboard(data, file_path=self.main_path, backup_path=self.backup_path)

        with open(self.main_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        payload["hash"] = "tampered"
        with open(self.main_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        recovered = scoreboard.load_scoreboard(file_path=self.main_path, backup_path=self.backup_path)
        self.assertEqual(recovered, data)


if __name__ == "__main__":
    unittest.main()
