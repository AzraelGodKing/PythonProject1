"""
Utility helpers to enforce a single running instance of a game.

Each process grabs an OS-level file lock so concurrent launches will
fail fast with a friendly message instead of opening duplicate windows.
"""

from __future__ import annotations

import atexit
import os
from pathlib import Path
from typing import Dict, Optional, TextIO

if os.name == "nt":  # pragma: win32-no-cover
    import msvcrt
else:  # pragma: linux/mac-no-cover
    import fcntl

# Keep lock handles alive for the lifetime of the process.
_LOCK_HANDLES: Dict[Path, TextIO] = {}


def _unlock(path: Path) -> None:
    handle = _LOCK_HANDLES.pop(path, None)
    if not handle:
        return
    try:
        if os.name == "nt":  # pragma: win32-no-cover
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:  # pragma: linux/mac-no-cover
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def release_lock(lock_path: Path) -> None:
    """Release a previously acquired lock, if held by this process."""
    try:
        _unlock(Path(lock_path))
    except PermissionError:
        # If we somehow don't own the handle anymore, ignore.
        pass


def try_acquire_lock(lock_path: Path, label: Optional[str] = None) -> bool:
    """
    Attempt to acquire a non-blocking file lock at ``lock_path``.

    Returns True if the lock was obtained, False if another process
    already holds it.

    ``label`` lets callers record a human-readable owner string in the
    lock file (e.g., the game name) for friendlier error messages.
    """
    if lock_path in _LOCK_HANDLES:
        return True

    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    handle: Optional[TextIO] = None
    try:
        handle = lock_path.open("a+")
        handle.seek(0)
        if os.name == "nt":  # pragma: win32-no-cover
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:  # pragma: linux/mac-no-cover
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        handle.seek(0)
        handle.truncate()
        handle.write(label or str(os.getpid()))
        handle.flush()
    except OSError:
        if handle:
            handle.close()
        return False

    _LOCK_HANDLES[lock_path] = handle
    atexit.register(_unlock, lock_path)
    return True


def lock_holder(lock_path: Path) -> Optional[str]:
    """
    Return the textual identifier stored in the lock file, if present.
    """
    lock_path = Path(lock_path)
    if not lock_path.exists():
        return None
    try:
        return lock_path.read_text().strip() or None
    except OSError:
        return None
