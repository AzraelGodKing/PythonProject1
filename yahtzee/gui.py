"""A minimal Yahtzee GUI with scoring categories and persistent best score."""

from __future__ import annotations

import os
import random
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.options import PALETTES
from shared import settings, single_instance

LOCK_DIR = PROJECT_ROOT / "data" / "locks"
LOCK_FILE = LOCK_DIR / "yahtzee.lock"
ACTIVE_GAME_LOCK = LOCK_DIR / "active_game.lock"
SETTINGS_FILE = PROJECT_ROOT / "data" / "yahtzee_settings.json"

CATEGORIES = [
    "Aces",
    "Twos",
    "Threes",
    "Fours",
    "Fives",
    "Sixes",
    "Three of a Kind",
    "Four of a Kind",
    "Full House",
    "Small Straight",
    "Large Straight",
    "Yahtzee",
    "Chance",
]


def score_category(category: str, dice: List[int]) -> int:
    counts = {i: dice.count(i) for i in range(1, 7)}
    total = sum(dice)
    if category == "Aces":
        return counts.get(1, 0) * 1
    if category == "Twos":
        return counts.get(2, 0) * 2
    if category == "Threes":
        return counts.get(3, 0) * 3
    if category == "Fours":
        return counts.get(4, 0) * 4
    if category == "Fives":
        return counts.get(5, 0) * 5
    if category == "Sixes":
        return counts.get(6, 0) * 6
    if category == "Three of a Kind":
        return total if any(v >= 3 for v in counts.values()) else 0
    if category == "Four of a Kind":
        return total if any(v >= 4 for v in counts.values()) else 0
    if category == "Full House":
        return 25 if sorted(counts.values(), reverse=True)[:2] == [3, 2] else 0
    if category == "Small Straight":
        straights = [{1, 2, 3, 4}, {2, 3, 4, 5}, {3, 4, 5, 6}]
        return 30 if any(s.issubset(set(dice)) for s in straights) else 0
    if category == "Large Straight":
        return 40 if set(dice) in ({1, 2, 3, 4, 5}, {2, 3, 4, 5, 6}) else 0
    if category == "Yahtzee":
        return 50 if any(v == 5 for v in counts.values()) else 0
    if category == "Chance":
        return total
    return 0


class YahtzeeGame:
    def __init__(self) -> None:
        self.dice: List[int] = [1] * 5
        self.held: List[bool] = [False] * 5
        self.rolls_left = 3
        self.scores: Dict[str, Optional[int]] = {cat: None for cat in CATEGORIES}
        self.total = 0
        self.roll()

    def roll(self) -> None:
        if self.rolls_left <= 0:
            return
        for i in range(5):
            if not self.held[i]:
                self.dice[i] = random.randint(1, 6)
        self.rolls_left -= 1

    def toggle_hold(self, idx: int) -> None:
        if self.rolls_left == 3:  # must roll once before holding
            return
        self.held[idx] = not self.held[idx]

    def potential_score(self, category: str) -> int:
        return score_category(category, self.dice)

    def score_category(self, category: str) -> None:
        if self.scores[category] is not None:
            return
        self.scores[category] = self.potential_score(category)
        self.total = sum(v for v in self.scores.values() if v is not None)
        self.dice = [1] * 5
        self.held = [False] * 5
        self.rolls_left = 3
        self.roll()

    def all_scored(self) -> bool:
        return all(v is not None for v in self.scores.values())


class YahtzeeGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Yahtzee")
        self.root.geometry("900x640")
        self.root.minsize(820, 600)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(4, weight=1)

        defaults = {"theme": "default", "best_score": 0}
        self.settings = settings.load_settings(Path(SETTINGS_FILE), defaults)
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "default"))
        self.best_score = int(self.settings.get("best_score", 0))
        self.language = os.environ.get("GAME_LANGUAGE", "en")
        self.translations: Dict[str, str] = {}
        self._load_translations(self.language)

        self.game = YahtzeeGame()
        self.dice_buttons: List[tk.Button] = []
        self.score_buttons: Dict[str, ttk.Button] = {}
        self.status_var = tk.StringVar()
        self.total_var = tk.StringVar()
        self.best_var = tk.StringVar()
        self._rolling = False
        self._build_ui()
        self._refresh()
        self.root.bind("<Configure>", self._on_resize)

    def _build_ui(self) -> None:
        self._apply_theme()
        menubar = tk.Menu(self.root)
        menubar.add_command(label="Options", command=self._show_options)
        self.root.config(menu=menubar)

        header = ttk.Label(self.root, text="Yahtzee", style="Title.TLabel")
        header.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        self.status_label = ttk.Label(self.root, textvariable=self.status_var, style="Subtitle.TLabel", wraplength=760, justify="left")
        self.status_label.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))

        dice_frame = ttk.Frame(self.root, padding=10)
        dice_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        dice_frame.columnconfigure(tuple(range(5)), weight=1)
        for i in range(5):
            btn = tk.Button(
                dice_frame,
                text="1",
                width=6,
                height=3,
                command=lambda idx=i: self._toggle_hold(idx),
                relief="raised",
                bg="#1f2937",
                fg="#f8fafc",
            )
            btn.grid(row=0, column=i, padx=6, sticky="ew")
            self.dice_buttons.append(btn)

        controls = ttk.Frame(self.root, padding=10)
        controls.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))
        controls.columnconfigure(0, weight=1)
        ttk.Button(controls, text="Roll", command=self._roll).pack(side="left", padx=4)
        ttk.Button(controls, text="New Game", command=self._new_game).pack(side="left", padx=4)
        ttk.Label(controls, textvariable=self.total_var, style="Title.TLabel").pack(side="right", padx=6)
        ttk.Label(controls, textvariable=self.best_var, style="Subtitle.TLabel").pack(side="right", padx=6)

        scores_frame = ttk.Frame(self.root, padding=10)
        scores_frame.grid(row=4, column=0, sticky="nsew", padx=12, pady=(0, 12))
        for idx, cat in enumerate(CATEGORIES):
            btn = ttk.Button(
                scores_frame,
                text=cat,
                command=lambda c=cat: self._score_category(c),
                style="Score.TButton",
                width=18,
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=4, pady=2)
            lbl = ttk.Label(scores_frame, text="", style="CardText.TLabel")
            lbl.grid(row=idx, column=1, sticky="w", padx=4)
            self.score_buttons[cat] = btn
        scores_frame.columnconfigure(1, weight=1)

    def _apply_theme(self) -> None:
        palette = PALETTES.get(self.theme_var.get(), PALETTES["default"])
        bg = palette.get("BG", "#0c1222")
        panel = palette.get("PANEL", "#142039")
        text = palette.get("TEXT", "#f8fafc")
        muted = palette.get("MUTED", "#cbd5e1")
        accent = palette.get("ACCENT", "#2563eb")
        btn_color = palette.get("BTN", accent)
        self.root.configure(bg=bg)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=bg)
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), background=bg, foreground=text)
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), background=bg, foreground=muted)
        style.configure("CardText.TLabel", background=bg, foreground=muted)
        style.configure("Score.TButton", padding=(8, 6), background=btn_color, foreground=bg)
        style.map("Score.TButton", background=[("active", accent), ("disabled", panel)], foreground=[("active", bg), ("disabled", muted)])
        self._palette_cache = palette

    def _on_resize(self, event: tk.Event) -> None:
        if getattr(self, "status_label", None):
            self.status_label.configure(wraplength=max(360, event.width - 160))

    def _roll(self) -> None:
        if self._rolling or self.game.rolls_left <= 0:
            return
        self._rolling = True
        self._animate_roll(steps=8)

    def _animate_roll(self, steps: int) -> None:
        if steps <= 0:
            self.game.roll()
            self._rolling = False
            self._refresh()
            return
        temp = [random.randint(1, 6) if not self.game.held[i] else self.game.dice[i] for i in range(5)]
        for i, btn in enumerate(self.dice_buttons):
            btn.config(text=str(temp[i]))
        # schedule next animation frame
        self.root.after(60, lambda: self._animate_roll(steps - 1))

    def _toggle_hold(self, idx: int) -> None:
        self.game.toggle_hold(idx)
        self._refresh()

    def _score_category(self, category: str) -> None:
        if self.game.scores[category] is not None:
            return
        self.game.score_category(category)
        if self.game.all_scored():
            if self.game.total > self.best_score:
                self.best_score = self.game.total
            self._save_settings()
            messagebox.showinfo("Game over", f"Final score: {self.game.total}\nBest: {self.best_score}")
        self._refresh()

    def _new_game(self) -> None:
        self.game = YahtzeeGame()
        self._refresh()

    def _refresh(self) -> None:
        dice_colors = ("#0ea5e9", "#38bdf8")
        for i, btn in enumerate(self.dice_buttons):
            btn.config(text=str(self.game.dice[i]))
            if self.game.held[i]:
                btn.config(bg=dice_colors[0], relief="sunken")
            else:
                btn.config(bg=dice_colors[1], relief="raised")
        for cat, btn in self.score_buttons.items():
            used = self.game.scores[cat] is not None
            btn.state(["disabled"] if used else ["!disabled"])
            score_text = self.game.scores[cat]
            potential = self.game.potential_score(cat)
            label = btn.master.grid_slaves(row=list(CATEGORIES).index(cat), column=1)[0]
            label.config(text=f"Score: {score_text if score_text is not None else potential}")
        self.status_var.set(f"Rolls left: {self.game.rolls_left}")
        self.total_var.set(f"Total: {self.game.total}")
        self.best_var.set(f"Best: {self.best_score}")

    def _show_options(self) -> None:
        popup = tk.Toplevel(self.root)
        popup.title(self._t("yahtzee.options.title", "Options"))
        popup.configure(bg=self._palette_cache.get("BG", "#0c1222"))
        ttk.Label(popup, text="Theme", style="Title.TLabel").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        theme_box = ttk.Combobox(
            popup,
            textvariable=self.theme_var,
            values=list(PALETTES.keys()),
            state="readonly",
            width=18,
        )
        theme_box.grid(row=1, column=0, sticky="ew", padx=12)
        theme_box.bind("<<ComboboxSelected>>", lambda e: self._on_theme_change())
        ttk.Button(popup, text=self._t("yahtzee.options.rules", "Rules"), command=self._show_rules).grid(row=2, column=0, sticky="w", padx=12, pady=(10, 0))
        ttk.Button(popup, text=self._t("yahtzee.options.close", "Close"), command=popup.destroy).grid(row=3, column=0, sticky="e", padx=12, pady=12)
        popup.columnconfigure(0, weight=1)

    def _on_theme_change(self) -> None:
        self._apply_theme()
        self._save_settings()
        self._refresh()

    def _show_rules(self) -> None:
        rules = self._t(
            "yahtzee.rules.body",
            "Yahtzee rules:\n"
            "- Up to 3 rolls per turn. You may hold dice between rolls.\n"
            "- Score each category once. Upper section scores sum of matching faces.\n"
            "- Three/Four of a Kind: sum of all dice (must have 3/4 same faces).\n"
            "- Full House: 25 points for a 3-of-a-kind plus a pair.\n"
            "- Small Straight: 30 points for a sequence of 4 (e.g., 1-2-3-4).\n"
            "- Large Straight: 40 points for a sequence of 5 (1-2-3-4-5 or 2-3-4-5-6).\n"
            "- Yahtzee: 50 points for five of a kind.\n"
            "- Chance: sum of all dice, no restrictions.",
        )
        messagebox.showinfo(self._t("yahtzee.rules.title", "Yahtzee Rules"), rules)

    def _save_settings(self) -> None:
        settings.save_settings(
            Path(SETTINGS_FILE),
            {"theme": self.theme_var.get(), "best_score": self.best_score},
        )

    def _load_translations(self, lang: str) -> None:
        """Load translations for Yahtzee UI."""
        import json

        self.translations = {}
        base_dir = Path(__file__).resolve().parent.parent / "shared" / "locales"
        fallback = base_dir / "en.json"
        lang_file = base_dir / f"{lang}.json"
        for path in (fallback, lang_file):
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self.translations.update(data)
            except Exception:
                continue

    def _t(self, key: str, default: str) -> str:
        return self.translations.get(key, default)


def _notify_already_running() -> None:
    message = "Yahtzee is already running. Close the other window before starting a new session."
    try:
        tmp = tk.Tk()
        tmp.withdraw()
        messagebox.showinfo("Already running", message)
        tmp.destroy()
    except tk.TclError:
        print(message, file=sys.stderr)


def _notify_other_game_running(holder: Optional[str]) -> None:
    name = holder or "another game"
    message = f"{name} is already running. Close it before starting Yahtzee."
    try:
        tmp = tk.Tk()
        tmp.withdraw()
        messagebox.showinfo("Another game is running", message)
        tmp.destroy()
    except tk.TclError:
        print(message, file=sys.stderr)


def main() -> None:
    if not single_instance.try_acquire_lock(ACTIVE_GAME_LOCK, "Yahtzee"):
        _notify_other_game_running(single_instance.lock_holder(ACTIVE_GAME_LOCK))
        return
    if not single_instance.try_acquire_lock(LOCK_FILE, "Yahtzee"):
        single_instance.release_lock(ACTIVE_GAME_LOCK)
        _notify_already_running()
        return
    root = tk.Tk()
    YahtzeeGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
