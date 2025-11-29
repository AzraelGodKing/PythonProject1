import hashlib
import json
import os
import tempfile
from typing import Dict

DATA_DIR = "data"
SCOREBOARD_DIR = os.path.join(DATA_DIR, "scoreboard")
SCOREBOARD_FILE = os.path.join(SCOREBOARD_DIR, "scoreboard.json")
SCOREBOARD_BACKUP = os.path.join(SCOREBOARD_DIR, "scoreboard.json.bak")
MATCH_SCOREBOARD_FILE = os.path.join(SCOREBOARD_DIR, "match_scoreboard.json")
MATCH_SCOREBOARD_BACKUP = MATCH_SCOREBOARD_FILE + ".bak"

SAFE_MODE = os.getenv("TICTACTOE_SAFE_MODE", "0") not in {"0", "false", "False", "", None}
SAFE_MODE_MESSAGE = "Safe mode enabled; skipping persistence."

DIFFICULTIES = ("Easy", "Normal", "Hard")
DEFAULT_SCORE = {"X": 0, "O": 0, "Draw": 0}
SCORE_HASH_KEY = "hash"
SCORE_DATA_KEY = "data"
SCORE_PREV_KEY = "previous"


def new_scoreboard() -> Dict[str, Dict[str, int]]:
    return {diff: DEFAULT_SCORE.copy() for diff in DIFFICULTIES}


def print_scoreboard(scoreboard: Dict[str, Dict[str, int]]) -> None:
    print("\nScoreboard (per difficulty):")
    for diff in DIFFICULTIES:
        entry = scoreboard.get(diff, DEFAULT_SCORE)
        print(f"{diff}: You (X): {entry['X']}  |  AI (O): {entry['O']}  |  Draws: {entry['Draw']}")


def print_match_scoreboard(scoreboard: Dict[str, Dict[str, int]]) -> None:
    print("\nMatch Scoreboard (per difficulty):")
    for diff in DIFFICULTIES:
        entry = scoreboard.get(diff, DEFAULT_SCORE)
        print(f"{diff}: X match wins={entry['X']}  O match wins={entry['O']}  Match draws={entry['Draw']}")


def set_safe_mode(enabled: bool) -> None:
    """Allow callers (e.g., CLI flags/tests) to toggle persistence at runtime."""
    global SAFE_MODE
    SAFE_MODE = bool(enabled)


def _compute_score_hash(scoreboard: Dict[str, Dict[str, int]]) -> str:
    payload = json.dumps(scoreboard, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _valid_score_data(data: Dict[str, int], default_score: Dict[str, int]) -> Dict[str, int]:
    if not isinstance(data, dict):
        return default_score.copy()

    merged = {}
    for key, default_val in default_score.items():
        try:
            merged[key] = int(data.get(key, default_val))
        except (TypeError, ValueError):
            merged[key] = default_val
    return merged


def _valid_scoreboard(data: Dict[str, object]) -> Dict[str, Dict[str, int]]:
    scoreboard = new_scoreboard()
    if not isinstance(data, dict):
        return scoreboard
    for diff in DIFFICULTIES:
        scoreboard[diff] = _valid_score_data(data.get(diff, {}), DEFAULT_SCORE)
    return scoreboard


def _extract_scored_payload(payload: Dict[str, object]) -> Dict[str, Dict[str, int]] | None:
    if not isinstance(payload, dict):
        return None
    stored_scoreboard = payload.get(SCORE_DATA_KEY)
    stored_hash = payload.get(SCORE_HASH_KEY)
    merged = _valid_scoreboard(stored_scoreboard)
    if stored_hash == _compute_score_hash(merged):
        return merged
    return None


def load_scoreboard(file_path: str = SCOREBOARD_FILE, backup_path: str = SCOREBOARD_BACKUP) -> Dict[str, Dict[str, int]]:
    default_scoreboard = new_scoreboard()
    if SAFE_MODE:
        return default_scoreboard

    data = None
    try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print("Scoreboard restored from backup.")
        except (OSError, json.JSONDecodeError):
            return default_scoreboard

    if isinstance(data, dict) and SCORE_DATA_KEY not in data:
        legacy = _valid_score_data(data, DEFAULT_SCORE)
        migrated = new_scoreboard()
        migrated["Normal"] = legacy
        return migrated

    if not isinstance(data, dict):
        return default_scoreboard

    current_score = _extract_scored_payload(data)
    if current_score is not None:
        return current_score

    prev_payload = data.get(SCORE_PREV_KEY)
    previous_score = _extract_scored_payload(prev_payload)
    if previous_score is not None:
        print("Scoreboard seemed corrupted; restored last valid score.")
        return previous_score

    print("Scoreboard appears tampered or corrupted. Resetting to 0s.")
    return default_scoreboard


def save_scoreboard(score: Dict[str, Dict[str, int]], file_path: str = SCOREBOARD_FILE, backup_path: str = SCOREBOARD_BACKUP) -> None:
    if SAFE_MODE:
        print(SAFE_MODE_MESSAGE)
        return
    previous_payload = None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if isinstance(existing, dict):
            validated = _extract_scored_payload(existing)
            if validated is not None:
                previous_payload = {
                    SCORE_DATA_KEY: validated,
                    SCORE_HASH_KEY: _compute_score_hash(validated),
                }
    except (FileNotFoundError, json.JSONDecodeError):
        previous_payload = None

    payload = {
        SCORE_DATA_KEY: score,
        SCORE_HASH_KEY: _compute_score_hash(score),
        SCORE_PREV_KEY: previous_payload,
    }
    dir_name = os.path.dirname(file_path) or "."
    os.makedirs(dir_name, exist_ok=True)
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                current = f.read()
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(current)
    except OSError:
        pass

    fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix=".scoreboard.", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(temp_path, file_path)
    except (OSError, PermissionError) as exc:
        print(f"Could not save scoreboard ({exc}). Your latest results may not be persisted.")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def load_match_scoreboard(file_path: str = MATCH_SCOREBOARD_FILE) -> Dict[str, Dict[str, int]]:
    """Load the match-level scoreboard (per difficulty) from disk."""
    return load_scoreboard(file_path=file_path, backup_path=MATCH_SCOREBOARD_BACKUP)


def save_match_scoreboard(score: Dict[str, Dict[str, int]], file_path: str = MATCH_SCOREBOARD_FILE) -> None:
    """Persist the match-level scoreboard (per difficulty) to disk."""
    save_scoreboard(score, file_path=file_path, backup_path=MATCH_SCOREBOARD_BACKUP)


def maybe_reset_scoreboard(scoreboard: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
    choice = input("Reset scoreboard to zeroes? (y/n): ").strip().lower()
    if choice in {"y", "yes"}:
        scoreboard = new_scoreboard()
        save_scoreboard(scoreboard)
        print("Scoreboard reset.")
    return scoreboard
