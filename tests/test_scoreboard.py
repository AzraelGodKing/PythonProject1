"""Unit tests for shared.scoreboard module."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.scoreboard import ScoreEntry, load_scores, add_score


class TestScoreEntry:
    """Test cases for the ScoreEntry dataclass."""

    def test_score_entry_creation(self):
        """Test basic ScoreEntry creation."""
        entry = ScoreEntry(name="Alice", score=100)
        assert entry.name == "Alice"
        assert entry.score == 100

    def test_score_entry_equality(self):
        """Test ScoreEntry equality."""
        entry1 = ScoreEntry(name="Alice", score=100)
        entry2 = ScoreEntry(name="Alice", score=100)
        entry3 = ScoreEntry(name="Bob", score=100)

        assert entry1 == entry2
        assert entry1 != entry3


class TestLoadScores:
    """Test cases for load_scores function."""

    def test_load_scores_nonexistent_file(self):
        """Test loading from non-existent file returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.json"
            scores = load_scores(path)
            assert scores == []

    def test_load_scores_empty_file(self):
        """Test loading from empty JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"
            path.write_text("[]", encoding="utf-8")

            scores = load_scores(path)
            assert scores == []

    def test_load_scores_valid_single_entry(self):
        """Test loading single score entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"
            data = [{"name": "Alice", "score": 100}]
            path.write_text(json.dumps(data), encoding="utf-8")

            scores = load_scores(path)
            assert len(scores) == 1
            assert scores[0].name == "Alice"
            assert scores[0].score == 100

    def test_load_scores_valid_multiple_entries(self):
        """Test loading multiple score entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"
            data = [
                {"name": "Alice", "score": 100},
                {"name": "Bob", "score": 200},
                {"name": "Charlie", "score": 150},
            ]
            path.write_text(json.dumps(data), encoding="utf-8")

            scores = load_scores(path)
            assert len(scores) == 3
            assert scores[0].name == "Alice"
            assert scores[1].name == "Bob"
            assert scores[2].name == "Charlie"

    def test_load_scores_missing_name_field(self):
        """Test that entries without 'name' are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"
            data = [
                {"name": "Alice", "score": 100},
                {"score": 200},  # Missing name
                {"name": "Charlie", "score": 150},
            ]
            path.write_text(json.dumps(data), encoding="utf-8")

            scores = load_scores(path)
            assert len(scores) == 2
            assert scores[0].name == "Alice"
            assert scores[1].name == "Charlie"

    def test_load_scores_missing_score_field(self):
        """Test that entries without 'score' are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"
            data = [
                {"name": "Alice", "score": 100},
                {"name": "Bob"},  # Missing score
                {"name": "Charlie", "score": 150},
            ]
            path.write_text(json.dumps(data), encoding="utf-8")

            scores = load_scores(path)
            assert len(scores) == 2
            assert scores[0].name == "Alice"
            assert scores[1].name == "Charlie"

    def test_load_scores_extra_fields_cause_failure(self):
        """Test that extra fields cause entries to be skipped (dataclass limitation)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"
            data = [
                {"name": "Alice", "score": 100, "extra": "ignored"},
                {"name": "Bob", "score": 200, "another": 123},
            ]
            path.write_text(json.dumps(data), encoding="utf-8")

            # Due to dataclass strict initialization, extra fields cause TypeError
            # The exception handler catches this and returns empty list
            scores = load_scores(path)
            assert len(scores) == 0  # Extra fields cause failure

    def test_load_scores_invalid_json(self):
        """Test that invalid JSON returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"
            path.write_text("{ invalid json }", encoding="utf-8")

            scores = load_scores(path)
            assert scores == []

    def test_load_scores_corrupted_data(self):
        """Test that corrupted data returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"
            path.write_text("not json at all!", encoding="utf-8")

            scores = load_scores(path)
            assert scores == []

    def test_load_scores_wrong_format(self):
        """Test that non-array JSON returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"
            path.write_text('{"name": "Alice", "score": 100}', encoding="utf-8")

            scores = load_scores(path)
            assert scores == []


class TestAddScore:
    """Test cases for add_score function."""

    def test_add_score_to_empty_file(self):
        """Test adding score when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            scores = add_score(path, "Alice", 100)

            assert len(scores) == 1
            assert scores[0].name == "Alice"
            assert scores[0].score == 100
            assert path.exists()

    def test_add_score_to_existing_scores(self):
        """Test adding score to existing scoreboard."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"
            initial_data = [{"name": "Bob", "score": 50}]
            path.write_text(json.dumps(initial_data), encoding="utf-8")

            scores = add_score(path, "Alice", 100)

            assert len(scores) == 2
            # Should be sorted by score descending
            assert scores[0].name == "Alice"
            assert scores[0].score == 100
            assert scores[1].name == "Bob"
            assert scores[1].score == 50

    def test_add_score_sorting_descending(self):
        """Test that scores are sorted in descending order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            add_score(path, "Alice", 100)
            add_score(path, "Bob", 200)
            add_score(path, "Charlie", 150)

            scores = load_scores(path)
            assert scores[0].score == 200  # Bob
            assert scores[1].score == 150  # Charlie
            assert scores[2].score == 100  # Alice

    def test_add_score_default_limit(self):
        """Test default limit of 10 scores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            # Add 15 scores
            for i in range(15):
                add_score(path, f"Player{i}", i * 10)

            scores = load_scores(path)
            # Should only keep top 10
            assert len(scores) == 10
            # Highest score should be 140 (14 * 10)
            assert scores[0].score == 140
            # Lowest score should be 50 (5 * 10)
            assert scores[-1].score == 50

    def test_add_score_custom_limit(self):
        """Test custom score limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            # Add 10 scores with limit of 5
            for i in range(10):
                add_score(path, f"Player{i}", i * 10, limit=5)

            scores = load_scores(path)
            assert len(scores) == 5
            # Top 5 scores: 90, 80, 70, 60, 50
            assert scores[0].score == 90
            assert scores[-1].score == 50

    def test_add_score_creates_parent_directory(self):
        """Test that parent directories are created if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir" / "nested" / "scores.json"

            scores = add_score(path, "Alice", 100)

            assert path.exists()
            assert path.parent.exists()
            assert len(scores) == 1

    def test_add_score_persists_to_disk(self):
        """Test that scores are actually written to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            add_score(path, "Alice", 100)
            add_score(path, "Bob", 200)

            # Read directly from file
            content = json.loads(path.read_text(encoding="utf-8"))
            assert len(content) == 2
            assert content[0]["name"] == "Bob"
            assert content[0]["score"] == 200

    def test_add_score_json_formatting(self):
        """Test that JSON is formatted with indentation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            add_score(path, "Alice", 100)

            content = path.read_text(encoding="utf-8")
            # Should be indented (indent=2)
            assert "  " in content
            assert "\n" in content

    def test_add_score_returns_updated_list(self):
        """Test that add_score returns the updated score list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            scores1 = add_score(path, "Alice", 100)
            assert len(scores1) == 1

            scores2 = add_score(path, "Bob", 200)
            assert len(scores2) == 2
            assert scores2[0].name == "Bob"

    def test_add_score_same_name_multiple_times(self):
        """Test adding scores for same player name multiple times."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            add_score(path, "Alice", 100)
            add_score(path, "Alice", 200)
            add_score(path, "Alice", 150)

            scores = load_scores(path)
            assert len(scores) == 3
            # All Alice entries should be present
            assert all(s.name == "Alice" for s in scores)
            # Sorted by score
            assert scores[0].score == 200
            assert scores[1].score == 150
            assert scores[2].score == 100

    def test_add_score_equal_scores(self):
        """Test handling of equal scores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            add_score(path, "Alice", 100)
            add_score(path, "Bob", 100)
            add_score(path, "Charlie", 100)

            scores = load_scores(path)
            assert len(scores) == 3
            assert all(s.score == 100 for s in scores)

    def test_add_score_zero_score(self):
        """Test adding score of zero."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            scores = add_score(path, "Alice", 0)

            assert len(scores) == 1
            assert scores[0].score == 0

    def test_add_score_negative_score(self):
        """Test adding negative score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            add_score(path, "Alice", -50)
            scores = add_score(path, "Bob", 100)

            assert len(scores) == 2
            # Higher scores first
            assert scores[0].score == 100
            assert scores[1].score == -50

    def test_add_score_large_numbers(self):
        """Test adding very large scores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            scores = add_score(path, "Alice", 999_999_999)

            assert scores[0].score == 999_999_999

    def test_add_score_unicode_names(self):
        """Test adding scores with unicode names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            add_score(path, "José", 100)
            add_score(path, "François", 200)
            scores = add_score(path, "李明", 150)

            assert len(scores) == 3
            assert any(s.name == "José" for s in scores)
            assert any(s.name == "François" for s in scores)
            assert any(s.name == "李明" for s in scores)

    def test_add_score_empty_name(self):
        """Test adding score with empty name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            scores = add_score(path, "", 100)

            assert len(scores) == 1
            assert scores[0].name == ""

    def test_add_score_limit_zero(self):
        """Test add_score with limit of 0 keeps no scores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            scores = add_score(path, "Alice", 100, limit=0)

            assert len(scores) == 0

    def test_add_score_limit_one(self):
        """Test add_score with limit of 1 keeps only top score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scores.json"

            add_score(path, "Alice", 100, limit=1)
            scores = add_score(path, "Bob", 200, limit=1)

            assert len(scores) == 1
            assert scores[0].name == "Bob"
            assert scores[0].score == 200

    def test_integration_realistic_game_session(self):
        """Test realistic game session with multiple players."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "game_scores.json"

            # Simulate a game session
            add_score(path, "Player1", 1500)
            add_score(path, "Player2", 2300)
            add_score(path, "Player1", 1800)
            add_score(path, "Player3", 2100)
            add_score(path, "Player2", 1200)

            scores = load_scores(path)

            # Should have 5 entries
            assert len(scores) == 5

            # Top score should be Player2 with 2300
            assert scores[0].name == "Player2"
            assert scores[0].score == 2300

            # Bottom score should be Player2 with 1200
            assert scores[-1].score == 1200
