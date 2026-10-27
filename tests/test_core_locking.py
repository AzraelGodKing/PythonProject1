import subprocess
import sys
import textwrap

from arcade.core.locking import InstanceLock


def test_only_one_holder(tmp_path):
    first, second = InstanceLock("g", tmp_path), InstanceLock("g", tmp_path)
    assert first.acquire("tictactoe")
    assert first.acquire("tictactoe")  # re-entrant for the same object
    assert not second.acquire("blackjack")
    assert second.is_locked()
    assert second.owner() == "tictactoe"
    first.release()
    assert not second.is_locked()
    assert second.owner() is None
    assert second.acquire("blackjack")
    second.release()


def test_release_is_idempotent_and_context_manager(tmp_path):
    with InstanceLock("g", tmp_path) as lock:
        assert lock.acquire("x")
        assert lock.held
    assert not lock.held
    lock.release()


def test_free_lock_without_file(tmp_path):
    lock = InstanceLock("never", tmp_path)
    assert not lock.is_locked()
    assert lock.owner() is None


def test_owner_unknown_when_owner_file_missing(tmp_path):
    holder = InstanceLock("g", tmp_path)
    holder.acquire("x")
    holder.owner_path.unlink()
    assert InstanceLock("g", tmp_path).owner() == "unknown"
    holder.release()


def test_lock_is_released_when_holder_process_exits(tmp_path):
    script = textwrap.dedent(
        f"""
        import sys
        from arcade.core.locking import InstanceLock
        lock = InstanceLock("g", {str(tmp_path)!r})
        assert lock.acquire("child")
        print("held", flush=True)
        sys.stdin.readline()
        """
    )
    child = subprocess.Popen([sys.executable, "-c", script], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "held"
        probe = InstanceLock("g", tmp_path)
        assert probe.owner() == "child"
        assert not probe.acquire("parent")
    finally:
        child.communicate("\n", timeout=10)
    assert probe.acquire("parent")
    probe.release()
