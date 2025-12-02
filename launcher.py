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

        self._apply_theme()
        self._build_header()
        self._build_game_list()

    def _apply_theme(self) -> None:
        self.root.configure(bg="#0f172a")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Card.TFrame", background="#1e293b")
        style.configure("CardHeading.TLabel", background="#1e293b", foreground="#e2e8f0", font=("Segoe UI", 12, "bold"))
        style.configure("CardText.TLabel", background="#1e293b", foreground="#cbd5e1", wraplength=360)
        style.configure("Status.TLabel", background="#1e293b", foreground="#38bdf8", font=("Segoe UI", 10, "bold"))
        style.configure("DisabledStatus.TLabel", background="#1e293b", foreground="#94a3b8", font=("Segoe UI", 10, "bold"))
        style.configure("Launch.TButton", padding=(10, 6))

    def _build_header(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="x")

        title = ttk.Label(container, text="Arcade Hub", font=("Segoe UI", 16, "bold"), foreground="#e2e8f0", background="#0f172a")
        subtitle = ttk.Label(
            container,
            text="Choose a game to launch in its own window. Add new games to the project and they will appear here.",
            font=("Segoe UI", 10),
            foreground="#cbd5e1",
            background="#0f172a",
            wraplength=480,
            justify="left",
        )

        title.pack(anchor="w")
        subtitle.pack(anchor="w", pady=(4, 0))

    def _build_game_list(self) -> None:
        list_container = ttk.Frame(self.root, padding=(16, 4))
        list_container.pack(fill="both", expand=True)

        for game in self.games:
            self._render_game_card(list_container, game)

    def _render_game_card(self, parent: ttk.Frame, game: GameEntry) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=14)
        card.pack(fill="x", pady=8)

        heading = ttk.Label(card, text=game.name, style="CardHeading.TLabel")
        heading.grid(row=0, column=0, sticky="w")

        status_style = "Status.TLabel" if game.available else "DisabledStatus.TLabel"
        status_text = "Ready" if game.available else "Not installed yet"
        status = ttk.Label(card, text=status_text, style=status_style)
        status.grid(row=0, column=1, sticky="e")

        desc = ttk.Label(card, text=game.description, style="CardText.TLabel", justify="left")
        desc.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 10))

        launch_btn = ttk.Button(
            card,
            text="Launch",
            style="Launch.TButton",
            command=lambda g=game: self._launch_game(g),
            state=("normal" if game.available else "disabled"),
            width=14,
        )
        launch_btn.grid(row=0, column=2, rowspan=2, padx=(12, 0))

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
                script_path=project_root / "a tic-tac-toe game" / "gui.py",
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
