"""A minimal but playable Blackjack GUI using Tkinter.

Leverages the shared deck implementation so future games can reuse card helpers.
"""

from __future__ import annotations

import sys
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path

# Ensure project root is on sys.path so we can import shared.deck when run directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.deck import Card, Deck
from shared.chips import Chips
from shared import scoreboard
from shared import options as shared_options
from shared.options import PALETTES

SETTINGS_FILE = "blackjack_settings.json"


def hand_value(cards: list[Card]) -> tuple[int, bool]:
    """Return (best_total, is_soft)."""
    total = 0
    aces = 0
    for card in cards:
        if card.rank == "A":
            aces += 1
            total += 11
        elif card.rank in {"K", "Q", "J"}:
            total += 10
        else:
            total += int(card.rank)

    while total > 21 and aces:
        total -= 10
        aces -= 1

    is_soft = aces > 0 and total <= 21
    return total, is_soft


class BlackjackApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Blackjack")
        self.root.geometry("540x420")
        self.theme_var = tk.StringVar(value="default")
        self._language = "en"
        self._available_languages = ["en"]
        self.settings_path = PROJECT_ROOT / "data" / SETTINGS_FILE
        self._load_settings()
        self.root.configure(bg=self._color("BG"))

        self.deck: Deck = Deck()
        self.deck.shuffle()
        self.chips = Chips(balance=500)
        self.current_bet: int = 50
        self.player_hand: list[Card] = []
        self.dealer_hand: list[Card] = []
        self.round_over = False
        self.scoreboard_path = PROJECT_ROOT / "data" / "blackjack_scores.json"

        self._build_ui()
        self.start_round()

    def _build_ui(self) -> None:
        menubar = tk.Menu(self.root)
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_command(label="Options", command=self._show_options)
        menubar.add_cascade(label="Options", menu=options_menu)
        self.root.config(menu=menubar)

        self.title_label = tk.Label(
            self.root,
            text="Blackjack",
            font=("Segoe UI", 18, "bold"),
            fg="#f8fafc",
            bg=self._color("BG"),
        )
        self.title_label.pack(pady=(16, 4))

        self.subtitle_label = tk.Label(
            self.root,
            text="Hit or stand against the dealer. Dealer stands on 17+.",
            font=("Segoe UI", 10),
            fg="#e2e8f0",
            bg=self._color("BG"),
        )
        self.subtitle_label.pack(pady=(0, 14))

        self.main_frame = ttk.Frame(self.root, padding=12, style="BJ.TFrame")
        self.main_frame.pack(fill="both", expand=True)

        self.dealer_label = ttk.Label(self.main_frame, text="Dealer:", font=("Segoe UI", 12, "bold"), style="BJ.TLabel")
        self.dealer_cards = ttk.Label(self.main_frame, text="", font=("Consolas", 12), style="BJ.TLabel")
        self.player_label = ttk.Label(self.main_frame, text="You:", font=("Segoe UI", 12, "bold"), style="BJ.TLabel")
        self.player_cards = ttk.Label(self.main_frame, text="", font=("Consolas", 12), style="BJ.TLabel")
        self.status_label = ttk.Label(self.main_frame, text="", font=("Segoe UI", 11, "bold"), style="BJ.TLabel")
        self.bank_label = ttk.Label(self.main_frame, text="", font=("Segoe UI", 11), style="BJ.TLabel")
        bet_row = ttk.Frame(self.main_frame, style="BJ.TFrame")
        self.bet_label = ttk.Label(bet_row, text="Bet:", style="BJ.TLabel")
        self.bet_label.pack(side="left")
        self.bet_var = tk.StringVar(value=str(self.current_bet))
        self.bet_entry = ttk.Entry(bet_row, textvariable=self.bet_var, width=8, style="BJ.TEntry")
        self.bet_entry.pack(side="left", padx=(4, 0))

        self.dealer_label.pack(anchor="w", pady=(0, 2))
        self.dealer_cards.pack(anchor="w", pady=(0, 10))
        self.player_label.pack(anchor="w", pady=(0, 2))
        self.player_cards.pack(anchor="w", pady=(0, 10))
        self.status_label.pack(anchor="w", pady=(8, 0))
        self.bank_label.pack(anchor="w", pady=(4, 0))
        bet_row.pack(anchor="w", pady=(6, 0))

        self.btn_frame = ttk.Frame(self.root, padding=12, style="BJ.TFrame")
        self.btn_frame.pack()

        self.hit_btn = ttk.Button(self.btn_frame, text="Hit", width=10, command=self.hit, style="BJ.TButton")
        self.stand_btn = ttk.Button(self.btn_frame, text="Stand", width=10, command=self.stand, style="BJ.TButton")
        self.new_round_btn = ttk.Button(self.btn_frame, text="New Round", width=12, command=self.start_round, style="BJ.TButton")
        self.save_score_btn = ttk.Button(self.btn_frame, text="Save Score", width=12, command=self._save_score, style="BJ.TButton")
        self.view_scores_btn = ttk.Button(self.btn_frame, text="View Scores", width=12, command=self._show_scores, style="BJ.TButton")

        self.hit_btn.grid(row=0, column=0, padx=6)
        self.stand_btn.grid(row=0, column=1, padx=6)
        self.new_round_btn.grid(row=0, column=2, padx=6)
        self.save_score_btn.grid(row=1, column=0, padx=6, pady=(8, 0))
        self.view_scores_btn.grid(row=1, column=1, padx=6, pady=(8, 0))
        self._apply_theme()

    def start_round(self) -> None:
        bet = self._parse_bet()
        if bet is None:
            self._set_status("Enter a valid bet.")
            self._update_buttons(force_disable=True)
            return
        if not self.chips.place_bet(bet):
            self._set_status("Insufficient chips for that bet.")
            self._update_buttons(force_disable=True)
            return

        self.current_bet = bet
        if len(self.deck) < 15:
            self.deck.reset(shuffle=True)

        self.player_hand = [self.deck.draw_one(), self.deck.draw_one()]
        self.dealer_hand = [self.deck.draw_one(), self.deck.draw_one()]
        self.round_over = False

        # Check for naturals
        player_total, _ = hand_value(self.player_hand)
        dealer_total, _ = hand_value(self.dealer_hand)
        if player_total == 21 or dealer_total == 21:
            self.round_over = True
            outcome = self._decide_winner(natural=True)
            self._set_status(outcome)
            self._settle(outcome, natural=True)
        else:
            self._set_status("Hit or Stand.")

        self._refresh_ui()
        self._update_buttons()

    def hit(self) -> None:
        if self.round_over:
            return
        if len(self.deck) == 0:
            self.deck.reset(shuffle=True)
        self.player_hand.append(self.deck.draw_one())
        player_total, _ = hand_value(self.player_hand)
        if player_total > 21:
            self.round_over = True
            self._set_status("You bust! Dealer wins.")
            self._settle("You bust! Dealer wins.")
        self._refresh_ui()
        self._update_buttons()

    def stand(self) -> None:
        if self.round_over:
            return

        # Dealer draws to 17 or higher (stands on soft 17)
        while True:
            total, _ = hand_value(self.dealer_hand)
            if total < 17:
                if len(self.deck) == 0:
                    self.deck.reset(shuffle=True)
                self.dealer_hand.append(self.deck.draw_one())
            else:
                break

        self.round_over = True
        outcome = self._decide_winner()
        self._set_status(outcome)
        self._settle(outcome)
        self._refresh_ui()
        self._update_buttons()

    def _decide_winner(self, natural: bool = False) -> str:
        player_total, _ = hand_value(self.player_hand)
        dealer_total, _ = hand_value(self.dealer_hand)

        if natural:
            if player_total == 21 and dealer_total == 21:
                return "Push. Both have Blackjack."
            if player_total == 21:
                return "Blackjack! You win."
            if dealer_total == 21:
                return "Dealer has Blackjack."

        if player_total > 21:
            return "You bust! Dealer wins."
        if dealer_total > 21:
            return "Dealer busts! You win."
        if player_total > dealer_total:
            return "You win!"
        if dealer_total > player_total:
            return "Dealer wins."
        return "Push."

    def _settle(self, outcome: str, natural: bool = False) -> None:
        """Adjust chips based on outcome and refresh bank label."""
        bet = self.current_bet
        if outcome.startswith("Push"):
            self.chips.payout_push(bet)
        elif "Blackjack! You win." in outcome:
            self.chips.payout_win(bet, blackjack=True)
        elif "You win!" in outcome or "Dealer busts" in outcome:
            self.chips.payout_win(bet, blackjack=False)
        # losses keep the bet already deducted
        self._update_bank_label()

    def _save_score(self) -> None:
        name = simpledialog.askstring("Save Score", "Enter your name:", parent=self.root)
        if not name:
            return
        scores = scoreboard.add_score(self.scoreboard_path, name.strip(), self.chips.balance, limit=10)
        messagebox.showinfo("Score Saved", f"Saved! You now have ${self.chips.balance:,}.\nTop score: ${scores[0].score:,} by {scores[0].name}.")

    def _show_scores(self) -> None:
        if getattr(self, "_scores_popup", None) and self._scores_popup.winfo_exists():
            self._scores_popup.lift()
            self._scores_popup.focus_set()
            return

        scores = scoreboard.load_scores(self.scoreboard_path)
        if not scores:
            messagebox.showinfo("Scores", "No scores saved yet.")
            return
        top = tk.Toplevel(self.root)
        self._scores_popup = top
        top.title("Blackjack Scores")
        top.configure(bg=self._color("BG"))
        top.geometry("360x360")

        header = tk.Label(
            top,
            text="High Scores",
            font=("Segoe UI", 16, "bold"),
            fg=self._color("TEXT"),
            bg=self._color("BG"),
        )
        header.pack(pady=(12, 4))
        sub = tk.Label(
            top,
            text="Top bankrolls (saved locally)",
            font=("Segoe UI", 10),
            fg=self._color("MUTED"),
            bg=self._color("BG"),
        )
        sub.pack(pady=(0, 10))

        columns = ("rank", "name", "score")
        tree = ttk.Treeview(top, columns=columns, show="headings", height=10)
        tree.heading("rank", text="#")
        tree.heading("name", text="Player")
        tree.heading("score", text="Chips")
        tree.column("rank", width=40, anchor="center")
        tree.column("name", width=160, anchor="w")
        tree.column("score", width=100, anchor="e")
        tree.pack(fill="both", expand=True, padx=12, pady=8)

        for idx, entry in enumerate(scores):
            tree.insert("", "end", values=(idx + 1, entry.name, f"${entry.score:,}"))

        ttk.Button(top, text="Close", command=lambda: self._close_scores_popup(top)).pack(pady=(0, 12))

    def _close_scores_popup(self, popup: tk.Toplevel) -> None:
        try:
            popup.destroy()
        finally:
            self._scores_popup = None

    def _refresh_ui(self) -> None:
        show_dealer_hole = self.round_over
        dealer_text = self._format_hand(self.dealer_hand, reveal=show_dealer_hole)
        player_text = self._format_hand(self.player_hand, reveal=True)

        self.dealer_cards.config(text=dealer_text)
        self.player_cards.config(text=player_text)
        self._update_bank_label()

    def _format_hand(self, hand: list[Card], *, reveal: bool) -> str:
        if not hand:
            return ""
        if reveal:
            total, _ = hand_value(hand)
            cards = " ".join(card.short_name() for card in hand)
            return f"{cards}  (Total: {total})"
        # Hide dealer hole card
        visible = hand[0].short_name()
        return f"{visible} [hidden]"

    def _set_status(self, msg: str) -> None:
        self.status_label.config(text=msg)

    def _update_buttons(self) -> None:
        state = "disabled" if self.round_over else "normal"
        self.hit_btn.config(state=state)
        self.stand_btn.config(state=state)
        # Enable new round only if the player has chips
        if self.chips.balance <= 0:
            self.new_round_btn.config(state="disabled")
            self._set_status("Out of chips.")
        else:
            self.new_round_btn.config(state="normal")

    def _update_bank_label(self) -> None:
        self.bank_label.config(text=f"Chips: ${self.chips.balance:,}")

    def _parse_bet(self) -> int | None:
        try:
            bet = int(self.bet_var.get())
        except ValueError:
            return None
        return bet if bet > 0 else None

    # Shared options integration (minimal toggles for now)
    def _show_options(self) -> None:
        self._apply_options_styles()
        toggles = [
            ("Sound cues", tk.BooleanVar(value=False), lambda: None),
        ]
        presets: list[tuple[str, callable]] = []
        shared_options.show_options_popup(
            self,
            toggles=toggles,
            preset_actions=presets,
            title="Options",
            subtitle="Shared options (expand with blackjack-specific controls).",
        )

    def _color(self, key: str) -> str:
        theme = self.theme_var.get()
        colors = PALETTES.get(theme) or PALETTES.get("default", {})
        return colors.get(key, PALETTES.get("default", {}).get(key, "#0b3d2e"))

    @property
    def options_popup(self):
        return getattr(self, "_options_popup", None)

    @options_popup.setter
    def options_popup(self, value):
        self._options_popup = value

    def _on_theme_change(self, event=None):
        self._apply_theme()

    def _lang_display(self, code: str) -> str:
        return code

    @property
    def language(self) -> str:
        return self._language

    @property
    def available_languages(self):
        return self._available_languages if hasattr(self, "_available_languages") else ["en"]

    def _on_language_change(self, code: str) -> None:
        self._language = code

    def _update_theme_swatch(self, canvas: tk.Canvas | None) -> None:
        # Update a simple swatch if provided
        if canvas is not None:
            canvas.configure(bg=self._color("PANEL"))

    def _apply_options_styles(self) -> None:
        colors = PALETTES.get(self.theme_var.get(), PALETTES["default"])
        bg = colors.get("BG", "#0b3d2e")
        panel = colors.get("PANEL", bg)
        text = colors.get("TEXT", "#f8fafc")
        muted = colors.get("MUTED", text)
        accent = colors.get("ACCENT", "#38bdf8")
        style = ttk.Style(self.root)
        style.configure("Panel.TFrame", background=panel)
        style.configure("Banner.TLabel", background=panel, foreground=text, font=("Segoe UI", 14, "bold"))
        style.configure("Muted.TLabel", background=panel, foreground=muted, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=panel, foreground=text, font=("Segoe UI", 11, "bold"))
        style.configure("App.TCheckbutton", background=panel, foreground=text)
        style.configure("App.TCombobox", fieldbackground=panel, background=panel, foreground=text)
        style.configure("Accent.TButton", padding=(10, 4), background=accent, foreground=text)
        style.map("Accent.TButton", background=[("active", accent)])

    def _load_settings(self) -> None:
        try:
            if self.settings_path.exists():
                data = json.loads(self.settings_path.read_text(encoding="utf-8"))
                theme = data.get("theme")
                if theme and theme in PALETTES:
                    self.theme_var.set(theme)
        except Exception:
            pass

    def _save_settings(self) -> None:
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(json.dumps({"theme": self.theme_var.get()}), encoding="utf-8")
        except Exception:
            pass

    def _apply_theme(self) -> None:
        colors = PALETTES.get(self.theme_var.get(), PALETTES["default"])
        bg = colors.get("BG", "#0b3d2e")
        panel = colors.get("PANEL", bg)
        text = colors.get("TEXT", "#f8fafc")
        accent = colors.get("ACCENT", "#38bdf8")
        btn_bg = colors.get("BTN", accent)
        muted = colors.get("MUTED", text)

        self.root.configure(bg=bg)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("BJ.TLabel", background=panel, foreground=text)
        style.configure("BJ.Muted.TLabel", background=panel, foreground=muted)
        style.configure(
            "BJ.TButton",
            padding=(10, 4),
            foreground=text,
            background=btn_bg,
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "BJ.TButton",
            background=[("active", accent)],
            foreground=[("active", bg)],
        )
        style.configure("BJ.TFrame", background=panel)
        style.configure("BJ.TEntry", fieldbackground=panel, foreground=text, insertcolor=text)
        style.map("BJ.TEntry", fieldbackground=[("focus", panel)], foreground=[("disabled", muted)])

        # Apply to tk labels
        self.title_label.configure(bg=bg, fg=text)
        self.subtitle_label.configure(bg=bg, fg=muted)

        # Update frames backgrounds
        self.main_frame.configure(style="BJ.TFrame")
        self.btn_frame.configure(style="BJ.TFrame")
        for widget in self.main_frame.winfo_children():
            if isinstance(widget, tk.Label):
                widget.configure(bg=panel, fg=text)
        # Entry/label styles
        self.bet_entry.configure(style="BJ.TEntry")
        self.bet_label.configure(style="BJ.TLabel")
        self._apply_options_styles()
        self._refresh_score_popup_theme()
        self._refresh_options_popup_theme()
        self._save_settings()

    def _copy_diagnostics(self) -> None:
        pass

    def _refresh_score_popup_theme(self) -> None:
        popup = getattr(self, "_scores_popup", None)
        if not popup or not popup.winfo_exists():
            return
        colors = PALETTES.get(self.theme_var.get(), PALETTES["default"])
        bg = colors.get("BG", "#0b3d2e")
        text = colors.get("TEXT", "#f8fafc")
        muted = colors.get("MUTED", text)
        popup.configure(bg=bg)
        for child in popup.winfo_children():
            if isinstance(child, tk.Label):
                # Header/subtitle labels
                if child.cget("font") == ("Segoe UI", 16, "bold"):
                    child.configure(bg=bg, fg=text)
                else:
                    child.configure(bg=bg, fg=muted)

    def _refresh_options_popup_theme(self) -> None:
        popup = getattr(self, "options_popup", None)
        if not popup or not popup.winfo_exists():
            return
        popup.configure(bg=self._color("BG"))


def main() -> None:
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(
            "Could not start Tkinter. Make sure Tcl/Tk is installed. Details:",
            exc,
            sep="\n",
            file=sys.stderr,
        )
        return
    BlackjackApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
