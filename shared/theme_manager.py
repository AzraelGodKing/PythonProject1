"""
Centralized theme management for all games.

Provides a base class that games can inherit to get consistent
theme management without code duplication.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional, Callable

from shared.options import PALETTES, THEME_CHOICES


class ThemedApp:
    """
    Base class for themed Tkinter applications.

    Provides centralized theme management, color lookups, and style
    configuration. Games should inherit from this class to get
    automatic theme support.

    Example:
        class MyGameGUI(ThemedApp):
            def __init__(self):
                self.root = tk.Tk()
                self.theme_var = tk.StringVar(value="default")
                super().__init__(self.root, self.theme_var)

            def _customize_styles(self):
                # Optional: Add game-specific style customizations
                pass
    """

    def __init__(
        self,
        root: tk.Tk,
        theme_var: tk.StringVar,
        initial_theme: str = "default"
    ):
        """
        Initialize themed application.

        Args:
            root: The Tk root window
            theme_var: StringVar holding current theme name
            initial_theme: Initial theme to apply
        """
        self.root = root
        self.theme_var = theme_var
        self._current_theme = initial_theme
        self.theme_var.set(initial_theme)

        # Set up ttk Style
        self.style = ttk.Style()

        # Optional callback for games to hook into theme changes
        self._theme_change_callbacks: list[Callable[[], None]] = []

    def _color(self, key: str, theme: Optional[str] = None) -> str:
        """
        Get color for given key in current or specified theme.

        Args:
            key: Color key (e.g., "BG", "TEXT", "ACCENT")
            theme: Optional theme name (uses current if not specified)

        Returns:
            Hex color string (e.g., "#0c1222")
        """
        theme_name = theme or self._current_theme
        palette = PALETTES.get(theme_name, PALETTES["default"])
        return palette.get(key, palette.get("BG", "#000000"))

    def register_theme_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a callback to be called when theme changes.

        Args:
            callback: Function to call on theme change
        """
        self._theme_change_callbacks.append(callback)

    def _apply_theme(self, theme_name: Optional[str] = None) -> None:
        """
        Apply theme to all widgets.

        Args:
            theme_name: Theme to apply (uses current if not specified)
        """
        if theme_name:
            self._current_theme = theme_name
            self.theme_var.set(theme_name)

        theme = self._current_theme

        # Configure root window
        self.root.configure(bg=self._color("BG", theme))

        # Configure ttk styles
        self._configure_ttk_styles(theme)

        # Allow subclasses to customize
        self._customize_styles()

        # Call registered callbacks
        for callback in self._theme_change_callbacks:
            try:
                callback()
            except Exception:
                pass  # Don't let callback errors break theme application

    def _configure_ttk_styles(self, theme: str) -> None:
        """
        Configure ttk widget styles for current theme.

        Args:
            theme: Theme name to configure styles for
        """
        bg = self._color("BG", theme)
        fg = self._color("TEXT", theme)
        panel = self._color("PANEL", theme)
        accent = self._color("ACCENT", theme)
        muted = self._color("MUTED", theme)
        btn = self._color("BTN", theme)
        border = self._color("BORDER", theme)

        # Frame styles
        self.style.configure("TFrame", background=bg)
        self.style.configure("Panel.TFrame", background=panel)

        # Label styles
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure("Banner.TLabel", background=bg, foreground=accent, font=("Arial", 16, "bold"))
        self.style.configure("Title.TLabel", background=bg, foreground=fg, font=("Arial", 12, "bold"))
        self.style.configure("Muted.TLabel", background=bg, foreground=muted, font=("Arial", 9))
        self.style.configure("Panel.TLabel", background=panel, foreground=fg)

        # Button styles
        self.style.configure(
            "TButton",
            background=panel,
            foreground=fg,
            borderwidth=1,
            relief="flat",
        )
        self.style.map(
            "TButton",
            background=[("active", btn), ("pressed", accent)],
            foreground=[("active", bg)],
        )

        self.style.configure(
            "Accent.TButton",
            background=accent,
            foreground=bg,
            borderwidth=0,
            font=("Arial", 10, "bold"),
        )
        self.style.map(
            "Accent.TButton",
            background=[("active", btn), ("pressed", panel)],
        )

        self.style.configure(
            "Panel.TButton",
            background=panel,
            foreground=fg,
            borderwidth=1,
        )

        # Checkbutton styles
        self.style.configure(
            "App.TCheckbutton",
            background=panel,
            foreground=fg,
        )
        self.style.map(
            "App.TCheckbutton",
            background=[("active", panel)],
        )

        # Combobox styles
        self.style.configure(
            "App.TCombobox",
            fieldbackground=panel,
            background=panel,
            foreground=fg,
            arrowcolor=fg,
            bordercolor=border,
        )
        self.style.map(
            "App.TCombobox",
            fieldbackground=[("readonly", panel)],
            selectbackground=[("readonly", accent)],
            selectforeground=[("readonly", bg)],
        )

    def _customize_styles(self) -> None:
        """
        Override this method to add game-specific style customizations.

        This is called after standard styles are configured, allowing
        games to add or override specific styles.
        """
        pass

    def _on_theme_change(self, event: Optional[tk.Event] = None) -> None:
        """
        Handle theme change event.

        Args:
            event: Tk event (from combobox selection)
        """
        new_theme = self.theme_var.get()
        self._apply_theme(new_theme)

    def _update_theme_swatch(self, canvas: tk.Canvas) -> None:
        """
        Update theme preview swatch with current theme colors.

        Args:
            canvas: Canvas widget to draw swatch on
        """
        canvas.delete("all")
        width = canvas.winfo_width() or 400
        segment_width = width // 8

        colors = [
            self._color("BG"),
            self._color("PANEL"),
            self._color("CELL"),
            self._color("BTN"),
            self._color("ACCENT"),
            self._color("TEXT"),
            self._color("MUTED"),
            self._color("BORDER"),
        ]

        for i, color in enumerate(colors):
            x1 = i * segment_width
            x2 = x1 + segment_width
            canvas.create_rectangle(
                x1, 0, x2, 28,
                fill=color,
                outline="",
            )


def create_themed_root(title: str, theme: str = "default") -> tuple[tk.Tk, tk.StringVar]:
    """
    Helper function to create a themed Tk root window.

    Args:
        title: Window title
        theme: Initial theme name

    Returns:
        Tuple of (root window, theme variable)
    """
    root = tk.Tk()
    root.title(title)
    theme_var = tk.StringVar(value=theme)
    root.configure(bg=PALETTES[theme]["BG"])
    return root, theme_var
