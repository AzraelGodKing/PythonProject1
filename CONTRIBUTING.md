## Contributing to Arcade Hub

Thank you for your interest in contributing to Arcade Hub! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Adding a New Game](#adding-a-new-game)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/PythonProject1.git
   cd PythonProject1
   ```
3. Create a new branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git

### Installation

1. Ensure Python is installed:
   ```bash
   python --version
   ```

2. Install pytest for running tests:
   ```bash
   pip install pytest
   ```

3. Run tests to verify setup:
   ```bash
   python -m pytest tests/
   ```

## Project Structure

```
PythonProject1/
├── launcher.py              # Main game launcher
├── shared/                  # Shared utilities
│   ├── deck.py             # Card deck implementation
│   ├── chips.py            # Betting system
│   ├── scoreboard.py       # Score persistence
│   ├── settings.py         # Settings management
│   ├── single_instance.py  # Single-instance enforcement
│   ├── audio.py            # Sound effects
│   ├── options.py          # Theme and UI options
│   └── locales/            # Translation files
├── [game-name]/            # Individual game directories
│   ├── gui.py              # Game entry point
│   └── [game modules]      # Game-specific modules
├── tests/                  # Unit tests
│   ├── test_deck.py
│   ├── test_chips.py
│   └── ...
├── data/                   # Runtime data (not in git)
└── README.md
```

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) style guidelines:

- Use 4 spaces for indentation (no tabs)
- Maximum line length: 120 characters
- Use descriptive variable names
- Add docstrings to all public functions and classes
- Use type hints for function parameters and return values

### Example Function

```python
def calculate_score(cards: List[Card], multiplier: int = 1) -> int:
    """
    Calculate the total score for a list of cards.

    Args:
        cards: List of Card objects to score
        multiplier: Score multiplier (default: 1)

    Returns:
        The calculated score as an integer
    """
    return sum(card.value for card in cards) * multiplier
```

### Type Hints

Use type hints consistently:

```python
from __future__ import annotations
from typing import List, Optional, Dict

def load_config(path: Path) -> Dict[str, Any]:
    ...
```

### Imports

Order imports as follows:

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from shared.deck import Card, Deck
from shared.settings import load_settings
```

## Testing

### Running Tests

Run all tests:
```bash
python -m pytest tests/
```

Run specific test file:
```bash
python -m pytest tests/test_deck.py
```

Run with coverage:
```bash
python -m pytest tests/ --cov=shared --cov-report=html
```

### Writing Tests

- Create test files matching the module name: `test_<module>.py`
- Use descriptive test names: `test_function_name_scenario`
- Test edge cases and error conditions
- Aim for 80%+ code coverage
- Use pytest fixtures for common setup

Example test:

```python
def test_deck_shuffle_changes_order():
    """Test that shuffle changes card order."""
    deck1 = Deck(seed=42)
    deck2 = Deck(seed=42)

    cards_before = list(deck1)
    deck1.shuffle()
    cards_after = list(deck1)

    assert cards_before != cards_after
```

### Test Organization

```python
class TestClassName:
    """Test cases for ClassName."""

    def test_method_success_case(self):
        """Test successful operation."""
        ...

    def test_method_error_case(self):
        """Test error handling."""
        ...
```

## Submitting Changes

### Commit Messages

Write clear, descriptive commit messages:

```
Add shuffle method to Deck class

- Implement in-place shuffling using random module
- Add seed parameter for deterministic shuffling
- Include tests for shuffle functionality
```

Format:
- First line: Brief summary (50 chars or less)
- Blank line
- Detailed description (wrap at 72 chars)

### Pull Request Process

1. Update tests for your changes
2. Ensure all tests pass:
   ```bash
   python -m pytest tests/
   ```
3. Update documentation if needed
4. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
5. Create a Pull Request with:
   - Clear title and description
   - Reference to any related issues
   - Screenshots for UI changes

### PR Checklist

- [ ] Tests added/updated
- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
- [ ] Commit messages are clear

## Adding a New Game

To add a new game to the launcher:

### 1. Create Game Directory

```bash
mkdir newgame
```

### 2. Create Game Entry Point

Create `newgame/gui.py`:

```python
"""New Game GUI implementation."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

from shared.single_instance import try_acquire_lock
from shared.settings import load_settings, save_settings

LOCK_FILE = Path(__file__).parent.parent / "data" / "locks" / "active_game.lock"

def main() -> None:
    # Enforce single instance
    if not try_acquire_lock(LOCK_FILE, "NewGame"):
        tk.messagebox.showerror("Already Running", "NewGame is already running!")
        return

    # Create your game UI
    root = tk.Tk()
    root.title("New Game")
    # ... your game implementation ...
    root.mainloop()

if __name__ == "__main__":
    main()
```

### 3. Update Launcher

Add your game to `launcher.py` in the `_load_games()` method:

```python
GameEntry(
    name="New Game",
    description="Description of your game.",
    name_key="launcher.game.newgame.name",
    desc_key="launcher.game.newgame.desc",
    script_path=self.project_root / "newgame" / "gui.py",
)
```

### 4. Add Translations

Update each file in `shared/locales/` with your game's name and description:

```json
{
  "launcher.game.newgame.name": "New Game",
  "launcher.game.newgame.desc": "Description of your game in this language."
}
```

### 5. Add Tests

Create `tests/test_newgame.py` with comprehensive tests for your game logic.

### 6. Test Integration

1. Run the launcher: `python launcher.py`
2. Verify your game appears in the list
3. Test launching your game
4. Verify single-instance enforcement

## Reporting Bugs

### Before Submitting

- Check if the bug has already been reported
- Test with the latest version
- Collect relevant information

### Bug Report Template

```markdown
**Description**
Clear description of the bug

**To Reproduce**
1. Launch launcher.py
2. Click on '...'
3. See error

**Expected Behavior**
What you expected to happen

**Actual Behavior**
What actually happened

**Environment**
- OS: [e.g., Windows 11, Ubuntu 22.04]
- Python Version: [e.g., 3.11.5]
- Game: [e.g., Blackjack]

**Screenshots**
If applicable

**Additional Context**
Any other relevant information
```

## Feature Requests

We welcome feature requests! Please provide:

- **Use Case**: Why is this feature needed?
- **Proposed Solution**: How should it work?
- **Alternatives**: Have you considered alternatives?
- **Additional Context**: Mockups, examples, etc.

## Development Tips

### Debugging

Use Python's built-in debugger:

```python
import pdb; pdb.set_trace()
```

Or use print statements:

```python
print(f"Debug: {variable_name}")
```

### Performance

- Profile code with `cProfile` for bottlenecks
- Use generators for large datasets
- Cache expensive computations

### Common Patterns

#### Loading Game Settings

```python
from shared.settings import load_settings, save_settings

defaults = {"difficulty": "medium", "volume": 50}
settings = load_settings(SETTINGS_FILE, defaults)
```

#### Using the Deck

```python
from shared.deck import Deck

deck = Deck(seed=42)  # Deterministic for testing
deck.shuffle()
hands = deck.deal_hands(num_hands=4, cards_per_hand=5)
```

#### Score Tracking

```python
from shared.scoreboard import add_score, load_scores

add_score(SCORES_FILE, player_name="Alice", score=100)
top_scores = load_scores(SCORES_FILE)
```

## Questions?

If you have questions:

1. Check the README.md
2. Look at existing code for examples
3. Open an issue for discussion

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

**Thank you for contributing to Arcade Hub!**
