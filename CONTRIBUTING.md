# Contributing

## Setup

```bash
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Before opening a pull request:

```bash
ruff check . && ruff format --check .
python -m pytest --cov
```

CI runs the same commands, so a green local run usually means green CI.

## Guidelines

- Keep rules in `logic.py` and out of Tkinter so they can be tested. A new
  rule or bug fix comes with a test.
- Never write runtime files into the repository. Use `arcade.core.paths`,
  `Settings`, `HighScores` or `Tally`.
- Every user-visible string goes through the translator (`self.t("key")`).
  Add the key to **all nine** files in `src/arcade/locales/`. The tests fail
  if a language is missing a key, if placeholders differ, or if a key is unused.
- Colours come from the active `Palette`. Never hard-code a colour in a game.

## Adding a game

1. Create `src/arcade/games/<id>/` with `logic.py`, `gui.py` (subclass
   `GameApp` and set `game_id = "<id>"`) and a three-line `__main__.py` like the
   other games.
2. Add `GameInfo("<id>", "<icon>")` to `GAMES` in `src/arcade/games/__init__.py`.
3. Add `<id>.name`, `<id>.description` and `<id>.rules` plus your game's
   strings to every locale.
4. Add `tests/test_<id>.py` for the rules and a smoke test in `tests/test_gui.py`.

## Adding a language

Copy `src/arcade/locales/en.json` to `<code>.json`, translate the values and
leave every `{placeholder}` as it is. Add the native language name to
`LANGUAGE_NAMES` in `src/arcade/core/i18n.py` and the code to `LANGUAGES` in
`tests/test_core_i18n_themes.py`.
