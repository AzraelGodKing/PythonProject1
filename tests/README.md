# Test Suite Documentation

This directory contains the comprehensive test suite for the PythonProject1 Arcade Hub.

## Quick Start

### Install Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
python -m pytest tests/ -v
```

### Run with Coverage

```bash
python -m pytest tests/ --cov=shared --cov-report=html --cov-report=term
```

View the HTML report: `htmlcov/index.html`

## Test Files Overview

| File | Module Tested | Test Cases | Focus Areas |
|------|---------------|------------|-------------|
| `test_deck.py` | `shared/deck.py` | 49 | Card & Deck classes, shuffling, dealing |
| `test_chips.py` | `shared/chips.py` | 42 | Betting system, payouts, debt limits |
| `test_scoreboard.py` | `shared/scoreboard.py` | 33 | Score persistence, JSON handling |
| `test_settings.py` | `shared/settings.py` | 31 | Settings load/save, merging with defaults |
| `test_single_instance.py` | `shared/single_instance.py` | 29 | File locking, single-instance enforcement |

**Total**: 184+ test cases

## Running Specific Tests

### By File

```bash
python -m pytest tests/test_deck.py -v
```

### By Class

```bash
python -m pytest tests/test_deck.py::TestCard -v
```

### By Method

```bash
python -m pytest tests/test_deck.py::TestCard::test_card_creation -v
```

### By Pattern

```bash
# Run all tests with "shuffle" in the name
python -m pytest tests/ -k shuffle -v

# Run all tests in TestDeck class
python -m pytest tests/ -k TestDeck -v
```

## Test Organization

Each test file follows this structure:

```python
class TestClassName:
    """Test cases for ClassName."""

    def test_method_success_case(self):
        """Test successful operation."""
        ...

    def test_method_error_case(self):
        """Test error handling."""
        ...

    def test_method_edge_case(self):
        """Test edge case behavior."""
        ...
```

## Coverage Goals

- **Shared Modules**: 90%+ coverage
- **Game Modules**: 70%+ coverage (future work)
- **Integration Tests**: Key user workflows

## Current Coverage (Shared Modules)

Expected coverage for shared modules:

- ✅ `deck.py`: ~95%
- ✅ `chips.py`: ~98%
- ✅ `scoreboard.py`: ~95%
- ✅ `settings.py`: ~95%
- ✅ `single_instance.py`: ~85% (OS-specific code harder to test)

## Writing New Tests

### Test Template

```python
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from module_to_test import ClassToTest


class TestClassName:
    """Test cases for ClassName."""

    def test_basic_functionality(self):
        """Test basic use case."""
        obj = ClassToTest()
        result = obj.method()
        assert result == expected_value

    def test_error_handling(self):
        """Test that errors are handled correctly."""
        obj = ClassToTest()
        with pytest.raises(ValueError):
            obj.method_with_invalid_input()
```

### Best Practices

1. **Descriptive Names**: Test names should describe what they test
   - ✅ `test_deck_shuffle_changes_order`
   - ❌ `test_1`, `test_shuffle`

2. **One Assertion Focus**: Each test should focus on one behavior
   - Tests can have multiple asserts, but should test one logical thing

3. **Arrange-Act-Assert**: Structure tests clearly
   ```python
   # Arrange
   deck = Deck(seed=42)

   # Act
   deck.shuffle()

   # Assert
   assert len(deck) == 52
   ```

4. **Use Fixtures for Common Setup**: For repeated setup code
   ```python
   @pytest.fixture
   def sample_deck():
       return Deck(seed=42)

   def test_something(sample_deck):
       assert len(sample_deck) == 52
   ```

5. **Test Edge Cases**: Don't just test the happy path
   - Empty inputs
   - Maximum values
   - Invalid inputs
   - Boundary conditions

## Common pytest Options

```bash
# Verbose output
pytest -v

# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Run last failed tests only
pytest --lf

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Generate coverage report
pytest --cov=shared --cov-report=html

# Show slowest 10 tests
pytest --durations=10
```

## Continuous Integration

Tests should be run automatically on:

1. **Pull Requests**: Before merging
2. **Commits to main**: After merging
3. **Nightly**: Full test suite with coverage

Example GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/ --cov=shared --cov-report=xml
```

## Debugging Tests

### Run with Debugger

```python
import pdb; pdb.set_trace()
```

### Print Debug Info

```bash
pytest -s  # Shows print() output
```

### Run Single Test

```bash
pytest tests/test_deck.py::TestCard::test_card_creation -v -s
```

## Test Categories

Our tests include:

1. **Unit Tests**: Test individual functions/methods in isolation
2. **Integration Tests**: Test multiple components working together
3. **Edge Case Tests**: Test boundary conditions and unusual inputs
4. **Error Tests**: Test that errors are raised/handled correctly

## Future Test Areas

Areas that need tests (future work):

- [ ] Game logic tests (tic-tac-toe, blackjack, etc.)
- [ ] GUI component tests
- [ ] Launcher tests
- [ ] Integration tests (full game flow)
- [ ] Performance/benchmark tests
- [ ] Cross-platform tests (Windows, Linux, macOS)

## Troubleshooting

### Import Errors

If you get `ModuleNotFoundError`:

```python
# Add this at the top of test files
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Pytest Not Found

```bash
pip install pytest
```

### Test Discovery Issues

Make sure:
- Test files start with `test_`
- Test classes start with `Test`
- Test methods start with `test_`
- `__init__.py` exists in `tests/` directory

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest best practices](https://docs.pytest.org/en/latest/goodpractices.html)
- [Python testing guide](https://realpython.com/pytest-python-testing/)

## Questions?

See [CONTRIBUTING.md](../CONTRIBUTING.md) for more information on development practices.
