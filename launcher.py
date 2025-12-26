"""
A lightweight Tkinter-based launcher for the project's mini-games.
The window lists available games and spins up their GUI entry points
as separate Python processes so players can jump in from a single hub.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Iterable, List, Optional

from shared.options import PALETTES
from shared import settings, single_instance, audio

LOCALES_DIR = Path(__file__).resolve().parent / "shared" / "locales"
SETTINGS_FILE = Path(__file__).resolve().parent / "data" / "launcher_settings.json"
ACTIVE_GAME_LOCK = Path(__file__).resolve().parent / "data" / "locks" / "active_game.lock"


@dataclass
class GameEntry:
    """Describe a playable game that can be launched from the hub."""

    name: str
    description: str
    script_path: Path
    name_key: Optional[str] = None
    desc_key: Optional[str] = None
    extra_args: Optional[List[str]] = None

    @property
    def available(self) -> bool:
        return self.script_path.exists()

    @property
    def command(self) -> List[str]:
        args: Iterable[str] = self.extra_args or []
        return [sys.executable, str(self.script_path), *args]


class GameLauncherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.geometry("820x620")
        self.root.minsize(760, 580)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=0)
        self.root.rowconfigure(2, weight=1)

        self.project_root = Path(__file__).resolve().parent
        self.games = self._load_games()
        self.language_names = {
            "en": "English",
            "es": "Espanol",
            "fr": "Francais",
            "de": "Deutsch",
            "it": "Italiano",
            "pt": "Portugues",
            "ru": "Russkiy",
            "ja": "Nihongo",
            "no": "Norsk (Bokmal)",
        }
        self.available_languages = self._discover_languages()
        default_lang = "en" if "en" in self.available_languages else (self.available_languages[0] if self.available_languages else "en")
        defaults = {"language": default_lang, "theme": "default"}
        loaded = settings.load_settings(SETTINGS_FILE, defaults)
        self.language_var = tk.StringVar(value=self._lang_display(loaded.get("language", default_lang)))
        self.language = loaded.get("language", default_lang)
        self.theme_var = tk.StringVar(value=loaded.get("theme", "default"))
        self.sound_enabled = tk.BooleanVar(value=loaded.get("sound", True))
        self.click_player = audio.ClickPlayer()
        self.translations: dict[str, str] = {}
        self._load_translations(self.language)

        self._desc_labels: list[ttk.Label] = []
        self._render_ui()
        self.root.bind("<Configure>", self._on_resize)

    def _palette(self) -> dict[str, str]:
        return PALETTES.get(self.theme_var.get(), PALETTES.get("default", {}))

    def _color(self, key: str) -> str:
        return self._palette().get(key, "#0f172a")

    def _apply_theme(self) -> None:
        self.root.configure(bg=self._color("BG"))
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background=self._color("BG"))
        style.configure("Hero.TFrame", background=self._color("PANEL"))
        style.configure("HeroTitle.TLabel", background=self._color("PANEL"), foreground=self._color("TEXT"), font=("Segoe UI", 18, "bold"))
        style.configure("HeroMuted.TLabel", background=self._color("PANEL"), foreground=self._color("MUTED"), font=("Segoe UI", 10))
        style.configure("Badge.TLabel", background=self._color("ACCENT"), foreground=self._color("BG"), padding=(12, 6), font=("Segoe UI", 10, "bold"))
        style.configure("BadgeMuted.TLabel", background=self._color("BORDER"), foreground=self._color("TEXT"), padding=(12, 6), font=("Segoe UI", 10, "bold"))
        style.configure("Card.TFrame", background=self._color("CARD"), borderwidth=0, relief="flat")
        style.configure("CardInner.TFrame", background=self._color("CARD"))
        style.configure("CardHeading.TLabel", background=self._color("CARD"), foreground=self._color("TEXT"), font=("Segoe UI", 14, "bold"))
        style.configure("CardText.TLabel", background=self._color("CARD"), foreground=self._color("MUTED"), wraplength=460, font=("Segoe UI", 10))
        style.configure("Path.TLabel", background=self._color("CARD"), foreground=self._color("MUTED"), font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=self._color("ACCENT"), foreground=self._color("BG"), font=("Segoe UI", 10, "bold"), padding=(10, 4))
        style.configure("DisabledStatus.TLabel", background=self._color("BORDER"), foreground=self._color("TEXT"), font=("Segoe UI", 10, "bold"), padding=(10, 4))
        style.configure(
            "Launch.TButton",
            padding=(12, 8),
            background=self._color("BTN"),
            foreground=self._color("BG"),
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Launch.TButton",
            background=[("active", self._color("ACCENT")), ("disabled", self._color("CARD"))],
            foreground=[("active", self._color("BG")), ("disabled", self._color("MUTED"))],
        )
        style.configure("Separator.TFrame", background=self._color("BG"))
        style.configure("TSeparator", background=self._color("BORDER"))

    def _build_header(self) -> ttk.Frame:
        container = ttk.Frame(self.root, padding=16, style="Hero.TFrame")

        title = ttk.Label(container, text=self._t("launcher.title", "Arcade Hub"), style="HeroTitle.TLabel")
        self.subtitle_label = ttk.Label(
            container,
            text=self._t(
                "launcher.subtitle",
                "Choose a game to launch in its own window. Add new games to the project and they will appear here.",
            ),
            style="HeroMuted.TLabel",
            wraplength=520,
            justify="left",
        )

        title.pack(anchor="w")
        self.subtitle_label.pack(anchor="w", pady=(4, 8))

        ready = sum(1 for g in self.games if g.available)
        total = len(self.games)
        badge_style = "Badge.TLabel" if ready else "BadgeMuted.TLabel"
        badge_text = self._t("launcher.badge", "{ready}/{total} ready to launch", ready=ready, total=total)
        ttk.Label(container, text=badge_text, style=badge_style).pack(anchor="w")

        lang_row = ttk.Frame(container, style="Hero.TFrame")
        lang_row.pack(anchor="w", pady=(10, 0))
        ttk.Label(lang_row, text=self._t("launcher.language", "Language") + ":", style="HeroTitle.TLabel").pack(
            side="left", padx=(0, 8)
        )
        lang_box = ttk.Combobox(
            lang_row,
            textvariable=self.language_var,
            values=[self._lang_display(code) for code in self.available_languages],
            state="readonly",
            width=16,
        )
        lang_box.pack(side="left", padx=(0, 12))
        lang_box.bind("<<ComboboxSelected>>", lambda e: self._on_language_change(lang_box.get()))

        ttk.Label(lang_row, text=self._t("launcher.theme", "Theme") + ":", style="HeroTitle.TLabel").pack(side="left", padx=(0, 8))
        theme_box = ttk.Combobox(
            lang_row,
            textvariable=self.theme_var,
            values=list(PALETTES.keys()),
            state="readonly",
            width=16,
        )
        theme_box.pack(side="left")
        theme_box.bind("<<ComboboxSelected>>", lambda e: self._on_theme_change())

        sound_chk = ttk.Checkbutton(
            lang_row, text=self._t("launcher.sound", "Sound"), variable=self.sound_enabled, command=self._save_settings
        )
        sound_chk.pack(side="left", padx=(12, 0))

        return container

    def _build_game_list(self) -> ttk.Frame:
        list_container = ttk.Frame(self.root, padding=(16, 4), style="App.TFrame")
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)

        canvas = tk.Canvas(list_container, highlightthickness=0, bg=self._color("BG"))
        vbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")

        inner = ttk.Frame(canvas, style="App.TFrame")
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _update_scrollregion(event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _resize_inner(event: tk.Event) -> None:
            canvas.itemconfigure(inner_id, width=event.width)

        inner.bind("<Configure>", _update_scrollregion)
        canvas.bind("<Configure>", _resize_inner)

        for game in self.games:
            self._render_game_card(inner, game)

        # Basic mouse wheel support
        def _on_mousewheel(event: tk.Event) -> None:
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+")

        return list_container

    def _render_game_card(self, parent: ttk.Frame, game: GameEntry) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=0)
        card.pack(fill="x", pady=10)

        stripe = tk.Frame(card, bg=self._color("ACCENT"), width=6)
        stripe.grid(row=0, column=0, rowspan=3, sticky="ns")

        inner = ttk.Frame(card, style="CardInner.TFrame", padding=14)
        inner.grid(row=0, column=1, sticky="nsew")

        heading_text = self._t(game.name_key, game.name) if game.name_key else game.name
        heading = ttk.Label(inner, text=heading_text, style="CardHeading.TLabel")
        heading.grid(row=0, column=0, sticky="w")

        lock_holder = getattr(self, "active_game_holder", None)
        locked_by_other = lock_holder and lock_holder != game.name
        locked_by_self = lock_holder and lock_holder == game.name
        status_style = "Status.TLabel" if game.available and not (locked_by_other or locked_by_self) else "DisabledStatus.TLabel"
        if not game.available:
            status_text = self._t("launcher.status.missing", "Missing files")
        elif locked_by_other:
            status_text = f"In use by {lock_holder}"
        elif locked_by_self:
            status_text = "Already running"
        else:
            status_text = self._t("launcher.status.ready", "Ready to play")
        status = ttk.Label(inner, text=status_text, style=status_style)
        status.grid(row=0, column=1, sticky="e", padx=(10, 0))

        desc_text = self._t(game.desc_key, game.description) if game.desc_key else game.description
        desc = ttk.Label(inner, text=desc_text, style="CardText.TLabel", justify="left")
        desc.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 6))
        desc.bind(
            "<Configure>",
            lambda e, lbl=desc: lbl.configure(wraplength=max(240, e.width - 20)),
        )
        self._desc_labels.append(desc)

        meta = ttk.Frame(inner, style="CardInner.TFrame")
        meta.grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Label(meta, text=self._display_path(game.script_path), style="Path.TLabel").pack(side="left")

        launch_btn = ttk.Button(
            inner,
            text=self._t("launcher.launch", "Launch"),
            style="Launch.TButton",
            command=lambda g=game: self._launch_game(g),
            state=("normal" if game.available and not (locked_by_other or locked_by_self) else "disabled"),
            width=14,
        )
        launch_btn.grid(row=0, column=2, rowspan=3, padx=(16, 0))

        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=0)
        inner.columnconfigure(2, weight=0)
        card.columnconfigure(0, weight=0)
        card.columnconfigure(1, weight=1)

    def _discover_languages(self) -> list[str]:
        locales_dir = Path(__file__).resolve().parent / "shared" / "locales"
        codes = [p.stem for p in locales_dir.glob("*.json")]
        codes = sorted(set(codes))
        return codes or ["en"]

    def _display_path(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.project_root))
        except Exception:
            return path.name

    def _lang_display(self, code: str) -> str:
        return self.language_names.get(code, code)

    def _on_language_change(self, display_value: str) -> None:
        code = next((c for c, lbl in self.language_names.items() if lbl == display_value), display_value)
        self.language = code if code in self.available_languages else "en"
        self.language_var.set(self._lang_display(self.language))
        self._load_translations(self.language)
        self._render_ui()
        self._save_settings()

    def _on_theme_change(self) -> None:
        self._render_ui()
        self._save_settings()

    def _load_translations(self, lang: str) -> None:
        """Load translations for the launcher UI."""
        self.translations = {}
        fallback_file = LOCALES_DIR / "en.json"
        lang_file = LOCALES_DIR / f"{lang}.json"
        for path in (fallback_file, lang_file):
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.translations.update(data)
            except Exception:
                continue

    def _t(self, key: str, default: str, **kwargs) -> str:
        text = self.translations.get(key, default)
        try:
            return text.format(**kwargs)
        except Exception:
            return text

    def _render_ui(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()
        self.root.title(self._t("launcher.window_title", "Game Launcher"))
        self.active_game_holder = self._active_lock_holder()
        self.palette = self._palette()
        self._apply_theme()
        self._desc_labels = []
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=0)
        self.root.rowconfigure(2, weight=1)
        header = self._build_header()
        header.grid(row=0, column=0, sticky="ew")
        ttk.Separator(self.root).grid(row=1, column=0, sticky="ew")
        games = self._build_game_list()
        games.grid(row=2, column=0, sticky="nsew")

    def _save_settings(self) -> None:
        payload = {"language": self.language, "theme": self.theme_var.get(), "sound": self.sound_enabled.get()}
        settings.save_settings(SETTINGS_FILE, payload)

    def _active_lock_holder(self) -> Optional[str]:
        """
        Check who holds the active-game lock without blocking launcher startup.

        The launcher itself never locks this; games own it. If we can acquire
        it non-blocking, it is free; release immediately and report None.
        """
        try:
            if single_instance.try_acquire_lock(ACTIVE_GAME_LOCK, "launcher-probe"):
                try:
                    single_instance.release_lock(ACTIVE_GAME_LOCK)
                except PermissionError:
                    pass
                return None
            return single_instance.lock_holder(ACTIVE_GAME_LOCK)
        except PermissionError:
            return single_instance.lock_holder(ACTIVE_GAME_LOCK)

    def _on_resize(self, event: tk.Event) -> None:
        if getattr(self, "subtitle_label", None):
            wrap = max(320, event.width - 180)
            self.subtitle_label.configure(wraplength=wrap)
        for lbl in getattr(self, "_desc_labels", []):
            lbl.configure(wraplength=max(240, lbl.winfo_width() - 20))

    def _launch_game(self, game: GameEntry) -> None:
        # Prevent launching if another game holds the shared lock.
        if getattr(self, "active_game_holder", None):
            holder = self.active_game_holder
            if holder != game.name:
                messagebox.showwarning(
                    self._t("launcher.launch_blocked.title", "Another game is running"),
                    self._t(
                        "launcher.launch_blocked.body",
                        "{holder} is already running. Close it before starting {name}.",
                        holder=holder,
                        name=game.name,
                    ),
                )
                return
            else:
                messagebox.showinfo(
                    self._t("launcher.launch_blocked.self.title", "Already running"),
                    self._t(
                        "launcher.launch_blocked.self.body",
                        "{name} appears to be running already.",
                        name=game.name,
                    ),
                )
                return
        if not game.available:
            messagebox.showinfo(
                self._t("launcher.coming_soon.title", "Coming soon"),
                self._t(
                    "launcher.coming_soon.body",
                    "The {name} files are not present yet. Add {path} to enable launching this game.",
                    name=game.name,
                    path=game.script_path,
                ),
            )
            return

        try:
            env = os.environ.copy()
            env["GAME_LANGUAGE"] = self.language or "en"
            if not self.sound_enabled.get():
                env["GAME_SOUND"] = "0"
            subprocess.Popen(game.command, cwd=game.script_path.parent, env=env)
            self._play_click()
        except FileNotFoundError:
            messagebox.showerror(
                self._t("launcher.launch_failed.title", "Launch failed"),
                self._t("launcher.launch_failed.missing", "Unable to find {path}.", path=game.script_path),
            )
        except Exception as exc:  # pragma: no cover - user-facing safeguard
            messagebox.showerror(
                self._t("launcher.launch_failed.title", "Launch failed"),
                self._t("launcher.launch_failed.generic", "Could not start {name}: {error}", name=game.name, error=exc),
            )

    def _play_click(self) -> None:
        if not self.sound_enabled.get():
            return
        self.click_player.play_click()

    def _load_games(self) -> list[GameEntry]:
        return [
            GameEntry(
                name="Tic-Tac-Toe",
                description="Play the classic 3x3 grid with AI personas, themes, and scoreboard tracking.",
                name_key="launcher.game.tictactoe.name",
                desc_key="launcher.game.tictactoe.desc",
                script_path=self.project_root / "tic-tac-toe" / "gui.py",
            ),
            GameEntry(
                name="Blackjack",
                description="Beat the dealer to 21. Drop your Blackjack GUI into a blackjack/gui.py to enable it.",
                name_key="launcher.game.blackjack.name",
                desc_key="launcher.game.blackjack.desc",
                script_path=self.project_root / "blackjack" / "gui.py",
            ),
            GameEntry(
                name="Go Fish",
                description="Collect matching sets in a laid-back card game. Add your Go Fish GUI at gofish/gui.py.",
                name_key="launcher.game.gofish.name",
                desc_key="launcher.game.gofish.desc",
                script_path=self.project_root / "gofish" / "gui.py",
            ),
            GameEntry(
                name="Yahtzee",
                description="Roll five dice and fill your scorecard with the best categories you can.",
                name_key="launcher.game.yahtzee.name",
                desc_key="launcher.game.yahtzee.desc",
                script_path=self.project_root / "yahtzee" / "gui.py",
            ),
            GameEntry(
                name="Minesweeper",
                description="Clear the board without hitting a mine. Classic puzzle with a safe first click.",
                name_key="launcher.game.minesweeper.name",
                desc_key="launcher.game.minesweeper.desc",
                script_path=self.project_root / "minesweeper" / "gui.py",
            ),
        ]


def main() -> None:
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        message = (
            "Could not start the launcher because Tk/Tcl is unavailable in this Python build.\n\n"
            "If you're on Windows with multiple Python versions (e.g., 3.12 and a 3.14 preview), "
            "try running with a version that bundles Tk:\n"
            "    py -3.12 launcher.py\n\n"
            f"Details: {exc}"
        )
        print(message, file=sys.stderr)
        return
    GameLauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
