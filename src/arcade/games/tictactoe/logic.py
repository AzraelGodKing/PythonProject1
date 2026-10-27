"""Tic-tac-toe rules and computer opponents.

The board is a list of nine strings (``""``, ``"X"`` or ``"O"``) indexed
row by row. Every AI works for either symbol so the same code powers the
human-vs-AI game and the AI-vs-AI simulator.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from functools import cache

LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))
CORNERS = (0, 2, 6, 8)
SIDES = (1, 3, 5, 7)
CENTER = 4

DIFFICULTIES = ("easy", "normal", "hard")
PERSONALITIES = ("balanced", "defensive", "aggressive", "misdirection", "mirror")
DEFAULT_ERROR_RATE = 0.15

Board = list[str]
Strategy = Callable[[Board, str, random.Random], int]


def other(symbol: str) -> str:
    return "O" if symbol == "X" else "X"


def winner(board: Sequence[str]) -> str | None:
    for a, b, c in LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def winning_line(board: Sequence[str]) -> tuple[int, int, int] | None:
    for line in LINES:
        a, b, c = line
        if board[a] and board[a] == board[b] == board[c]:
            return line
    return None


def open_cells(board: Sequence[str]) -> list[int]:
    return [i for i, cell in enumerate(board) if not cell]


def is_over(board: Sequence[str]) -> bool:
    return winner(board) is not None or not open_cells(board)


# -- search ----------------------------------------------------------------
@cache
def _negamax(board: tuple[str, ...], to_move: str) -> int:
    """Score for the side to move: positive wins, faster wins score higher."""
    empties = board.count("")
    if winner(board) is not None:
        return -(1 + empties)  # the previous mover just won
    if not empties:
        return 0
    best = -100
    for i in range(9):
        if not board[i]:
            child = (*board[:i], to_move, *board[i + 1 :])
            best = max(best, -_negamax(child, other(to_move)))
    return best


def move_scores(board: Sequence[str], me: str) -> dict[int, int]:
    """Minimax value of every legal move for ``me``."""
    state = tuple(board)
    return {i: -_negamax((*state[:i], me, *state[i + 1 :]), other(me)) for i in open_cells(board)}


def best_moves(board: Sequence[str], me: str) -> list[int]:
    scores = move_scores(board, me)
    top = max(scores.values())
    return [i for i, s in scores.items() if s == top]


def finishing_move(board: Sequence[str], symbol: str) -> int | None:
    """A cell that completes a line for ``symbol`` (to win, or to block it)."""
    for a, b, c in LINES:
        line = [board[a], board[b], board[c]]
        if line.count(symbol) == 2 and line.count("") == 1:
            return (a, b, c)[line.index("")]
    return None


def fork_moves(board: Sequence[str], symbol: str) -> list[int]:
    """Cells that would give ``symbol`` two open threats at once."""
    forks = []
    for i in open_cells(board):
        trial = list(board)
        trial[i] = symbol
        threats = sum(
            1
            for line in LINES
            if [trial[j] for j in line].count(symbol) == 2 and [trial[j] for j in line].count("") == 1
        )
        if threats >= 2:
            forks.append(i)
    return forks


def _pick(rng: random.Random, board: Sequence[str], *groups: Sequence[int]) -> int:
    for group in groups:
        free = [i for i in group if not board[i]]
        if free:
            return rng.choice(free)
    return rng.choice(open_cells(board))


# -- strategies -------------------------------------------------------------
def easy(board: Board, me: str, rng: random.Random) -> int:
    return rng.choice(open_cells(board))


def hard(board: Board, me: str, rng: random.Random) -> int:
    return rng.choice(best_moves(board, me))


def balanced(board: Board, me: str, rng: random.Random) -> int:
    for symbol in (me, other(me)):
        move = finishing_move(board, symbol)
        if move is not None:
            return move
    return _pick(rng, board, (CENTER,), CORNERS, SIDES)


def defensive(board: Board, me: str, rng: random.Random) -> int:
    """Plays to avoid losing: blocks forks as well as lines, and prefers the sides."""
    for symbol in (me, other(me)):
        move = finishing_move(board, symbol)
        if move is not None:
            return move
    threats = fork_moves(board, other(me))
    if threats:
        return rng.choice(threats)
    return _pick(rng, board, (CENTER,), SIDES, CORNERS)


def aggressive(board: Board, me: str, rng: random.Random) -> int:
    move = finishing_move(board, me)
    if move is not None:
        return move
    forks = fork_moves(board, me)
    if forks:
        return rng.choice(forks)
    move = finishing_move(board, other(me))
    if move is not None:
        return move
    return _pick(rng, board, CORNERS, (CENTER,), SIDES)


def misdirection(board: Board, me: str, rng: random.Random) -> int:
    for symbol in (me, other(me)):
        move = finishing_move(board, symbol)
        if move is not None:
            return move
    forks = fork_moves(board, me)
    if forks:
        return rng.choice(forks)
    if fork_moves(board, other(me)):
        # Force the opponent to answer a threat instead of building their fork.
        return hard(board, me, rng)
    return _pick(rng, board, (CENTER,), CORNERS, SIDES)


def mirror(board: Board, me: str, rng: random.Random) -> int:
    for symbol in (me, other(me)):
        move = finishing_move(board, symbol)
        if move is not None:
            return move
    them = other(me)
    mirrored = [8 - i for i, cell in enumerate(board) if cell == them and not board[8 - i]]
    good = set(best_moves(board, me))
    candidates = [i for i in mirrored if i in good]
    return rng.choice(candidates) if candidates else hard(board, me, rng)


NORMAL: dict[str, Strategy] = {
    "balanced": balanced,
    "defensive": defensive,
    "aggressive": aggressive,
    "misdirection": misdirection,
    "mirror": mirror,
}


@dataclass(frozen=True)
class Opponent:
    difficulty: str = "normal"
    personality: str = "balanced"
    error_rate: float = DEFAULT_ERROR_RATE  # chance a Normal AI plays a random move

    def __post_init__(self) -> None:
        if self.difficulty not in DIFFICULTIES:
            raise ValueError(f"unknown difficulty {self.difficulty!r}")
        if self.personality not in PERSONALITIES:
            raise ValueError(f"unknown personality {self.personality!r}")

    @property
    def key(self) -> str:
        return f"normal:{self.personality}" if self.difficulty == "normal" else self.difficulty

    def move(self, board: Board, me: str, rng: random.Random) -> int:
        if not open_cells(board):
            raise ValueError("board is full")
        if self.difficulty == "easy":
            return easy(board, me, rng)
        if self.difficulty == "hard":
            return hard(board, me, rng)
        if rng.random() < self.error_rate:
            return easy(board, me, rng)
        return NORMAL[self.personality](board, me, rng)


@dataclass
class Game:
    starter: str = "X"
    board: Board = field(default_factory=lambda: [""] * 9)
    moves: list[int] = field(default_factory=list)

    @property
    def to_move(self) -> str:
        return self.starter if len(self.moves) % 2 == 0 else other(self.starter)

    @property
    def winner(self) -> str | None:
        return winner(self.board)

    @property
    def over(self) -> bool:
        return is_over(self.board)

    @property
    def result(self) -> str | None:
        """``"X"``, ``"O"``, ``"draw"`` or None while the game is running."""
        if not self.over:
            return None
        return self.winner or "draw"

    def play(self, index: int) -> None:
        if self.over:
            raise ValueError("game is over")
        if not 0 <= index < 9 or self.board[index]:
            raise ValueError(f"cell {index} is not free")
        self.board[index] = self.to_move
        self.moves.append(index)

    def undo(self, count: int = 1) -> None:
        for _ in range(min(count, len(self.moves))):
            self.board[self.moves.pop()] = ""


@dataclass
class Match:
    best_of: int = 1
    wins: Counter[str] = field(default_factory=Counter)
    draws: int = 0

    def __post_init__(self) -> None:
        if self.best_of < 1 or self.best_of % 2 == 0:
            raise ValueError("best_of must be a positive odd number")

    @property
    def target(self) -> int:
        return self.best_of // 2 + 1

    @property
    def games_played(self) -> int:
        return sum(self.wins.values()) + self.draws

    def record(self, result: str) -> None:
        if self.over:
            raise ValueError("match is over")
        if result == "draw":
            self.draws += 1
        else:
            self.wins[result] += 1

    @property
    def champion(self) -> str | None:
        for symbol, count in self.wins.items():
            if count >= self.target:
                return symbol
        return None

    @property
    def over(self) -> bool:
        return self.champion is not None


def play_out(x: Opponent, o: Opponent, rng: random.Random, starter: str = "X") -> str:
    """Play one full AI-vs-AI game and return its result."""
    game = Game(starter=starter)
    players = {"X": x, "O": o}
    while not game.over:
        game.play(players[game.to_move].move(game.board, game.to_move, rng))
    assert game.result is not None
    return game.result


def simulate(x: Opponent, o: Opponent, rounds: int, *, seed: int | None = None, alternate: bool = True) -> Counter[str]:
    rng = random.Random(seed)
    results: Counter[str] = Counter()
    for n in range(rounds):
        starter = "O" if alternate and n % 2 else "X"
        results[play_out(x, o, rng, starter)] += 1
    return results


# -- achievements ---------------------------------------------------------------
ACHIEVEMENTS = ("first_win", "streak_3", "games_10", "hold_hard", "all_personalities", "match_win")


def earned_achievements(stats: dict[str, int]) -> set[str]:
    earned = set()
    if stats.get("wins", 0) >= 1:
        earned.add("first_win")
    if stats.get("best_streak", 0) >= 3:
        earned.add("streak_3")
    if stats.get("games", 0) >= 10:
        earned.add("games_10")
    if stats.get("draws:hard", 0) >= 1:
        earned.add("hold_hard")
    if all(stats.get(f"wins:normal:{p}", 0) for p in PERSONALITIES):
        earned.add("all_personalities")
    if stats.get("match_wins", 0) >= 1:
        earned.add("match_win")
    return earned
