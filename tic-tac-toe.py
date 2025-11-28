"""Terminal tic-tac-toe: you (X) vs. a simple AI (O) using row, column coordinates with a persistent scoreboard."""

import hashlib
import json
import os
import random
from datetime import datetime
import tempfile
from typing import Callable, Dict, List, Optional, Tuple

SCOREBOARD_FILE = "scoreboard"
HISTORY_FILE = "session_history.log"
SCORE_HASH_KEY = "hash"
SCORE_DATA_KEY = "data"
SCORE_PREV_KEY = "previous"
DIFFICULTIES = ("Easy", "Normal", "Hard")
DEFAULT_SCORE = {"X": 0, "O": 0, "Draw": 0}
HistoryEntry = Tuple[str, str, str, float]
_MINIMAX_CACHE: Dict[Tuple[str, bool], int] = {}
MINIMAX_CACHE_LIMIT = 2048
SessionStats = Dict[str, Dict[str, float]]


def _new_scoreboard() -> Dict[str, Dict[str, int]]:
    return {diff: DEFAULT_SCORE.copy() for diff in DIFFICULTIES}


def print_board(board: List[str]) -> None:
    print("\nCurrent board:")
    print("   1   2   3")
    for r in range(3):
        row_cells = board[r * 3 : (r + 1) * 3]
        print(f"{r + 1}  " + " | ".join(row_cells))
        if r < 2:
            print("  --+---+--")
    print()


def print_scoreboard(scoreboard: Dict[str, Dict[str, int]]) -> None:
    print("\nScoreboard (per difficulty):")
    for diff in DIFFICULTIES:
        entry = scoreboard.get(diff, DEFAULT_SCORE)
        print(f"{diff}: You (X): {entry['X']}  |  AI (O): {entry['O']}  |  Draws: {entry['Draw']}")


def print_history(history: List[HistoryEntry]) -> None:
    if not history:
        return
    print("Session history (most recent last):")
    for diff, result, ts, duration in history:
        dur_text = f"{duration:.1f}s" if duration else "n/a"
        print(f"- {ts} | {diff}: {result} ({dur_text})")


def _new_stats() -> SessionStats:
    return {
        diff: {
            "games": 0,
            "X": 0,
            "O": 0,
            "Draw": 0,
            "current_streak": 0,
            "best_streak": 0,
            "longest_game": 0.0,
        }
        for diff in DIFFICULTIES
    }


def update_stats(stats: SessionStats, difficulty: str, result: str, duration: float) -> None:
    entry = stats.setdefault(
        difficulty,
        {"games": 0, "X": 0, "O": 0, "Draw": 0, "current_streak": 0, "best_streak": 0, "longest_game": 0.0},
    )
    entry["games"] += 1
    entry[result] = entry.get(result, 0) + 1
    if result == "X":
        entry["current_streak"] += 1
        entry["best_streak"] = max(entry["best_streak"], entry["current_streak"])
    else:
        entry["current_streak"] = 0
    entry["longest_game"] = max(entry.get("longest_game", 0.0), duration)


def print_stats(stats: SessionStats) -> None:
    print("\nSession stats:")
    for diff in DIFFICULTIES:
        entry = stats.get(diff, {})
        games = int(entry.get("games", 0))
        if games == 0:
            print(f"- {diff}: no games played")
            continue
        win_rate = (entry.get("X", 0) / games) * 100 if games else 0
        print(
            f"- {diff}: games={games}, wins={entry.get('X', 0)}, "
            f"losses={entry.get('O', 0)}, draws={entry.get('Draw', 0)}, "
            f"win rate={win_rate:.0f}%, best streak={entry.get('best_streak', 0)}, "
            f"longest game={entry.get('longest_game', 0.0):.1f}s"
        )


def _compute_score_hash(scoreboard: Dict[str, Dict[str, int]]) -> str:
    """Generate a checksum to detect scoreboard tampering."""
    payload = json.dumps(scoreboard, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _valid_score_data(data: Dict[str, int], default_score: Dict[str, int]) -> Dict[str, int]:
    """Validate and coerce scoreboard numbers, falling back to defaults if needed."""
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
    """Validate nested per-difficulty scores."""
    scoreboard = _new_scoreboard()
    if not isinstance(data, dict):
        return scoreboard
    for diff in DIFFICULTIES:
        scoreboard[diff] = _valid_score_data(data.get(diff, {}), DEFAULT_SCORE)
    return scoreboard


def _extract_scored_payload(payload: Dict[str, object]) -> Optional[Dict[str, Dict[str, int]]]:
    """Validate a stored payload (data + hash) and return the scoreboard if valid."""
    if not isinstance(payload, dict):
        return None
    stored_scoreboard = payload.get(SCORE_DATA_KEY)
    stored_hash = payload.get(SCORE_HASH_KEY)
    merged = _valid_scoreboard(stored_scoreboard)
    if stored_hash == _compute_score_hash(merged):
        return merged
    return None


def load_scoreboard(file_path: str = SCOREBOARD_FILE) -> Dict[str, Dict[str, int]]:
    default_scoreboard = _new_scoreboard()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_scoreboard

    # Support legacy flat dict files for backward compatibility
    if isinstance(data, dict) and SCORE_DATA_KEY not in data:
        legacy = _valid_score_data(data, DEFAULT_SCORE)
        migrated = _new_scoreboard()
        migrated["Normal"] = legacy
        return migrated

    if not isinstance(data, dict):
        return default_scoreboard

    current_score = _extract_scored_payload(data)
    if current_score is not None:
        return current_score

    # Try previous snapshot before giving up
    prev_payload = data.get(SCORE_PREV_KEY)
    previous_score = _extract_scored_payload(prev_payload)
    if previous_score is not None:
        print("Scoreboard seemed corrupted; restored last valid score.")
        return previous_score

    print("Scoreboard appears tampered or corrupted. Resetting to 0s.")
    return default_scoreboard


def save_scoreboard(score: Dict[str, Dict[str, int]], file_path: str = SCOREBOARD_FILE) -> None:
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


def save_session_history_to_file(history: List[HistoryEntry], file_path: str = HISTORY_FILE, rotate: bool = False) -> str:
    if not history:
        print("No session history to save.")
        return file_path
    if rotate:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base, ext = os.path.splitext(file_path)
        file_path = f"{base}_{ts}{ext or '.log'}"
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            for diff, result, ts, duration in history:
                f.write(f"{ts} - {diff}: {result} ({duration:.1f}s)\n")
        print(f"Session history saved to {file_path}.")
    except (OSError, PermissionError) as exc:
        print(f"Could not save session history ({exc}).")
    return file_path


def maybe_reset_scoreboard(scoreboard: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
    choice = input("Reset scoreboard to zeroes? (y/n): ").strip().lower()
    if choice in {"y", "yes"}:
        scoreboard = _new_scoreboard()
        save_scoreboard(scoreboard)
        print("Scoreboard reset.")
    return scoreboard


def maybe_clear_history_file(file_path: str = HISTORY_FILE) -> None:
    if not os.path.exists(file_path):
        return
    choice = input("Clear saved session history file before starting? (y/n): ").strip().lower()
    if choice in {"y", "yes"}:
        try:
            os.remove(file_path)
            print("Session history file cleared.")
        except (OSError, PermissionError) as exc:
            print(f"Could not clear session history file ({exc}).")


def view_saved_history(file_path: str = HISTORY_FILE) -> None:
    if not os.path.exists(file_path):
        print("No saved session history file found.")
        return
    try:
        print(f"\nSaved session history from {file_path}:")
        with open(file_path, "r", encoding="utf-8") as f:
            contents = f.read().strip()
            if contents:
                print(contents)
            else:
                print("(file is empty)")
    except (OSError, PermissionError) as exc:
        print(f"Could not read session history file ({exc}).")


def check_winner(board: List[str]) -> Optional[str]:
    winning_lines = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),
        (0, 4, 8),
        (2, 4, 6),
    ]
    for a, b, c in winning_lines:
        if board[a] == board[b] == board[c] and board[a] != " ":
            return board[a]
    return None


def board_full(board: List[str]) -> bool:
    return all(cell != " " for cell in board)


def parse_move(text: str) -> Optional[Tuple[int, int]]:
    parts = text.replace(",", " ").split()
    if len(parts) == 1 and parts[0].isdigit():
        single = int(parts[0])
        if 1 <= single <= 9:
            single -= 1
            return (single // 3) + 1, (single % 3) + 1
        return None

    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return None

    row, col = (int(parts[0]), int(parts[1]))
    if not (1 <= row <= 3 and 1 <= col <= 3):
        return None
    return row, col


def get_player_move(board: List[str]) -> Optional[int]:
    """Prompt for a valid move; return None if player quits the round."""
    attempts = 0
    while True:
        move_text = input("Player X, enter row and column (or single spot 1-9, h for hint, q to quit): ").strip()
        if move_text.lower() in {"q", "quit"}:
            return None
        if move_text.lower() in {"h", "hint"}:
            hint_idx = best_player_hint(board)
            if hint_idx is None:
                print("No available moves to suggest.")
            else:
                r, c = divmod(hint_idx, 3)
                print(f"Hint: try row {r + 1}, column {c + 1}.")
            continue
        coords = parse_move(move_text)
        if not coords:
            attempts += 1
            print("Please enter a row/col from 1 to 3 (e.g., 1,3 or 2 2) or a single spot 1-9.")
            if attempts >= 5:
                confirm = input("Too many invalid tries. Quit this round? (y/n) Scores will not change if you quit: ").strip().lower()
                if confirm in {"y", "yes"}:
                    return None
                attempts = 0
            continue

        row, col = coords
        idx = (row - 1) * 3 + (col - 1)
        if board[idx] != " ":
            attempts += 1
            print("That spot is already taken. Choose another.")
            if attempts >= 5:
                confirm = input("Too many invalid tries. Quit this round? (y/n): ").strip().lower()
                if confirm in {"y", "yes"}:
                    return None
                attempts = 0
            continue
        return idx


def find_winning_move(board: List[str], symbol: str) -> Optional[int]:
    """Return index of a winning/blocking move for symbol, if any."""
    for idx in range(9):
        if board[idx] != " ":
            continue
        board[idx] = symbol
        if check_winner(board) == symbol:
            board[idx] = " "
            return idx
        board[idx] = " "
    return None


def ai_move_easy(board: List[str]) -> int:
    """Easy AI: choose a random open spot."""
    open_spots = [idx for idx, cell in enumerate(board) if cell == " "]
    return random.choice(open_spots)


def ai_move_normal(board: List[str]) -> int:
    """Normal AI: win if possible, block if needed, else take center/corner/first free."""
    win_idx = find_winning_move(board, "O")
    if win_idx is not None:
        return win_idx

    block_idx = find_winning_move(board, "X")
    if block_idx is not None:
        return block_idx

    if board[4] == " ":
        return 4

    corners = [idx for idx in (0, 2, 6, 8) if board[idx] == " "]
    if corners:
        return random.choice(corners)

    sides = [idx for idx in (1, 3, 5, 7) if board[idx] == " "]
    if sides:
        return random.choice(sides)

    open_spots = [idx for idx, cell in enumerate(board) if cell == " "]
    if open_spots:
        return random.choice(open_spots)

    return 0  # fallback, should never hit if called correctly


def ai_move_normal_defensive(board: List[str]) -> int:
    """Defensive flavor: block first, then win, favor edges to slow the game."""
    block_idx = find_winning_move(board, "X")
    if block_idx is not None:
        return block_idx

    win_idx = find_winning_move(board, "O")
    if win_idx is not None:
        return win_idx

    if board[4] == " ":
        return 4

    sides = [idx for idx in (1, 3, 5, 7) if board[idx] == " "]
    if sides:
        return random.choice(sides)

    corners = [idx for idx in (0, 2, 6, 8) if board[idx] == " "]
    if corners:
        return random.choice(corners)

    open_spots = [idx for idx, cell in enumerate(board) if cell == " "]
    return random.choice(open_spots) if open_spots else 0


def ai_move_normal_aggressive(board: List[str]) -> int:
    """Aggressive flavor: prioritize quick wins and corners before blocking."""
    win_idx = find_winning_move(board, "O")
    if win_idx is not None:
        return win_idx

    corners = [idx for idx in (0, 2, 6, 8) if board[idx] == " "]
    if corners:
        return random.choice(corners)

    block_idx = find_winning_move(board, "X")
    if block_idx is not None:
        return block_idx

    if board[4] == " ":
        return 4

    sides = [idx for idx in (1, 3, 5, 7) if board[idx] == " "]
    if sides:
        return random.choice(sides)

    open_spots = [idx for idx, cell in enumerate(board) if cell == " "]
    return random.choice(open_spots) if open_spots else 0


def find_fork_move(board: List[str], symbol: str) -> Optional[int]:
    """Return a move that creates two or more winning lines (a fork) for symbol."""
    winning_lines = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),
        (0, 4, 8),
        (2, 4, 6),
    ]
    best: List[Tuple[int, int]] = []  # (two_way_count, idx)
    for idx in range(9):
        if board[idx] != " ":
            continue
        board[idx] = symbol
        two_way = 0
        for a, b, c in winning_lines:
            line = (board[a], board[b], board[c])
            if line.count(symbol) == 2 and line.count(" ") == 1:
                two_way += 1
        board[idx] = " "
        if two_way >= 2:
            best.append((two_way, idx))

    if not best:
        return None

    # prefer higher two-way counts, then corners, then center, then lowest index
    def sort_key(item: Tuple[int, int]) -> Tuple[int, int, int]:
        count, idx = item
        is_corner = 1 if idx in (0, 2, 6, 8) else 0
        is_center = 1 if idx == 4 else 0
        return (count, is_corner, is_center, -idx)

    best_idx = max(best, key=sort_key)[1]
    return best_idx


def ai_move_misdirection(board: List[str]) -> int:
    """AI that prefers forks and trickier setups before standard play."""
    win_idx = find_winning_move(board, "O")
    if win_idx is not None:
        return win_idx

    block_idx = find_winning_move(board, "X")
    if block_idx is not None:
        return block_idx

    has_opposite_corners = (board[0] == board[8] == "X") or (board[2] == board[6] == "X")
    side_spots = [i for i in (1, 3, 5, 7) if board[i] == " "]

    fork_idx = find_fork_move(board, "O")
    if fork_idx is not None:
        return fork_idx

    block_fork_idx = find_fork_move(board, "X")
    if block_fork_idx is not None:
        if has_opposite_corners and block_fork_idx not in side_spots and side_spots:
            return random.choice(side_spots)
        return block_fork_idx

    # If player has opposite corners, take a side to avoid easy fork setups.
    if has_opposite_corners and side_spots:
        return random.choice(side_spots)

    if board[4] == " ":
        return 4

    corners = [i for i in (0, 2, 6, 8) if board[i] == " "]
    if corners:
        return random.choice(corners)

    sides = [i for i in (1, 3, 5, 7) if board[i] == " "]
    if sides:
        return random.choice(sides)

    open_spots = [idx for idx, cell in enumerate(board) if cell == " "]
    return random.choice(open_spots) if open_spots else 0


def ai_move_mirror(board: List[str]) -> int:
    """AI that mirrors the player's position across the center when possible, with defensive tweaks."""
    win_idx = find_winning_move(board, "O")
    if win_idx is not None:
        return win_idx

    block_idx = find_winning_move(board, "X")
    if block_idx is not None:
        return block_idx

    has_opposite_corners = (board[0] == board[8] == "X") or (board[2] == board[6] == "X")
    side_spots = [i for i in (1, 3, 5, 7) if board[i] == " "]

    block_fork_idx = find_fork_move(board, "X")
    if block_fork_idx is not None:
        if has_opposite_corners and block_fork_idx not in side_spots and side_spots:
            return random.choice(side_spots)
        return block_fork_idx

    if has_opposite_corners and side_spots:
        return random.choice(side_spots)

    # If the player has multiple moves on the board, fall back to optimal play to avoid easy lures.
    if board.count("X") >= 2:
        return ai_move_hard(board)

    mirror_targets = set()
    for idx, cell in enumerate(board):
        if cell == "X":
            mirror_idx = 8 - idx
            if board[mirror_idx] == " ":
                mirror_targets.add(mirror_idx)

    if board.count("X") == 1 and mirror_targets:
        return next(iter(mirror_targets))

    open_spots = [i for i, v in enumerate(board) if v == " "]
    if not open_spots:
        return 0

    best_idx = open_spots[0]
    best_score = -float("inf")
    for idx in open_spots:
        board[idx] = "O"
        score = _minimax(board, False, 0)
        board[idx] = " "
        if idx in mirror_targets:
            score += 0.5  # prefer mirroring when equally good
        if score > best_score:
            best_score = score
            best_idx = idx

    return best_idx


NORMAL_PERSONALITIES: Dict[str, Callable[[List[str]], int]] = {
    "balanced": ai_move_normal,
    "defensive": ai_move_normal_defensive,
    "aggressive": ai_move_normal_aggressive,
    "misdirection": ai_move_misdirection,
    "mirror": ai_move_mirror,
}


def _minimax(board: List[str], is_ai_turn: bool, depth: int) -> int:
    """Minimax search for tic-tac-toe. AI is O, player is X."""
    winner = check_winner(board)
    if winner == "O":
        return 10 - depth  # prefer faster wins
    if winner == "X":
        return depth - 10  # prefer slower losses
    if board_full(board):
        return 0

    key = ("".join(board), is_ai_turn)
    cached = _MINIMAX_CACHE.get(key)
    if cached is not None:
        return cached

    if is_ai_turn:
        best_score = -float("inf")
        for idx, cell in enumerate(board):
            if cell != " ":
                continue
            board[idx] = "O"
            score = _minimax(board, False, depth + 1)
            board[idx] = " "
            best_score = max(best_score, score)
        if len(_MINIMAX_CACHE) >= MINIMAX_CACHE_LIMIT:
            _MINIMAX_CACHE.clear()
        _MINIMAX_CACHE[key] = best_score
        return best_score

    best_score = float("inf")
    for idx, cell in enumerate(board):
        if cell != " ":
            continue
        board[idx] = "X"
        score = _minimax(board, True, depth + 1)
        board[idx] = " "
        best_score = min(best_score, score)
    if len(_MINIMAX_CACHE) >= MINIMAX_CACHE_LIMIT:
        _MINIMAX_CACHE.clear()
    _MINIMAX_CACHE[key] = best_score
    return best_score


def ai_move_hard(board: List[str]) -> int:
    """Hard AI: optimal play using minimax."""
    best_score = -float("inf")
    best_idx = 0
    for idx, cell in enumerate(board):
        if cell != " ":
            continue
        board[idx] = "O"
        score = _minimax(board, False, 0)
        board[idx] = " "
        if score > best_score:
            best_score = score
            best_idx = idx
    return best_idx


def best_player_hint(board: List[str]) -> Optional[int]:
    """Suggest the best move for the player (X) by minimizing the AI's outcome."""
    best_score = float("inf")
    best_idx: Optional[int] = None
    for idx, cell in enumerate(board):
        if cell != " ":
            continue
        board[idx] = "X"
        score = _minimax(board, True, 0)  # AI to move next; lower is better for player
        board[idx] = " "
        if score < best_score:
            best_score = score
            best_idx = idx
    return best_idx


def choose_normal_personality() -> Tuple[str, Callable[[List[str]], int]]:
    options = {
        "1": "balanced",
        "balanced": "balanced",
        "2": "defensive",
        "defensive": "defensive",
        "3": "aggressive",
        "aggressive": "aggressive",
        "4": "misdirection",
        "misdirection": "misdirection",
        "5": "mirror",
        "mirror": "mirror",
    }
    while True:
        choice = input(
            "Choose AI personality for Normal - 1: Balanced, 2: Defensive, 3: Aggressive, 4: Misdirection, 5: Mirror: "
        ).strip().lower()
        if choice in options:
            personality = options[choice]
            return personality, NORMAL_PERSONALITIES[personality]
        print("Please enter 1-5 or a personality name (balanced/defensive/aggressive/misdirection/mirror).")


def choose_difficulty() -> Tuple[str, Callable[[List[str]], int], str]:
    options = {
        "1": "Easy",
        "easy": "Easy",
        "2": "Normal",
        "normal": "Normal",
        "3": "Hard",
        "hard": "Hard",
    }
    while True:
        choice = input("Choose AI difficulty - 1: Easy, 2: Normal, 3: Hard: ").strip().lower()
        if choice in options:
            level = options[choice]
            if level == "Easy":
                return level, ai_move_easy, "standard"
            if level == "Normal":
                personality, move_fn = choose_normal_personality()
                return level, move_fn, personality
            return level, ai_move_hard, "standard"
        print("Please enter 1, 2, 3, or a difficulty name (easy/normal/hard).")


def difficulty_display_label(level: str, personality: str) -> str:
    if level != "Normal":
        return level
    return f"{level} ({personality})"


def play_round(ai_move_fn: Callable[[List[str]], int], difficulty_label: str) -> Optional[Tuple[str, float]]:
    board = [" "] * 9
    print(f"\nNew round! Difficulty: {difficulty_label}. You are X, the AI is O.")
    print("Enter your move as row, column (both 1-3) or a single spot 1-9. Example: 2,3 or 5")
    start_time = datetime.now()

    while True:
        print_board(board)
        idx = get_player_move(board)
        if idx is None:
            print("Exiting round by request. No score recorded for this round.")
            return None

        if board[idx] != " ":
            # This case is already handled in get_player_move but keep guard-rail.
            print("That spot is already taken. Choose another.")
            continue

        row_label, col_label = divmod(idx, 3)
        confirm = input(f"Confirm move at row {row_label + 1}, column {col_label + 1}? (y to confirm, u to re-enter, q to quit round): ").strip().lower()
        if confirm in {"q", "quit"}:
            print("Exiting round by request. No score recorded for this round.")
            return None
        if confirm not in {"y", "yes"}:
            continue

        board[idx] = "X"

        winner = check_winner(board)
        if winner:
            print_board(board)
            print(f"Player {winner} wins!")
            duration = (datetime.now() - start_time).total_seconds()
            return winner, duration

        if board_full(board):
            print_board(board)
            print("It's a draw.")
            duration = (datetime.now() - start_time).total_seconds()
            return "Draw", duration

        ai_idx = ai_move_fn(board)
        board[ai_idx] = "O"
        ai_row, ai_col = divmod(ai_idx, 3)
        print(f"AI plays at row {ai_row + 1}, column {ai_col + 1}.")

        winner = check_winner(board)
        if winner:
            print_board(board)
            print(f"Player {winner} wins!")
            duration = (datetime.now() - start_time).total_seconds()
            return winner, duration

        if board_full(board):
            print_board(board)
            print("It's a draw.")
            duration = (datetime.now() - start_time).total_seconds()
            return "Draw", duration


def play_session(scoreboard: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
    _MINIMAX_CACHE.clear()
    session_history: List[HistoryEntry] = []
    stats = _new_stats()

    diff_key, ai_move_fn, personality = choose_difficulty()
    difficulty_label = difficulty_display_label(diff_key, personality)
    print(f"Starting game on {difficulty_label}.")

    while True:
        print_history(session_history)
        print_stats(stats)

        result = play_round(ai_move_fn, difficulty_label)
        if result is None:
            quit_game = input("Quit the game entirely? (y/n): ").strip().lower()
            if quit_game in {"y", "yes"}:
                break
            continue

        winner, duration = result

        if diff_key not in scoreboard:
            scoreboard[diff_key] = DEFAULT_SCORE.copy()
        scoreboard[diff_key][winner] += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session_history.append((difficulty_label, winner, timestamp, duration))
        update_stats(stats, diff_key, winner, duration)

        save_scoreboard(scoreboard)
        print_scoreboard(scoreboard)
        print_stats(stats)
        print_history(session_history)

        again = input("Play again? (y/n): ").strip().lower()
        if again not in {"y", "yes"}:
            break

        change_diff = input("Change difficulty/personality for next round? (y/n): ").strip().lower()
        if change_diff in {"y", "yes"}:
            diff_key, ai_move_fn, personality = choose_difficulty()
            difficulty_label = difficulty_display_label(diff_key, personality)
            print(f"Switched to {difficulty_label}.")

    print("\nThanks for playing this session!")
    print_scoreboard(scoreboard)
    print_stats(stats)
    print_history(session_history)

    save_session_history_to_file(session_history, rotate=True)

    return scoreboard


def play_game() -> None:
    scoreboard = load_scoreboard()
    print("Tic-Tac-Toe (persistent scoreboard)")
    print_scoreboard(scoreboard)
    scoreboard = maybe_reset_scoreboard(scoreboard)
    print_scoreboard(scoreboard)
    maybe_clear_history_file()

    while True:
        print(
            "\nMain menu:\n"
            "1) Start session\n"
            "2) View scoreboard\n"
            "3) View saved session history file\n"
            "4) Reset scoreboard\n"
            "5) Quit\n"
        )
        choice = input("Select an option: ").strip().lower()
        if choice in {"1", "start", "s"}:
            scoreboard = play_session(scoreboard)
        elif choice in {"2", "scoreboard", "view"}:
            print_scoreboard(scoreboard)
        elif choice in {"3", "history", "h"}:
            view_saved_history()
        elif choice in {"4", "reset", "r"}:
            scoreboard = maybe_reset_scoreboard(scoreboard)
            print_scoreboard(scoreboard)
        elif choice in {"5", "quit", "q", "exit"}:
            break
        else:
            print("Please choose 1-5 or a listed command.")

    print("\nThanks for playing!")
    print_scoreboard(scoreboard)
    input("\nGame over. Press Enter to close the game.")


if __name__ == "__main__":
    play_game()
