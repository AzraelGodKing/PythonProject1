"""Headless AI-vs-AI simulator.

Example::

    python -m arcade.games.tictactoe.sim --x hard --o normal:mirror --rounds 500
"""

from __future__ import annotations

import argparse

from arcade.games.tictactoe.logic import DIFFICULTIES, PERSONALITIES, Opponent, simulate

CHOICES = [d for d in DIFFICULTIES if d != "normal"] + [f"normal:{p}" for p in PERSONALITIES]


def parse_opponent(text: str) -> Opponent:
    difficulty, _, personality = text.partition(":")
    return Opponent(difficulty, personality or "balanced")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pit two tic-tac-toe AIs against each other.")
    parser.add_argument("--x", default="hard", choices=CHOICES, help="AI playing X")
    parser.add_argument("--o", default="normal:balanced", choices=CHOICES, help="AI playing O")
    parser.add_argument("--rounds", type=int, default=100)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--no-alternate", action="store_true", help="X always moves first")
    args = parser.parse_args(argv)
    if args.rounds < 1:
        parser.error("--rounds must be at least 1")

    results = simulate(
        parse_opponent(args.x), parse_opponent(args.o), args.rounds, seed=args.seed, alternate=not args.no_alternate
    )
    print(f"X = {args.x}, O = {args.o}, {args.rounds} games")
    for key, label in (("X", "X wins"), ("O", "O wins"), ("draw", "Draws")):
        count = results[key]
        print(f"  {label:<7} {count:>6}  ({count / args.rounds:.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
