"""Lightweight helpers for reading/writing small JSON settings files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


def load_settings(path: Path, defaults: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load settings from ``path`` merging with ``defaults``.

    Returns defaults if the file is missing or invalid.
    """
    data = dict(defaults)
    if not path.exists():
        return data
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            for key, value in raw.items():
                data[key] = value
    except Exception:
        # Fall back to defaults on any error.
        return data
    return data


def save_settings(path: Path, data: Dict[str, Any]) -> None:
    """Write ``data`` as JSON to ``path``; ignore errors silently."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass
