"""A minimal Go Fish GUI using Tkinter and the shared deck helpers."""

from __future__ import annotations

import argparse
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from collections import Counter
import random

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.deck import Deck, Card
from shared.options import PALETTES
from shared import single_instance, settings
from shared.theme_manager import ThemedApp

CARD_BG = "#f8fafc"
CARD_BORDER = "#cbd5e1"
CARD_TEXT = "#0f172a"
ACCENT = "#2563eb"
SUIT_SYMBOLS = {"Hearts": "♥", "Diamonds": "♦", "Clubs": "♣", "Spades": "♠"}
SUIT_COLORS = {"Hearts": "#dc2626", "Diamonds": "#dc2626", "Clubs": "#0f172a", "Spades": "#0f172a"}

SETTINGS_FILE = "gofish_settings.json"
LOCK_DIR = PROJECT_ROOT / "data" / "locks"
LOCK_FILE = LOCK_DIR / "gofish.lock"
ACTIVE_GAME_LOCK = LOCK_DIR / "active_game.lock"
SCOREBOARD_FILE = PROJECT_ROOT / "data" / "gofish_scoreboard.json"


class GoFishGame:
    def __init__(self) -> None:
        self.deck = Deck(include_jokers=False, num_decks=1)
        self.deck.shuffle()
        self.player_hand: list[Card] = []
        self.ai_hand: list[Card] = []
        self.player_books = 0
        self.ai_books = 0
        self.turn = "player"
        self.log: list[str] = []
        self.player_memory: set[str] = set()
        self._deal_initial()

    def _deal_initial(self) -> None:
        self.player_hand = self.deck.draw(7)
        self.ai_hand = self.deck.draw(7)
        self._collect_books(self.player_hand, owner="player")
        self._collect_books(self.ai_hand, owner="ai")

    @staticmethod
    def _collect_books(hand: list[Card], *, owner: str) -> int:
        books = 0
        counts = Counter(c.rank for c in hand)
        for rank, count in counts.items():
            pairs = count // 4
            if pairs:
                books += pairs
                hand[:] = [c for c in hand if c.rank != rank]
        return books

    def _draw_if_needed(self, hand: list[Card]) -> None:
        if not hand and self.deck.remaining() > 0:
            try:
                hand.extend(self.deck.draw(1))
            except IndexError:
                pass

    def available_ranks(self, hand: list[Card]) -> list[str]:
        return sorted({c.rank for c in hand})

    def player_turn(self, rank: str) -> None:
        if self.turn != "player" or rank not in self.available_ranks(self.player_hand):
            return
        self.player_memory.add(rank)
        matches = [c for c in self.ai_hand if c.rank == rank]
        if matches:
            self.ai_hand = [c for c in self.ai_hand if c.rank != rank]
            self.player_hand.extend(matches)
            self.log.append(f"You took {len(matches)} card(s) of {rank}.")
        else:
            self.log.append(f"No {rank}. Go fish!")
            self._go_fish(self.player_hand)
            self.turn = "ai"
        self.player_books += self._collect_books(self.player_hand, owner="player")
        self._draw_if_needed(self.player_hand)

    def ai_turn(self) -> None:
        if self.turn != "ai":
            return
        if not self.ai_hand:
            self._draw_if_needed(self.ai_hand)
            # If AI still has no cards (and deck is empty), hand off turn to player or end.
            if not self.ai_hand:
                self.log.append("AI has no cards to ask with.")
                if self.player_hand:
                    self.turn = "player"
                return
        memory_choices = [r for r in self.available_ranks(self.ai_hand) if r in self.player_memory]
        if memory_choices:
            rank = random.choice(memory_choices)
        else:
            rank = random.choice(self.available_ranks(self.ai_hand))
        matches = [c for c in self.player_hand if c.rank == rank]
        if matches:
            self.player_hand = [c for c in self.player_hand if c.rank != rank]
            self.ai_hand.extend(matches)
            self.log.append(f"AI took your {len(matches)} card(s) of {rank}.")
        else:
            self.log.append(f"AI asked for {rank}. No luck.")
            self._go_fish(self.ai_hand)
            self.turn = "player"
        # If AI successfully grabbed, remember it; if not, drop from memory to avoid loops.
        if matches:
            self.player_memory.add(rank)
        else:
            self.player_memory.discard(rank)
        self.ai_books += self._collect_books(self.ai_hand, owner="ai")
        self._draw_if_needed(self.ai_hand)

    def _go_fish(self, hand: list[Card]) -> None:
        try:
            hand.extend(self.deck.draw(1))
        except IndexError:
            pass

    def game_over(self) -> bool:
        if self.deck.remaining() == 0 and not self.player_hand and not self.ai_hand:
            return True
        return False

    def winner(self) -> str:
        if self.player_books > self.ai_books:
            return "player"
        if self.ai_books > self.player_books:
            return "ai"
        return "draw"


class GoFishGUI(ThemedApp):
    def __init__(self, root: tk.Tk, *, debug: bool = False, headless: bool = False) -> None:
        self.root = root
        self.root.title("Go Fish")
        self.root.geometry("780x560")
        self.root.minsize(640, 480)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.headless = headless
        if headless:
            self.root.withdraw()

        self.settings_path = PROJECT_ROOT / "data" / SETTINGS_FILE
        self.scoreboard_path = SCOREBOARD_FILE
        self.theme_var = tk.StringVar(value="default")
        self._load_settings()

        # Initialize ThemedApp parent class
        super().__init__(root, self.theme_var, self.theme_var.get())

        self.game = GoFishGame()

        self.status_var = tk.StringVar()
        self.ai_count_var = tk.StringVar()
        self.books_var = tk.StringVar()
        self.debug_info_var = tk.StringVar()
        self.scoreboard_var = tk.StringVar()
        self.log_text: tk.Text | None = None

        self.hand_frame: ttk.Frame | None = None
        self.debug_enabled = debug
        self._ai_pending = False
        self.scoreboard = self._load_scoreboard()
        self._build_ui()
        self._refresh()
        self.root.bind("<Configure>", self._on_resize)

    def _customize_styles(self) -> None:
        """Go Fish-specific style customizations."""
        # Get current theme colors
        bg = self._color("BG")
        panel = self._color("PANEL")
        text = self._color("TEXT")
        muted = self._color("MUTED")
        btn = self._color("BTN")
        border = self._color("BORDER")
        accent = self._color("ACCENT")

        # Configure Go Fish-specific ttk styles
        self.style.theme_use("clam")
        self.style.configure("TLabel", background=bg, foreground=text)
        self.style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), background=bg, foreground=text)
        self.style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground=muted, background=bg)
        self.style.configure("Card.TFrame", background=panel, relief="solid", borderwidth=1)
        self.style.configure("TFrame", background=bg)
        self.style.configure("TLabelframe", background=panel, foreground=text)
        self.style.configure("TLabelframe.Label", background=panel, foreground=text, font=("Segoe UI", 10, "bold"))
        self.style.configure("TButton", background=btn, foreground=bg)
        self.style.map("TButton", background=[("active", accent)], foreground=[("active", bg)])

        # Remember palette pieces for card rendering
        self._palette_colors = {
            "bg": bg,
            "panel": panel,
            "text": text,
            "muted": muted,
            "btn": btn,
            "border": border,
            "accent": accent,
        }

    def _build_ui(self) -> None:
        self._apply_theme()

        menubar = tk.Menu(self.root)
        menubar.add_command(label="Scores", command=self._show_scores)
        menubar.add_command(label="Options", command=self._show_options)
        self.root.config(menu=menubar)

        container = ttk.Frame(self.root, padding=12)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=3)
        container.columnconfigure(1, weight=2)
        container.rowconfigure(2, weight=1)
        container.rowconfigure(4, weight=1)

        header_row = ttk.Frame(container)
        header_row.grid(row=0, column=0, columnspan=2, sticky="ew")
        header_row.columnconfigure(0, weight=1)
        header = ttk.Label(header_row, text="Go Fish", style="Title.TLabel")
        header.grid(row=0, column=0, sticky="w")

        self.status_label = ttk.Label(container, textvariable=self.status_var, style="Subtitle.TLabel", wraplength=520, justify="left")
        self.status_label.grid(row=1, column=0, sticky="w", pady=(2, 10))

        hand_frame = ttk.LabelFrame(container, text="Your hand", padding=10)
        hand_frame.grid(row=2, column=0, sticky="nsew")
        hand_frame.columnconfigure(tuple(range(6)), weight=1)
        self.hand_frame = hand_frame

        controls = ttk.Frame(container, padding=10)
        controls.grid(row=3, column=0, sticky="w", pady=(10, 0))
        ttk.Label(controls, text="Click a card to ask for that rank.").pack(side="left", padx=(0, 10))
        ttk.Button(controls, text="New Game", command=self._new_game).pack(side="left", padx=(0, 0))

        info_frame = ttk.LabelFrame(container, text="Game info", padding=10)
        info_frame.grid(row=2, column=1, rowspan=2, sticky="nsew", padx=(10, 0))
        ttk.Label(info_frame, textvariable=self.ai_count_var).pack(anchor="w")
        ttk.Label(info_frame, textvariable=self.books_var, padding=(0, 6)).pack(anchor="w")
        self.scoreboard_label = ttk.Label(info_frame, textvariable=self.scoreboard_var, padding=(0, 6), wraplength=240, justify="left")
        self.scoreboard_label.pack(anchor="w")
        self.debug_label = ttk.Label(info_frame, textvariable=self.debug_info_var, foreground="#475569", wraplength=240, justify="left")
        self.debug_label.pack(anchor="w", pady=(6, 0))

        log_frame = ttk.LabelFrame(container, text="Log", padding=10)
        log_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=6, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)

    def _on_resize(self, event: tk.Event) -> None:
        wrap = max(280, event.width - 260)
        if getattr(self, "status_label", None):
            self.status_label.configure(wraplength=wrap)
        if getattr(self, "scoreboard_label", None):
            self.scoreboard_label.configure(wraplength=max(200, int(event.width * 0.3)))
        if getattr(self, "debug_label", None):
            self.debug_label.configure(wraplength=max(200, int(event.width * 0.3)))

    def _new_game(self) -> None:
        self.game = GoFishGame()
        self._refresh(log_clear=True)

    def _append_log(self, message: str) -> None:
        if not self.log_text:
            return
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _on_card_click(self, rank: str) -> None:
        if self.game.game_over() or self.game.turn != "player":
            return
        self.game.player_turn(rank)
        for entry in self.game.log:
            self._append_log(entry)
        self.game.log.clear()
        self._check_end()
        self._refresh()

    def _check_end(self) -> None:
        if not self.game.game_over():
            return
        winner = self.game.winner()
        if winner == "player":
            msg = "You win!"
            self.scoreboard["wins"] = self.scoreboard.get("wins", 0) + 1
        else:
            msg = "AI wins."
            self.scoreboard["losses"] = self.scoreboard.get("losses", 0) + 1
        self._save_scoreboard()
        messagebox.showinfo("Game over", msg)

    def _refresh(self, *, log_clear: bool = False) -> None:
        if log_clear and self.log_text:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")
        self._render_hand_cards()
        self.ai_count_var.set(f"AI hand: {len(self.game.ai_hand)} cards")
        self.books_var.set(f"Books - You: {self.game.player_books} | AI: {self.game.ai_books}")
        if self.game.turn == "player":
            self.status_var.set("Your turn: click a rank you hold to ask the AI.")
        else:
            self.status_var.set("AI's turn...")
        if self.game.game_over():
            self.status_var.set("Game over.")
        if self.game.game_over() and self.log_text:
            self._append_log("Game over.")
        if self.debug_enabled:
            ai_cards = " ".join(sorted(c.short_name() for c in self.game.ai_hand)) or "(none)"
            debug_lines = [
                f"Deck remaining: {self.game.deck.remaining()}",
                f"AI hand: {len(self.game.ai_hand)} cards -> {ai_cards}",
                f"Turn: {self.game.turn}",
            ]
            self.debug_info_var.set("\n".join(debug_lines))
        else:
            self.debug_info_var.set("")
        self._update_scoreboard_var()
        self._maybe_run_ai_turn()

    def _render_hand_cards(self) -> None:
        if not self.hand_frame:
            return
        for child in list(self.hand_frame.winfo_children()):
            child.destroy()
        hand = sorted(self.game.player_hand, key=lambda c: (c.rank, c.suit))
        if not hand:
            ttk.Label(self.hand_frame, text="(Empty hand)").grid(row=0, column=0, sticky="w")
            return
        max_per_row = 6
        for idx, card in enumerate(hand):
            row, col = divmod(idx, max_per_row)
            border_color = self._palette_colors.get("border", CARD_BORDER)
            card_bg = CARD_BG
            frame = tk.Frame(self.hand_frame, bg=border_color, bd=1, relief="solid", padx=1, pady=1)
            inner = tk.Frame(frame, bg=card_bg, width=78, height=104)
            inner.pack_propagate(False)
            inner.pack(fill="both", expand=True)
            rank_label = tk.Label(inner, text=card.rank, fg=CARD_TEXT, bg=card_bg, font=("Segoe UI", 14, "bold"), anchor="nw")
            rank_label.pack(anchor="nw", padx=4, pady=(4, 0))
            suit_symbol = SUIT_SYMBOLS.get(card.suit, card.suit[0].upper())
            suit_color = SUIT_COLORS.get(card.suit, CARD_TEXT)
            suit_label = tk.Label(inner, text=suit_symbol, fg=suit_color, bg=card_bg, font=("Segoe UI", 22, "bold"), anchor="center")
            suit_label.pack(expand=True)
            btn = tk.Button(
                inner,
                text="Ask",
                command=lambda r=card.rank: self._on_card_click(r),
                state=("normal" if self.game.turn == "player" and not self.game.game_over() else "disabled"),
                bg=self._palette_colors.get("accent", ACCENT),
                fg="white",
                relief="flat",
                padx=6,
                pady=2,
                font=("Segoe UI", 9, "bold"),
                activebackground=self._palette_colors.get("btn", ACCENT),
            )
            btn.pack(pady=(0, 6))
            frame.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        for c in range(max_per_row):
            self.hand_frame.columnconfigure(c, weight=1)

    def _maybe_run_ai_turn(self) -> None:
        if self._ai_pending or self.game.game_over() or self.game.turn != "ai":
            return
        self._ai_pending = True
        # Slight delay to avoid locking the UI thread.
        self.root.after(300, self._run_ai_turn)

    def _run_ai_turn(self) -> None:
        self._ai_pending = False
        if self.game.game_over() or self.game.turn != "ai":
            return
        self.game.ai_turn()
        for entry in self.game.log:
            self._append_log(entry)
        self.game.log.clear()
        self._check_end()
        self._refresh()

    def _on_theme_change(self) -> None:
        self._init_styles()
        self._refresh()
        self._save_settings()

    def _load_scoreboard(self) -> dict[str, int]:
        defaults = {"wins": 0, "losses": 0}
        return settings.load_settings(self.scoreboard_path, defaults)

    def _save_scoreboard(self) -> None:
        settings.save_settings(self.scoreboard_path, self.scoreboard)

    def _update_scoreboard_var(self) -> None:
        self.scoreboard_var.set(f"Wins: {self.scoreboard.get('wins',0)}  |  Losses: {self.scoreboard.get('losses',0)}")

    def _show_options(self) -> None:
        if getattr(self, "options_popup", None) and self.options_popup.winfo_exists():
            self.options_popup.lift()
            return
        popup = tk.Toplevel(self.root)
        popup.title("Options")
        popup.configure(bg=self._palette_colors.get("bg", "#0c1222"))
        popup.resizable(False, False)
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
        ttk.Button(popup, text="Reset to defaults", command=self._reset_settings).grid(row=2, column=0, sticky="w", padx=12, pady=(10, 0))
        ttk.Button(popup, text="Close", command=popup.destroy).grid(row=3, column=0, sticky="e", padx=12, pady=12)
        popup.columnconfigure(0, weight=1)
        self.options_popup = popup

    def _load_settings(self) -> None:
        defaults = {"theme": "default"}
        data = settings.load_settings(self.settings_path, defaults)
        theme = data.get("theme", "default")
        if isinstance(theme, str) and theme in PALETTES:
            self.theme_var.set(theme)

    def _save_settings(self) -> None:
        settings.save_settings(self.settings_path, {"theme": self.theme_var.get()})

    def _reset_settings(self) -> None:
        self.theme_var.set("default")
        self._on_theme_change()
        popup = getattr(self, "options_popup", None)
        if popup and popup.winfo_exists():
            popup.lift()

    def _show_scores(self) -> None:
        if getattr(self, "scores_popup", None) and self.scores_popup.winfo_exists():
            self.scores_popup.lift()
            return
        popup = tk.Toplevel(self.root)
        popup.title("Scores")
        popup.configure(bg=self._palette_colors.get("bg", "#0c1222"))
        popup.resizable(False, False)
        ttk.Label(popup, text="Go Fish Scoreboard", style="Title.TLabel").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
        ttk.Label(popup, textvariable=self.scoreboard_var, style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", padx=12, pady=(0, 12))
        ttk.Button(popup, text="Close", command=popup.destroy).grid(row=2, column=0, sticky="e", padx=12, pady=12)
        popup.columnconfigure(0, weight=1)
        self.scores_popup = popup


def _notify_already_running() -> None:
    message = "Go Fish is already running. Close the other window before starting a new session."
    try:
        tmp = tk.Tk()
        tmp.withdraw()
        messagebox.showinfo("Already running", message)
        tmp.destroy()
    except tk.TclError:
        print(message, file=sys.stderr)


def _notify_other_game_running(holder: str | None) -> None:
    name = holder or "another game"
    message = f"{name} is already running. Close it before starting Go Fish."
    try:
        tmp = tk.Tk()
        tmp.withdraw()
        messagebox.showinfo("Another game is running", message)
        tmp.destroy()
    except tk.TclError:
        print(message, file=sys.stderr)


def main() -> None:
    args = _parse_args(sys.argv[1:])
    if not single_instance.try_acquire_lock(ACTIVE_GAME_LOCK, "Go Fish"):
        _notify_other_game_running(single_instance.lock_holder(ACTIVE_GAME_LOCK))
        return
    if not single_instance.try_acquire_lock(LOCK_FILE, "Go Fish"):
        single_instance.release_lock(ACTIVE_GAME_LOCK)
        _notify_already_running()
        return
    root = tk.Tk()
    if not args.sound:
        settings.save_settings(SCOREBOARD_FILE.parent / "gofish_audio.json", {"sound": False})
    GoFishGUI(root, debug=args.debug, headless=args.headless)
    root.mainloop()


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Go Fish GUI")
    parser.add_argument("--debug", action="store_true", help="Show debug info (AI hand, deck count).")
    parser.add_argument("--headless", action="store_true", help="Withdraw the window for headless/smoke tests.")
    parser.add_argument("--sound", dest="sound", action="store_true", help="Enable sounds (default).")
    parser.add_argument("--no-sound", dest="sound", action="store_false", help="Disable sounds.")
    parser.set_defaults(sound=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
