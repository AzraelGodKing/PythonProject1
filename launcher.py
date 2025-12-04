"""
A lightweight Tkinter-based launcher for the project's mini-games.
The window lists available games and spins up their GUI entry points
as separate Python processes so players can jump in from a single hub.
"""

from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Iterable, List, Optional

from shared.options import PALETTES


@dataclass
class GameEntry:
    """Describe a playable game that can be launched from the hub."""

    name: str
    description: str
    script_path: Path
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
        self.root.title("Game Launcher")
        self.root.geometry("700x540")
        self.root.minsize(640, 500)

        self.games = self._load_games()
        self.palette = PALETTES.get("default", {})

        self._apply_theme()
        self._build_header()
        self._build_game_list()

    def _color(self, key: str) -> str:
        return self.palette.get(key, "#0f172a")

    def _apply_theme(self) -> None:
        self.root.configure(bg=self._color("BG"))
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background=self._color("BG"))
        style.configure("Hero.TFrame", background=self._color("PANEL"))
        style.configure("HeroTitle.TLabel", background=self._color("PANEL"), foreground=self._color("TEXT"), font=("Segoe UI", 16, "bold"))
        style.configure("HeroMuted.TLabel", background=self._color("PANEL"), foreground=self._color("MUTED"), font=("Segoe UI", 10))
        style.configure("Card.TFrame", background=self._color("CARD"), borderwidth=1, relief="solid")
        style.configure("CardHeading.TLabel", background=self._color("CARD"), foreground=self._color("TEXT"), font=("Segoe UI", 13, "bold"))
        style.configure("CardText.TLabel", background=self._color("CARD"), foreground=self._color("MUTED"), wraplength=420)
        style.configure("Status.TLabel", background=self._color("CARD"), foreground=self._color("ACCENT"), font=("Segoe UI", 10, "bold"), padding=(8, 2))
        style.configure("DisabledStatus.TLabel", background=self._color("CARD"), foreground=self._color("MUTED"), font=("Segoe UI", 10, "bold"), padding=(8, 2))
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
            background=[("active", self._color("ACCENT"))],
            foreground=[("active", self._color("BG"))],
        )
        style.configure("Separator.TFrame", background=self._color("BG"))
        style.configure("Badge.TLabel", background=self._color("ACCENT"), foreground=self._color("BG"), padding=(10, 4), font=("Segoe UI", 9, "bold"))
        style.configure("BadgeMuted.TLabel", background=self._color("BORDER"), foreground=self._color("TEXT"), padding=(10, 4), font=("Segoe UI", 9, "bold"))
        style.configure("TSeparator", background=self._color("BORDER"))

    def _build_header(self) -> None:
        container = ttk.Frame(self.root, padding=16, style="Hero.TFrame")
        container.pack(fill="x")

        title = ttk.Label(container, text="Arcade Hub", style="HeroTitle.TLabel")
        subtitle = ttk.Label(
            container,
            text="Choose a game to launch in its own window. Add new games to the project and they will appear here.",
            style="HeroMuted.TLabel",
            wraplength=520,
            justify="left",
        )

        title.pack(anchor="w")
        subtitle.pack(anchor="w", pady=(4, 8))

        ready = sum(1 for g in self.games if g.available)
        total = len(self.games)
        badge_style = "Badge.TLabel" if ready else "BadgeMuted.TLabel"
        ttk.Label(container, text=f"{ready}/{total} ready to launch", style=badge_style).pack(anchor="w")

        ttk.Separator(self.root).pack(fill="x")

    def _build_game_list(self) -> None:
        list_container = ttk.Frame(self.root, padding=(16, 4), style="App.TFrame")
        list_container.pack(fill="both", expand=True)

        for game in self.games:
            self._render_game_card(list_container, game)

    def _render_game_card(self, parent: ttk.Frame, game: GameEntry) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=14)
        card.pack(fill="x", pady=8)

        heading = ttk.Label(card, text=game.name, style="CardHeading.TLabel")
        heading.grid(row=0, column=0, sticky="w")

        status_style = "Status.TLabel" if game.available else "DisabledStatus.TLabel"
        status_text = "Ready to play" if game.available else "Missing files"
        status = ttk.Label(card, text=status_text, style=status_style)
        status.grid(row=0, column=1, sticky="e", padx=(6, 0))

        desc = ttk.Label(card, text=game.description, style="CardText.TLabel", justify="left")
        desc.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 8))

        path_label = ttk.Label(card, text=str(game.script_path), style="CardText.TLabel", justify="left")
        path_label.grid(row=2, column=0, columnspan=2, sticky="w")

        launch_btn = ttk.Button(
            card,
            text="Launch",
            style="Launch.TButton",
            command=lambda g=game: self._launch_game(g),
            state=("normal" if game.available else "disabled"),
            width=14,
        )
        launch_btn.grid(row=0, column=2, rowspan=3, padx=(12, 0))

        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=0)
        card.columnconfigure(2, weight=0)

    def _launch_game(self, game: GameEntry) -> None:
        if not game.available:
            messagebox.showinfo(
                "Coming soon",
                f"The {game.name} files are not present yet. Add {game.script_path} to enable launching this game.",
            )
            return

        try:
            subprocess.Popen(game.command, cwd=game.script_path.parent)
        except FileNotFoundError:
            messagebox.showerror("Launch failed", f"Unable to find {game.script_path}.")
        except Exception as exc:  # pragma: no cover - user-facing safeguard
            messagebox.showerror("Launch failed", f"Could not start {game.name}: {exc}")

    def _load_games(self) -> list[GameEntry]:
        project_root = Path(__file__).resolve().parent
        return [
            GameEntry(
                name="Tic-Tac-Toe",
                description="Play the classic 3x3 grid with AI personas, themes, and scoreboard tracking.",
                script_path=project_root / "tic-tac-toe" / "gui.py",
            ),
            GameEntry(
                name="Blackjack",
                description="Beat the dealer to 21. Drop your Blackjack GUI into a blackjack/gui.py to enable it.",
                script_path=project_root / "blackjack" / "gui.py",
            ),
            GameEntry(
                name="Go Fish",
                description="Collect matching sets in a laid-back card game. Add your Go Fish GUI at gofish/gui.py.",
                script_path=project_root / "gofish" / "gui.py",
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
