"""Typed, validated settings backed by a JSON file.

A :class:`Settings` object is created from a dict of defaults. Values read
from disk are only accepted if they have the same type as the default (and,
for keys with a ``choices`` list, one of the allowed values). Anything else
falls back to the default instead of crashing or silently coercing
``"false"`` into ``True``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from arcade.core import i18n, paths, storage, themes


def _valid(value: Any, default: Any, choices: Iterable[Any] | None) -> bool:
    if choices is not None and value not in choices:
        return False
    if default is None:
        return True
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, int):
        return isinstance(value, int) and not isinstance(value, bool)
    if isinstance(default, float):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, type(default))


class Settings:
    def __init__(
        self,
        path: Path,
        defaults: Mapping[str, Any],
        choices: Mapping[str, Iterable[Any]] | None = None,
    ) -> None:
        self.path = Path(path)
        self.defaults = dict(defaults)
        self.choices = {key: tuple(values) for key, values in (choices or {}).items()}
        self._values = dict(self.defaults)
        self.load()

    @classmethod
    def named(cls, name: str, defaults: Mapping[str, Any], **kwargs: Any) -> Settings:
        return cls(paths.settings_file(name), defaults, **kwargs)

    def load(self) -> None:
        raw = storage.read_json(self.path, default={})
        self._values = dict(self.defaults)
        if not isinstance(raw, dict):
            return
        for key, value in raw.items():
            if key in self.defaults and _valid(value, self.defaults[key], self.choices.get(key)):
                self._values[key] = value

    def save(self) -> bool:
        return storage.write_json(self.path, self._values)

    def get(self, key: str) -> Any:
        return self._values[key]

    def set(self, key: str, value: Any, *, save: bool = True) -> None:
        if key not in self.defaults:
            raise KeyError(key)
        if not _valid(value, self.defaults[key], self.choices.get(key)):
            raise ValueError(f"Invalid value for {key!r}: {value!r}")
        self._values[key] = value
        if save:
            self.save()

    def reset(self) -> None:
        self._values = dict(self.defaults)
        self.save()

    def as_dict(self) -> dict[str, Any]:
        return dict(self._values)

    __getitem__ = get


def hub_settings() -> Settings:
    """Preferences shared by the launcher and every game."""
    return Settings.named(
        "hub",
        {"language": i18n.DEFAULT_LANGUAGE, "theme": themes.DEFAULT_THEME, "sound": True, "player_name": ""},
        choices={"language": i18n.available_languages(), "theme": tuple(themes.THEMES)},
    )
