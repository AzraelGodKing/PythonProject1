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
        "BG": "#0f172a",
        "PANEL": "#1e293b",
        "ACCENT": "#38bdf8",
        "TEXT": "#e2e8f0",
        "MUTED": "#94a3b8",
        "BTN": "#0ea5e9",
        "O": "#f97316",
        "CELL": "#233244",
    },
    "high_contrast": {
        "BG": "#000000",
        "PANEL": "#111111",
        "ACCENT": "#ffeb3b",
        "TEXT": "#ffffff",
        "MUTED": "#cccccc",
        "BTN": "#ff9800",
        "O": "#ff5722",
        "CELL": "#1f1f1f",
    },
    "light": {
        "BG": "#f6f8fb",
        "PANEL": "#e1e7f2",
        "ACCENT": "#0077ff",
        "TEXT": "#111827",
        "MUTED": "#4b5563",
        "BTN": "#2563eb",
        "O": "#f97316",
        "CELL": "#ffffff",
    },
    "colorblind_protan": {
        "BG": "#0f1627",
        "PANEL": "#192339",
        "ACCENT": "#f2c14e",
        "TEXT": "#e6edf5",
        "MUTED": "#c0cad8",
        "BTN": "#f08a5d",
        "O": "#00b7a8",
        "CELL": "#1f2c40",
    },
    "colorblind_deutan": {
        "BG": "#0e1524",
        "PANEL": "#1b273a",
        "ACCENT": "#ffc857",
        "TEXT": "#edf2f7",
        "MUTED": "#cbd5e1",
        "BTN": "#ef476f",
        "O": "#06d6a0",
        "CELL": "#1f2c42",
    },
    "colorblind_tritan": {
        "BG": "#0f172a",
        "PANEL": "#1c2540",
        "ACCENT": "#f9c80e",
        "TEXT": "#e5ecf5",
        "MUTED": "#cbd5e1",
        "BTN": "#a4508b",
        "O": "#2dd4bf",
        "CELL": "#22314f",
    },
    "monochrome": {
        "BG": "#0f1115",
        "PANEL": "#1b1f26",
        "ACCENT": "#d1d5db",
        "TEXT": "#f3f4f6",
        "MUTED": "#9ca3af",
        "BTN": "#e5e7eb",
        "O": "#d1d5db",
        "CELL": "#222630",
    },
    "dark": {
        "BG": "#0b1220",
        "PANEL": "#111a2c",
        "ACCENT": "#4cc9f0",
        "TEXT": "#e2e8f0",
        "MUTED": "#94a3b8",
        "BTN": "#4895ef",
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

    frame = ttk.Frame(popup, padding=16, style="Panel.TFrame")
    frame.grid(row=0, column=0, sticky="nsew")
    popup.columnconfigure(0, weight=1)
    popup.rowconfigure(0, weight=1)
    frame.columnconfigure((0, 1), weight=1)

    ttk.Label(frame, text=title, style="Banner.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
    ttk.Label(frame, text=subtitle, style="Muted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 12))

    row = 2
    for text, var, cmd in toggles:
        ttk.Checkbutton(frame, text=text, variable=var, style="App.TCheckbutton", command=cmd).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=2
        )
        row += 1

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

    swatch = tk.Canvas(frame, height=24, bg=gui._color("PANEL"), highlightthickness=0)
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
