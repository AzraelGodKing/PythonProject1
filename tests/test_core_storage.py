import json
import sys

import pytest

from arcade.core import paths, settings, storage
from arcade.core.settings import Settings


def test_data_dir_honours_override(data_dir):
    assert paths.data_dir() == data_dir
    assert paths.scores_file("x").parent == data_dir / "scores"
    assert paths.locks_dir().is_dir()


def test_data_dir_default_is_outside_the_source_tree(monkeypatch, tmp_path):
    monkeypatch.delenv(paths.ENV_VAR)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    root = paths.data_dir()
    assert tmp_path in root.parents
    expected = {"win32": "ArcadeHub", "darwin": "ArcadeHub"}.get(sys.platform, "arcade-hub")
    assert root.name == expected


def test_write_then_read_round_trip(tmp_path):
    target = tmp_path / "nested" / "file.json"
    assert storage.write_json(target, {"a": [1, 2]})
    assert storage.read_json(target) == {"a": [1, 2]}
    assert not list(target.parent.glob("*.tmp"))


def test_previous_version_is_kept_as_backup(tmp_path):
    target = tmp_path / "f.json"
    storage.write_json(target, 1)
    storage.write_json(target, 2)
    assert json.loads(storage.backup_path(target).read_text()) == 1


def test_corrupt_file_falls_back_to_backup(tmp_path):
    target = tmp_path / "f.json"
    storage.write_json(target, {"v": 1})
    storage.write_json(target, {"v": 2})
    target.write_text("{not json", encoding="utf-8")
    assert storage.read_json(target) == {"v": 1}


def test_corrupt_file_does_not_replace_good_backup(tmp_path):
    target = tmp_path / "f.json"
    storage.write_json(target, "good")
    storage.write_json(target, "newer")
    target.write_text("garbage", encoding="utf-8")
    storage.write_json(target, "fresh")
    assert storage.read_json(storage.backup_path(target)) == "good"
    assert storage.read_json(target) == "fresh"


def test_missing_file_returns_default(tmp_path):
    assert storage.read_json(tmp_path / "nope.json", default=[]) == []


def test_unserialisable_data_is_rejected_without_touching_file(tmp_path):
    target = tmp_path / "f.json"
    storage.write_json(target, "keep")
    assert not storage.write_json(target, {"bad": object()})
    assert storage.read_json(target) == "keep"


def test_settings_defaults_and_persistence(tmp_path):
    path = tmp_path / "s.json"
    s = Settings(path, {"flag": True, "count": 3, "name": "x"})
    assert s["flag"] is True
    s.set("count", 7)
    assert Settings(path, s.defaults)["count"] == 7


def test_settings_reject_wrong_types_from_disk(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"flag": "false", "count": True, "ratio": 2, "unknown": 1}), encoding="utf-8")
    s = Settings(path, {"flag": True, "count": 3, "ratio": 0.5})
    # "false" is not silently turned into True, and bool is not an int.
    assert s["flag"] is True
    assert s["count"] == 3
    assert s["ratio"] == 2
    assert "unknown" not in s.as_dict()


def test_settings_choices(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"mode": "nope"}), encoding="utf-8")
    s = Settings(path, {"mode": "a"}, choices={"mode": ("a", "b")})
    assert s["mode"] == "a"
    s.set("mode", "b")
    with pytest.raises(ValueError):
        s.set("mode", "c")
    with pytest.raises(KeyError):
        s.set("missing", 1)


def test_settings_reset_and_non_dict_file(tmp_path):
    path = tmp_path / "s.json"
    path.write_text("[1, 2]", encoding="utf-8")
    s = Settings(path, {"n": 1})
    s.set("n", 5)
    s.reset()
    assert s["n"] == 1
    assert json.loads(path.read_text()) == {"n": 1}


def test_hub_settings_validate_language_and_theme(data_dir):
    hub = settings.hub_settings()
    hub.set("language", "ja")
    hub.set("theme", "colorblind_tritan")
    with pytest.raises(ValueError):
        hub.set("language", "xx")
    again = settings.hub_settings()
    assert again["language"] == "ja"
    assert again["theme"] == "colorblind_tritan"
