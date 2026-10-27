# Architecture

```
src/arcade/
├── launcher.py          the hub window; starts each game as its own process
├── core/                shared library
│   ├── paths.py         per-user data directory (ARCADE_HUB_DATA overrides it)
│   ├── storage.py       atomic JSON writes with a .bak fallback
│   ├── settings.py      typed settings; hub_settings() holds language/theme/sound
│   ├── scores.py        HighScores (top-N tables) and Tally (counters)
│   ├── locking.py       InstanceLock: OS file lock that allows one game at a time
│   ├── i18n.py          Translator over locales/<code>.json, English fallback
│   ├── themes.py        Palette per theme plus WCAG contrast helpers
│   ├── cards.py         Card and Shoe (discard tray, so no duplicate cards)
│   ├── chips.py         Bank for betting games
│   ├── log.py           rotating log file per program
│   └── ui.py            the only Tk module: styles, card drawing, GameApp, run_game
├── games/
│   ├── __init__.py      GAMES catalogue used by the launcher
│   └── <game>/
│       ├── logic.py     rules and state, no Tkinter, fully unit tested
│       ├── gui.py       a GameApp subclass
│       └── __main__.py  python -m arcade.games.<game>
└── locales/             en.json is the reference; 8 translations
```

## Rules live apart from widgets

Each game's `logic.py` is plain Python: a dataclass holding the state and
methods for each move, raising an error on an illegal move. The GUI only
calls those methods and redraws. That split is what makes the rules testable
without a display, and it's where most tests point.

## GameApp

`arcade.core.ui.GameApp` provides the window chrome every game shares: ttk
styles from the current palette, a menu (new game, scores, options, quit,
rules, about), an options dialog (theme, language, sound, plus the toggles a
game returns from `extra_options()`) and a scores dialog built from
`score_sections()`.

A game implements:

- `build(parent)`: create widgets.
- `refresh()`: copy state into the widgets. Called after every move.
- `new_game()`.
- optionally `extra_options()`, `score_sections()` and `reset_scores()`.

Changing theme or language destroys and rebuilds the widgets with `build`,
then calls `refresh`. Game state lives on the app, not in widgets, so nothing is lost.

## Processes and locking

The launcher starts games with `python -m arcade.games.<id>`. `run_game`
takes the shared `active_game` lock before opening a window. It writes the
owner's id to `active_game.owner` because Windows can't read a locked file. The
launcher polls the lock every 1.5 seconds to update the cards. Locks use
`fcntl.flock` on Linux and macOS and `msvcrt.locking` on Windows. The OS
releases them when the process exits.

## Persistence

Everything goes through `storage.write_json`: write to a temp file, fsync,
keep the previous good file as `.bak`, then rename into place. Readers fall
back to the `.bak` if the main file is unreadable. Score tables validate each
row on its own, so one bad row can't empty a table.
