"""Minesweeper board logic with a guaranteed-safe first click."""

from __future__ import annotations

import enum
import random
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass, field

DIFFICULTIES: dict[str, tuple[int, int, int]] = {
    # rows, columns, mines
    "beginner": (9, 9, 10),
    "intermediate": (16, 16, 40),
    "expert": (16, 30, 99),
}


class State(enum.Enum):
    READY = "ready"  # no mines placed yet
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


@dataclass
class Cell:
    mine: bool = False
    revealed: bool = False
    flagged: bool = False
    adjacent: int = 0


@dataclass
class Board:
    rows: int
    cols: int
    mines: int
    rng: random.Random = field(default_factory=random.Random)
    state: State = State.READY
    exploded: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        if self.rows < 2 or self.cols < 2:
            raise ValueError("board must be at least 2x2")
        if not 1 <= self.mines <= self.rows * self.cols - 9:
            raise ValueError("too many or too few mines for this board")
        self.cells = [[Cell() for _ in range(self.cols)] for _ in range(self.rows)]

    @classmethod
    def for_difficulty(cls, name: str, rng: random.Random | None = None) -> Board:
        rows, cols, mines = DIFFICULTIES[name]
        return cls(rows, cols, mines, rng=rng or random.Random())

    @property
    def over(self) -> bool:
        return self.state in (State.WON, State.LOST)

    @property
    def flags(self) -> int:
        return sum(cell.flagged for row in self.cells for cell in row)

    @property
    def mines_left(self) -> int:
        return self.mines - self.flags

    def neighbours(self, r: int, c: int) -> Iterator[tuple[int, int]]:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = r + dr, c + dc
                if (dr or dc) and 0 <= nr < self.rows and 0 <= nc < self.cols:
                    yield nr, nc

    def place_mines(self, safe: tuple[int, int], positions: list[tuple[int, int]] | None = None) -> None:
        """Lay mines anywhere except ``safe`` and its neighbours (so the first click opens an area)."""
        if positions is None:
            excluded = {safe, *self.neighbours(*safe)}
            candidates = [(r, c) for r in range(self.rows) for c in range(self.cols) if (r, c) not in excluded]
            positions = self.rng.sample(candidates, self.mines)
        for r, c in positions:
            self.cells[r][c].mine = True
        for r in range(self.rows):
            for c in range(self.cols):
                self.cells[r][c].adjacent = sum(self.cells[nr][nc].mine for nr, nc in self.neighbours(r, c))
        self.state = State.PLAYING

    def reveal(self, r: int, c: int) -> list[tuple[int, int]]:
        """Open a cell (flood-filling zeros). Returns the cells that were opened."""
        if self.over:
            return []
        if self.state is State.READY:
            self.place_mines((r, c))
        cell = self.cells[r][c]
        if cell.revealed or cell.flagged:
            return []
        if cell.mine:
            cell.revealed = True
            self.exploded = (r, c)
            self.state = State.LOST
            return [(r, c)]
        opened = []
        queue = deque([(r, c)])
        while queue:
            cr, cc = queue.popleft()
            current = self.cells[cr][cc]
            if current.revealed or current.flagged:
                continue
            current.revealed = True
            opened.append((cr, cc))
            if current.adjacent == 0:
                queue.extend(n for n in self.neighbours(cr, cc) if not self.cells[n[0]][n[1]].revealed)
        self._check_win()
        return opened

    def chord(self, r: int, c: int) -> list[tuple[int, int]]:
        """On a revealed number with that many flags around it, open the other neighbours."""
        cell = self.cells[r][c]
        if self.over or not cell.revealed or cell.adjacent == 0:
            return []
        around = list(self.neighbours(r, c))
        if sum(self.cells[nr][nc].flagged for nr, nc in around) != cell.adjacent:
            return []
        opened: list[tuple[int, int]] = []
        for nr, nc in around:
            opened += self.reveal(nr, nc)
            if self.state is State.LOST:
                break
        return opened

    def toggle_flag(self, r: int, c: int) -> bool:
        cell = self.cells[r][c]
        if self.over or cell.revealed:
            return False
        cell.flagged = not cell.flagged
        return True

    def _check_win(self) -> None:
        if all(cell.revealed or cell.mine for row in self.cells for cell in row):
            self.state = State.WON
            for row in self.cells:
                for cell in row:
                    if cell.mine:
                        cell.flagged = True
