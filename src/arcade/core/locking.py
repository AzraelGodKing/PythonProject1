"""Single-instance enforcement with OS file locks.

Every game holds the shared ``active_game`` lock while it runs, so only one
game window is open at a time and the launcher can tell which one it is.
The lock is released by the OS when the process exits, even after a crash,
so there are no stale lock files to clean up.

The holder's name is written to a separate ``.owner`` file because Windows
byte-range locks make the locked file itself unreadable to other processes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import IO, Any

from arcade.core import paths

if os.name == "nt":
    import msvcrt
else:
    import fcntl

ACTIVE_GAME = "active_game"


def _lock(handle: IO[Any]) -> None:
    if os.name == "nt":
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(handle: IO[Any]) -> None:
    if os.name == "nt":
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class InstanceLock:
    """A non-blocking, process-wide exclusive lock identified by ``name``."""

    def __init__(self, name: str = ACTIVE_GAME, directory: Path | None = None) -> None:
        self.directory = Path(directory) if directory else paths.locks_dir()
        self.path = self.directory / f"{name}.lock"
        self.owner_path = self.directory / f"{name}.owner"
        self._handle: IO[Any] | None = None

    @property
    def held(self) -> bool:
        return self._handle is not None

    def acquire(self, owner: str) -> bool:
        """Try to take the lock for ``owner``. Returns False if someone else has it."""
        if self._handle is not None:
            return True
        self.directory.mkdir(parents=True, exist_ok=True)
        handle = open(self.path, "a+")  # noqa: SIM115 - kept open while the lock is held
        try:
            _lock(handle)
        except OSError:
            handle.close()
            return False
        self._handle = handle
        self.owner_path.write_text(json.dumps({"owner": owner, "pid": os.getpid()}), encoding="utf-8")
        return True

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            self.owner_path.unlink(missing_ok=True)
            _unlock(self._handle)
        except OSError:
            pass
        finally:
            self._handle.close()
            self._handle = None

    def is_locked(self) -> bool:
        """True if another holder (process or object) currently has the lock."""
        if self._handle is not None:
            return True
        if not self.path.exists():
            return False
        if self.acquire("probe"):
            self.release()
            return False
        return True

    def owner(self) -> str | None:
        """Return who holds the lock, or None if it is free."""
        if not self.is_locked():
            return None
        try:
            data = json.loads(self.owner_path.read_text(encoding="utf-8"))
            return str(data["owner"])
        except (OSError, ValueError, KeyError, TypeError):
            return "unknown"

    def __enter__(self) -> InstanceLock:
        return self

    def __exit__(self, *exc: object) -> None:
        self.release()
