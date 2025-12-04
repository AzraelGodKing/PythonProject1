# Tic-Tac-Toe Suite

A polished Python tic-tac-toe collection that runs both in the terminal and with a Tkinter windowed interface. The project includes multiple AI personalities, persistent scorekeeping, and configurable settings so you can explore strategies, demo the game, or just play a quick match without any external dependencies. A root-level **Game Launcher** window (`launcher.py`) lets you open Tic-Tac-Toe or any future games you drop into the repository, while shared assets live under `shared/` for reuse across modules.

## Highlights
- **Game modes:** Human vs AI in the CLI or GUI, plus an AI-vs-AI simulator with its own scoreboard.
- **AI depth:** Easy random play, a set of Normal personas (balanced, defensive, aggressive, misdirection, mirror), and a Hard minimax opponent.
- **Resilient data:** Automatic backups for scoreboards and GUI settings to guard against tampering or corruption.
- **Standard library only:** Runs on CPython 3.10+ with no third-party packages. Tkinter is bundled with most CPython distributions.

## Setup
1. Clone the repository and move into the project root.
2. (Optional) Create and activate a virtual environment if you plan to extend the project:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
   ```
3. Run commands from the repository root; the code and assets live under `tic-tac-toe/`.

## Running the games
- **Game Launcher:**
  ```bash
  python launcher.py
  ```
  Opens a top-level hub where you can launch Tic-Tac-Toe today and enable future games (e.g., Blackjack or Go Fish) by adding their GUI entry points.

- **CLI:**
  ```bash
  python "tic-tac-toe/tic-tac-toe.py"
  ```
  Guides you through move input and records results in the main scoreboard.

- **GUI:**
  ```bash
  python "tic-tac-toe/gui.py"
  ```
  Opens a Tkinter window with board controls, score tracking, and configurable themes (default, high-contrast, colorblind, light).

- **AI vs AI:**
  ```bash
  python "tic-tac-toe/ai_vs_ai.py"
  ```
  Choose two AI personas and a round count to watch automated play. Results save to a dedicated AI-vs-AI scoreboard.

## Controls and workflows
- **CLI conveniences:** Row/column or single-digit input, hints, undo, persistent scoreboard, and session history logging.
- **GUI controls:** Undo and hint buttons, status panel, scoreboard, options dialog for themes, font sizing, animation and sound toggles, plus keyboard shortcuts.

## Data and persistence
- **Scoreboards:** Stored under `tic-tac-toe/data/scoreboard/` with automatic `.bak` backups.
- **GUI settings:** Written to `gui_settings.json` (backed up at `tic-tac-toe/data/logs/gui_settings.json.bak`). Override the location with the `GUI_SETTINGS_PATH` environment variable.
- **Logs:** Session histories and backups live under `tic-tac-toe/data/logs/`; the folder is tracked via `tic-tac-toe/data/logs/.gitkeep`.

## Testing
Run the bundled smoke tests from the project root:
```bash
python -m unittest -q
```

## Install & CLI entry points
With Python 3.10+ available, you can install editable tooling and get commands on your PATH:
```bash
pip install -e .
```

New commands after install:
- `tictactoe` — launch the CLI game (with flags for difficulty/personality and best-of length).
- `tictactoe-gui` — open the Tkinter GUI.
- `tictactoe-ai` — run the AI-vs-AI simulator.
