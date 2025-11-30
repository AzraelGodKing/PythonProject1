"""Terminal tic-tac-toe: you (X) vs. a simple AI (O) using row, column coordinates with a persistent scoreboard."""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple
from . import scoreboard

DATA_DIR = scoreboard.DATA_DIR
SCOREBOARD_DIR = scoreboard.SCOREBOARD_DIR
HISTORY_DIR = os.path.join(DATA_DIR, "history")
SCOREBOARD_FILE = scoreboard.SCOREBOARD_FILE
SCOREBOARD_BACKUP = scoreboard.SCOREBOARD_BACKUP
HISTORY_FILE = os.path.join(HISTORY_DIR, "session_history.log")
BANNER_FILE = os.path.join(SCOREBOARD_DIR, "badges.json")
SAFE_MODE = scoreboard.SAFE_MODE
SAFE_MODE_MESSAGE = scoreboard.SAFE_MODE_MESSAGE
DEFAULT_MATCH_LENGTH = 3
DIFFICULTIES = scoreboard.DIFFICULTIES
DEFAULT_SCORE = scoreboard.DEFAULT_SCORE
DEFAULT_ERROR_RATE = 0.0
HistoryEntry = Tuple[str, str, str, float]
_MINIMAX_CACHE: Dict[Tuple[str, bool], int] = {}
MINIMAX_CACHE_LIMIT = 2048
SessionStats = Dict[str, Dict[str, float]]

new_scoreboard = scoreboard.new_scoreboard
print_scoreboard = scoreboard.print_scoreboard
load_scoreboard = scoreboard.load_scoreboard
save_scoreboard = scoreboard.save_scoreboard
maybe_reset_scoreboard = scoreboard.maybe_reset_scoreboard
load_match_scoreboard = scoreboard.load_match_scoreboard
save_match_scoreboard = scoreboard.save_match_scoreboard
print_match_scoreboard = scoreboard.print_match_scoreboard


def configure_history_file(path: Optional[str]) -> None:
    """Allow CLI/tests to override where history logs are written/read."""
    global HISTORY_FILE, HISTORY_DIR
    if not path:
        return
    HISTORY_FILE = path
    HISTORY_DIR = os.path.dirname(path) or "."


def set_safe_mode(enabled: bool) -> None:
    """Expose runtime safe-mode toggling for CLI flags/tests."""
    scoreboard.set_safe_mode(enabled)
    global SAFE_MODE
    SAFE_MODE = scoreboard.SAFE_MODE


def load_badges(file_path: str = BANNER_FILE) -> Dict[str, Dict[str, float]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {
                diff: {
                    "best_streak": float(entry.get("best_streak", 0)),
                    "fastest_win": float(entry.get("fastest_win")) if entry.get("fastest_win") is not None else None,
                }
                for diff, entry in data.items()
                if isinstance(entry, dict)
            }
    except (OSError, json.JSONDecodeError):
        return {}
    return {}


def save_badges(badges: Dict[str, Dict[str, float]], file_path: str = BANNER_FILE) -> None:
    if SAFE_MODE:
        return
    try:
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(badges, f)
    except OSError:
        pass
    return None


def run_doctor() -> None:
    print("Tic-Tac-Toe diagnostics")
    print(f"- Python: {sys.version.split()[0]}")
    print(f"- Safe mode: {SAFE_MODE}")
    print(f"- Scoreboard file: {SCOREBOARD_FILE}")
    print(f"- History file: {HISTORY_FILE}")
    print(f"- Badges file: {BANNER_FILE}")

    def _check(path: str) -> str:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    f.read(64)
                return "ok"
            return "missing"
        except Exception as exc:
            return f"error ({exc})"

    print(f"- Scoreboard status: {_check(SCOREBOARD_FILE)}")
    print(f"- Match scoreboard status: {_check(scoreboard.MATCH_SCOREBOARD_FILE)}")
    print(f"- History status: {_check(HISTORY_FILE)}")
    print(f"- Badges status: {_check(BANNER_FILE)}")


def play_replay(file_path: str) -> None:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read replay ({exc}).")
        return
    moves: List[Tuple[str, int]] = data.get("moves", [])
    board = [" "] * 9
    print(f"Replaying {len(moves)} moves from {file_path}")
    for turn, item in enumerate(moves, start=1):
        if not (isinstance(item, list) or isinstance(item, tuple)) or len(item) != 2:
            print(f"Invalid move format at turn {turn}")
            return
        symbol, idx = item
        if symbol not in {"X", "O"}:
            print(f"Invalid symbol at move {turn}")
            return
        if not isinstance(idx, int) or idx < 0 or idx > 8:
            print(f"Invalid index at move {turn}")
            return
        if board[idx] != " ":
            print(f"Conflict at move {turn}: spot already taken.")
            return
        board[idx] = symbol
        print_board(board)
        winner = check_winner(board)
        if winner:
            print(f"Winner at move {turn}: {winner}")
            break
        if board_full(board):
            print("Board full: draw.")
            break
    print("Replay complete.")


def run_hard_batch(rounds: int) -> int:
    """Run headless Hard vs Hard to ensure no losses."""
    failures = 0
    for _ in range(rounds):
        board = [" "] * 9
        current = "X"
        while True:
            idx = ai_move_hard(board)
            board[idx] = current
            winner = check_winner(board)
            if winner:
                if winner != "Draw":
                    failures += 1
                break
            if board_full(board):
                break
            current = "O" if current == "X" else "X"
    return failures


def run_perf_dashboard() -> None:
    print("Performance dashboard (minimax)")
    start = time.perf_counter()
    for _ in range(200):
        ai_move_hard([" "] * 9)
    elapsed_empty = time.perf_counter() - start
    print(f"- 200 empty-board Hard moves: {elapsed_empty:.3f}s")
    import random

    boards = []
    for _ in range(200):
        b = [" "] * 9
        filled = random.sample(range(9), k=random.randint(0, 6))
        for idx in filled:
            b[idx] = random.choice(["X", "O"])
        boards.append(b)
    start = time.perf_counter()
    for b in boards:
        ai_move_hard(b[:])
    elapsed_mixed = time.perf_counter() - start
    print(f"- 200 mixed-board Hard moves: {elapsed_mixed:.3f}s")


def update_badges_for_diff(
    badges: Dict[str, Dict[str, float]],
    difficulty: str,
    best_streak: Optional[int],
    fastest_win: Optional[float],
) -> Dict[str, bool]:
    updated = {"streak": False, "fastest": False}
    entry = badges.setdefault(difficulty, {"best_streak": 0, "fastest_win": None})
    if best_streak is not None and best_streak > entry.get("best_streak", 0):
        entry["best_streak"] = best_streak
        updated["streak"] = True
    if fastest_win is not None:
        current_fw = entry.get("fastest_win")
        if current_fw is None or fastest_win < current_fw:
            entry["fastest_win"] = fastest_win
            updated["fastest"] = True
    return updated


def reset_badges_and_history() -> None:
    """Clean slate: reset badges file and clear session history; leave scoreboard intact."""
    save_badges({})
    try:
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
    except OSError:
        pass


def print_board(board: List[str]) -> None:
    print("\nCurrent board:")
    print("   1   2   3")
    for r in range(3):
        row_cells = board[r * 3 : (r + 1) * 3]
        print(f"{r + 1}  " + " | ".join(row_cells))
        if r < 2:
            print("  --+---+--")
    print()


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
            "fastest_win": None,
        }
        for diff in DIFFICULTIES
    }


def update_stats(stats: SessionStats, difficulty: str, result: str, duration: float) -> None:
    entry = stats.setdefault(
        difficulty,
        {
            "games": 0,
            "X": 0,
            "O": 0,
            "Draw": 0,
            "current_streak": 0,
            "best_streak": 0,
            "longest_game": 0.0,
            "fastest_win": None,
        },
    )
    entry["games"] += 1
    entry[result] = entry.get(result, 0) + 1
    if result == "X":
        entry["current_streak"] += 1
        entry["best_streak"] = max(entry["best_streak"], entry["current_streak"])
        if duration and duration > 0:
            fw = entry.get("fastest_win")
            entry["fastest_win"] = duration if fw is None else min(fw, duration)
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
            f"longest game={entry.get('longest_game', 0.0):.1f}s, "
            f"fastest win={entry.get('fastest_win') or 'n/a'}"
        )


def compute_achievements(stats: SessionStats, history: List[HistoryEntry]) -> List[str]:
    achievements: List[str] = []
    total_wins = sum(int(stats.get(diff, {}).get("X", 0)) for diff in DIFFICULTIES)
    total_games = sum(int(stats.get(diff, {}).get("games", 0)) for diff in DIFFICULTIES)
    total_draws = sum(int(stats.get(diff, {}).get("Draw", 0)) for diff in DIFFICULTIES)
    max_streak = max(int(stats.get(diff, {}).get("best_streak", 0)) for diff in DIFFICULTIES)
    fastest_wins = [entry.get("fastest_win") for entry in stats.values() if entry.get("fastest_win")]
    fastest_win = min(fastest_wins) if fastest_wins else None
    hard_wins = int(stats.get("Hard", {}).get("X", 0))
    easy_wins = int(stats.get("Easy", {}).get("X", 0))
    normal_wins = int(stats.get("Normal", {}).get("X", 0))
    hard_draws = int(stats.get("Hard", {}).get("Draw", 0))
    normal_draws = int(stats.get("Normal", {}).get("Draw", 0))
    easy_draws = int(stats.get("Easy", {}).get("Draw", 0))
    longest_games = [entry.get("longest_game", 0.0) for entry in stats.values()]
    longest_game = max(longest_games) if longest_games else 0.0
    recent_hard_wins = sum(1 for diff, res, _, _ in history[-5:] if diff == "Hard" and res == "X")
    recent_normal_wins = sum(1 for diff, res, _, _ in history[-5:] if diff == "Normal" and res == "X")
    recent_easy_wins = sum(1 for diff, res, _, _ in history[-5:] if diff == "Easy" and res == "X")
    recent_draws = sum(1 for _, res, _, _ in history[-5:] if res == "Draw")

    streak = 0
    best_streak_recent = 0
    for _, res, _, _ in history[-10:]:
        if res == "X":
            streak += 1
            best_streak_recent = max(best_streak_recent, streak)
        else:
            streak = 0

    milestones = [
        (total_wins >= 1, "First win!"),
        (total_wins >= 5, "Win 5 games overall."),
        (total_wins >= 10, "Win 10 games overall."),
        (total_wins >= 25, "Win 25 games overall."),
        (total_wins >= 50, "Win 50 games overall."),
        (total_wins >= 100, "Win 100 games overall."),
        (total_games >= 10, "Play 10 games overall."),
        (total_games >= 50, "Play 50 games overall."),
        (total_games >= 100, "Play 100 games overall."),
        (total_draws >= 5, "Five draws overall."),
        (total_draws >= 15, "Draw connoisseur: 15 draws overall."),
    ]
    achievements.extend([desc for ok, desc in milestones if ok])

    streaks = [
        (max_streak >= 3, f"Hot streak: {max_streak} wins in a row."),
        (max_streak >= 5, f"On fire: {max_streak} wins in a row."),
        (best_streak_recent >= 3, f"Recent streak: {best_streak_recent} in last 10."),
    ]
    achievements.extend([desc for ok, desc in streaks if ok])

    if fastest_win and fastest_win <= 15:
        achievements.append(f"Speedster: win under {fastest_win:.1f}s.")
    if fastest_win and fastest_win <= 8:
        achievements.append(f"Blazing fast: win under {fastest_win:.1f}s.")
    if longest_game >= 60:
        achievements.append(f"Marathoner: played a game lasting {longest_game:.1f}s.")

    difficulty_achs = [
        (easy_wins >= 3, "Easy mode warmup: 3 wins."),
        (easy_wins >= 10, "Easy mode veteran: 10 wins."),
        (normal_wins >= 3, "Normal contender: 3 wins."),
        (normal_wins >= 10, "Normal champ: 10 wins."),
        (hard_wins >= 1, "Cracked Hard mode once."),
        (hard_wins >= 3, "Hard mode regular (3+ wins)."),
        (hard_wins >= 5, "Hard mode seasoned (5 wins)."),
        (hard_draws >= 3, "Stalemate with Hard: 3 draws."),
        (normal_draws >= 5, "Middle ground: 5 draws on Normal."),
        (easy_draws >= 3, "Even on Easy: 3 draws."),
    ]
    achievements.extend([desc for ok, desc in difficulty_achs if ok])

    recent_achs = [
        (recent_hard_wins >= 1, "Recent Hard win in last 5 games."),
        (recent_normal_wins >= 2, "Two Normal wins in last 5."),
        (recent_easy_wins >= 3, "Easy sweep: 3 wins in last 5 on Easy."),
        (recent_draws >= 2, "Recent draw-heavy run."),
    ]
    achievements.extend([desc for ok, desc in recent_achs if ok])

    if hard_wins >= 1 and normal_wins >= 1 and easy_wins >= 1:
        achievements.append("All-rounder: wins on Easy, Normal, Hard.")
    if hard_wins >= 2 and max_streak >= 2:
        achievements.append("Hard streaker: 2+ Hard wins with streak 2+.")
    if fastest_win and max_streak >= 3:
        achievements.append("Fast and consistent: streak 3+ with a fast win.")

    return achievements or ["None yet. Keep playing!"]


def print_achievements(stats: SessionStats, history: List[HistoryEntry]) -> None:
    print("\nAchievements:")
    for item in compute_achievements(stats, history):
        print(f"- {item}")


def save_session_history_to_file(history: List[HistoryEntry], file_path: Optional[str] = None, rotate: bool = False) -> str:
    file_path = file_path or HISTORY_FILE
    if SAFE_MODE:
        print(SAFE_MODE_MESSAGE)
        return file_path
    if not history:
        print("No session history to save.")
        return file_path
    if rotate:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base, ext = os.path.splitext(file_path)
        file_path = f"{base}_{ts}{ext or '.log'}"
    dir_name = os.path.dirname(file_path) or "."
    os.makedirs(dir_name, exist_ok=True)
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            for diff, result, ts, duration in history:
                f.write(f"{ts} - {diff}: {result} ({duration:.1f}s)\n")
        print(f"Session history saved to {file_path}.")
    except (OSError, PermissionError) as exc:
        print(f"Could not save session history ({exc}).")
    return file_path


def load_session_history_from_file(file_path: Optional[str] = None, limit: int = 100) -> List[HistoryEntry]:
    file_path = file_path or HISTORY_FILE
    if SAFE_MODE:
        return []
    entries: List[HistoryEntry] = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
    except FileNotFoundError:
        return []
    except OSError:
        return []

    for line in lines:
        text = line.strip()
        if " - " not in text or ":" not in text:
            continue
        ts_part, rest = text.split(" - ", 1)
        diff_part, result_part = rest.split(":", 1)
        result_part = result_part.strip()
        duration = 0.0
        if "(" in result_part and ")" in result_part:
            main, _, dur_text = result_part.partition("(")
            result_part = main.strip()
            dur_text = dur_text.strip("()s ")
            try:
                duration = float(dur_text)
            except ValueError:
                duration = 0.0
        diff = diff_part.strip()
        result = result_part
        entries.append((diff, result, ts_part, duration))
    return entries


def maybe_clear_history_file(file_path: Optional[str] = None) -> None:
    file_path = file_path or HISTORY_FILE
    if not os.path.exists(file_path):
        return
    choice = input("Clear saved session history file before starting? (y/n): ").strip().lower()
    if choice in {"y", "yes"}:
        try:
            os.remove(file_path)
            print("Session history file cleared.")
        except (OSError, PermissionError) as exc:
            print(f"Could not clear session history file ({exc}).")


def view_saved_history(file_path: Optional[str] = None) -> None:
    file_path = file_path or HISTORY_FILE
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
            open_moves = [str(i + 1) for i, v in enumerate(board) if v == " "]
            if open_moves:
                print(
                    "Please enter a row/col from 1 to 3 (e.g., 1,3 or 2 2) or a single spot 1-9. "
                    f"Open spots: {', '.join(open_moves)}"
                )
            else:
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


def ai_move_normal_humanish(board: List[str], error_rate: float = 0.15) -> int:
    """Normal AI with occasional suboptimal move to mimic human mistakes."""
    if random.random() < error_rate:
        open_spots = [idx for idx, cell in enumerate(board) if cell == " "]
        if open_spots:
            return random.choice(open_spots)
    return ai_move_normal(board)


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


def choose_normal_personality(preferred: Optional[str] = None) -> Tuple[str, Callable[[List[str]], int]]:
    if preferred and preferred in NORMAL_PERSONALITIES:
        return preferred, NORMAL_PERSONALITIES[preferred]
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


def choose_match_length(preferred: Optional[int] = None) -> int:
    if isinstance(preferred, int) and preferred >= 1 and preferred % 2 == 1:
        return preferred
    while True:
        text = input(f"Choose match length (odd number, best-of). Press Enter for default {DEFAULT_MATCH_LENGTH}: ").strip()
        if not text:
            return DEFAULT_MATCH_LENGTH
        if text.isdigit():
            val = int(text)
            if val >= 1 and val % 2 == 1:
                return val
        print("Please enter an odd number like 3, 5, or 7 (or press Enter for default).")


def print_match_score(match_wins: Dict[str, int], target: int) -> None:
    print(f"Match score (target {target} wins): X={match_wins['X']}  O={match_wins['O']}  Draws={match_wins['Draw']}")


def choose_difficulty(preferred: Optional[str] = None, personality: Optional[str] = None, error_rate: float = DEFAULT_ERROR_RATE) -> Tuple[str, Callable[[List[str]], int], str]:
    options = {
        "1": "Easy",
        "easy": "Easy",
        "2": "Normal",
        "normal": "Normal",
        "3": "Hard",
        "hard": "Hard",
    }
    if preferred:
        normalized = preferred if preferred in {"Easy", "Normal", "Hard"} else options.get(preferred.lower())
        if normalized == "Easy":
            return normalized, ai_move_easy, "standard"
        if normalized == "Normal":
            personality = personality or "balanced"
            if personality not in NORMAL_PERSONALITIES:
                personality = "balanced"
            if error_rate > 0:
                return normalized, lambda board: ai_move_normal_humanish(board, error_rate), personality
            return normalized, NORMAL_PERSONALITIES[personality], personality
        if normalized == "Hard":
            return normalized, ai_move_hard, "standard"
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


def play_round(
    ai_move_fn: Callable[[List[str]], int],
    difficulty_label: str,
    moves_log: Optional[List[Tuple[str, int]]] = None,
) -> Optional[Tuple[str, float]]:
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
        if moves_log is not None:
            moves_log.append(("X", idx))

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
        if moves_log is not None:
            moves_log.append(("O", ai_idx))
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


def play_session(
    scoreboard: Dict[str, Dict[str, int]],
    diff_key_override: Optional[str] = None,
    personality_override: Optional[str] = None,
    match_length_override: Optional[int] = None,
    non_interactive: bool = False,
    summary: Optional[Dict[str, object]] = None,
    history_limit: int = 100,
    moves_log: Optional[List[Tuple[str, int]]] = None,
    error_rate: float = DEFAULT_ERROR_RATE,
) -> Dict[str, Dict[str, int]]:
    _MINIMAX_CACHE.clear()
    session_history: List[HistoryEntry] = load_session_history_from_file(limit=history_limit)
    stats = _new_stats()
    match_scoreboard = load_match_scoreboard()
    badges = load_badges()

    diff_key, ai_move_fn, personality = choose_difficulty(diff_key_override, personality_override, error_rate)
    difficulty_label = difficulty_display_label(diff_key, personality)
    print(f"Starting game on {difficulty_label}.")
    match_length = choose_match_length(match_length_override)
    match_target = (match_length // 2) + 1
    match_wins = {"X": 0, "O": 0, "Draw": 0}
    match_rounds = 0
    match_winner: Optional[str] = None
    last_result: Optional[str] = None

    while True:
        print_history(session_history)
        print_stats(stats)
        print_match_score(match_wins, match_target)
        print_achievements(stats, session_history)

        result = play_round(ai_move_fn, difficulty_label, moves_log=moves_log)
        if result is None:
            if non_interactive:
                break
            quit_game = input("Quit the game entirely? (y/n): ").strip().lower()
            if quit_game in {"y", "yes"}:
                break
            continue

        winner, duration = result
        last_result = winner

        if diff_key not in scoreboard:
            scoreboard[diff_key] = DEFAULT_SCORE.copy()
        scoreboard[diff_key][winner] += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session_history.append((difficulty_label, winner, timestamp, duration))
        update_stats(stats, diff_key, winner, duration)
        match_wins[winner] = match_wins.get(winner, 0) + 1
        match_rounds += 1

        # Badge tracking per difficulty (best streak, fastest win)
        streak_best = stats.get(diff_key, {}).get("best_streak")
        fastest_win = stats.get(diff_key, {}).get("fastest_win")
        improved = update_badges_for_diff(badges, diff_key, streak_best, fastest_win)
        if any(improved.values()):
            save_badges(badges)
            if improved["streak"]:
                print(f"New best streak on {diff_key}: {streak_best} wins.")
            if improved["fastest"] and fastest_win:
                print(f"Fastest win on {diff_key}: {fastest_win:.1f}s.")

        save_scoreboard(scoreboard)
        print_scoreboard(scoreboard)
        print_stats(stats)
        print_history(session_history)
        print_match_score(match_wins, match_target)
        print_achievements(stats, session_history)

        match_done = False
        reason = "target"
        if match_wins["X"] >= match_target or match_wins["O"] >= match_target:
            match_done = True
            reason = "target"
        elif match_rounds >= match_length:
            match_done = True
            reason = "rounds"

        if match_done:
            if match_wins["X"] > match_wins["O"]:
                match_winner = "X"
            elif match_wins["O"] > match_wins["X"]:
                match_winner = "O"
            else:
                match_winner = "Draw"
            if match_winner == "Draw":
                if reason == "rounds":
                    print("Match over! No winner after the full match length (draw).")
                else:
                    print("Match over! It ended in a draw.")
            else:
                print(f"Match over! Winner: {match_winner}")
            # record match outcome per difficulty (skip single-round Bo1)
            if match_target > 1:
                if diff_key not in match_scoreboard:
                    match_scoreboard[diff_key] = DEFAULT_SCORE.copy()
                match_scoreboard[diff_key][match_winner] += 1
                save_match_scoreboard(match_scoreboard)
                print_match_scoreboard(match_scoreboard)
            if non_interactive:
                break
            another_match = input("Start another match? (y/n): ").strip().lower()
            if another_match in {"y", "yes"}:
                match_length = choose_match_length()
                match_target = (match_length // 2) + 1
                match_wins = {"X": 0, "O": 0, "Draw": 0}
                match_rounds = 0
                change_diff = input("Change difficulty/personality for next match? (y/n): ").strip().lower()
                if change_diff in {"y", "yes"}:
                    diff_key, ai_move_fn, personality = choose_difficulty()
                    difficulty_label = difficulty_display_label(diff_key, personality)
                    print(f"Switched to {difficulty_label}.")
                continue
            break
        else:
            if non_interactive:
                break
            cont = input("Continue the current match? (y to continue, n to end): ").strip().lower()
            if cont not in {"y", "yes"}:
                break

    print("\nThanks for playing this session!")
    print_scoreboard(scoreboard)
    print_stats(stats)
    print_history(session_history)
    print_match_scoreboard(match_scoreboard)

    save_session_history_to_file(session_history, rotate=True)

    if summary is not None:
        summary.clear()
        summary.update(
            {
                "difficulty": diff_key,
                "personality": personality,
                "match_length": match_length,
                "match_target": match_target,
                "match_rounds": match_rounds,
                "match_winner": match_winner,
                "last_result": last_result,
                "match_wins": dict(match_wins),
                "history_entries": len(session_history),
                "scoreboard": {k: dict(v) for k, v in scoreboard.items()},
                "badges": badges,
                "moves": moves_log or [],
            }
        )
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
            "3) View match scoreboard\n"
            "4) View saved session history file\n"
            "5) Reset scoreboard\n"
            "6) Quit\n"
        )
        choice = input("Select an option: ").strip().lower()
        if choice in {"1", "start", "s"}:
            scoreboard = play_session(scoreboard)
        elif choice in {"2", "scoreboard", "view"}:
            print_scoreboard(scoreboard)
        elif choice in {"3", "match", "m"}:
            print_match_scoreboard(load_match_scoreboard())
        elif choice in {"4", "history", "h"}:
            view_saved_history()
        elif choice in {"5", "reset", "r"}:
            scoreboard = maybe_reset_scoreboard(scoreboard)
            print_scoreboard(scoreboard)
        elif choice in {"6", "quit", "q", "exit"}:
            break
        else:
            print("Please choose 1-6 or a listed command.")

    print("\nThanks for playing!")
    print_scoreboard(scoreboard)
    input("\nGame over. Press Enter to close the game.")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tic-Tac-Toe CLI with optional automation-friendly flags.")
    parser.add_argument("--difficulty", choices=DIFFICULTIES, help="AI difficulty to start with.")
    parser.add_argument(
        "--personality",
        choices=tuple(NORMAL_PERSONALITIES.keys()),
        help="Normal-mode AI personality (only used when difficulty=Normal).",
    )
    parser.add_argument("--best-of", type=int, help="Match length (odd number) to start with.")
    parser.add_argument("--history-file", help="Path to session history log.")
    safe = parser.add_mutually_exclusive_group()
    safe.add_argument("--safe-mode", dest="safe_mode", action="store_true", help="Disable persistence during this run.")
    safe.add_argument("--persist", dest="safe_mode", action="store_false", help="Force persistence during this run.")
    parser.set_defaults(safe_mode=None)
    parser.add_argument(
        "--start",
        action="store_true",
        help="Skip the main menu and start a match immediately (uses provided flags if set).",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip follow-up prompts (e.g., new match) after the first match completes.",
    )
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Choose text (default) or json summary output when auto-starting.",
    )
    parser.add_argument("--result-file", help="Optional path to write the summary JSON.")
    parser.add_argument(
        "--expect-winner",
        choices=("X", "O", "Draw"),
        help="If set, exit non-zero unless the match winner (or last result) matches.",
    )
    parser.add_argument(
        "--history-limit",
        type=int,
        default=100,
        help="Maximum history entries to load for the session (default 100).",
    )
    parser.add_argument(
        "--truncate-history",
        action="store_true",
        help="Remove existing history file before starting (saves clean logs).",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Run diagnostics (paths, safe mode, scoreboard integrity) and exit.",
    )
    parser.add_argument(
        "--preset",
        choices=("easy3", "normal5", "hard1"),
        help="Quick-start preset: easy3 (Easy Bo3), normal5 (Normal balanced Bo5), hard1 (Hard Bo1).",
    )
    parser.add_argument("--save-replay", help="Write the auto-started game replay to this JSON file.")
    parser.add_argument("--replay-file", help="Play back a saved replay JSON and exit.")
    parser.add_argument("--ai-error-rate", type=float, default=DEFAULT_ERROR_RATE, help="Chance (0-1) for Normal AI to make a random move.")
    parser.add_argument("--batch-hard", type=int, default=0, help="Run N hard-mode self-tests to ensure no losses (headless).")
    parser.add_argument("--perf", action="store_true", help="Run a quick performance dashboard (minimax benchmarks).")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    if args.replay_file:
        play_replay(args.replay_file)
        return
    if args.doctor:
        run_doctor()
        return
    if args.safe_mode is not None:
        set_safe_mode(args.safe_mode)
    if args.history_file:
        configure_history_file(args.history_file)
    if args.truncate_history:
        try:
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
        except OSError:
            pass

    if args.batch_hard and args.batch_hard > 0:
        failures = run_hard_batch(args.batch_hard)
        if failures:
            print(f"Hard batch failures: {failures}")
            raise SystemExit(1)
        print(f"Hard batch ({args.batch_hard}) passed with no losses.")
        return

    if args.perf:
        run_perf_dashboard()
        return

    scoreboard_obj = load_scoreboard()
    if args.preset and not args.difficulty:
        if args.preset == "easy3":
            args.difficulty = "Easy"
            args.best_of = 3
        elif args.preset == "normal5":
            args.difficulty = "Normal"
            args.personality = args.personality or "balanced"
            args.best_of = 5
        elif args.preset == "hard1":
            args.difficulty = "Hard"
            args.best_of = 1

    auto_start = args.start or args.difficulty or args.personality or args.best_of
    if auto_start:
        summary: Dict[str, object] = {}
        play_session(
            scoreboard_obj,
            diff_key_override=args.difficulty,
            personality_override=args.personality,
            match_length_override=args.best_of,
            non_interactive=args.non_interactive,
            summary=summary,
            history_limit=max(1, args.history_limit),
            moves_log=[],
            error_rate=max(0.0, args.ai_error_rate),
        )
        expected = args.expect_winner
        if expected:
            actual = summary.get("match_winner") or summary.get("last_result")
            if actual != expected:
                print(f"Expected winner {expected}, but got {actual}.")
                raise SystemExit(1)
        if args.save_replay:
            try:
                os.makedirs(os.path.dirname(args.save_replay) or ".", exist_ok=True)
                with open(args.save_replay, "w", encoding="utf-8") as f:
                    json.dump(summary, f)
                print(f"Replay saved to {args.save_replay}")
            except OSError as exc:
                print(f"Could not save replay: {exc}")
        if args.output == "json":
            payload = json.dumps(summary, indent=2)
            print(payload)
            if args.result_file:
                try:
                    with open(args.result_file, "w", encoding="utf-8") as f:
                        f.write(payload)
                except OSError as exc:
                    print(f"Could not write result file: {exc}")
    else:
        play_game()


if __name__ == "__main__":
    main()
