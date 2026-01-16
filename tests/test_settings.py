"""Unit tests for shared.settings module."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.settings import load_settings, save_settings


class TestLoadSettings:
    """Test cases for load_settings function."""

    def test_load_settings_nonexistent_file_returns_defaults(self):
        """Test loading from non-existent file returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.json"
            defaults = {"theme": "dark", "volume": 50}

            settings = load_settings(path, defaults)

            assert settings == defaults

    def test_load_settings_empty_file_returns_defaults(self):
        """Test loading from empty JSON returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            path.write_text("{}", encoding="utf-8")
            defaults = {"theme": "dark", "volume": 50}

            settings = load_settings(path, defaults)

            assert settings == defaults

    def test_load_settings_merges_with_defaults(self):
        """Test that loaded settings merge with defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            data = {"theme": "light"}
            path.write_text(json.dumps(data), encoding="utf-8")
            defaults = {"theme": "dark", "volume": 50, "language": "en"}

            settings = load_settings(path, defaults)

            # theme should be overridden, others from defaults
            assert settings["theme"] == "light"
            assert settings["volume"] == 50
            assert settings["language"] == "en"

    def test_load_settings_overrides_defaults(self):
        """Test that file settings override defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            data = {"theme": "light", "volume": 75}
            path.write_text(json.dumps(data), encoding="utf-8")
            defaults = {"theme": "dark", "volume": 50}

            settings = load_settings(path, defaults)

            assert settings["theme"] == "light"
            assert settings["volume"] == 75

    def test_load_settings_adds_new_keys(self):
        """Test that settings can add keys not in defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            data = {"theme": "light", "new_setting": "value"}
            path.write_text(json.dumps(data), encoding="utf-8")
            defaults = {"theme": "dark"}

            settings = load_settings(path, defaults)

            assert settings["theme"] == "light"
            assert settings["new_setting"] == "value"

    def test_load_settings_empty_defaults(self):
        """Test loading with empty defaults dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            data = {"theme": "light", "volume": 75}
            path.write_text(json.dumps(data), encoding="utf-8")
            defaults = {}

            settings = load_settings(path, defaults)

            assert settings["theme"] == "light"
            assert settings["volume"] == 75

    def test_load_settings_invalid_json_returns_defaults(self):
        """Test that invalid JSON returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            path.write_text("{ invalid json }", encoding="utf-8")
            defaults = {"theme": "dark"}

            settings = load_settings(path, defaults)

            assert settings == defaults

    def test_load_settings_non_dict_json_returns_defaults(self):
        """Test that non-dictionary JSON returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            # JSON array instead of object
            path.write_text('["theme", "dark"]', encoding="utf-8")
            defaults = {"theme": "dark"}

            settings = load_settings(path, defaults)

            assert settings == defaults

    def test_load_settings_corrupted_file_returns_defaults(self):
        """Test that corrupted file returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            path.write_text("not json at all!", encoding="utf-8")
            defaults = {"theme": "dark"}

            settings = load_settings(path, defaults)

            assert settings == defaults

    def test_load_settings_various_data_types(self):
        """Test loading settings with various data types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            data = {
                "string": "value",
                "number": 42,
                "float": 3.14,
                "boolean": True,
                "null": None,
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            defaults = {}

            settings = load_settings(path, defaults)

            assert settings["string"] == "value"
            assert settings["number"] == 42
            assert settings["float"] == 3.14
            assert settings["boolean"] is True
            assert settings["null"] is None
            assert settings["list"] == [1, 2, 3]
            assert settings["dict"] == {"nested": "value"}

    def test_load_settings_unicode_values(self):
        """Test loading settings with unicode values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            data = {"language": "français", "name": "José", "city": "東京"}
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            defaults = {}

            settings = load_settings(path, defaults)

            assert settings["language"] == "français"
            assert settings["name"] == "José"
            assert settings["city"] == "東京"

    def test_load_settings_does_not_modify_defaults(self):
        """Test that loading settings doesn't modify the defaults dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            data = {"theme": "light"}
            path.write_text(json.dumps(data), encoding="utf-8")
            defaults = {"theme": "dark", "volume": 50}
            defaults_copy = defaults.copy()

            settings = load_settings(path, defaults)

            # Original defaults should be unchanged
            assert defaults == defaults_copy

    def test_load_settings_permission_error_returns_defaults(self):
        """Test that permission errors return defaults (edge case)."""
        # This is hard to test portably, but the function should handle it
        defaults = {"theme": "dark"}
        # Using a path that definitely doesn't exist
        path = Path("/nonexistent/path/to/settings.json")

        settings = load_settings(path, defaults)

        assert settings == defaults


class TestSaveSettings:
    """Test cases for save_settings function."""

    def test_save_settings_creates_file(self):
        """Test that save_settings creates a new file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            data = {"theme": "dark", "volume": 50}

            save_settings(path, data)

            assert path.exists()

    def test_save_settings_creates_parent_directories(self):
        """Test that parent directories are created if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir" / "nested" / "settings.json"
            data = {"theme": "dark"}

            save_settings(path, data)

            assert path.exists()
            assert path.parent.exists()

    def test_save_settings_writes_correct_data(self):
        """Test that data is correctly written to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            data = {"theme": "dark", "volume": 50, "language": "en"}

            save_settings(path, data)

            # Read back and verify
            loaded = json.loads(path.read_text(encoding="utf-8"))
            assert loaded == data

    def test_save_settings_overwrites_existing_file(self):
        """Test that save_settings overwrites existing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            old_data = {"theme": "dark"}
            new_data = {"theme": "light", "volume": 75}

            # Write old data
            path.write_text(json.dumps(old_data), encoding="utf-8")

            # Overwrite with new data
            save_settings(path, new_data)

            # Verify new data
            loaded = json.loads(path.read_text(encoding="utf-8"))
            assert loaded == new_data

    def test_save_settings_json_formatting(self):
        """Test that JSON is formatted with indentation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            data = {"theme": "dark", "volume": 50}

            save_settings(path, data)

            content = path.read_text(encoding="utf-8")
            # Should be indented (indent=2)
            assert "  " in content
            assert "\n" in content

    def test_save_settings_empty_dict(self):
        """Test saving empty settings dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            data = {}

            save_settings(path, data)

            loaded = json.loads(path.read_text(encoding="utf-8"))
            assert loaded == {}

    def test_save_settings_various_data_types(self):
        """Test saving settings with various data types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            data = {
                "string": "value",
                "number": 42,
                "float": 3.14,
                "boolean": True,
                "null": None,
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
            }

            save_settings(path, data)

            loaded = json.loads(path.read_text(encoding="utf-8"))
            assert loaded == data

    def test_save_settings_unicode_values(self):
        """Test saving settings with unicode values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            data = {"language": "français", "name": "José", "city": "東京"}

            save_settings(path, data)

            loaded = json.loads(path.read_text(encoding="utf-8"))
            assert loaded["language"] == "français"
            assert loaded["name"] == "José"
            assert loaded["city"] == "東京"

    def test_save_settings_error_handling(self):
        """Test that save_settings silently ignores errors."""
        # Try to save to an invalid path
        # On Windows, certain paths are invalid; on Unix, we can't write to root
        if sys.platform == "win32":
            path = Path("CON")  # Invalid Windows device name
        else:
            path = Path("/root/forbidden/settings.json")

        data = {"theme": "dark"}

        # Should not raise an exception
        try:
            save_settings(path, data)
        except Exception as e:
            # If an exception is raised, the test should fail
            assert False, f"save_settings raised exception: {e}"

    def test_save_settings_large_data(self):
        """Test saving large settings dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            # Create a large settings dict
            data = {f"key_{i}": f"value_{i}" for i in range(1000)}

            save_settings(path, data)

            loaded = json.loads(path.read_text(encoding="utf-8"))
            assert len(loaded) == 1000
            assert loaded["key_0"] == "value_0"
            assert loaded["key_999"] == "value_999"


class TestIntegrationLoadSave:
    """Integration tests for load and save working together."""

    def test_round_trip_save_and_load(self):
        """Test that save and load work together correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            original_data = {"theme": "dark", "volume": 75, "language": "en"}

            # Save
            save_settings(path, original_data)

            # Load
            loaded_data = load_settings(path, {})

            assert loaded_data == original_data

    def test_save_load_with_defaults(self):
        """Test save and load with defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            saved_data = {"theme": "light"}
            defaults = {"theme": "dark", "volume": 50}

            # Save partial settings
            save_settings(path, saved_data)

            # Load with defaults
            loaded_data = load_settings(path, defaults)

            # Should have theme from file, volume from defaults
            assert loaded_data["theme"] == "light"
            assert loaded_data["volume"] == 50

    def test_update_settings_workflow(self):
        """Test realistic workflow of loading, updating, and saving settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            defaults = {"theme": "dark", "volume": 50, "language": "en"}

            # First load (file doesn't exist)
            settings = load_settings(path, defaults)
            assert settings == defaults

            # Update a setting
            settings["theme"] = "light"
            settings["volume"] = 75

            # Save
            save_settings(path, settings)

            # Load again
            reloaded = load_settings(path, defaults)
            assert reloaded["theme"] == "light"
            assert reloaded["volume"] == 75
            assert reloaded["language"] == "en"

    def test_multiple_save_cycles(self):
        """Test multiple save and load cycles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"

            # Cycle 1
            save_settings(path, {"theme": "dark"})
            loaded1 = load_settings(path, {})
            assert loaded1["theme"] == "dark"

            # Cycle 2
            loaded1["volume"] = 50
            save_settings(path, loaded1)
            loaded2 = load_settings(path, {})
            assert loaded2["theme"] == "dark"
            assert loaded2["volume"] == 50

            # Cycle 3
            loaded2["language"] = "fr"
            save_settings(path, loaded2)
            loaded3 = load_settings(path, {})
            assert loaded3["theme"] == "dark"
            assert loaded3["volume"] == 50
            assert loaded3["language"] == "fr"

    def test_defaults_evolve_over_time(self):
        """Test that defaults can evolve while preserving user settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"

            # Version 1: Save with old defaults
            old_defaults = {"theme": "dark", "volume": 50}
            settings_v1 = load_settings(path, old_defaults)
            settings_v1["theme"] = "light"
            save_settings(path, settings_v1)

            # Version 2: Load with new defaults (added language)
            new_defaults = {"theme": "dark", "volume": 50, "language": "en"}
            settings_v2 = load_settings(path, new_defaults)

            # User's theme choice preserved
            assert settings_v2["theme"] == "light"
            # Old default preserved
            assert settings_v2["volume"] == 50
            # New default added
            assert settings_v2["language"] == "en"
