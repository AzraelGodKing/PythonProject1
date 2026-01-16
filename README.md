# Arcade Hub - Classic Games Collection

A collection of classic games built with Python and Tkinter, featuring a unified launcher, multiple themes, internationalization support, and persistent scoreboards.

## 🎮 Games Included

### Available Games

- **Tic-Tac-Toe** - Play against AI with multiple difficulty levels and personalities. Includes match mode, achievements, and session history.
- **Blackjack** - Classic casino card game with hit, stand, double down, split, and insurance options. Features a chip betting system.
- **Solitaire** - Klondike Solitaire with draw-1 and draw-3 modes. Classic patience gameplay.
- **Yahtzee** - Roll five dice and fill your scorecard with the best scoring combinations.
- **Minesweeper** - Clear the board without hitting mines. Multiple difficulty levels with safe first click.
- **Go Fish** - Collect matching sets of four cards against an AI opponent with memory.

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Tkinter (usually included with Python)
- Windows, Linux, or macOS

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd PythonProject1
```

2. Verify Python installation:
```bash
python --version
# or
py -3.11 --version
```

3. Run the launcher:
```bash
python launcher.py
# or on Windows with multiple Python versions:
py -3.11 launcher.py
```

### Quick Start

1. Launch the game hub by running `launcher.py`
2. Select your preferred language and theme from the header
3. Click "Launch" on any available game
4. Enjoy!

## 🎨 Features

### Unified Launcher
- Central hub for all games
- Language selection (9 languages supported)
- Theme selection (8 themes including colorblind modes)
- Sound toggle
- Single-instance game enforcement

### Internationalization
Supported languages:
- English (en)
- Español (es)
- Français (fr)
- Deutsch (de)
- Italiano (it)
- Português (pt)
- Русский (ru)
- 日本語 (ja)
- Norsk Bokmål (no)

### Themes
- Default
- Dark
- Light
- Ocean
- Forest
- Sunset
- Colorblind (Deuteranopia)
- Colorblind (Protanopia)

### Persistent Data
- Scoreboards for each game
- Settings saved between sessions
- Game statistics and achievements (Tic-Tac-Toe)
- Best times and high scores

## 📁 Project Structure

```
PythonProject1/
├── launcher.py              # Main game hub application
├── shared/                  # Shared utilities and resources
│   ├── audio.py            # Sound effects system
│   ├── chips.py            # Betting/chip system
│   ├── deck.py             # Card deck implementation
│   ├── options.py          # Theme and UI options
│   ├── scoreboard.py       # Score persistence
│   ├── settings.py         # Settings management
│   ├── single_instance.py  # Single-instance enforcement
│   └── locales/            # Translation files (9 languages)
├── tic-tac-toe/            # Tic-Tac-Toe game
│   ├── gui.py              # Main GUI entry point
│   ├── ai_vs_ai.py         # AI vs AI mode
│   └── tictactoe/          # Game logic modules
├── blackjack/              # Blackjack game
│   └── gui.py
├── solitaire/              # Solitaire game
│   └── gui.py
├── yahtzee/                # Yahtzee game
│   └── gui.py
├── minesweeper/            # Minesweeper game
│   └── gui.py
├── gofish/                 # Go Fish game
│   └── gui.py
└── data/                   # Runtime data (scores, settings, logs)
    ├── scoreboard/         # Game scoreboards
    ├── locks/              # Single-instance lock files
    └── *.json              # Settings files
```

## 🎯 Game-Specific Features

### Tic-Tac-Toe
- **AI Difficulty**: Easy, Normal, Hard
- **AI Personalities**: Standard, Aggressive, Defensive, Random, Perfectionist
- **Match Mode**: Play best-of-N matches
- **Achievements**: Unlock badges for various accomplishments
- **Session History**: Review and replay past games
- **AI vs AI Mode**: Watch AI personalities compete
- **Performance Dashboard**: Monitor AI computation metrics

### Blackjack
- **Actions**: Hit, Stand, Double Down, Split, Insurance
- **Chip System**: Start with $1000, debt limit of $500
- **Multi-hand**: Play multiple hands when splitting pairs
- **Strategy Hints**: Basic strategy recommendations
- **Statistics**: Track wins, losses, blackjacks, and busts

### Solitaire
- **Game Modes**: Draw-1 and Draw-3
- **Classic Rules**: Seven tableau piles, four foundations
- **Move Validation**: Only valid moves allowed
- **Scoring**: Track successful completions

### Yahtzee
- **Standard Scoring**: All 13 categories
- **Dice Rolling**: Three rolls per turn with hold functionality
- **Best Score Tracking**: Personal high scores
- **Category Hints**: See potential scores before committing

### Minesweeper
- **Difficulty Levels**: Beginner (8×8, 10 mines), Intermediate (16×16, 40 mines), Expert (30×16, 99 mines)
- **Game Modes**: Classic, Challenge, Puzzle
- **Safe First Click**: First click never triggers a mine
- **Timer**: Track completion times
- **Keyboard Navigation**: Full keyboard support

### Go Fish
- **AI Opponent**: Computer player with memory
- **Book Collection**: Collect sets of four matching cards
- **Score Tracking**: Track books collected
- **Smart AI**: Remembers what you've asked for

## 🔧 Configuration

### Settings Files
Settings are stored in JSON format in the `data/` directory:
- `launcher_settings.json` - Launcher preferences
- `gui_settings.json` - Global GUI settings
- `*_settings.json` - Game-specific settings

### Environment Variables
- `GAME_LANGUAGE` - Override language selection (e.g., `en`, `es`, `fr`)
- `GAME_SOUND` - Set to `0` to disable sound effects

Example:
```bash
GAME_LANGUAGE=es python launcher.py
```

## 🧪 Development

### Running Tests
```bash
python -m pytest tests/
```

### Code Style
The project follows PEP 8 style guidelines with type hints.

### Adding a New Game
1. Create a new directory: `newgame/`
2. Add `gui.py` as the entry point
3. Update `launcher.py` `_load_games()` method
4. Add translations to `shared/locales/*.json`
5. Test with the launcher

## 📝 Technical Details

### Dependencies
- **Python Standard Library Only** - No external packages required
- **Tkinter** - GUI framework (included with Python)
- **winsound** - Audio on Windows (optional, falls back gracefully)

### Platform Support
- **Windows**: Full support including audio
- **Linux**: Supported (audio limited)
- **macOS**: Supported (audio limited)

### File Locking
The project uses file-based locking to ensure only one game runs at a time. Lock files are stored in `data/locks/` and cleaned up automatically.

## 🐛 Troubleshooting

### "Could not start the launcher because Tk/Tcl is unavailable"
This occurs when Python was built without Tkinter support. Solutions:
- On Windows: Use a different Python version that includes Tkinter (e.g., `py -3.11 launcher.py`)
- On Linux: Install `python3-tk` package (`apt install python3-tk` or `yum install python3-tkinter`)
- On macOS: Reinstall Python from python.org

### Game won't launch
- Check that the game's `gui.py` file exists
- Verify no other game is currently running
- Check `data/locks/` for stale lock files (safe to delete if no games are running)

### Settings not saving
- Ensure the `data/` directory exists and is writable
- Check for corrupted JSON files in `data/`
- Try deleting the specific settings file to reset to defaults

### Audio not working
- Audio is currently Windows-only using `winsound`
- On other platforms, audio is disabled automatically
- Ensure sound is enabled in launcher settings

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Areas for Contribution
- Cross-platform audio support
- Additional game modes and features
- More themes and translations
- Bug fixes and performance improvements
- Test coverage expansion
- Documentation improvements

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

- Classic game rules and mechanics from their respective original creators
- Built with Python and Tkinter
- Inspired by timeless arcade and card games

## 📊 Project Status

**Current Version**: 0.12 (Tic-Tac-Toe), others in active development

**Stability**:
- Tic-Tac-Toe: Stable with extensive features
- Blackjack: Stable with core features
- Solitaire: Stable, basic implementation
- Yahtzee: Beta (missing bonus calculations)
- Minesweeper: Beta (some modes incomplete)
- Go Fish: Beta (basic implementation)

## 🔮 Roadmap

- [ ] Complete test coverage (target: 80%)
- [ ] Cross-platform audio support
- [ ] Game state save/load functionality
- [ ] Unified achievements system
- [ ] Undo/redo for all applicable games
- [ ] Tutorial/help screens
- [ ] Accessibility improvements
- [ ] Performance optimizations

---

**Made with ❤️ and Python**
