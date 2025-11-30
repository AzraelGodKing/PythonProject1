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
    popup.minsize(380, 500)
    gui.options_popup = popup
    frame = ttk.Frame(popup, padding=16, style="Panel.TFrame")
    frame.grid(row=0, column=0, sticky="nsew")
    popup.columnconfigure(0, weight=1)
    popup.rowconfigure(0, weight=1)
    frame.columnconfigure((0, 1), weight=1)

    ttk.Label(frame, text="Options", style="Banner.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
    ttk.Label(frame, text="Tweak visuals, sounds, and behavior to your liking.", style="Muted.TLabel").grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(0, 12)
    )

    row = 2
    for text, var, cmd in [
        ("Require confirmations", gui.confirm_moves, gui._toggle_confirm),
        ("Auto-start next game", gui.auto_start, gui._toggle_auto_start),
        ("Larger fonts", gui.large_fonts, gui._toggle_font_size),
        ("Animations", gui.animations_enabled, gui._toggle_animations),
        ("Sound cues", gui.sound_enabled, gui._toggle_sound),
        ("Show board coordinates", gui.show_coords, gui._toggle_show_coords),
        ("Show AI heatmap", gui.show_heatmap, gui._toggle_heatmap),
        ("Show welcome overlay at launch", gui.show_intro_overlay, gui._save_settings),
        ("Human-like Normal AI (occasional mistakes)", gui.humanish_normal, gui._save_settings),
        ("AI commentary", gui.show_commentary, gui._save_settings),
    ]:
        ttk.Checkbutton(frame, text=text, variable=var, style="App.TCheckbutton", command=cmd).grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
        row += 1

    ttk.Button(frame, text="No animation/sound preset", style="Panel.TButton", command=gui._disable_motion_sound).grid(
        row=row, column=0, sticky="ew", pady=(10, 4)
    )
    ttk.Button(frame, text="Reset toggles to default", style="Panel.TButton", command=gui._reset_toggles).grid(
        row=row, column=1, sticky="ew", pady=(10, 4)
    )
    row += 1

    ttk.Separator(frame).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 8))
    row += 1

    ttk.Label(frame, text="Theme", style="Title.TLabel").grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 2))
    row += 1
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
    theme_box.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 4))
    theme_box.bind("<<ComboboxSelected>>", gui._on_theme_change)
    row += 1

    ttk.Label(frame, text=gui._t("options.language", "Language"), style="Title.TLabel").grid(
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

    ttk.Button(frame, text="Copy diagnostics", style="Panel.TButton", command=gui._copy_diagnostics).grid(
        row=row, column=0, columnspan=1, sticky="ew", pady=(6, 0)
    )
    ttk.Button(frame, text="Close", style="Panel.TButton", command=lambda: _close_options_popup(gui, popup)).grid(
        row=row, column=1, columnspan=1, sticky="ew", pady=(6, 0)
    )


def _close_options_popup(gui, popup: tk.Toplevel) -> None:
    try:
        popup.destroy()
    finally:
        gui.options_popup = None
