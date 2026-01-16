"""Lightweight helpers for reading/writing small JSON settings files."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def validate_setting_value(key: str, value: Any, default_value: Any) -> Any:
    """
    Validate that a setting value matches the type of its default.

    Returns the value if valid, otherwise returns the default.
    """
    if default_value is None:
        # No type checking for None defaults
        return value

    expected_type = type(default_value)
    if isinstance(value, expected_type):
        return value

    # Try to convert to expected type
    try:
        if expected_type == bool:
            # Handle boolean conversion specially
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        return expected_type(value)
    except (TypeError, ValueError):
        logger.warning(
            f"Setting '{key}' has invalid type {type(value).__name__}, "
            f"expected {expected_type.__name__}. Using default: {default_value}"
        )
        return default_value


def load_settings(path: Path, defaults: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load settings from ``path`` merging with ``defaults``.

    Returns defaults if the file is missing or invalid.
    Settings are validated against default types for safety.
    """
    data = dict(defaults)
    if not path.exists():
        return data
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            for key, value in raw.items():
                if key in defaults:
                    # Validate type against default
                    data[key] = validate_setting_value(key, value, defaults[key])
                else:
                    # Unknown key, but allow it (extensibility)
                    data[key] = value
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse settings file {path}: {e}")
        return dict(defaults)
    except Exception as e:
        logger.warning(f"Error loading settings from {path}: {e}")
        # Fall back to defaults on any error.
        return dict(defaults)
    return data


def save_settings(path: Path, data: Dict[str, Any]) -> None:
    """Write ``data`` as JSON to ``path``; logs errors but continues."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning(f"Failed to save settings to {path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error saving settings to {path}: {e}")
