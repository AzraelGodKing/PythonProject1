"""Tkinter plumbing shared by the launcher and the games.

:class:`GameApp` gives every game the same window chrome: themed ttk styles,
a menu bar, an options dialog (theme, language, sound plus game-specific
toggles), a scoreboard dialog and rules. Changing the theme or language
rebuilds the widgets from the game's state, so games only implement
``build`` (create widgets) and ``refresh`` (sync widgets with state).
"""

from __future__ import annotations

import logging
import sys
import time
import tkinter as tk
import traceback
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from tkinter import font as tkfont
from tkinter import messagebox, simpledialog, ttk

from arcade import __version__
from arcade.core import i18n, locking, themes
from arcade.core import log as arcade_log
from arcade.core.cards import Card
from arcade.core.settings import Settings, hub_settings

log = logging.getLogger(__name__)

CARD_W, CARD_H = 72, 100


@dataclass
class Toggle:
    """A boolean option shown in the options dialog."""

    label_key: str
    variable: tk.BooleanVar
    on_change: Callable[[], None] | None = None


@dataclass
class ScoreSection:
    title: str
    headers: Sequence[str]
    rows: Sequence[Sequence[object]]


def base_font_family(root: tk.Misc) -> str:
    return tkfont.nametofont("TkDefaultFont", root=root).actual("family")


def apply_styles(root: tk.Misc, palette: themes.Palette) -> ttk.Style:
    """Configure the shared ttk styles for ``palette``."""
    p = palette
    family = base_font_family(root)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=p.bg, foreground=p.text, bordercolor=p.border, font=(family, 10))
    style.configure("TFrame", background=p.bg)
    style.configure("Panel.TFrame", background=p.panel)
    style.configure("TLabel", background=p.bg, foreground=p.text)
    style.configure("Panel.TLabel", background=p.panel, foreground=p.text)
    style.configure("Muted.TLabel", background=p.bg, foreground=p.muted)
    style.configure("PanelMuted.TLabel", background=p.panel, foreground=p.muted)
    style.configure("Title.TLabel", background=p.bg, foreground=p.accent, font=(family, 18, "bold"))
    style.configure("Heading.TLabel", background=p.panel, foreground=p.text, font=(family, 13, "bold"))
    style.configure("Status.TLabel", background=p.panel, foreground=p.text, font=(family, 11), padding=(10, 6))
    style.configure("Good.TLabel", background=p.panel, foreground=p.good, font=(family, 11, "bold"))
    style.configure("Bad.TLabel", background=p.panel, foreground=p.bad, font=(family, 11, "bold"))
    style.configure("Badge.TLabel", background=p.accent, foreground=p.bg, font=(family, 9, "bold"), padding=(8, 3))
    style.configure(
        "MutedBadge.TLabel", background=p.border, foreground=p.text, font=(family, 9, "bold"), padding=(8, 3)
    )
    style.configure("TButton", background=p.panel, foreground=p.text, padding=(10, 5), borderwidth=1)
    style.map(
        "TButton",
        background=[("disabled", p.bg), ("active", p.border)],
        foreground=[("disabled", p.muted)],
    )
    style.configure("Accent.TButton", background=p.button, foreground=p.button_text, font=(family, 10, "bold"))
    style.map(
        "Accent.TButton",
        background=[("disabled", p.panel), ("active", p.accent)],
        foreground=[("disabled", p.muted), ("active", p.bg)],
    )
    for name in ("TCheckbutton", "TRadiobutton"):
        style.configure(name, background=p.panel, foreground=p.text, indicatorcolor=p.bg)
        style.map(name, background=[("active", p.panel)], indicatorcolor=[("selected", p.accent)])
    style.configure("TCombobox", fieldbackground=p.panel, background=p.panel, foreground=p.text, arrowcolor=p.text)
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", p.panel)],
        foreground=[("readonly", p.text)],
        selectbackground=[("readonly", p.panel)],
        selectforeground=[("readonly", p.text)],
    )
    style.configure("TSpinbox", fieldbackground=p.panel, foreground=p.text, arrowcolor=p.text)
    style.configure("TEntry", fieldbackground=p.panel, foreground=p.text, insertcolor=p.text)
    style.configure("Treeview", background=p.panel, fieldbackground=p.panel, foreground=p.text)
    style.configure("Treeview.Heading", background=p.border, foreground=p.text, font=(family, 10, "bold"))
    style.map("Treeview", background=[("selected", p.button)], foreground=[("selected", p.button_text)])
    style.configure("TSeparator", background=p.border)
    root.option_add("*TCombobox*Listbox.background", p.panel)
    root.option_add("*TCombobox*Listbox.foreground", p.text)
    root.option_add("*Menu.background", p.panel)
    root.option_add("*Menu.foreground", p.text)
    if isinstance(root, (tk.Tk, tk.Toplevel)):
        root.configure(bg=p.bg)
    return style


def draw_card(
    canvas: tk.Canvas,
    x: float,
    y: float,
    card: Card | None,
    palette: themes.Palette,
    *,
    face_up: bool = True,
    selected: bool = False,
    tags: str | tuple[str, ...] = (),
    width: int = CARD_W,
    height: int = CARD_H,
) -> None:
    """Draw a card (or an empty slot when ``card`` is None) with its top-left at x, y."""
    outline = palette.accent if selected else palette.border
    line = 3 if selected else 1
    if card is None:
        canvas.create_rectangle(x, y, x + width, y + height, outline=palette.border, dash=(4, 3), width=1, tags=tags)
        return
    if not face_up:
        canvas.create_rectangle(
            x, y, x + width, y + height, fill=palette.card_back, outline=outline, width=line, tags=tags
        )
        canvas.create_rectangle(x + 6, y + 6, x + width - 6, y + height - 6, outline=palette.card_face, tags=tags)
        return
    colour = palette.suit_red if card.is_red else palette.suit_black
    family = base_font_family(canvas)
    canvas.create_rectangle(x, y, x + width, y + height, fill=palette.card_face, outline=outline, width=line, tags=tags)
    canvas.create_text(
        x + 6,
        y + 4,
        text=f"{card.rank}\n{card.symbol}",
        anchor="nw",
        fill=colour,
        font=(family, 11, "bold"),
        justify="center",
        tags=tags,
    )
    canvas.create_text(x + width / 2, y + height / 2 + 6, text=card.symbol, fill=colour, font=(family, 26), tags=tags)


class GameApp:
    """Base class for a game window. Subclasses set ``game_id`` and implement build/refresh."""

    game_id = "game"
    min_size = (720, 560)

    def __init__(self, root: tk.Tk, *, hub: Settings | None = None) -> None:
        self.root = root
        self.hub = hub or hub_settings()
        self.t = i18n.Translator(self.hub["language"])
        self.palette = themes.get(self.hub["theme"])
        self.family = base_font_family(root)
        root.report_callback_exception = self._report_error
        root.minsize(*self.min_size)
        root.protocol("WM_DELETE_WINDOW", self.quit)
        self.body: ttk.Frame | None = None
        self._dialogs: list[tk.Toplevel] = []
        self._render()

    # -- lifecycle -------------------------------------------------------
    def build(self, parent: ttk.Frame) -> None:
        raise NotImplementedError

    def refresh(self) -> None:
        """Update widgets from game state. Called after build and after every move."""

    def new_game(self) -> None:
        raise NotImplementedError

    def quit(self) -> None:
        self.root.destroy()

    def _render(self) -> None:
        for dialog in self._dialogs:
            if dialog.winfo_exists():
                dialog.destroy()
        self._dialogs.clear()
        if self.body is not None:
            self.body.destroy()
        apply_styles(self.root, self.palette)
        self.root.title(self.t(f"{self.game_id}.name"))
        self._build_menu()
        self.body = ttk.Frame(self.root, padding=12)
        self.body.pack(fill="both", expand=True)
        self.build(self.body)
        self.refresh()

    # -- menu -------------------------------------------------------------
    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root, tearoff=False)
        game = tk.Menu(menubar, tearoff=False)
        game.add_command(label=self.t("menu.new_game"), accelerator="Ctrl+N", command=self.new_game)
        game.add_command(label=self.t("menu.scores"), command=self.show_scores)
        game.add_command(label=self.t("menu.options"), command=self.show_options)
        game.add_separator()
        game.add_command(label=self.t("menu.quit"), command=self.quit)
        menubar.add_cascade(label=self.t("menu.game"), menu=game)
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label=self.t("menu.rules"), accelerator="F1", command=self.show_rules)
        help_menu.add_command(label=self.t("menu.about"), command=self.show_about)
        menubar.add_cascade(label=self.t("menu.help"), menu=help_menu)
        self.root.configure(menu=menubar)
        self.root.bind_all("<Control-n>", lambda _e: self.new_game())
        self.root.bind_all("<F1>", lambda _e: self.show_rules())

    # -- shared dialogs ---------------------------------------------------
    def dialog(self, title: str) -> tuple[tk.Toplevel, ttk.Frame]:
        top = tk.Toplevel(self.root)
        top.title(title)
        top.configure(bg=self.palette.bg)
        top.transient(self.root)
        frame = ttk.Frame(top, padding=16, style="Panel.TFrame")
        frame.pack(fill="both", expand=True)
        top.bind("<Escape>", lambda _e: top.destroy())
        self._dialogs.append(top)
        return top, frame

    def extra_options(self) -> list[Toggle]:
        return []

    def show_options(self) -> None:
        top, frame = self.dialog(self.t("options.title"))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text=self.t("options.theme"), style="Panel.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        theme_names = list(themes.THEMES)
        theme_labels = [self.t(f"theme.{name}") for name in theme_names]
        theme_box = ttk.Combobox(frame, values=theme_labels, state="readonly", width=28)
        theme_box.current(theme_names.index(self.hub["theme"]))
        theme_box.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=4)
        theme_box.bind("<<ComboboxSelected>>", lambda _e: self.set_theme(theme_names[theme_box.current()]))

        ttk.Label(frame, text=self.t("options.language"), style="Panel.TLabel").grid(
            row=1, column=0, sticky="w", pady=4
        )
        codes = i18n.available_languages()
        lang_box = ttk.Combobox(
            frame, values=[i18n.LANGUAGE_NAMES.get(c, c) for c in codes], state="readonly", width=28
        )
        lang_box.current(codes.index(self.t.language))
        lang_box.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=4)
        lang_box.bind("<<ComboboxSelected>>", lambda _e: self.set_language(codes[lang_box.current()]))

        sound = tk.BooleanVar(value=self.hub["sound"])
        toggles = [Toggle("options.sound", sound, lambda: self.hub.set("sound", sound.get())), *self.extra_options()]
        for row, toggle in enumerate(toggles, start=2):
            ttk.Checkbutton(
                frame, text=self.t(toggle.label_key), variable=toggle.variable, command=toggle.on_change
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=2)

        ttk.Button(frame, text=self.t("button.close"), command=top.destroy).grid(
            row=len(toggles) + 2, column=1, sticky="e", pady=(12, 0)
        )

    def score_sections(self) -> list[ScoreSection]:
        return []

    def reset_scores(self) -> None:
        """Clear this game's saved scores."""

    def show_scores(self) -> None:
        top, frame = self.dialog(self.t("scores.title"))
        sections = self.score_sections()
        if not any(section.rows for section in sections):
            ttk.Label(frame, text=self.t("scores.empty"), style="Panel.TLabel").pack(anchor="w", pady=8)
        for section in sections:
            ttk.Label(frame, text=section.title, style="Heading.TLabel").pack(anchor="w", pady=(8, 4))
            if not section.rows:
                ttk.Label(frame, text=self.t("scores.none_yet"), style="PanelMuted.TLabel").pack(anchor="w")
                continue
            columns = [f"c{i}" for i in range(len(section.headers))]
            tree = ttk.Treeview(frame, columns=columns, show="headings", height=min(len(section.rows), 10))
            for column, header in zip(columns, section.headers, strict=True):
                tree.heading(column, text=header)
                tree.column(column, width=120, anchor="center")
            for row in section.rows:
                tree.insert("", "end", values=[str(value) for value in row])
            tree.pack(fill="x")

        buttons = ttk.Frame(frame, style="Panel.TFrame")
        buttons.pack(fill="x", pady=(12, 0))

        def reset() -> None:
            if messagebox.askyesno(self.t("scores.reset"), self.t("scores.reset_confirm"), parent=top):
                self.reset_scores()
                top.destroy()
                self.refresh()

        ttk.Button(buttons, text=self.t("scores.reset"), command=reset).pack(side="left")
        ttk.Button(buttons, text=self.t("button.close"), command=top.destroy).pack(side="right")

    def show_rules(self) -> None:
        messagebox.showinfo(self.t("menu.rules"), self.t(f"{self.game_id}.rules"), parent=self.root)

    def show_about(self) -> None:
        messagebox.showinfo(
            self.t("menu.about"),
            self.t("about.body", name=self.t(f"{self.game_id}.name"), version=__version__),
            parent=self.root,
        )

    def ask_name(self) -> str | None:
        name = simpledialog.askstring(
            self.t("scores.name_title"),
            self.t("scores.name_prompt"),
            initialvalue=self.hub["player_name"] or self.t("scores.default_name"),
            parent=self.root,
        )
        if name is None:
            return None
        name = name.strip() or self.t("scores.default_name")
        self.hub.set("player_name", name)
        return name

    # -- preferences ------------------------------------------------------
    def set_theme(self, name: str) -> None:
        self.hub.set("theme", name)
        self.palette = themes.get(name)
        self.root.after_idle(self._render)

    def set_language(self, code: str) -> None:
        self.hub.set("language", code)
        self.t.set_language(code)
        self.root.after_idle(self._render)

    def play_sound(self) -> None:
        if self.hub["sound"]:
            play_click(self.root)

    def _report_error(self, exc_type: type[BaseException], exc: BaseException, tb: object) -> None:
        log.error("Unhandled error", exc_info=(exc_type, exc, tb))  # type: ignore[arg-type]
        traceback.print_exception(exc_type, exc, tb)  # type: ignore[arg-type]
        messagebox.showerror(self.t("error.title"), self.t("error.body", error=exc), parent=self.root)


def play_click(root: tk.Misc) -> None:
    if sys.platform == "win32":
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_OK)
            return
        except (ImportError, RuntimeError):
            pass
    root.bell()


def run_game(app_cls: type[GameApp]) -> int:
    """Entry point for a game process: take the single-instance lock, then run."""
    game_id = app_cls.game_id
    arcade_log.setup(game_id)
    hub = hub_settings()
    t = i18n.Translator(hub["language"])
    lock = locking.InstanceLock()
    # The launcher probes the lock briefly, so retry for a moment before giving up.
    for _ in range(10):
        if lock.acquire(game_id):
            break
        time.sleep(0.1)
    else:
        owner = lock.owner()
        _alert_blocked(t, game_id, owner)
        return 1
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        lock.release()
        print(t("error.no_display", error=exc), file=sys.stderr)
        return 1
    try:
        app_cls(root, hub=hub)
        root.mainloop()
    finally:
        lock.release()
    return 0


def _alert_blocked(t: i18n.Translator, game_id: str, owner: str | None) -> None:
    name = t(f"{game_id}.name")
    if owner == game_id:
        title, body = t("lock.self.title"), t("lock.self.body", name=name)
    else:
        holder = t(f"{owner}.name") if owner and t.has(f"{owner}.name") else (owner or "?")
        title, body = t("lock.other.title"), t("lock.other.body", holder=holder, name=name)
    try:
        root = tk.Tk()
    except tk.TclError:
        print(f"{title}: {body}", file=sys.stderr)
        return
    root.withdraw()
    messagebox.showwarning(title, body, parent=root)
    root.destroy()
