# Changelog

## 2.0.0 - full rewrite

Same idea: six games, one shared library, nine languages, colourblind-friendly
themes, one game at a time, scoreboards and settings. The code underneath is new.

### Structure
- Installable `arcade` package under `src/`, with `arcade-hub` and
  `arcade-ttt-sim` commands. `pyproject.toml` now describes the whole project.
- Each game is split into `logic.py` (rules, no Tkinter) and `gui.py`.
- One `GameApp` base class gives every game the same menus, options, scores
  and rules dialogs. Changing theme or language rebuilds the window in place.
- The 13 overlapping summary/progress documents are replaced by README,
  CONTRIBUTING, this changelog and `docs/ARCHITECTURE.md`.

### Data and reliability
- Runtime data (settings, scores, locks, logs) moved out of the repository into
  the per-user data directory. The tracked `__pycache__`, lock, log, scoreboard
  and settings files (including a log with a local Windows path) are gone.
- Atomic JSON writes with `.bak` fallback.
- Fixed: one malformed scoreboard entry made `load_scores` return an empty list,
  so the next save wiped every score. Bad rows are now skipped one at a time.
- Settings are validated against their defaults (type and allowed values), so a
  hand-edited or outdated file can't put a game into an invalid state.
- Locks record their owner in a side file, so the launcher can name the
  running game on Windows too (a locked file can't be read there).

### Games
- **Blackjack:** removed the rigged first hand, which re-dealt to stop a
  dealer blackjack. Insurance is now offered before the dealer peeks, so it can
  actually pay. The dealer also peeks with a ten showing. Split aces get one
  card each. A 21 after a split pays 1:1, not 3:2. Splits go up to four hands,
  and doubling after a split is allowed. A mid-round reshuffle can no longer
  put duplicate cards on the table. The basic-strategy hint only suggests
  moves that are allowed.
- **Tic-Tac-Toe:** one minimax with a correct cache shared by every AI. AIs
  play either symbol, which powers the new in-window AI-vs-AI mode and the
  simulator. Openers alternate between games. Hint and undo work on every difficulty.
- **Yahtzee:** added the 35 point upper bonus, the 100 point Yahtzee bonus and
  the joker rule.
- **Go Fish:** books made during the deal now count. Drawing the rank you
  asked for gives you another turn. Players with no cards draw before asking.
- **Minesweeper:** the first click always opens an area, not just a safe
  square. The expert board is the standard 16x30 with 99 mines. Removed the
  "challenge" and "puzzle" modes, which played the same as classic.
- **Solitaire:** undo, double-click to the best spot, auto-complete, timer
  and fastest-win table.
- Every game and the launcher are fully translated into all nine languages
  (before, only the launcher, Tic-Tac-Toe and parts of two games were).

### Tooling
- CI runs on GitHub-hosted runners instead of the self-hosted NAS runner:
  ruff lint and format, tests on Ubuntu (Python 3.11-3.13, GUI tests under
  xvfb, coverage gate 85%) and Windows. The old CI ran 4 of 6 test files
  (about 17% coverage); now all tests run and coverage is about 92%.
- The Blackjack tests now import the real `hand_value` rather than a pasted copy.
