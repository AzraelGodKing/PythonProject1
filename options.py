import tkinter as tk
from tkinter import ttk


def show_options_popup(gui) -> None:
    """Display the options popup, hosted in a separate module for clarity."""
    if gui.options_popup and gui.options_popup.winfo_exists():
        gui.options_popup.lift()
        gui.options_popup.focus_set()
        return

    popup = tk.Toplevel(gui.root)
    popup.title("Options")
    popup.configure(bg=gui._color("BG"))
    gui.options_popup = popup
    frame = ttk.Frame(popup, padding=12, style="App.TFrame")
    frame.grid(row=0, column=0, sticky="nsew")
    popup.columnconfigure(0, weight=1)
    popup.rowconfigure(0, weight=1)

    ttk.Label(frame, text="Options", style="Title.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))

    ttk.Checkbutton(frame, text="Require confirmations", variable=gui.confirm_moves, style="App.TCheckbutton", command=gui._toggle_confirm).grid(row=1, column=0, sticky="w", pady=2)
    ttk.Checkbutton(frame, text="Auto-start next game", variable=gui.auto_start, style="App.TCheckbutton", command=gui._toggle_auto_start).grid(row=2, column=0, sticky="w", pady=2)
    ttk.Checkbutton(frame, text="Rotate history filenames", variable=gui.rotate_logs, style="App.TCheckbutton", command=gui._toggle_rotate_logs).grid(row=3, column=0, sticky="w", pady=2)
    ttk.Checkbutton(frame, text="Larger fonts", variable=gui.large_fonts, style="App.TCheckbutton", command=gui._toggle_font_size).grid(row=4, column=0, sticky="w", pady=2)
    ttk.Checkbutton(frame, text="Animations", variable=gui.animations_enabled, style="App.TCheckbutton", command=gui._toggle_animations).grid(row=5, column=0, sticky="w", pady=2)
    ttk.Checkbutton(frame, text="Sound cues", variable=gui.sound_enabled, style="App.TCheckbutton", command=gui._toggle_sound).grid(row=6, column=0, sticky="w", pady=2)
    ttk.Checkbutton(frame, text="Show board coordinates", variable=gui.show_coords, style="App.TCheckbutton", command=gui._toggle_show_coords).grid(row=7, column=0, sticky="w", pady=2)
    ttk.Checkbutton(frame, text="Show AI heatmap", variable=gui.show_heatmap, style="App.TCheckbutton", command=gui._toggle_heatmap).grid(row=8, column=0, sticky="w", pady=2)
    ttk.Checkbutton(frame, text="AI commentary", variable=gui.show_commentary, style="App.TCheckbutton").grid(row=9, column=0, sticky="w", pady=2)

    ttk.Button(frame, text="No animation/sound preset", style="Panel.TButton", command=gui._disable_motion_sound).grid(row=10, column=0, sticky="ew", pady=(6, 2))
    ttk.Button(frame, text="Reset toggles to default", style="Panel.TButton", command=gui._reset_toggles).grid(row=11, column=0, sticky="ew", pady=(2, 4))

    ttk.Label(frame, text="Theme", style="Title.TLabel").grid(row=12, column=0, sticky="w", pady=(8, 2))
    theme_box = ttk.Combobox(
        frame,
        textvariable=gui.theme_var,
        state="readonly",
        values=[
            "default",
            "high_contrast",
            "colorblind_protan",
            "colorblind_deutan",
            "colorblind_tritan",
            "monochrome",
            "light",
        ],
        style="App.TCombobox",
        width=20,
    )
    theme_box.grid(row=10, column=0, sticky="ew", pady=(0, 4))
    theme_box.bind("<<ComboboxSelected>>", gui._on_theme_change)

    swatch = tk.Canvas(frame, height=20, bg=gui._color("PANEL"), highlightthickness=0)
    swatch.grid(row=11, column=0, sticky="ew", pady=(0, 6))
    gui._update_theme_swatch(swatch)

    ttk.Button(frame, text="Copy diagnostics", style="Panel.TButton", command=gui._copy_diagnostics).grid(row=12, column=0, sticky="ew", pady=(6, 0))
    ttk.Button(frame, text="Close", style="Panel.TButton", command=lambda: _close_options_popup(gui, popup)).grid(row=13, column=0, sticky="e", pady=(10, 0))


def _close_options_popup(gui, popup: tk.Toplevel) -> None:
    try:
        popup.destroy()
    finally:
        gui.options_popup = None
