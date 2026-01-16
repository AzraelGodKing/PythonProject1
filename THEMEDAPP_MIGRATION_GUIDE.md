# ThemedApp Migration Guide

**Purpose**: Migrate games from manual theme handling to ThemedApp base class

**Benefits**:
- ~150 lines saved per game
- Consistent theme behavior
- Easier to maintain
- Automatic style configuration

---

## Migration Steps

### Step 1: Add Import

**Before**:
```python
from shared.options import PALETTES
```

**After**:
```python
from shared.theme_manager import ThemedApp
from shared.options import PALETTES  # Keep if needed for compatibility
```

### Step 2: Inherit from ThemedApp

**Before**:
```python
class BlackjackApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.theme_var = tk.StringVar(value="default")
        # ...
```

**After**:
```python
class BlackjackApp(ThemedApp):
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.theme_var = tk.StringVar(value="default")

        # Initialize ThemedApp BEFORE building UI
        super().__init__(root, self.theme_var)

        # ... rest of init
```

### Step 3: Replace _color() calls

**Before**:
```python
def _color(self, key: str) -> str:
    colors = PALETTES.get(self.theme_var.get(), PALETTES["default"])
    return colors.get(key, "#000000")
```

**After**:
```python
# Remove _color() method entirely - inherited from ThemedApp
# All self._color() calls will now use the inherited version
```

### Step 4: Simplify _apply_theme()

**Before** (50+ lines):
```python
def _apply_theme(self) -> None:
    colors = PALETTES.get(self.theme_var.get(), PALETTES["default"])
    bg = colors.get("BG", "#0b3d2e")
    panel = colors.get("PANEL", bg)
    text = colors.get("TEXT", "#f8fafc")
    # ... 40 more lines ...

    self.root.configure(bg=bg)
    style = ttk.Style(self.root)
    style.theme_use("clam")
    style.configure("BJ.TLabel", ...)
    # ... many more style configurations ...
```

**After** (5-10 lines):
```python
def _apply_theme(self, theme_name=None) -> None:
    # Call parent to handle common stuff
    super()._apply_theme(theme_name)

    # Only game-specific customizations here
    # Most standard widgets are already styled by parent
```

### Step 5: Use _customize_styles() for Game-Specific Styles

**Pattern**:
```python
def _customize_styles(self) -> None:
    """Override to add game-specific style customizations."""
    # Add game-specific ttk styles
    self.style.configure(
        "BJ.Special.TButton",
        # ... game-specific style
    )

    # Configure non-ttk widgets with colors
    self.title_label.configure(
        bg=self._color("BG"),
        fg=self._color("TEXT")
    )
```

---

## Complete Example: Blackjack Migration

### Before (Partial):

```python
class BlackjackApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.theme_var = tk.StringVar(value="default")
        # ... lots of setup ...
        self._apply_theme()

    def _color(self, key: str) -> str:
        colors = PALETTES.get(self.theme_var.get(), PALETTES["default"])
        return colors.get(key, "#000000")

    def _apply_theme(self) -> None:
        # 50+ lines of theme configuration
        colors = PALETTES.get(self.theme_var.get(), PALETTES["default"])
        bg = colors.get("BG", "#0b3d2e")
        # ... lots of color extraction ...

        self.root.configure(bg=bg)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        # ... many style configurations ...
```

### After (Simplified):

```python
from shared.theme_manager import ThemedApp

class BlackjackApp(ThemedApp):
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.theme_var = tk.StringVar(value="default")

        # Initialize parent (sets up theme infrastructure)
        super().__init__(root, self.theme_var)

        # ... rest of init ...
        # Build UI
        # Theme is automatically applied by parent

    def _customize_styles(self) -> None:
        """Game-specific style customizations."""
        # Only Blackjack-specific styles here
        # Standard styles already configured by parent

        # Example: Configure tk widgets that need custom styling
        if hasattr(self, 'title_label'):
            self.title_label.configure(
                bg=self._color("BG"),
                fg=self._color("TEXT")
            )

        # Example: Add game-specific ttk styles
        self.style.configure(
            "BJ.Custom.TButton",
            padding=(12, 6),
            foreground=self._color("TEXT"),
            background=self._color("BTN"),
        )
```

---

## Migration Checklist

For each game:

- [ ] Add `from shared.theme_manager import ThemedApp`
- [ ] Change class to inherit from `ThemedApp`
- [ ] Call `super().__init__(root, theme_var)` early in `__init__`
- [ ] Remove local `_color()` method
- [ ] Simplify or remove `_apply_theme()`
- [ ] Move game-specific styles to `_customize_styles()`
- [ ] Test theme switching works
- [ ] Test all UI elements display correctly
- [ ] Verify settings persistence still works

---

## Common Patterns

### Pattern 1: Standard ttk Widgets

**Before**:
```python
self.style.configure("Game.TButton", foreground=text, background=btn_bg)
```

**After**:
```python
# Already configured by parent as "TButton"
# Just use standard style name
button = ttk.Button(parent, text="Click", style="TButton")
```

### Pattern 2: Custom ttk Styles

**Before**:
```python
def _apply_theme(self):
    # ... lots of code ...
    style.configure("Game.Special.TButton", ...)
```

**After**:
```python
def _customize_styles(self):
    self.style.configure("Game.Special.TButton",
        foreground=self._color("ACCENT"),
        background=self._color("PANEL")
    )
```

### Pattern 3: tk Widgets (Canvas, Label, Frame)

**Before**:
```python
def _apply_theme(self):
    colors = PALETTES.get(...)
    bg = colors.get("BG")
    self.canvas.configure(bg=bg)
```

**After**:
```python
def _customize_styles(self):
    # Or in _apply_theme() override
    self.canvas.configure(bg=self._color("BG"))
```

### Pattern 4: Dynamic Theme Changes

**Before**:
```python
def _on_theme_change(self, event=None):
    new_theme = self.theme_var.get()
    # ... custom logic ...
    self._apply_theme()
```

**After**:
```python
def _on_theme_change(self, event=None):
    # Parent handles most of it
    super()._on_theme_change(event)

    # Add game-specific logic if needed
    self._refresh_custom_widgets()
```

---

## Testing After Migration

For each migrated game:

1. **Visual Test**: Launch game, verify all elements visible
2. **Theme Test**: Switch themes, verify colors update
3. **Settings Test**: Change settings, restart, verify persistence
4. **Interaction Test**: Play the game, verify functionality
5. **Options Test**: Open options dialog, verify it displays

---

## Expected Savings

Per game:
- **Lines Removed**: ~150 lines
- **Code Duplication**: Eliminated
- **Maintenance**: Much easier

Total across 6 games:
- **Lines Saved**: ~900 lines
- **Consistency**: 100%
- **Time Saved**: Significant for future theme additions

---

## Troubleshooting

### Issue: "AttributeError: 'Game' object has no attribute 'style'"

**Fix**: Call `super().__init__()` BEFORE trying to use `self.style`

### Issue: Theme doesn't apply

**Fix**: Make sure `_apply_theme()` is called after UI is built

### Issue: Custom styles not working

**Fix**: Put them in `_customize_styles()` and ensure it's called

### Issue: Colors look wrong

**Fix**: Check that `self._color()` calls use correct key names

---

## Order of Migration

Recommended order (easiest to hardest):

1. ✅ Yahtzee (simpler UI)
2. ✅ Minesweeper (simpler UI)
3. ✅ Go Fish (simpler UI)
4. ✅ Blackjack (moderate complexity)
5. ✅ Solitaire (moderate complexity)
6. ✅ Tic-Tac-Toe (most complex, do last)

---

*This guide will be updated as migrations are completed.*
