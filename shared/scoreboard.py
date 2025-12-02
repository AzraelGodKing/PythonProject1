"""Simple JSON-backed scoreboard helper."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List


@dataclass
class ScoreEntry:
    name: str
    score: int


def load_scores(path: Path) -> List[ScoreEntry]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [ScoreEntry(**item) for item in raw if "name" in item and "score" in item]
    except Exception:
        return []


def add_score(path: Path, name: str, score: int, limit: int = 10) -> List[ScoreEntry]:
    scores = load_scores(path)
    scores.append(ScoreEntry(name=name, score=score))
    scores = sorted(scores, key=lambda s: s.score, reverse=True)[:limit]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(s) for s in scores], indent=2), encoding="utf-8")
    return scores
