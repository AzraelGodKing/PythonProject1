"""Persistent scoreboards.

Two shapes cover every game:

* :class:`HighScores` - a ranked top-N table of ``(name, score)`` entries
  (Yahtzee totals, Blackjack bankrolls, Minesweeper times).
* :class:`Tally` - named counters (wins / losses / draws, games played...).

Malformed entries on disk are skipped one by one, so a single bad row never
causes the rest of the table to be thrown away on the next save.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from arcade.core import paths, storage

log = logging.getLogger(__name__)

MAX_NAME_LENGTH = 24


def clean_name(name: str, fallback: str = "Player") -> str:
    name = " ".join(str(name).split())[:MAX_NAME_LENGTH]
    return name or fallback


@dataclass(frozen=True)
class ScoreEntry:
    name: str
    score: int
    timestamp: float = field(default_factory=time.time)

    @classmethod
    def from_raw(cls, raw: Any) -> ScoreEntry | None:
        if not isinstance(raw, dict):
            return None
        name, score = raw.get("name"), raw.get("score")
        if not isinstance(name, str) or isinstance(score, bool) or not isinstance(score, int):
            return None
        stamp = raw.get("timestamp", 0.0)
        if isinstance(stamp, bool) or not isinstance(stamp, (int, float)):
            stamp = 0.0
        return cls(clean_name(name), score, float(stamp))


class HighScores:
    """Top-N table. ``lower_is_better`` flips the ranking (e.g. best times)."""

    def __init__(self, path: Path, *, limit: int = 10, lower_is_better: bool = False) -> None:
        self.path = Path(path)
        self.limit = limit
        self.lower_is_better = lower_is_better

    @classmethod
    def named(cls, name: str, **kwargs: Any) -> HighScores:
        return cls(paths.scores_file(name), **kwargs)

    def _sorted(self, entries: list[ScoreEntry]) -> list[ScoreEntry]:
        sign = 1 if self.lower_is_better else -1
        # Ties keep the earlier entry ahead.
        return sorted(entries, key=lambda e: (sign * e.score, e.timestamp))[: self.limit]

    def load(self) -> list[ScoreEntry]:
        raw = storage.read_json(self.path, default=[])
        if not isinstance(raw, list):
            log.warning("Ignoring scoreboard %s: expected a list", self.path)
            return []
        entries = []
        for item in raw:
            entry = ScoreEntry.from_raw(item)
            if entry is None:
                log.warning("Skipping malformed score entry in %s: %r", self.path, item)
            else:
                entries.append(entry)
        return self._sorted(entries)

    def qualifies(self, score: int) -> bool:
        entries = self.load()
        if len(entries) < self.limit:
            return True
        worst = entries[-1].score
        return score < worst if self.lower_is_better else score > worst

    def add(self, name: str, score: int) -> int | None:
        """Record a score. Returns its 1-based rank, or None if it didn't place."""
        entry = ScoreEntry(clean_name(name), int(score))
        entries = self._sorted([*self.load(), entry])
        if entry not in entries:
            return None
        storage.write_json(self.path, [asdict(e) for e in entries])
        return entries.index(entry) + 1

    def best(self) -> ScoreEntry | None:
        entries = self.load()
        return entries[0] if entries else None

    def clear(self) -> None:
        storage.write_json(self.path, [])


class Tally:
    """A dict of non-negative integer counters."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    @classmethod
    def named(cls, name: str) -> Tally:
        return cls(paths.scores_file(name))

    def load(self) -> dict[str, int]:
        raw = storage.read_json(self.path, default={})
        if not isinstance(raw, dict):
            return {}
        return {
            str(key): value
            for key, value in raw.items()
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0
        }

    def get(self, key: str) -> int:
        return self.load().get(key, 0)

    def bump(self, *keys: str, amount: int = 1) -> dict[str, int]:
        counts = self.load()
        for key in keys:
            counts[key] = counts.get(key, 0) + amount
        storage.write_json(self.path, counts)
        return counts

    def set(self, key: str, value: int) -> None:
        if value < 0:
            raise ValueError("counters cannot be negative")
        counts = self.load()
        counts[key] = value
        storage.write_json(self.path, counts)

    def set_max(self, key: str, value: int) -> bool:
        """Store ``value`` if it beats the current one. Returns True when it did."""
        counts = self.load()
        if value <= counts.get(key, -1):
            return False
        counts[key] = value
        storage.write_json(self.path, counts)
        return True

    def clear(self) -> None:
        storage.write_json(self.path, {})
