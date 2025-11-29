# Tic-Tac-Toe Suite

A polished Python tic-tac-toe collection that runs both in the terminal and with a Tkinter windowed interface. The project includes multiple AI personalities, persistent scorekeeping, and configurable settings so you can explore strategies, demo the game, or just play a quick match without any external dependencies.

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
3. Launch commands from the repository root so assets and logs resolve correctly.

## Running the games
- **CLI:**
  ```bash
  python tic-tac-toe.py
  ```
  Guides you through move input and records results in the main scoreboard.

- **GUI:**
  ```bash
  python gui.py
  ```
  Opens a Tkinter window with board controls, score tracking, and configurable themes (default, high-contrast, colorblind, light).

- **AI vs AI:**
  ```bash
  python ai_vs_ai.py
  ```
  Choose two AI personas and a round count to watch automated play. Results save to a dedicated AI-vs-AI scoreboard.

## Controls and workflows
- **CLI conveniences:** Row/column or single-digit input, hints, undo, persistent scoreboard, and session history logging.
- **GUI controls:** Undo and hint buttons, status panel, scoreboard, options dialog for themes, font sizing, animation and sound toggles, plus keyboard shortcuts.

## Data and persistence
- **Scoreboards:** Stored under `data/scoreboard/` with automatic `.bak` backups.
- **GUI settings:** Written to `gui_settings.json` (backed up at `logs/gui_settings.json.bak`). Override the location with the `GUI_SETTINGS_PATH` environment variable.
- **Logs:** Session histories and backups live under `logs/`; the folder is tracked via `logs/.gitkeep`.

## Testing
Run the bundled smoke tests from the project root:
```bash
python -m unittest -q
```
