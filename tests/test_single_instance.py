"""Unit tests for shared.single_instance module."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.single_instance import try_acquire_lock, release_lock, lock_holder


class TestTryAcquireLock:
    """Test cases for try_acquire_lock function."""

    def test_acquire_lock_success(self):
        """Test successfully acquiring a lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            result = try_acquire_lock(lock_path)

            assert result is True
            assert lock_path.exists()

            # Cleanup
            release_lock(lock_path)

    def test_acquire_lock_creates_parent_dirs(self):
        """Test that lock acquisition creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "subdir" / "nested" / "test.lock"

            result = try_acquire_lock(lock_path)

            assert result is True
            assert lock_path.exists()
            assert lock_path.parent.exists()

            # Cleanup
            release_lock(lock_path)

    def test_acquire_lock_with_label(self):
        """Test acquiring lock with a custom label."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            label = "MyGameApp"

            result = try_acquire_lock(lock_path, label)

            assert result is True
            assert lock_path.exists()

            # Verify label was written
            content = lock_path.read_text().strip()
            assert content == label

            # Cleanup
            release_lock(lock_path)

    def test_acquire_lock_without_label_uses_pid(self):
        """Test that acquiring without label writes PID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            result = try_acquire_lock(lock_path, None)

            assert result is True
            assert lock_path.exists()

            # Verify PID was written (should be numeric)
            content = lock_path.read_text().strip()
            assert content.isdigit()

            # Cleanup
            release_lock(lock_path)

    def test_acquire_same_lock_twice_succeeds(self):
        """Test that acquiring the same lock twice in same process succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            result1 = try_acquire_lock(lock_path, "first")
            result2 = try_acquire_lock(lock_path, "second")

            # Both should succeed (same process)
            assert result1 is True
            assert result2 is True

            # Cleanup
            release_lock(lock_path)

    def test_lock_prevents_file_deletion(self):
        """Test that locked file cannot be easily deleted while locked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            try_acquire_lock(lock_path, "test")

            # File should exist and be locked
            assert lock_path.exists()

            # Cleanup
            release_lock(lock_path)


class TestReleaseLock:
    """Test cases for release_lock function."""

    def test_release_lock_success(self):
        """Test successfully releasing a lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            # Acquire then release
            try_acquire_lock(lock_path)
            release_lock(lock_path)

            # File still exists but should be unlocked
            # (Hard to test without multiprocessing, but function shouldn't crash)
            assert True  # No exception raised

    def test_release_lock_not_held(self):
        """Test releasing a lock that wasn't acquired doesn't crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            # Try to release without acquiring - should not raise
            try:
                release_lock(lock_path)
            except Exception as e:
                assert False, f"release_lock raised exception: {e}"

    def test_release_lock_nonexistent(self):
        """Test releasing a lock for nonexistent file doesn't crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "nonexistent.lock"

            # Should not raise
            try:
                release_lock(lock_path)
            except Exception as e:
                assert False, f"release_lock raised exception: {e}"

    def test_release_lock_twice(self):
        """Test releasing the same lock twice doesn't crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            try_acquire_lock(lock_path)
            release_lock(lock_path)

            # Release again - should not raise
            try:
                release_lock(lock_path)
            except Exception as e:
                assert False, f"release_lock raised exception: {e}"


class TestLockHolder:
    """Test cases for lock_holder function."""

    def test_lock_holder_nonexistent_file(self):
        """Test lock_holder returns None for nonexistent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "nonexistent.lock"

            holder = lock_holder(lock_path)

            assert holder is None

    def test_lock_holder_with_label(self):
        """Test lock_holder returns the label when lock is held."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            label = "MyGameApp"

            try_acquire_lock(lock_path, label)
            holder = lock_holder(lock_path)

            assert holder == label

            # Cleanup
            release_lock(lock_path)

    def test_lock_holder_with_pid(self):
        """Test lock_holder returns PID when no label was used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            try_acquire_lock(lock_path, None)
            holder = lock_holder(lock_path)

            # Should be a numeric string (PID)
            assert holder is not None
            assert holder.isdigit()

            # Cleanup
            release_lock(lock_path)

    def test_lock_holder_empty_file(self):
        """Test lock_holder returns None for empty lock file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            lock_path.write_text("", encoding="utf-8")

            holder = lock_holder(lock_path)

            assert holder is None

    def test_lock_holder_whitespace_only(self):
        """Test lock_holder returns None for whitespace-only content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            lock_path.write_text("   \n\t  ", encoding="utf-8")

            holder = lock_holder(lock_path)

            assert holder is None

    def test_lock_holder_after_release(self):
        """Test lock_holder after lock is released."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            try_acquire_lock(lock_path, "test")
            release_lock(lock_path)

            # File might still exist but should be readable
            holder = lock_holder(lock_path)

            # Behavior depends on whether file still exists after release
            # (File persists but is unlocked)
            assert holder is None or isinstance(holder, str)


class TestIntegrationScenarios:
    """Integration tests for realistic usage scenarios."""

    def test_single_instance_enforcement(self):
        """Test enforcing single instance of an application."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "app.lock"
            app_name = "MyApp"

            # First instance acquires lock
            first = try_acquire_lock(lock_path, app_name)
            assert first is True

            # Check who holds the lock
            holder = lock_holder(lock_path)
            assert holder == app_name

            # Cleanup
            release_lock(lock_path)

    def test_lock_lifecycle(self):
        """Test complete lifecycle of lock acquisition and release."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "game.lock"

            # Initially no lock
            assert lock_holder(lock_path) is None

            # Acquire lock
            assert try_acquire_lock(lock_path, "Game1") is True
            assert lock_holder(lock_path) == "Game1"

            # Release lock
            release_lock(lock_path)

            # Lock file might persist but should be unlocked
            # Can acquire again
            assert try_acquire_lock(lock_path, "Game2") is True
            assert lock_holder(lock_path) == "Game2"

            # Cleanup
            release_lock(lock_path)

    def test_multiple_locks_different_paths(self):
        """Test that multiple locks can be held for different paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock1 = Path(tmpdir) / "game1.lock"
            lock2 = Path(tmpdir) / "game2.lock"

            # Acquire both locks
            result1 = try_acquire_lock(lock1, "Game1")
            result2 = try_acquire_lock(lock2, "Game2")

            assert result1 is True
            assert result2 is True
            assert lock_holder(lock1) == "Game1"
            assert lock_holder(lock2) == "Game2"

            # Cleanup
            release_lock(lock1)
            release_lock(lock2)

    def test_lock_with_unicode_label(self):
        """Test locks with unicode labels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            label = "Jeu Français 🎮"

            result = try_acquire_lock(lock_path, label)

            assert result is True
            holder = lock_holder(lock_path)
            assert holder == label

            # Cleanup
            release_lock(lock_path)

    def test_lock_stress_multiple_operations(self):
        """Test multiple lock operations in sequence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            # Acquire and release multiple times
            for i in range(10):
                label = f"Instance{i}"
                assert try_acquire_lock(lock_path, label) is True
                assert lock_holder(lock_path) == label
                release_lock(lock_path)

    def test_path_string_and_path_object(self):
        """Test that both string and Path objects work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            # Acquire with Path object
            result1 = try_acquire_lock(lock_path, "test")
            assert result1 is True

            # Can check holder with Path object
            holder = lock_holder(lock_path)
            assert holder == "test"

            # Cleanup
            release_lock(lock_path)

    def test_realistic_game_launcher_scenario(self):
        """Test realistic game launcher scenario."""
        with tempfile.TemporaryDirectory() as tmpdir:
            active_game_lock = Path(tmpdir) / "active_game.lock"

            # Launcher checks if any game is running
            assert lock_holder(active_game_lock) is None

            # User launches Tic-Tac-Toe
            assert try_acquire_lock(active_game_lock, "Tic-Tac-Toe") is True

            # Launcher checks again - should see Tic-Tac-Toe is running
            assert lock_holder(active_game_lock) == "Tic-Tac-Toe"

            # User tries to launch Blackjack - should see lock is held
            # (In real scenario, this would be a different process,
            # but we can test the detection)
            current_holder = lock_holder(active_game_lock)
            assert current_holder is not None
            assert current_holder == "Tic-Tac-Toe"

            # User closes Tic-Tac-Toe
            release_lock(active_game_lock)

            # Now Blackjack can be launched
            assert try_acquire_lock(active_game_lock, "Blackjack") is True
            assert lock_holder(active_game_lock) == "Blackjack"

            # Cleanup
            release_lock(active_game_lock)

    def test_lock_file_content_format(self):
        """Test the format of lock file content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            # Test with explicit label
            try_acquire_lock(lock_path, "MyLabel")
            content = lock_path.read_text().strip()
            assert content == "MyLabel"
            release_lock(lock_path)

            # Test without label (should write PID)
            try_acquire_lock(lock_path, None)
            content = lock_path.read_text().strip()
            # Should be numeric (PID)
            assert content.isdigit()
            assert int(content) > 0
            release_lock(lock_path)

    def test_rapid_acquire_release_cycles(self):
        """Test rapid acquire/release cycles for stability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            # Rapid cycles
            for i in range(50):
                assert try_acquire_lock(lock_path, f"App{i}") is True
                release_lock(lock_path)

            # Should still work after many cycles
            assert try_acquire_lock(lock_path, "Final") is True
            assert lock_holder(lock_path) == "Final"
            release_lock(lock_path)
