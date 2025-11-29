"""
AI vs AI mode with its own scoreboard.
Select two AI variants and let them play automatic rounds while tracking wins/draws separately from the player scoreboard.
"""

import json
import os
from typing import Callable, Dict, List, Tuple

import tictactoe as module

AI_SCOREBOARD_FILE = os.path.join("data", "scoreboard", "ai_vs_ai.json")
AI_SCOREBOARD_BACKUP = AI_SCOREBOARD_FILE + ".bak"

AI_PLAYERS: Dict[str, Callable[[List[str]], int]] = {
    "Easy": module.ai_move_easy,
    "Normal (balanced)": module.ai_move_normal,
    "Normal (defensive)": module.ai_move_normal_defensive,
    "Normal (aggressive)": module.ai_move_normal_aggressive,
    "Normal (misdirection)": module.ai_move_misdirection,
    "Normal (mirror)": module.ai_move_mirror,
    "Hard": module.ai_move_hard,
}


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)


def _coerce_int(val, default: int = 0) -> int:
    try:
        return int(val)
    except Exception:
        return default


def load_ai_scoreboard(file_path: str = AI_SCOREBOARD_FILE) -> Dict[str, int]:
    _ensure_dir(file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k): _coerce_int(v) for k, v in data.items()}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        # attempt backup
        try:
            with open(AI_SCOREBOARD_BACKUP, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                print("AI-vs-AI scoreboard restored from backup.")
                return {str(k): _coerce_int(v) for k, v in data.items()}
        except Exception:
            return {}
    except Exception:
        return {}
    return {}


def save_ai_scoreboard(scores: Dict[str, int], file_path: str = AI_SCOREBOARD_FILE) -> None:
    _ensure_dir(file_path)
    # backup current file
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                current = f.read()
            with open(AI_SCOREBOARD_BACKUP, "w", encoding="utf-8") as f:
                f.write(current)
    except Exception:
        pass
    tmp_path = file_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(scores, f)
        os.replace(tmp_path, file_path)
    except Exception as exc:
        print(f"Could not save AI-vs-AI scoreboard ({exc}).")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _choose_ai(prompt: str) -> Tuple[str, Callable[[List[str]], int]]:
    keys = list(AI_PLAYERS.keys())
    print(f"\n{prompt}")
    for idx, name in enumerate(keys, start=1):
        print(f"{idx}) {name}")
    while True:
        choice = input("Select AI by number or name: ").strip()
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(keys):
                name = keys[idx - 1]
                return name, AI_PLAYERS[name]
        if choice in AI_PLAYERS:
            return choice, AI_PLAYERS[choice]
        print("Please choose a valid AI.")


def _play_ai_round(ai_x: Callable[[List[str]], int], ai_o: Callable[[List[str]], int]) -> str:
    board = [" "] * 9
    current = "X"
    # Clear minimax cache for fairness
    if hasattr(module, "_MINIMAX_CACHE"):
        module._MINIMAX_CACHE.clear()  # type: ignore[attr-defined]

    while True:
        if current == "X":
            idx = ai_x(board)
        else:
            idx = ai_o(board)
        if board[idx] != " ":
            # if an AI tries an invalid move, pick first open spot
            open_spots = [i for i, v in enumerate(board) if v == " "]
            if not open_spots:
                return "Draw"
            idx = open_spots[0]
        board[idx] = current
        winner = module.check_winner(board)
        if winner:
            return winner
        if module.board_full(board):
            return "Draw"
        current = "O" if current == "X" else "X"


def play_ai_vs_ai_session() -> None:
    scores = load_ai_scoreboard()
    print("Current AI-vs-AI scoreboard:")
    if scores:
        for name, val in sorted(scores.items()):
            print(f"- {name}: {val}")
    else:
        print("(empty)")

    ai_x_name, ai_x_fn = _choose_ai("Choose AI for X")
    ai_o_name, ai_o_fn = _choose_ai("Choose AI for O")
    rounds_text = input("How many rounds? (default 5): ").strip()
    try:
        rounds = int(rounds_text) if rounds_text else 5
    except ValueError:
        rounds = 5
    rounds = max(1, rounds)

    print(f"\nStarting AI vs AI: X={ai_x_name} vs O={ai_o_name} for {rounds} rounds.")
    scores.setdefault(ai_x_name, 0)
    scores.setdefault(ai_o_name, 0)
    scores.setdefault("Draw", 0)

    x_wins = o_wins = draws = 0
    for i in range(1, rounds + 1):
        winner = _play_ai_round(ai_x_fn, ai_o_fn)
        if winner == "X":
            scores[ai_x_name] += 1
            x_wins += 1
            print(f"Round {i}: X ({ai_x_name}) wins.")
        elif winner == "O":
            scores[ai_o_name] += 1
            o_wins += 1
            print(f"Round {i}: O ({ai_o_name}) wins.")
        else:
            scores["Draw"] = scores.get("Draw", 0) + 1
            draws += 1
            print(f"Round {i}: Draw.")

    save_ai_scoreboard(scores)
    print("\nSession complete.")
    print(f"X ({ai_x_name}) wins: {x_wins}")
    print(f"O ({ai_o_name}) wins: {o_wins}")
    print(f"Draws: {draws}")
    print("\nUpdated AI-vs-AI scoreboard:")
    for name, val in sorted(scores.items()):
        print(f"- {name}: {val}")


if __name__ == "__main__":
    play_ai_vs_ai_session()
