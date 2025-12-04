"""Shared options dialog builder for games."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable, Sequence


Toggle = tuple[str, tk.Variable, Callable[[], None]]
Action = tuple[str, Callable[[], None]]
THEME_CHOICES = (
    "default",
    "high_contrast",
    "colorblind_protan",
    "colorblind_deutan",
    "colorblind_tritan",
    "monochrome",
    "light",
    "dark",
)
PALETTES = {
    "default": {
        # Vivid but comfortable midnight palette for legibility
        "BG": "#0c1222",
        "PANEL": "#142039",
        "ACCENT": "#7dd3fc",
        "TEXT": "#f8fafc",
        "MUTED": "#cbd5e1",
        "BTN": "#3b82f6",
        "O": "#fbbf24",
        "CELL": "#0f1f3a",
        "CARD": "#0b162c",
        "BORDER": "#2c4163",
    },
    "high_contrast": {
        "BG": "#010409",
        "PANEL": "#0f172a",
        "ACCENT": "#facc15",
        "TEXT": "#f8fafc",
        "MUTED": "#e2e8f0",
        "BTN": "#fb923c",
        "O": "#f97316",
        "CELL": "#111827",
        "CARD": "#0b1220",
        "BORDER": "#facc15",
    },
    "light": {
        "BG": "#f8fafc",
        "PANEL": "#e5e7eb",
        "ACCENT": "#2563eb",
        "TEXT": "#0f172a",
        "MUTED": "#475569",
        "BTN": "#1d4ed8",
        "O": "#d97706",
        "CELL": "#ffffff",
        "CARD": "#ffffff",
        "BORDER": "#cbd5e1",
    },
    "colorblind_protan": {
        "BG": "#0d152a",
        "PANEL": "#16223b",
        "ACCENT": "#f4c430",
        "TEXT": "#e8edf5",
        "MUTED": "#c6cfdd",
        "BTN": "#f59e0b",
        "O": "#22c55e",
        "CELL": "#1c2b45",
        "CARD": "#13253d",
        "BORDER": "#304566",
    },
    "colorblind_deutan": {
        "BG": "#0d1426",
        "PANEL": "#1a263c",
        "ACCENT": "#f59e0b",
        "TEXT": "#edf2fb",
        "MUTED": "#cbd5e1",
        "BTN": "#ef476f",
        "O": "#16a34a",
        "CELL": "#1f2f48",
        "CARD": "#14243b",
        "BORDER": "#2c3f5c",
    },
    "colorblind_tritan": {
        "BG": "#0f172a",
        "PANEL": "#1b2540",
        "ACCENT": "#f59e0b",
        "TEXT": "#e5ecf5",
        "MUTED": "#cbd5e1",
        "BTN": "#a855f7",
        "O": "#22d3ee",
        "CELL": "#213153",
        "CARD": "#16233f",
        "BORDER": "#33476b",
    },
    "monochrome": {
        "BG": "#0e1117",
        "PANEL": "#161c27",
        "ACCENT": "#e5e7eb",
        "TEXT": "#f3f4f6",
        "MUTED": "#9ca3af",
        "BTN": "#d1d5db",
        "O": "#e5e7eb",
        "CELL": "#1d2431",
        "CARD": "#141a24",
        "BORDER": "#303746",
    },
    "dark": {
        "BG": "#0b1220",
        "PANEL": "#111a2c",
        "ACCENT": "#67e8f9",
        "TEXT": "#e2e8f0",
        "MUTED": "#94a3b8",
        "BTN": "#38bdf8",
        "O": "#f59e0b",
        "CELL": "#162135",
        "CARD": "#0f172a",
        "BORDER": "#22304a",
    },
}


def show_options_popup(
    gui,
    *,
    toggles: Sequence[Toggle],
    preset_actions: Sequence[Action] = (),
    title: str = "Options",
    subtitle: str = "Tweak visuals, sounds, and behavior to your liking.",
    theme_choices: Sequence[str] = THEME_CHOICES,
) -> None:
    """Render a shared options popup with themes/language and custom toggles.

    The ``gui`` object is expected to expose:
      - root, _color(str), options_popup
      - theme_var, _on_theme_change
      - language, available_languages, _lang_display, _on_language_change
      - _update_theme_swatch(canvas), _copy_diagnostics
    """
    if getattr(gui, "options_popup", None) and gui.options_popup.winfo_exists():
        gui.options_popup.lift()
        gui.options_popup.focus_set()
        return

    popup = tk.Toplevel(gui.root)
    popup.title(title)
    popup.configure(bg=gui._color("BG"))
    popup.minsize(380, 500)
    gui.options_popup = popup

    frame = ttk.Frame(popup, padding=20, style="Panel.TFrame")
    frame.grid(row=0, column=0, sticky="nsew")
    popup.columnconfigure(0, weight=1)
    popup.rowconfigure(0, weight=1)
    frame.columnconfigure((0, 1), weight=1)

    ttk.Label(frame, text=title, style="Banner.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
    ttk.Label(frame, text=subtitle, style="Muted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 12))

    row = 2
    toggle_frame = ttk.Frame(frame, style="Panel.TFrame", padding=(10, 8))
    toggle_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))
    toggle_frame.columnconfigure(0, weight=1)
    row += 1
    toggle_row = 0
    for text, var, cmd in toggles:
        ttk.Checkbutton(toggle_frame, text=text, variable=var, style="App.TCheckbutton", command=cmd).grid(
            row=toggle_row, column=0, columnspan=2, sticky="w", pady=2, padx=(0, 6)
        )
        toggle_row += 1
    row = 3

    for idx, (label, action) in enumerate(preset_actions):
        ttk.Button(frame, text=label, style="Panel.TButton", command=action).grid(
            row=row, column=idx % 2, sticky="ew", pady=(10, 4), padx=(0, 0)
        )
        if idx % 2 == 1:
            row += 1
    if preset_actions and len(preset_actions) % 2 != 0:
        row += 1

    ttk.Separator(frame).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 8))
    row += 1

    ttk.Label(frame, text="Theme", style="Title.TLabel").grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 2))
    row += 1
    theme_box = ttk.Combobox(
        frame,
        textvariable=gui.theme_var,
        state="readonly",
        values=list(theme_choices),
        style="App.TCombobox",
        width=20,
    )
    theme_box.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 4))
    theme_box.bind("<<ComboboxSelected>>", gui._on_theme_change)
    row += 1

    ttk.Label(frame, text=getattr(gui, "_t", lambda k, v: "Language")("options.language", "Language"), style="Title.TLabel").grid(
        row=row, column=0, columnspan=2, sticky="w", pady=(8, 2)
    )
    row += 1
    lang_var = tk.StringVar(value=gui._lang_display(gui.language))
    lang_box = ttk.Combobox(
        frame,
        textvariable=lang_var,
        values=[gui._lang_display(code) for code in gui.available_languages],
        state="readonly",
        style="App.TCombobox",
        width=20,
    )
    lang_box.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
    lang_box.bind(
        "<<ComboboxSelected>>",
        lambda e: gui._on_language_change(
            next((code for code in gui.available_languages if gui._lang_display(code) == lang_var.get()), gui.language)
        ),
    )
    row += 1

    swatch = tk.Canvas(frame, height=28, bg=gui._color("PANEL"), highlightthickness=1, highlightbackground=gui._color("BORDER"))
    swatch.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
    gui._update_theme_swatch(swatch)
    row += 1

    ttk.Button(frame, text="Copy diagnostics", style="Accent.TButton", command=gui._copy_diagnostics).grid(
        row=row, column=0, columnspan=1, sticky="ew", pady=(8, 0)
    )
    ttk.Button(frame, text="Close", style="Accent.TButton", command=lambda: _close_options_popup(gui, popup)).grid(
        row=row, column=1, columnspan=1, sticky="ew", pady=(8, 0)
    )


def _close_options_popup(gui, popup: tk.Toplevel) -> None:
    try:
        popup.destroy()
    finally:
        gui.options_popup = None
