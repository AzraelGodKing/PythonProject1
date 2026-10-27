# Arcade Hub

[![CI](https://github.com/AzraelGodKing/PythonProject1/actions/workflows/ci.yml/badge.svg)](https://github.com/AzraelGodKing/PythonProject1/actions/workflows/ci.yml)

Six classic games built with Python and Tkinter, sharing one launcher, one set of
themes (including colourblind-friendly ones) and translations in nine languages.
No third-party packages are needed to play.

| Game | Highlights |
| --- | --- |
| **Tic-Tac-Toe** | Easy / Normal / Hard AI, five Normal personalities, best-of matches, hints, undo, achievements, AI-vs-AI watch mode and a headless simulator |
| **Blackjack** | 6-deck shoe, splits (up to 4 hands), doubles, insurance, dealer peek, basic-strategy hints, bankroll leaderboard |
| **Solitaire** | Klondike, draw one or three, undo, double-click moves, auto-complete, fastest-win times |
| **Yahtzee** | All 13 categories, upper bonus, Yahtzee bonus and joker rule, high scores |
| **Minesweeper** | Three sizes, safe first click, flags, chording, keyboard play, best times |
| **Go Fish** | Proper go-again rules, books, a computer opponent that remembers your asks |

## Getting started

You need Python 3.11 or newer with Tk (the python.org installers for Windows and
macOS include it; on Debian/Ubuntu install `python3-tk`).

```bash
git clone https://github.com/AzraelGodKing/PythonProject1.git
cd PythonProject1
python -m pip install -e .
arcade-hub                 # or: python -m arcade
```

Run a single game directly with `python -m arcade.games.<name>`, for example
`python -m arcade.games.blackjack`. The game ids are `tictactoe`, `blackjack`,
`solitaire`, `yahtzee`, `minesweeper` and `gofish`.

Pit two tic-tac-toe AIs against each other without a window:

```bash
arcade-ttt-sim --x hard --o normal:mirror --rounds 500
```

## Features

- **One game at a time.** Every game holds an OS-level lock while it runs. The
  launcher shows which game is open, and a second game refuses to start with a
  message naming the one that is running. The OS drops the lock if a game
  crashes, so there are no stale lock files.
- **Themes:** Midnight (default), Dark, Light, High contrast, Monochrome and
  three colourblind themes (protanopia, deuteranopia, tritanopia). The tests
  check every theme for readable contrast and make sure the red/green-safe
  themes never show win/loss as red versus green.
- **Languages:** English, Español, Français, Deutsch, Italiano, Português,
  Русский, 日本語 and Norsk bokmål. The tests check that every language has every
  string with the same placeholders.
- **Scoreboards and settings** are saved per user, outside the project folder:

  | OS | Location |
  | --- | --- |
  | Windows | `%APPDATA%\ArcadeHub` |
  | macOS | `~/Library/Application Support/ArcadeHub` |
  | Linux | `$XDG_DATA_HOME/arcade-hub` (usually `~/.local/share/arcade-hub`) |

  Set `ARCADE_HUB_DATA` to use another folder. Files are written atomically
  with a `.bak` copy of the previous version. A damaged entry is skipped on its
  own and never wipes the rest of a scoreboard.

Theme, language and sound are shared by the launcher and every game. Change
them from the launcher header or from **Game → Options** in any game.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check . && ruff format --check .
python -m pytest --cov            # GUI tests skip themselves when there is no display
xvfb-run -a python -m pytest      # Linux without a desktop: run the GUI tests too
```

CI runs lint, then the tests on GitHub-hosted runners: Ubuntu with Python 3.11,
3.12 and 3.13 (GUI tests under a virtual display, coverage gate at 85%) and
Windows with Python 3.13.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the code is laid out
and [CONTRIBUTING.md](CONTRIBUTING.md) for adding a game or a language.

## License

MIT, see [LICENSE](LICENSE).
