"""Translations.

Locale files are flat JSON objects in ``arcade/locales/<code>.json``. English
is the reference: every other locale must have the same keys (a test checks
this) and missing keys fall back to English, then to the key itself.
"""

from __future__ import annotations

import json
import logging
from functools import cache
from importlib import resources
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "en"

# Native names, shown in language pickers.
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "pt": "Português",
    "ru": "Русский",
    "ja": "日本語",
    "no": "Norsk bokmål",
}


def available_languages() -> list[str]:
    folder = resources.files("arcade") / "locales"
    found = {entry.name.removesuffix(".json") for entry in folder.iterdir() if entry.name.endswith(".json")}
    ordered = [code for code in LANGUAGE_NAMES if code in found]
    return ordered + sorted(found - set(ordered))


@cache
def load_catalog(code: str) -> dict[str, str]:
    path = resources.files("arcade") / "locales" / f"{code}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("Could not load locale %s: %s", code, exc)
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


class Translator:
    def __init__(self, language: str = DEFAULT_LANGUAGE) -> None:
        self.language = DEFAULT_LANGUAGE
        self.set_language(language)

    def set_language(self, code: str) -> None:
        self.language = code if code in available_languages() else DEFAULT_LANGUAGE
        self._catalog = {**load_catalog(DEFAULT_LANGUAGE), **load_catalog(self.language)}

    def __call__(self, key: str, **params: Any) -> str:
        text = self._catalog.get(key, key)
        if not params:
            return text
        try:
            return text.format(**params)
        except (KeyError, IndexError, ValueError):
            log.warning("Bad placeholders for %r in %s", key, self.language)
            return text

    def has(self, key: str) -> bool:
        return key in self._catalog
