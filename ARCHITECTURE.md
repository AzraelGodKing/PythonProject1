# Arcade Hub - Architecture Documentation

**Version**: 1.0
**Date**: 2026-01-15
**Status**: Living Document

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Patterns](#architecture-patterns)
3. [Module Organization](#module-organization)
4. [Data Flow](#data-flow)
5. [Shared Infrastructure](#shared-infrastructure)
6. [Game Architecture](#game-architecture)
7. [Design Decisions](#design-decisions)
8. [Extension Points](#extension-points)

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Launcher (GUI)                      │
│              Central Hub for All Games                   │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ Launches
                  ▼
┌─────────────────────────────────────────────────────────┐
│                    Individual Games                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │Tic-Tac-Toe│  │Blackjack │  │Solitaire │  + 3 more   │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ Uses
                  ▼
┌─────────────────────────────────────────────────────────┐
│                   Shared Modules                         │
│  ┌────────┐ ┌────────┐ ┌─────────┐ ┌────────┐         │
│  │  Deck  │ │ Chips  │ │Settings │ │ Logger │  + more  │
│  └────────┘ └────────┘ └─────────┘ └────────┘         │
└─────────────────────────────────────────────────────────┘
```

### Component Layers

1. **Presentation Layer**: Tkinter GUIs (launcher + games)
2. **Business Logic**: Game rules, scoring, AI
3. **Infrastructure**: Settings, logging, persistence
4. **Data Layer**: JSON files for scores/settings

---

## Architecture Patterns

### 1. Hub and Spoke Pattern

**Pattern**: Launcher acts as central hub, games are independent spokes

**Benefits**:
- Games can run independently
- No game-to-game dependencies
- Easy to add/remove games
- Single-instance enforcement at hub level

**Implementation**:
```python
# launcher.py
class LauncherApp:
    def _load_games(self):
        return [
            GameEntry(name="Blackjack", script_path=...),
            GameEntry(name="Solitaire", script_path=...),
            # ...
        ]
```

### 2. Shared Infrastructure Pattern

**Pattern**: Common utilities in `shared/` module

**Benefits**:
- Code reuse across games
- Consistent behavior
- Single source of truth
- Easy to maintain

**Modules**:
- `deck.py` - Card deck for card games
- `chips.py` - Betting system for gambling games
- `settings.py` - Configuration management
- `scoreboard.py` - Score persistence
- `single_instance.py` - Lock mechanism
- `audio.py` - Sound effects
- `options.py` - Theme definitions
- `theme_manager.py` - Theme base class (NEW)
- `logger.py` - Logging infrastructure (NEW)

### 3. Inheritance Pattern (NEW)

**Pattern**: Games inherit from `ThemedApp` base class

**Benefits**:
- Consistent theme handling
- Reduced code duplication (~200 lines saved per game)
- Easy to add new themes
- Centralized style management

**Implementation**:
```python
from shared.theme_manager import ThemedApp

class BlackjackApp(ThemedApp):
    def __init__(self, root):
        self.theme_var = tk.StringVar(value="default")
        super().__init__(root, self.theme_var)
        # Theme is automatically configured
```

### 4. Data Persistence Pattern

**Pattern**: JSON files in `data/` directory

**Benefits**:
- Human-readable
- Easy to debug
- No database overhead
- Cross-platform

**Structure**:
```
data/
├── scoreboard/          # Game scores
│   ├── scoreboard.json
│   └── match_scoreboard.json
├── logs/                # Application logs
│   ├── blackjack.log
│   └── launcher.log
├── locks/               # Single-instance locks
│   └── active_game.lock
└── *_settings.json      # Game settings
```

---

## Module Organization

### Directory Structure

```
PythonProject1/
├── launcher.py              # Main entry point
│
├── shared/                  # Shared infrastructure
│   ├── deck.py             # Card deck (186 lines)
│   ├── chips.py            # Betting system (36 lines)
│   ├── scoreboard.py       # Score persistence (32 lines)
│   ├── settings.py         # Settings management (82 lines)
│   ├── single_instance.py  # Lock mechanism (95 lines)
│   ├── audio.py            # Sound effects (60 lines)
│   ├── options.py          # Theme definitions (239 lines)
│   ├── theme_manager.py    # Theme base class (200 lines)
│   ├── logger.py           # Logging infrastructure (100 lines)
│   └── locales/            # Translations (9 languages)
│       ├── en.json
│       ├── es.json
│       └── ...
│
├── [game-name]/            # Individual games
│   ├── gui.py             # Main game GUI
│   └── [game-modules]/    # Game-specific logic
│
├── tests/                  # Test suite
│   ├── test_deck.py       # 43 tests
│   ├── test_chips.py      # 42 tests
│   ├── test_settings.py   # 25 tests
│   ├── test_scoreboard.py # 27 tests
│   └── test_blackjack_logic.py  # 35 tests
│
└── data/                   # Runtime data (not in git)
    ├── scoreboard/
    ├── logs/
    └── locks/
```

### Module Dependencies

```
launcher.py
    ├── shared/single_instance
    ├── shared/settings
    ├── shared/options
    └── shared/audio

blackjack/gui.py
    ├── shared/deck
    ├── shared/chips
    ├── shared/scoreboard
    ├── shared/settings
    ├── shared/single_instance
    ├── shared/options
    └── shared/theme_manager (NEW)

solitaire/gui.py
    ├── shared/deck
    ├── shared/scoreboard
    ├── shared/settings
    ├── shared/single_instance
    └── shared/options

tic-tac-toe/gui.py
    ├── shared/scoreboard
    ├── shared/settings
    ├── shared/single_instance
    ├── shared/options
    └── shared/logger (NEW)
```

### Dependency Rules

1. ✅ **Games MAY depend on shared modules**
2. ✅ **Shared modules MAY depend on other shared modules**
3. ❌ **Shared modules MUST NOT depend on games**
4. ❌ **Games MUST NOT depend on other games**
5. ✅ **Tests MAY depend on anything**

---

## Data Flow

### 1. Game Launch Flow

```
User                Launcher              Game                Shared
 │                     │                   │                    │
 │──Click "Launch"───▶│                   │                    │
 │                     │                   │                    │
 │                     │──Check Lock──────────────────────────▶│
 │                     │◀─Lock Available───────────────────────│
 │                     │                   │                    │
 │                     │──subprocess.run──▶│                   │
 │                     │                   │──Acquire Lock────▶│
 │                     │                   │◀─Lock Acquired────│
 │                     │                   │                    │
 │                     │                   │──Load Settings───▶│
 │                     │                   │◀─Settings─────────│
 │                     │                   │                    │
 │                     │                   │──Apply Theme──────▶│
 │                     │                   │◀─Theme Applied────│
 │                     │                   │                    │
 │◀──────────────────────Game Window Shown│                    │
```

### 2. Settings Persistence Flow

```
Game                 Settings Module         File System
 │                        │                       │
 │──Load Settings────────▶│                       │
 │                        │──Read File───────────▶│
 │                        │◀─JSON Data────────────│
 │                        │                       │
 │                        │──Validate Types       │
 │                        │──Merge w/ Defaults    │
 │                        │                       │
 │◀─Validated Settings────│                       │
 │                        │                       │
 │  (Game runs...)        │                       │
 │                        │                       │
 │──Save Settings────────▶│                       │
 │                        │──Create Dirs──────────▶│
 │                        │──Write JSON───────────▶│
 │◀─Success───────────────│                       │
```

### 3. Theme Application Flow

```
Game (ThemedApp)    Theme Manager         Tkinter Widgets
 │                      │                       │
 │──Apply Theme────────▶│                       │
 │  (theme_name)        │                       │
 │                      │──Get Palette          │
 │                      │  (from options.py)    │
 │                      │                       │
 │                      │──Configure Root──────▶│
 │                      │  (background)         │
 │                      │                       │
 │                      │──Configure Styles────▶│
 │                      │  (ttk.Style)          │
 │                      │                       │
 │                      │──Callback: _customize_styles
 │◀─────────────────────│  (game-specific)      │
 │                      │                       │
 │──Update Widgets─────────────────────────────▶│
 │                      │                       │
```

### 4. Score Persistence Flow

```
Game              Scoreboard Module      File System
 │                      │                     │
 │──Add Score──────────▶│                     │
 │  (name, score)       │                     │
 │                      │──Load Existing──────▶│
 │                      │◀─Current Scores─────│
 │                      │                     │
 │                      │──Append New         │
 │                      │──Sort Descending    │
 │                      │──Limit to N         │
 │                      │                     │
 │                      │──Save JSON──────────▶│
 │◀─Updated Scores──────│                     │
```

---

## Shared Infrastructure

### Deck Module (`shared/deck.py`)

**Purpose**: Card deck implementation for card games

**Key Classes**:
- `Card`: Immutable card with rank and suit
- `Deck`: Manages card collection with shuffle, draw, discard

**Usage**:
```python
deck = Deck(num_decks=1, include_jokers=False, seed=None)
deck.shuffle()
hand = deck.draw(5)  # Draw 5 cards
deck.discard(hand)   # Return to discard pile
deck.recycle_discards()  # Shuffle discards back
```

**Features**:
- Multiple decks support
- Joker support
- Deterministic shuffling (seed)
- Discard pile management
- Type hints and immutability

### Chips Module (`shared/chips.py`)

**Purpose**: Betting system for gambling games

**Key Class**:
- `Chips`: Manages balance and debt

**Usage**:
```python
chips = Chips(balance=1000, max_debt=500)
if chips.can_bet(100):
    chips.place_bet(100)
    # ... game logic ...
    chips.payout_win(100, blackjack=True)  # 3:2 payout
```

**Features**:
- Debt limit enforcement
- Blackjack 3:2 payout
- Normal 1:1 payout
- Push (tie) handling

### Settings Module (`shared/settings.py`)

**Purpose**: Type-safe settings management

**Key Functions**:
- `load_settings(path, defaults)`: Load with validation
- `save_settings(path, data)`: Save to JSON
- `validate_setting_value()`: Type validation (NEW)

**Usage**:
```python
defaults = {"volume": 50, "mute": False}
settings = load_settings(Path("settings.json"), defaults)
settings["volume"] = 75
save_settings(Path("settings.json"), settings)
```

**Features** (NEW):
- Type validation against defaults
- Automatic type conversion
- Logging of validation warnings
- Graceful fallback on errors

### Theme Manager (`shared/theme_manager.py`)

**Purpose**: Centralized theme management

**Key Class**:
- `ThemedApp`: Base class for games

**Usage**:
```python
class MyGame(ThemedApp):
    def __init__(self):
        super().__init__(self.root, self.theme_var)

    def _customize_styles(self):
        # Optional: Add game-specific styles
        pass

    def build_ui(self):
        bg = self._color("BG")
        text = self._color("TEXT")
        # ... use colors ...
```

**Features**:
- Automatic ttk style configuration
- Color lookup with `_color(key)`
- Theme change callbacks
- Consistent styles across games

### Logger Module (`shared/logger.py`)

**Purpose**: Centralized logging infrastructure

**Key Functions**:
- `setup_logger(name)`: Create configured logger
- `get_logger(name)`: Get existing logger

**Usage**:
```python
from shared.logger import setup_logger

logger = setup_logger("blackjack")
logger.info("Game started")
logger.warning("Low balance: %d", balance)
logger.error("Failed to save", exc_info=True)
```

**Features**:
- Rotating file handlers (1MB, 5 backups)
- Console + file output
- Configurable log levels
- Structured output with timestamps
- Logs to `data/logs/{name}.log`

---

## Game Architecture

### Game Structure Pattern

Each game follows this structure:

```python
class GameApp:
    def __init__(self, root: tk.Tk):
        """Initialize game"""
        self.root = root
        self._load_settings()
        self._init_game_state()
        self._build_ui()
        self._apply_theme()

    def _load_settings(self):
        """Load game settings"""

    def _init_game_state(self):
        """Initialize game state variables"""

    def _build_ui(self):
        """Build Tkinter UI"""

    def _apply_theme(self):
        """Apply current theme"""

    def _new_game(self):
        """Start new game"""

    def _save_settings(self):
        """Save settings on exit"""

def main():
    """Entry point"""
    # Check single instance
    # Create root window
    # Run app
    # Cleanup on exit
```

### Game Categories

**Card Games** (use `shared/deck`):
- Blackjack
- Solitaire
- Go Fish

**Board Games**:
- Tic-Tac-Toe (with AI)
- Minesweeper

**Dice Games**:
- Yahtzee

---

## Design Decisions

### 1. Why Tkinter?

**Decision**: Use Tkinter for all GUIs

**Rationale**:
- ✅ Built into Python (no dependencies)
- ✅ Cross-platform
- ✅ Good enough for simple games
- ✅ Familiar to Python developers

**Trade-offs**:
- ❌ Limited styling capabilities
- ❌ Not as modern as web-based
- ✅ But: Simple, reliable, no installation

### 2. Why JSON for Data?

**Decision**: Use JSON files for all persistence

**Rationale**:
- ✅ Human-readable
- ✅ Easy to debug/edit
- ✅ Built into Python
- ✅ Cross-platform
- ✅ Good for small data

**Trade-offs**:
- ❌ Not suitable for large data
- ❌ No transactions
- ✅ But: Perfect for game scores/settings

### 3. Why Subprocess for Game Launch?

**Decision**: Launcher uses `subprocess` to start games

**Rationale**:
- ✅ Games run independently
- ✅ Game crash doesn't kill launcher
- ✅ Easy to enforce single-instance
- ✅ Clean separation

**Trade-offs**:
- ❌ Slightly slower startup
- ✅ But: More robust

### 4. Why Single-Instance Enforcement?

**Decision**: Only one game can run at a time

**Rationale**:
- ✅ Prevents data corruption (scores)
- ✅ Simpler state management
- ✅ Better user experience

**Implementation**: File locking with `msvcrt`/`fcntl`

### 5. Why Theme Base Class?

**Decision**: Create `ThemedApp` base class instead of utility functions

**Rationale**:
- ✅ Eliminates ~200 lines of duplicate code per game
- ✅ Consistent behavior
- ✅ Easy to extend
- ✅ Pythonic (inheritance)

**Trade-offs**:
- ❌ More complex for simple games
- ✅ But: Much cleaner overall

---

## Extension Points

### Adding a New Game

1. Create `newgame/gui.py` with main class
2. Inherit from `ThemedApp` (recommended)
3. Add to `launcher.py` `_load_games()`
4. Add translations to `shared/locales/*.json`
5. Write tests in `tests/test_newgame.py`
6. Test with launcher

**Template**:
```python
from shared.theme_manager import ThemedApp

class NewGameApp(ThemedApp):
    def __init__(self, root):
        self.theme_var = tk.StringVar(value="default")
        super().__init__(root, self.theme_var)
        self._build_ui()

    def _build_ui(self):
        # Use self._color() for colors
        pass
```

### Adding a New Theme

1. Add palette to `shared/options.py` `PALETTES`
2. Add theme name to `THEME_CHOICES`
3. Theme automatically available in all games

**Template**:
```python
PALETTES["new_theme"] = {
    "BG": "#xxxxxx",
    "PANEL": "#xxxxxx",
    "ACCENT": "#xxxxxx",
    "TEXT": "#xxxxxx",
    # ... all required keys
}
```

### Adding a New Language

1. Create `shared/locales/{code}.json`
2. Copy structure from `en.json`
3. Translate all keys
4. Add to launcher language detection

### Adding a New Shared Module

1. Create `shared/newmodule.py`
2. Add docstrings and type hints
3. Write tests in `tests/test_newmodule.py`
4. Document in this file
5. Use in games as needed

---

## Performance Considerations

### Current Performance

- **Launcher startup**: <1 second
- **Game startup**: 1-2 seconds
- **Theme switching**: Instant
- **Settings save/load**: <10ms
- **Score save/load**: <10ms

### Optimization Opportunities

1. **Tic-Tac-Toe AI**: Already optimized with caching
2. **Card rendering**: Could use sprite sheets
3. **Theme switching**: Could batch updates
4. **Settings loading**: Could cache in memory

### Performance Guidelines

- Keep JSON files small (<100KB)
- Use rotating logs (already implemented)
- Cache expensive computations
- Profile before optimizing

---

## Security Considerations

### Current Security Posture

✅ **Good**:
- No network communication
- No external dependencies
- No code execution (no `eval`)
- No SQL injection risk
- Settings validated (NEW)

⚠️ **Moderate**:
- File system access unrestricted
- JSON deserialization trusted

❌ **Not Applicable**:
- No authentication needed (single-user)
- No sensitive data stored

### Security Guidelines

- Don't add `eval()` or `exec()`
- Validate all JSON data (now done for settings)
- Don't store passwords/secrets
- Keep logging minimal (no PII)

---

## Testing Strategy

### Test Pyramid

```
         ┌─────────┐
         │   E2E   │  (Future: Integration tests)
         ├─────────┤
         │  Game   │  (Game logic tests: 35+)
         │  Logic  │
         ├─────────┤
         │  Unit   │  (Shared module tests: 137)
         │  Tests  │
         └─────────┘
```

### Current Coverage

- **Shared modules**: 97%
- **Game logic**: Blackjack (partial)
- **Integration**: None (future)

### Testing Guidelines

1. Test shared modules thoroughly (unit tests)
2. Test game logic separately (pure functions)
3. Mock Tkinter for GUI tests (future)
4. Add integration tests for critical flows (future)

---

## Future Architecture

### Planned Improvements

1. **Complete ThemedApp Migration**: All games inherit
2. **Modularize Tic-Tac-Toe**: Split into smaller files
3. **Add State Manager**: Centralize game state
4. **Add Event Bus**: Decouple components
5. **Add Plugin System**: External game support

### Migration Path

**Current** → **Phase 1** → **Phase 2** → **Future**

- Current: Individual game implementations
- Phase 1: Shared modules (DONE)
- Phase 2: Base classes (IN PROGRESS)
- Future: Plugin architecture

---

## Glossary

- **Hub and Spoke**: Launcher (hub) + Games (spokes)
- **ThemedApp**: Base class for themed applications
- **Single Instance**: Only one game runs at a time
- **Rotating Logs**: Log files that rotate when reaching size limit
- **Type Validation**: Checking data types match expected types

---

## References

- [README.md](README.md) - User documentation
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guide
- [IMPROVEMENTS_PHASE2.md](IMPROVEMENTS_PHASE2.md) - Recent changes
- [shared/theme_manager.py](shared/theme_manager.py) - Theme base class
- [shared/logger.py](shared/logger.py) - Logging infrastructure

---

*This is a living document. Update as architecture evolves.*

**Last Updated**: 2026-01-15
**Next Review**: When major changes occur
