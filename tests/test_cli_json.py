import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent / "a tic-tac-toe game"
sys.path.insert(0, os.fspath(PROJECT_ROOT))

import ai_vs_ai


class TestCliJson(unittest.TestCase):
    def test_ai_vs_ai_json_output_and_expectation(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            ai_vs_ai.main(
                [
                    "--ai-x",
                    "Hard",
                    "--ai-o",
                    "Hard",
                    "--rounds",
                    "2",
                    "--output",
                    "json",
                    "--expect-winner",
                    "Draw",
                    "--safe-mode",
                ]
            )
        output = buf.getvalue()
        # capture JSON object in output
        lines = output.splitlines()
        collect = []
        depth = 0
        started = False
        for line in lines:
            if not started and "{" in line:
                frag = line[line.index("{") :]
                collect.append(frag)
                depth += frag.count("{") - frag.count("}")
                started = True
            elif started:
                collect.append(line)
                depth += line.count("{") - line.count("}")
                if depth <= 0:
                    break
        self.assertTrue(collect, "No JSON found in output")
        payload = "\n".join(collect)
        data = json.loads(payload)
        self.assertEqual(data["ai_x"], "Hard")
        self.assertEqual(data["ai_o"], "Hard")
        self.assertIn("scores", data)
        self.assertIn("badges", data)

    def test_ai_vs_ai_expectation_failure_exits(self) -> None:
        with self.assertRaises(SystemExit):
            ai_vs_ai.main(
                [
                    "--ai-x",
                    "Hard",
                    "--ai-o",
                    "Hard",
                    "--rounds",
                    "1",
                    "--output",
                    "json",
                    "--expect-winner",
                    "X",
                    "--safe-mode",
                ]
            )


if __name__ == "__main__":
    unittest.main()
