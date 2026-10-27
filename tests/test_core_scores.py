import json

import pytest

from arcade.core.scores import HighScores, ScoreEntry, Tally, clean_name


def test_ranking_and_limit(tmp_path):
    table = HighScores(tmp_path / "t.json", limit=3)
    for name, score in [("a", 10), ("b", 30), ("c", 20), ("d", 5)]:
        table.add(name, score)
    assert [(e.name, e.score) for e in table.load()] == [("b", 30), ("c", 20), ("a", 10)]
    assert table.best().name == "b"


def test_add_returns_rank_or_none(tmp_path):
    table = HighScores(tmp_path / "t.json", limit=2)
    assert table.add("a", 10) == 1
    assert table.add("b", 20) == 1
    assert table.add("c", 5) is None
    assert not table.qualifies(5)
    assert table.qualifies(15)


def test_lower_is_better(tmp_path):
    table = HighScores(tmp_path / "t.json", limit=2, lower_is_better=True)
    table.add("slow", 90)
    table.add("fast", 30)
    assert table.add("slowest", 120) is None
    assert [e.name for e in table.load()] == ["fast", "slow"]
    assert table.qualifies(60)


def test_ties_keep_earlier_entry_first(tmp_path):
    table = HighScores(tmp_path / "t.json")
    table.add("first", 10)
    table.add("second", 10)
    assert [e.name for e in table.load()] == ["first", "second"]


def test_one_malformed_entry_does_not_wipe_the_table(tmp_path):
    """Regression: the old load_scores() returned [] on any bad row, so the next save erased everything."""
    path = tmp_path / "t.json"
    good = [{"name": "keep", "score": 50}, {"name": "also", "score": 40}]
    bad = [{"name": "x"}, {"score": "12", "name": "y"}, "junk", {"name": "b", "score": True}]
    path.write_text(json.dumps(good + bad), encoding="utf-8")
    table = HighScores(path)
    assert [e.name for e in table.load()] == ["keep", "also"]
    table.add("new", 45)
    assert [e.name for e in table.load()] == ["keep", "new", "also"]


def test_non_list_file_is_ignored(tmp_path):
    path = tmp_path / "t.json"
    path.write_text('{"name": "x"}', encoding="utf-8")
    assert HighScores(path).load() == []


def test_clear(tmp_path):
    table = HighScores(tmp_path / "t.json")
    table.add("a", 1)
    table.clear()
    assert table.load() == []
    assert table.best() is None


def test_named_tables_live_in_data_dir(data_dir):
    HighScores.named("demo").add("a", 1)
    assert (data_dir / "scores" / "demo.json").exists()


def test_clean_name():
    assert clean_name("  Ada   Lovelace ") == "Ada Lovelace"
    assert clean_name("") == "Player"
    assert len(clean_name("x" * 100)) == 24


def test_score_entry_from_raw_rejects_bad_types():
    assert ScoreEntry.from_raw({"name": "a", "score": 1}).score == 1
    assert ScoreEntry.from_raw({"name": "a", "score": 1, "timestamp": "x"}).timestamp == 0.0
    assert ScoreEntry.from_raw(None) is None
    assert ScoreEntry.from_raw({"name": 3, "score": 1}) is None


def test_tally_counts(tmp_path):
    tally = Tally(tmp_path / "c.json")
    tally.bump("wins")
    tally.bump("wins", "games")
    assert tally.load() == {"wins": 2, "games": 1}
    assert tally.get("missing") == 0
    tally.set("streak", 4)
    assert tally.set_max("best", 3)
    assert not tally.set_max("best", 2)
    assert tally.get("best") == 3
    with pytest.raises(ValueError):
        tally.set("streak", -1)
    tally.clear()
    assert tally.load() == {}


def test_tally_ignores_bad_values(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"ok": 2, "neg": -1, "str": "3", "bool": True}), encoding="utf-8")
    assert Tally(path).load() == {"ok": 2}
    path.write_text("[]", encoding="utf-8")
    assert Tally(path).load() == {}
