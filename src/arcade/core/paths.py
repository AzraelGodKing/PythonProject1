"""Where Arcade Hub keeps its runtime data.

Runtime files (settings, scores, locks, logs) live in a per-user directory,
never inside the source tree, so they can't end up committed by accident.
Set ``ARCADE_HUB_DATA`` to override the location (tests do this).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ENV_VAR = "ARCADE_HUB_DATA"
APP_DIR_NAME = "ArcadeHub"


def data_dir() -> Path:
    """Return the root data directory, creating it if needed."""
    override = os.environ.get(ENV_VAR)
    if override:
        root = Path(override).expanduser()
    elif sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        root = Path(base) / APP_DIR_NAME
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        root = Path(base) / "arcade-hub"
    root.mkdir(parents=True, exist_ok=True)
    return root


def subdir(name: str) -> Path:
    path = data_dir() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_file(name: str) -> Path:
    return subdir("settings") / f"{name}.json"


def scores_file(name: str) -> Path:
    return subdir("scores") / f"{name}.json"


def locks_dir() -> Path:
    return subdir("locks")


def logs_dir() -> Path:
    return subdir("logs")
