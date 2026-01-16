"""A starter Klondike Solitaire GUI using Tkinter."""

from __future__ import annotations

import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared import settings, single_instance
from shared.deck import Card, Deck, RANKS
from shared.options import PALETTES
from shared.theme_manager import ThemedApp

LOCK_DIR = PROJECT_ROOT / "data" / "locks"
LOCK_FILE = LOCK_DIR / "solitaire.lock"
ACTIVE_GAME_LOCK = LOCK_DIR / "active_game.lock"
SETTINGS_FILE = PROJECT_ROOT / "data" / "solitaire_settings.json"

SUIT_SYMBOLS = {"Hearts": "♥", "Diamonds": "♦", "Clubs": "♣", "Spades": "♠"}
RED_SUITS = {"Hearts", "Diamonds"}


@dataclass
class Selected:
    source: str
    index: int


class SolitaireApp(ThemedApp):
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Solitaire")
        self.root.geometry("960x680")
        self.root.minsize(860, 600)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        defaults = {"theme": "default", "draw_count": 1}
        self.settings = settings.load_settings(SETTINGS_FILE, defaults)
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "default"))
        self.draw_count_var = tk.IntVar(value=int(self.settings.get("draw_count", 1)))

        # Initialize ThemedApp parent class
        super().__init__(root, self.theme_var, self.theme_var.get())

        self.deck = Deck()
        self.stock: list[Card] = []
        self.waste: list[Card] = []
        self.foundations: list[list[Card]] = [[] for _ in range(4)]
        self.tableau: list[list[Card]] = [[] for _ in range(7)]
        self.tableau_hidden: list[int] = [0 for _ in range(7)]
        self.selected: Optional[Selected] = None

        self.status_var = tk.StringVar(value="")
        self._build_ui()
        self._new_game()
        self.root.bind("<Configure>", self._on_resize)

    def _build_ui(self) -> None:
        self._apply_theme()
        menubar = tk.Menu(self.root)
        menubar.add_command(label="New Game", command=self._new_game)
        menubar.add_command(label="Options", command=self._show_options)
        self.root.config(menu=menubar)

        header = ttk.Frame(self.root, padding=12, style="Hero.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Solitaire", style="HeroTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.subtitle_label = ttk.Label(
            header,
            text="Klondike draw-one starter. Click stock to draw, select a card, then choose a destination.",
            style="HeroMuted.TLabel",
            wraplength=640,
            justify="left",
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(4, 8))

        control_row = ttk.Frame(header, style="Hero.TFrame")
        control_row.grid(row=2, column=0, sticky="w")
        ttk.Button(control_row, text="New Game", style="Accent.TButton", command=self._new_game).pack(side="left")
        ttk.Label(control_row, text="Draw:", style="HeroMuted.TLabel").pack(side="left", padx=(12, 4))
        draw_box = ttk.Combobox(control_row, values=[1, 3], width=5, state="readonly", textvariable=self.draw_count_var)
        draw_box.pack(side="left")
        draw_box.bind("<<ComboboxSelected>>", lambda e: self._save_settings())

        self.status_label = ttk.Label(header, textvariable=self.status_var, style="HeroMuted.TLabel", wraplength=640, justify="left")
        self.status_label.grid(row=3, column=0, sticky="w", pady=(8, 0))

        self.board_frame = ttk.Frame(self.root, padding=(12, 4), style="App.TFrame")
        self.board_frame.grid(row=2, column=0, sticky="nsew")
        self.board_frame.columnconfigure(0, weight=1)
        self.board_frame.rowconfigure(1, weight=1)

        self.top_row = ttk.Frame(self.board_frame, style="App.TFrame")
        self.top_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.top_row.columnconfigure(0, weight=1)
        self.top_row.columnconfigure(1, weight=1)

        self.stock_waste_frame = ttk.Frame(self.top_row, style="App.TFrame")
        self.stock_waste_frame.grid(row=0, column=0, sticky="w")
        self.foundation_frame = ttk.Frame(self.top_row, style="App.TFrame")
        self.foundation_frame.grid(row=0, column=1, sticky="e")

        self.tableau_frame = ttk.Frame(self.board_frame, style="App.TFrame")
        self.tableau_frame.grid(row=1, column=0, sticky="nsew")
        for i in range(7):
            self.tableau_frame.columnconfigure(i, weight=1)

    def _apply_theme(self, theme_name=None) -> None:
        """Apply theme using parent class and add game-specific customizations."""
        # Call parent to handle standard theme configuration
        super()._apply_theme(theme_name)

    def _customize_styles(self) -> None:
        """Solitaire-specific style customizations."""
        # Get current theme colors
        bg = self._color("BG")
        panel = self._color("PANEL")
        text = self._color("TEXT")
        muted = self._color("MUTED")
        accent = self._color("ACCENT")
        border = self._color("BORDER")

        # Store palette and card dimensions for game rendering
        self._palette = {"bg": bg, "panel": panel, "text": text, "muted": muted, "accent": accent, "border": border}
        self._card_size = {"w": 56, "h": 80}
        self._card_pad = {"x": 4, "y": 2}

        # Configure Solitaire-specific ttk styles
        self.style.theme_use("clam")
        self.style.configure("App.TFrame", background=bg)
        self.style.configure("Hero.TFrame", background=panel)
        self.style.configure("HeroTitle.TLabel", background=panel, foreground=text, font=("Segoe UI", 18, "bold"))
        self.style.configure("HeroMuted.TLabel", background=panel, foreground=muted, font=("Segoe UI", 10))
        self.style.configure("Accent.TButton", padding=(12, 6), background=accent, foreground=bg, relief="flat")
        self.style.map("Accent.TButton", background=[("active", accent)], foreground=[("active", bg)])

    def _new_game(self) -> None:
        self.deck.reset(shuffle=True)
        self.stock = []
        self.waste = []
        self.foundations = [[] for _ in range(4)]
        self.tableau = [[] for _ in range(7)]
        self.tableau_hidden = [0 for _ in range(7)]
        self.selected = None

        for col in range(7):
            cards = self.deck.draw(col + 1)
            self.tableau[col] = cards
            self.tableau_hidden[col] = col
        self.stock = self.deck.draw(self.deck.remaining())
        self.status_var.set("New game dealt. Click the stock to draw.")
        self._render()

    def _rank_value(self, card: Card) -> int:
        return RANKS.index(card.rank) + 1

    def _on_stock_click(self) -> None:
        if self.selected:
            self.selected = None
        if not self.stock:
            if self.waste:
                self.stock = list(reversed(self.waste))
                self.waste.clear()
                self.status_var.set("Recycled the waste back into the stock.")
            else:
                self.status_var.set("No cards left in the stock.")
            self._render()
            return
        draw_count = 1 if self.draw_count_var.get() not in (1, 3) else self.draw_count_var.get()
        for _ in range(min(draw_count, len(self.stock))):
            self.waste.append(self.stock.pop())
        self.status_var.set("Drew from stock.")
        self._render()

    def _select_from_waste(self) -> None:
        if not self.waste:
            return
        if self.selected and self.selected.source == "waste":
            self.selected = None
        else:
            self.selected = Selected("waste", 0)
        self._render()

    def _select_from_tableau(self, index: int) -> None:
        if not self.tableau[index]:
            return
        if len(self.tableau[index]) <= self.tableau_hidden[index]:
            return
        if self.selected and self.selected.source == "tableau" and self.selected.index == index:
            self.selected = None
        else:
            self.selected = Selected("tableau", index)
        self._render()

    def _selected_card(self) -> Optional[Card]:
        if not self.selected:
            return None
        if self.selected.source == "waste":
            return self.waste[-1] if self.waste else None
        if self.selected.source == "tableau":
            pile = self.tableau[self.selected.index]
            if not pile:
                return None
            if len(pile) <= self.tableau_hidden[self.selected.index]:
                return None
            return pile[-1]
        return None

    def _remove_selected(self) -> Optional[Card]:
        if not self.selected:
            return None
        if self.selected.source == "waste":
            return self.waste.pop() if self.waste else None
        if self.selected.source == "tableau":
            pile = self.tableau[self.selected.index]
            if not pile:
                return None
            card = pile.pop()
            if len(pile) == self.tableau_hidden[self.selected.index] and self.tableau_hidden[self.selected.index] > 0:
                self.tableau_hidden[self.selected.index] -= 1
            return card
        return None

    def _can_move_to_foundation(self, card: Card, foundation: list[Card]) -> bool:
        if not foundation:
            return card.rank == "A"
        top = foundation[-1]
        return card.suit == top.suit and self._rank_value(card) == self._rank_value(top) + 1

    def _can_move_to_tableau(self, card: Card, pile: list[Card]) -> bool:
        if not pile:
            return card.rank == "K"
        top = pile[-1]
        if top.suit in RED_SUITS and card.suit in RED_SUITS:
            return False
        if top.suit not in RED_SUITS and card.suit not in RED_SUITS:
            return False
        return self._rank_value(card) == self._rank_value(top) - 1

    def _move_selected_to_foundation(self, index: int) -> None:
        card = self._selected_card()
        if not card:
            return
        foundation = self.foundations[index]
        if not self._can_move_to_foundation(card, foundation):
            self.status_var.set("That card cannot move to the foundation.")
            self._render()
            return
        moved = self._remove_selected()
        if moved:
            foundation.append(moved)
            self.selected = None
            self.status_var.set("Moved to foundation.")
            self._check_win()
        self._render()

    def _move_selected_to_tableau(self, index: int) -> None:
        card = self._selected_card()
        if not card:
            return
        if self.selected and self.selected.source == "tableau" and self.selected.index == index:
            self.selected = None
            self.status_var.set("Selection cleared.")
            self._render()
            return
        pile = self.tableau[index]
        if not self._can_move_to_tableau(card, pile):
            self.status_var.set("That card cannot move to the tableau.")
            self._render()
            return
        moved = self._remove_selected()
        if moved:
            pile.append(moved)
            self.selected = None
            self.status_var.set("Moved to tableau.")
        self._render()

    def _check_win(self) -> None:
        if all(len(pile) == 13 for pile in self.foundations):
            try:
                messagebox.showinfo("You win!", "All foundations complete. Nice work!")
            except tk.TclError:
                pass

    def _render(self) -> None:
        for child in self.stock_waste_frame.winfo_children():
            child.destroy()
        for child in self.foundation_frame.winfo_children():
            child.destroy()
        for child in self.tableau_frame.winfo_children():
            child.destroy()

        self._render_stock()
        self._render_waste()
        self._render_foundations()
        self._render_tableau()

    def _card_widget(
        self,
        parent: tk.Widget,
        *,
        card: Optional[Card] = None,
        text: str = "",
        command: Optional[Callable[[], None]] = None,
        highlight: bool = False,
        face_down: bool = False,
    ) -> tk.Frame:
        frame = tk.Frame(parent, bg=self._palette["bg"])
        canvas = tk.Canvas(
            frame,
            width=self._card_size["w"],
            height=self._card_size["h"],
            bg=self._palette["bg"],
            highlightthickness=0,
        )
        canvas.pack()
        border = self._palette["accent"] if highlight else self._palette["border"]
        outline = 3 if highlight else 2
        if face_down:
            card_bg = self._palette["panel"]
            canvas.create_rectangle(4, 4, self._card_size["w"] - 4, self._card_size["h"] - 4, fill=card_bg, outline=border, width=outline)
            for i in range(8, self._card_size["h"] - 12, 8):
                canvas.create_line(6, i, self._card_size["w"] - 6, i + 16, fill=self._palette["border"])
            if text:
                canvas.create_text(
                    self._card_size["w"] // 2,
                    self._card_size["h"] // 2,
                    text=text,
                    fill=self._palette["muted"],
                    font=("Segoe UI", 9, "bold"),
                )
        else:
            card_bg = "#f8fafc"
            canvas.create_rectangle(4, 4, self._card_size["w"] - 4, self._card_size["h"] - 4, fill=card_bg, outline=border, width=outline)
            if card:
                color = "#dc2626" if card.suit in RED_SUITS else "#0f172a"
                suit = SUIT_SYMBOLS.get(card.suit, card.suit[:1])
                canvas.create_text(8, 10, text=card.rank, fill=color, font=("Segoe UI", 8, "bold"), anchor="w")
                canvas.create_text(8, 20, text=suit, fill=color, font=("Segoe UI", 10, "bold"), anchor="w")
                canvas.create_text(
                    self._card_size["w"] // 2,
                    self._card_size["h"] // 2,
                    text=suit,
                    fill=color,
                    font=("Segoe UI", 16, "bold"),
                )
                canvas.create_text(
                    self._card_size["w"] - 6,
                    self._card_size["h"] - 8,
                    text=card.rank,
                    fill=color,
                    font=("Segoe UI", 8, "bold"),
                    anchor="e",
                )
            else:
                canvas.create_text(
                    self._card_size["w"] // 2,
                    self._card_size["h"] // 2,
                    text=text,
                    fill=self._palette["muted"],
                    font=("Segoe UI", 9, "bold"),
                )
        if command:
            for widget in (canvas, frame):
                widget.configure(cursor="hand2")
                widget.bind("<Button-1>", lambda _e, cmd=command: cmd())
        return frame

    def _render_stock(self) -> None:
        container = ttk.Frame(self.stock_waste_frame, style="App.TFrame")
        container.grid(row=0, column=0, padx=(0, 8))
        label = ttk.Label(container, text="Stock", style="HeroMuted.TLabel")
        label.pack()
        text = "##" if self.stock else "--"
        card = self._card_widget(container, text=text, command=self._on_stock_click, face_down=True)
        card.pack(pady=(4, 0))
        ttk.Label(container, text=str(len(self.stock)), style="HeroMuted.TLabel").pack(pady=(4, 0))

    def _render_waste(self) -> None:
        container = ttk.Frame(self.stock_waste_frame, style="App.TFrame")
        container.grid(row=0, column=1)
        label = ttk.Label(container, text="Waste", style="HeroMuted.TLabel")
        label.pack()
        if self.waste:
            top = self.waste[-1]
            highlight = bool(self.selected and self.selected.source == "waste")
            card = self._card_widget(container, card=top, command=self._select_from_waste, highlight=highlight)
            card.pack(pady=(4, 0))
        else:
            card = self._card_widget(container, text="--", command=self._select_from_waste, face_down=True)
            card.pack(pady=(4, 0))

    def _render_foundations(self) -> None:
        for idx in range(4):
            container = ttk.Frame(self.foundation_frame, style="App.TFrame")
            container.grid(row=0, column=idx, padx=4)
            label = ttk.Label(container, text=f"F{idx + 1}", style="HeroMuted.TLabel")
            label.pack()
            pile = self.foundations[idx]
            if pile:
                top = pile[-1]
                card = self._card_widget(
                    container,
                    card=top,
                    command=lambda i=idx: self._move_selected_to_foundation(i),
                    highlight=False,
                )
                card.pack(pady=(4, 0))
            else:
                card = self._card_widget(
                    container,
                    text="--",
                    command=lambda i=idx: self._move_selected_to_foundation(i),
                    face_down=True,
                )
                card.pack(pady=(4, 0))

    def _render_tableau(self) -> None:
        for idx in range(7):
            col = ttk.Frame(self.tableau_frame, style="App.TFrame")
            col.grid(row=0, column=idx, padx=4, sticky="n")
            pile = self.tableau[idx]
            if not pile:
                empty = self._card_widget(
                    col,
                    text="Empty",
                    command=lambda i=idx: self._move_selected_to_tableau(i),
                    face_down=True,
                )
                empty.pack(pady=(0, self._card_pad["y"]))
                continue
            for row_index, card in enumerate(pile):
                is_hidden = row_index < self.tableau_hidden[idx]
                is_top = row_index == len(pile) - 1
                highlight = bool(
                    is_top
                    and self.selected
                    and self.selected.source == "tableau"
                    and self.selected.index == idx
                )
                if is_top and not is_hidden:
                    if self.selected:
                        command = lambda i=idx: self._move_selected_to_tableau(i)
                    else:
                        command = lambda i=idx: self._select_from_tableau(i)
                else:
                    command = None
                if is_hidden:
                    widget = self._card_widget(col, text="##", command=command, highlight=highlight, face_down=True)
                else:
                    widget = self._card_widget(col, card=card, command=command, highlight=highlight)
                widget.pack(pady=(0, self._card_pad["y"]))

    def _show_options(self) -> None:
        if getattr(self, "options_popup", None) and self.options_popup.winfo_exists():
            self.options_popup.lift()
            return
        popup = tk.Toplevel(self.root)
        popup.title("Options")
        popup.configure(bg=self._palette["bg"])
        popup.resizable(False, False)

        ttk.Label(popup, text="Theme", style="HeroTitle.TLabel").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        theme_box = ttk.Combobox(popup, textvariable=self.theme_var, values=list(PALETTES.keys()), state="readonly", width=18)
        theme_box.grid(row=1, column=0, sticky="ew", padx=12)
        theme_box.bind("<<ComboboxSelected>>", lambda e: self._on_theme_change())

        ttk.Label(popup, text="Draw count", style="HeroTitle.TLabel").grid(row=2, column=0, sticky="w", padx=12, pady=(10, 4))
        draw_box = ttk.Combobox(popup, textvariable=self.draw_count_var, values=[1, 3], state="readonly", width=18)
        draw_box.grid(row=3, column=0, sticky="ew", padx=12)
        draw_box.bind("<<ComboboxSelected>>", lambda e: self._save_settings())

        ttk.Button(popup, text="Close", style="Accent.TButton", command=popup.destroy).grid(
            row=4, column=0, sticky="e", padx=12, pady=12
        )
        popup.columnconfigure(0, weight=1)
        self.options_popup = popup

    def _on_theme_change(self) -> None:
        self._apply_theme()
        self._render()
        self._save_settings()

    def _save_settings(self) -> None:
        settings.save_settings(
            SETTINGS_FILE,
            {
                "theme": self.theme_var.get(),
                "draw_count": int(self.draw_count_var.get()),
            },
        )

    def _on_resize(self, event: tk.Event) -> None:
        wrap = max(360, event.width - 240)
        if getattr(self, "subtitle_label", None):
            self.subtitle_label.configure(wraplength=wrap)
        if getattr(self, "status_label", None):
            self.status_label.configure(wraplength=wrap)


def _notify_already_running() -> None:
    message = "Solitaire is already running. Close the other window before starting a new session."
    try:
        tmp = tk.Tk()
        tmp.withdraw()
        messagebox.showinfo("Already running", message)
        tmp.destroy()
    except tk.TclError:
        print(message, file=sys.stderr)


def _notify_other_game_running(holder: Optional[str]) -> None:
    name = holder or "another game"
    message = f"{name} is already running. Close it before starting Solitaire."
    try:
        tmp = tk.Tk()
        tmp.withdraw()
        messagebox.showinfo("Another game is running", message)
        tmp.destroy()
    except tk.TclError:
        print(message, file=sys.stderr)


def main() -> None:
    if not single_instance.try_acquire_lock(ACTIVE_GAME_LOCK, "Solitaire"):
        _notify_other_game_running(single_instance.lock_holder(ACTIVE_GAME_LOCK))
        return
    if not single_instance.try_acquire_lock(LOCK_FILE, "Solitaire"):
        single_instance.release_lock(ACTIVE_GAME_LOCK)
        _notify_already_running()
        return
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"Could not start Tkinter: {exc}", file=sys.stderr)
        single_instance.release_lock(LOCK_FILE)
        single_instance.release_lock(ACTIVE_GAME_LOCK)
        return
    SolitaireApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
