"""Crash-safe JSON files.

Writes go to a temporary file that is then atomically renamed over the
target, and the previous good copy is kept as ``<name>.bak``. Reads fall back
to the backup when the main file is missing or corrupt, so one bad write
can't wipe a player's data.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def backup_path(path: Path) -> Path:
    return path.with_name(path.name + ".bak")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json(path: Path, default: Any = None) -> Any:
    """Return the parsed contents of ``path``, its backup, or ``default``."""
    path = Path(path)
    for candidate in (path, backup_path(path)):
        if not candidate.exists():
            continue
        try:
            return _read(candidate)
        except (OSError, ValueError) as exc:
            log.warning("Could not read %s: %s", candidate, exc)
    return default


def write_json(path: Path, data: Any) -> bool:
    """Atomically write ``data`` to ``path``. Returns False if the write failed."""
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if path.exists():
                try:
                    _read(path)
                except (OSError, ValueError):
                    pass  # don't overwrite a good backup with a corrupt file
                else:
                    os.replace(path, backup_path(path))
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
    except (OSError, TypeError, ValueError) as exc:
        log.error("Could not write %s: %s", path, exc)
        return False
    return True
