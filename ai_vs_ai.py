"""
AI vs AI mode with its own scoreboard.
Select two AI variants and let them play automatic rounds while tracking wins/draws separately from the player scoreboard.
"""

import argparse
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
    backup_path = AI_SCOREBOARD_BACKUP if file_path == AI_SCOREBOARD_FILE else f"{file_path}.bak"
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
            with open(backup_path, "r", encoding="utf-8") as f:
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
    backup_path = AI_SCOREBOARD_BACKUP if file_path == AI_SCOREBOARD_FILE else f"{file_path}.bak"
    # backup current file
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                current = f.read()
            with open(backup_path, "w", encoding="utf-8") as f:
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


def _run_headless_ai_vs_ai(
    ai_x_name: str,
    ai_o_name: str,
    rounds: int,
    delay_sec: float = 0.0,
    scoreboard_file: str = AI_SCOREBOARD_FILE,
    safe_mode: bool = False,
) -> Dict[str, object]:
    if ai_x_name not in AI_PLAYERS or ai_o_name not in AI_PLAYERS:
        raise ValueError("Unknown AI selection")
    rounds = max(1, rounds)
    scores = {} if safe_mode else load_ai_scoreboard(scoreboard_file)
    scores.setdefault(ai_x_name, 0)
    scores.setdefault(ai_o_name, 0)
    scores.setdefault("Draw", 0)
    ai_x_fn = AI_PLAYERS[ai_x_name]
    ai_o_fn = AI_PLAYERS[ai_o_name]

    for i in range(1, rounds + 1):
        winner = _play_ai_round(ai_x_fn, ai_o_fn)
        if winner == "X":
            scores[ai_x_name] += 1
            result = f"Round {i}: X ({ai_x_name}) wins."
        elif winner == "O":
            scores[ai_o_name] += 1
            result = f"Round {i}: O ({ai_o_name}) wins."
        else:
            scores["Draw"] = scores.get("Draw", 0) + 1
            result = f"Round {i}: Draw."
        print(result)
        if delay_sec > 0:
            try:
                import time

                time.sleep(delay_sec)
            except Exception:
                pass
    if not safe_mode:
        save_ai_scoreboard(scores, file_path=scoreboard_file)
    return {
        "ai_x": ai_x_name,
        "ai_o": ai_o_name,
        "rounds": rounds,
        "scores": scores,
    }


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


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AI-vs-AI matches (headless or interactive).")
    ai_names = list(AI_PLAYERS.keys())
    parser.add_argument("--ai-x", choices=ai_names, help="AI to play as X.")
    parser.add_argument("--ai-o", choices=ai_names, help="AI to play as O.")
    parser.add_argument("--rounds", type=int, default=5, help="How many rounds to play (default 5).")
    parser.add_argument("--delay", type=float, default=0.0, help="Optional delay (seconds) between rounds.")
    parser.add_argument("--scoreboard-file", help="Custom scoreboard path for AI vs AI results.")
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Skip persistence for AI-vs-AI scores (headless mode only).",
    )
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Choose text (default) or json summary output in headless mode.",
    )
    parser.add_argument("--result-file", help="Optional path to write the summary JSON.")
    parser.add_argument(
        "--expect-winner",
        choices=("X", "O", "Draw"),
        help="Exit non-zero unless the aggregate winner matches (ties become Draw).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    if args.ai_x and args.ai_o:
        scoreboard_file = args.scoreboard_file or AI_SCOREBOARD_FILE
        summary = _run_headless_ai_vs_ai(
            args.ai_x,
            args.ai_o,
            rounds=args.rounds,
            delay_sec=max(0.0, args.delay),
            scoreboard_file=scoreboard_file,
            safe_mode=args.safe_mode,
        )
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
            print("\nFinal scores:")
            for name, val in sorted(summary["scores"].items()):  # type: ignore[index]
                print(f"- {name}: {val}")
        if args.expect_winner:
            scores = summary["scores"]  # type: ignore[index]
            x_wins = scores.get(args.ai_x, 0)
            o_wins = scores.get(args.ai_o, 0)
            if x_wins > o_wins:
                winner = "X"
            elif o_wins > x_wins:
                winner = "O"
            else:
                winner = "Draw"
            if winner != args.expect_winner:
                print(f"Expected winner {args.expect_winner}, but got {winner}.")
                raise SystemExit(1)
    else:
        play_ai_vs_ai_session()


if __name__ == "__main__":
    main()
