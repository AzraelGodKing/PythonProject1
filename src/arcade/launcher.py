"""Arcade Hub launcher: pick a game and it opens in its own process."""

from __future__ import annotations

import logging
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from arcade import __version__
from arcade.core import i18n, locking, themes
from arcade.core import log as arcade_log
from arcade.core.settings import Settings, hub_settings
from arcade.core.ui import apply_styles, base_font_family, play_click
from arcade.games import GAMES, GameInfo

log = logging.getLogger(__name__)

POLL_MS = 1500


class Launcher:
    def __init__(self, root: tk.Tk, *, hub: Settings | None = None) -> None:
        self.root = root
        self.hub = hub or hub_settings()
        self.t = i18n.Translator(self.hub["language"])
        self.lock = locking.InstanceLock()
        self.running: str | None = None
        self.body: ttk.Frame | None = None
        root.geometry("880x640")
        root.minsize(720, 520)
        self.render()
        self._poll()

    @property
    def palette(self) -> themes.Palette:
        return themes.get(self.hub["theme"])

    def render(self) -> None:
        if self.body is not None:
            self.body.destroy()
        apply_styles(self.root, self.palette)
        self.root.title(self.t("launcher.window_title"))
        family = base_font_family(self.root)
        self.body = body = ttk.Frame(self.root, padding=20)
        body.pack(fill="both", expand=True)

        header = ttk.Frame(body, style="Panel.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text=self.t("launcher.title"), style="Heading.TLabel", font=(family, 22, "bold")).pack(
            anchor="w"
        )
        ttk.Label(header, text=self.t("launcher.subtitle"), style="PanelMuted.TLabel").pack(anchor="w", pady=(2, 10))

        prefs = ttk.Frame(header, style="Panel.TFrame")
        prefs.pack(anchor="w")
        ttk.Label(prefs, text=self.t("options.language"), style="Panel.TLabel").pack(side="left")
        codes = i18n.available_languages()
        lang = ttk.Combobox(prefs, values=[i18n.LANGUAGE_NAMES.get(c, c) for c in codes], state="readonly", width=14)
        lang.current(codes.index(self.t.language))
        lang.pack(side="left", padx=(6, 16))
        lang.bind("<<ComboboxSelected>>", lambda _e: self.set_language(codes[lang.current()]))

        ttk.Label(prefs, text=self.t("options.theme"), style="Panel.TLabel").pack(side="left")
        names = list(themes.THEMES)
        theme = ttk.Combobox(prefs, values=[self.t(f"theme.{n}") for n in names], state="readonly", width=24)
        theme.current(names.index(self.hub["theme"]))
        theme.pack(side="left", padx=(6, 16))
        theme.bind("<<ComboboxSelected>>", lambda _e: self.set_theme(names[theme.current()]))

        self.sound = tk.BooleanVar(value=self.hub["sound"])
        ttk.Checkbutton(
            prefs,
            text=self.t("options.sound"),
            variable=self.sound,
            command=lambda: self.hub.set("sound", self.sound.get()),
        ).pack(side="left")

        grid = ttk.Frame(body)
        grid.pack(fill="both", expand=True, pady=(16, 0))
        grid.columnconfigure((0, 1), weight=1, uniform="cards")
        self.cards: dict[str, tuple[ttk.Label, ttk.Button]] = {}
        for index, game in enumerate(GAMES):
            self._card(grid, game, family).grid(row=index // 2, column=index % 2, sticky="nsew", padx=6, pady=6)

        ttk.Label(body, text=f"v{__version__}", style="Muted.TLabel").pack(anchor="e", pady=(8, 0))
        self._update_cards()

    def _card(self, parent: ttk.Frame, game: GameInfo, family: str) -> ttk.Frame:
        card = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        card.columnconfigure(1, weight=1)
        ttk.Label(card, text=game.icon, style="Panel.TLabel", font=(family, 26), width=2, anchor="center").grid(
            row=0, column=0, rowspan=3, padx=(0, 12)
        )
        ttk.Label(card, text=self.t(game.name_key), style="Heading.TLabel").grid(row=0, column=1, sticky="w")
        desc = ttk.Label(card, text=self.t(game.description_key), style="PanelMuted.TLabel", wraplength=300)
        desc.grid(row=1, column=1, sticky="w", pady=(2, 8))
        # Wrap to the space left between the icon and the Play button.
        card.bind("<Configure>", lambda e, d=desc: d.configure(wraplength=max(160, e.width - 220)))
        status = ttk.Label(card, style="Badge.TLabel")
        status.grid(row=2, column=1, sticky="w")
        button = ttk.Button(
            card, text=self.t("launcher.launch"), style="Accent.TButton", command=lambda: self.launch(game)
        )
        button.grid(row=0, column=2, rowspan=3, padx=(12, 0))
        self.cards[game.id] = (status, button)
        return card

    def _poll(self) -> None:
        if not self.root.winfo_exists():
            return
        owner = self.lock.owner()
        if owner != self.running:
            self.running = owner
            self._update_cards()
        self.root.after(POLL_MS, self._poll)

    def _update_cards(self) -> None:
        for game in GAMES:
            status, button = self.cards[game.id]
            if not game.available:
                text, style, enabled = self.t("launcher.status.missing"), "MutedBadge.TLabel", False
            elif self.running == game.id:
                text, style, enabled = self.t("launcher.status.running"), "Badge.TLabel", False
            elif self.running:
                holder = self.t(f"{self.running}.name") if self.t.has(f"{self.running}.name") else self.running
                text, style, enabled = self.t("launcher.status.busy", holder=holder), "MutedBadge.TLabel", False
            else:
                text, style, enabled = self.t("launcher.status.ready"), "Badge.TLabel", True
            status.configure(text=text, style=style)
            button.state(["!disabled" if enabled else "disabled"])

    def launch(self, game: GameInfo) -> None:
        owner = self.lock.owner()
        if owner:
            self.running = owner
            self._update_cards()
            return
        try:
            subprocess.Popen(game.command())
        except OSError as exc:
            log.exception("Could not start %s", game.id)
            messagebox.showerror(self.t("launcher.launch_failed"), self.t("error.body", error=exc), parent=self.root)
            return
        if self.hub["sound"]:
            play_click(self.root)
        self.running = game.id  # optimistic until the game takes the lock
        self._update_cards()

    def set_language(self, code: str) -> None:
        self.hub.set("language", code)
        self.t.set_language(code)
        self.root.after_idle(self.render)

    def set_theme(self, name: str) -> None:
        self.hub.set("theme", name)
        self.root.after_idle(self.render)


def main() -> int:
    arcade_log.setup("launcher")
    hub = hub_settings()
    t = i18n.Translator(hub["language"])
    instance = locking.InstanceLock("launcher")
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(t("error.no_display", error=exc), file=sys.stderr)
        return 1
    if not instance.acquire("launcher"):
        root.withdraw()
        messagebox.showinfo(t("launcher.window_title"), t("launcher.already_open"), parent=root)
        root.destroy()
        return 1
    try:
        Launcher(root, hub=hub)
        root.mainloop()
    finally:
        instance.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
