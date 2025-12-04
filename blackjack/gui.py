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
        self.root.geometry("960x720")
        self.root.minsize(900, 700)
        self.theme_var = tk.StringVar(value="default")
        self.show_totals = tk.BooleanVar(value=True)
        self._language = "en"
        self._available_languages = ["en"]
        self.settings_path = PROJECT_ROOT / "data" / SETTINGS_FILE
        self._load_settings()
        self.root.configure(bg=self._color("BG"))

        self.deck: Deck = Deck()
        self.deck.shuffle()
        self.chips = Chips(balance=500)
        self.base_bet: int = 50
        self.current_bet: int = 50
        self.player_hands: list[list[Card]] = []
        self.hand_bets: list[int] = []
        self.hand_results: list[str | None] = []
        self.hand_actions: list[int] = []  # number of hits taken per hand (for double/split rules)
        self.current_hand_index: int = 0
        self.has_split: bool = False
        self.insurance_bet: int = 0
        self.dealer_hand: list[Card] = []
        self.round_over = False
        self.scoreboard_path = PROJECT_ROOT / "data" / "blackjack_scores.json"

        self._build_ui()
        self.start_round()

    def _build_ui(self) -> None:
        menubar = tk.Menu(self.root)
        menubar.add_command(label="View Scores", command=self._show_scores)
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
        self.dealer_cards_frame = tk.Frame(self.main_frame, bg=self._color("PANEL"))
        self.player_label = ttk.Label(self.main_frame, text="You:", font=("Segoe UI", 12, "bold"), style="BJ.TLabel")
        self.player_cards_frame = tk.Frame(self.main_frame, bg=self._color("PANEL"))
        self.status_label = ttk.Label(self.main_frame, text="", font=("Segoe UI", 11, "bold"), style="BJ.TLabel")
        self.bank_label = ttk.Label(self.main_frame, text="", font=("Segoe UI", 11), style="BJ.TLabel")
        bet_row = ttk.Frame(self.main_frame, style="BJ.TFrame")
        self.bet_label = ttk.Label(bet_row, text="Bet:", style="BJ.TLabel")
        self.bet_label.pack(side="left")
        self.bet_var = tk.StringVar(value=str(self.base_bet))
        self.bet_entry = ttk.Entry(bet_row, textvariable=self.bet_var, width=8, style="BJ.TEntry")
        self.bet_entry.pack(side="left", padx=(4, 0))

        self.dealer_label.pack(anchor="w", pady=(0, 2))
        self.dealer_cards_frame.pack(anchor="w", pady=(0, 10))
        self.player_label.pack(anchor="w", pady=(0, 2))
        self.player_cards_frame.pack(anchor="w", pady=(0, 10))
        self.status_label.pack(anchor="w", pady=(8, 0))
        self.bank_label.pack(anchor="w", pady=(4, 0))
        bet_row.pack(anchor="w", pady=(6, 0))

        self.btn_frame = ttk.Frame(self.root, padding=12, style="BJ.TFrame")
        self.btn_frame.pack()

        self.hit_btn = ttk.Button(self.btn_frame, text="Hit", width=10, command=self.hit, style="BJ.TButton")
        self.stand_btn = ttk.Button(self.btn_frame, text="Stand", width=10, command=self.stand, style="BJ.TButton")
        self.double_btn = ttk.Button(self.btn_frame, text="Double", width=10, command=self.double_down, style="BJ.TButton")
        self.split_btn = ttk.Button(self.btn_frame, text="Split", width=10, command=self.split_hand, style="BJ.TButton")
        self.insurance_btn = ttk.Button(self.btn_frame, text="Insurance", width=12, command=self.take_insurance, style="BJ.TButton")
        self.new_round_btn = ttk.Button(self.btn_frame, text="New Round", width=12, command=self.start_round, style="BJ.TButton")
        self.save_score_btn = ttk.Button(self.btn_frame, text="Save Score", width=12, command=self._save_score, style="BJ.TButton")

        self.hit_btn.grid(row=0, column=0, padx=6, pady=(0, 4))
        self.stand_btn.grid(row=0, column=1, padx=6, pady=(0, 4))
        self.double_btn.grid(row=0, column=2, padx=6, pady=(0, 4))
        self.split_btn.grid(row=0, column=3, padx=6, pady=(0, 4))
        self.insurance_btn.grid(row=1, column=0, padx=6, pady=(4, 0))
        self.new_round_btn.grid(row=1, column=1, padx=6, pady=(4, 0))
        self.save_score_btn.grid(row=1, column=2, padx=6, pady=(4, 0))
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
        self.base_bet = bet
        if len(self.deck) < 15:
            self.deck.reset(shuffle=True)

        self.player_hands = [[self.deck.draw_one(), self.deck.draw_one()]]
        self.hand_bets = [bet]
        self.hand_results = [None]
        self.hand_actions = [0]
        self.has_split = False
        self.insurance_bet = 0
        self.dealer_hand = [self.deck.draw_one(), self.deck.draw_one()]
        self.round_over = False
        self.current_hand_index = 0

        # Check for naturals
        player_total, _ = hand_value(self.player_hands[0])
        dealer_total, _ = hand_value(self.dealer_hand)
        if player_total == 21 or dealer_total == 21:
            self.round_over = True
            outcome = self._decide_winner(natural=True)
            self._set_status(outcome)
            self._settle(outcome, natural=True)
        else:
            if self._can_offer_insurance():
                self._set_status("Dealer shows Ace. Take insurance or play your hand.")
            else:
                self._set_status("Hit, Stand, or Double.")

        self._refresh_ui()
        self._update_buttons()

    def hit(self) -> None:
        if self.round_over:
            return
        if len(self.deck) == 0:
            self.deck.reset(shuffle=True)
        hand = self.player_hands[self.current_hand_index]
        hand.append(self.deck.draw_one())
        self.hand_actions[self.current_hand_index] += 1
        player_total, _ = hand_value(hand)
        if player_total > 21:
            self.hand_results[self.current_hand_index] = "Bust"
            if not self._advance_to_next_hand():
                self._finish_round()
                return
        self._refresh_ui()
        self._update_buttons()

    def stand(self) -> None:
        if self.round_over:
            return

        self.hand_results[self.current_hand_index] = "Stand"
        if not self._advance_to_next_hand():
            self._finish_round()
        self._refresh_ui()
        self._update_buttons()

    def double_down(self) -> None:
        if self.round_over or not self._can_double():
            return
        idx = self.current_hand_index
        bet = self.hand_bets[idx]
        if not self.chips.place_bet(bet):
            self._set_status("Not enough chips to double.")
            return
        self.hand_bets[idx] += bet
        if len(self.deck) == 0:
            self.deck.reset(shuffle=True)
        self.player_hands[idx].append(self.deck.draw_one())
        self.hand_actions[idx] += 1
        total, _ = hand_value(self.player_hands[idx])
        if total > 21:
            self.hand_results[idx] = "Bust"
        else:
            self.hand_results[idx] = "Double"
        if not self._advance_to_next_hand():
            self._finish_round()
        self._refresh_ui()
        self._update_buttons()

    def split_hand(self) -> None:
        if self.round_over or not self._can_split():
            return
        idx = self.current_hand_index
        hand = self.player_hands[idx]
        bet = self.hand_bets[idx]
        if not self.chips.place_bet(bet):
            self._set_status("Not enough chips to split.")
            return
        # Create two hands from the pair and draw one card to each new hand
        first_card, second_card = hand
        new_hand1 = [first_card, self.deck.draw_one()]
        new_hand2 = [second_card, self.deck.draw_one()]
        self.player_hands[idx] = new_hand1
        self.player_hands.insert(idx + 1, new_hand2)
        self.hand_bets[idx] = bet
        self.hand_bets.insert(idx + 1, bet)
        self.hand_results[idx] = None
        self.hand_results.insert(idx + 1, None)
        self.hand_actions[idx] = 0
        self.hand_actions.insert(idx + 1, 0)
        self.has_split = True
        self._set_status("Playing split hands. Finish both.")
        self._refresh_ui()
        self._update_buttons()

    def take_insurance(self) -> None:
        if self.round_over or not self._can_offer_insurance():
            return
        insurance_amount = self.base_bet // 2
        if insurance_amount <= 0:
            self._set_status("Insurance amount must be positive.")
            return
        if not self.chips.place_bet(insurance_amount):
            self._set_status("Not enough chips for insurance.")
            return
        self.insurance_bet = insurance_amount
        self._set_status(f"Insurance placed: ${insurance_amount}. Play your hand.")
        self._update_bank_label()
        self._update_buttons()

    def _decide_winner(self, natural: bool = False) -> str:
        # Legacy single-hand resolution for naturals.
        player_total, _ = hand_value(self.player_hands[0])
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
        # Supports both legacy single-hand natural resolution and multi-hand flow.
        if natural:
            bet = self.hand_bets[0]
            if outcome.startswith("Push"):
                self.chips.payout_push(bet)
            elif "Blackjack! You win." in outcome:
                self.chips.payout_win(bet, blackjack=True)
            elif "You win!" in outcome or "Dealer busts" in outcome:
                self.chips.payout_win(bet, blackjack=False)
            # losses keep the bet already deducted
            self._update_bank_label()
            return

        dealer_total, _ = hand_value(self.dealer_hand)
        messages: list[str] = []
        for idx, hand in enumerate(self.player_hands):
            bet = self.hand_bets[idx]
            total, _ = hand_value(hand)
            result = self.hand_results[idx]
            hand_label = f"Hand {idx + 1}"
            if total > 21:
                messages.append(f"{hand_label}: Bust.")
                continue
            if dealer_total == 21 and len(self.dealer_hand) == 2:
                # Dealer blackjack handled after loop for insurance/main bets
                pass
            if dealer_total > 21:
                self.chips.payout_win(bet)
                messages.append(f"{hand_label}: Dealer busts, you win!")
                continue
            if total > dealer_total:
                # Blackjack bonus only if no split and exactly two-card 21
                blackjack_bonus = (
                    not self.has_split and len(hand) == 2 and total == 21 and self.hand_actions[idx] == 0
                )
                self.chips.payout_win(bet, blackjack=blackjack_bonus)
                messages.append(f"{hand_label}: You win!" + (" (Blackjack!)" if blackjack_bonus else ""))
            elif total < dealer_total:
                messages.append(f"{hand_label}: Dealer wins.")
            else:
                self.chips.payout_push(bet)
                messages.append(f"{hand_label}: Push.")

        # Insurance resolution
        dealer_blackjack = dealer_total == 21 and len(self.dealer_hand) == 2
        if self.insurance_bet:
            if dealer_blackjack:
                self.chips.balance += self.insurance_bet * 3
                messages.append(f"Insurance pays ${self.insurance_bet * 2}.")
            else:
                messages.append("Insurance lost.")

        if dealer_blackjack:
            # If dealer has blackjack, losing hands already paid. Wins only on player blackjack push above.
            pass

        self._set_status("\n".join(messages) if messages else "Round complete.")
        self._update_bank_label()

    def _finish_round(self) -> None:
        # Let dealer play if any hand is still live.
        if any(hand_value(hand)[0] <= 21 for hand in self.player_hands):
            self._dealer_play()
        self.round_over = True
        self._settle("", natural=False)
        self._refresh_ui()
        self._update_buttons()

    def _dealer_play(self) -> None:
        while True:
            total, is_soft = hand_value(self.dealer_hand)
            if total < 17 or (total == 17 and is_soft is True):
                if len(self.deck) == 0:
                    self.deck.reset(shuffle=True)
                self.dealer_hand.append(self.deck.draw_one())
            else:
                break

    def _advance_to_next_hand(self) -> bool:
        for idx in range(self.current_hand_index + 1, len(self.player_hands)):
            if self.hand_results[idx] is None:
                self.current_hand_index = idx
                return True
        return False

    def _can_double(self) -> bool:
        if self.round_over:
            return False
        idx = self.current_hand_index
        if idx >= len(self.player_hands):
            return False
        if self.hand_results[idx] is not None:
            return False
        hand = self.player_hands[idx]
        if len(hand) != 2 or self.hand_actions[idx] != 0:
            return False
        bet = self.hand_bets[idx]
        return self.chips.can_bet(bet)

    def _card_value_for_split(self, card: Card) -> int:
        if card.rank == "A":
            return 11
        if card.rank in {"K", "Q", "J", "10"}:
            return 10
        return int(card.rank)

    def _can_split(self) -> bool:
        if self.round_over or self.has_split:
            return False
        idx = self.current_hand_index
        if self.hand_results[idx] is not None:
            return False
        hand = self.player_hands[idx]
        if len(hand) != 2 or self.hand_actions[idx] != 0:
            return False
        v1 = self._card_value_for_split(hand[0])
        v2 = self._card_value_for_split(hand[1])
        if v1 != v2:
            return False
        bet = self.hand_bets[idx]
        return self.chips.can_bet(bet)

    def _can_offer_insurance(self) -> bool:
        if self.round_over:
            return False
        if len(self.player_hands) != 1:
            return False
        if self.hand_actions[0] != 0:
            return False
        if not self.dealer_hand:
            return False
        return self.dealer_hand[0].rank == "A"

    def _render_hand(
        self,
        hand: list[Card],
        container: tk.Frame,
        *,
        reveal: bool,
        label: str | None = None,
        active: bool = False,
        result_text: str | None = None,
    ) -> None:
        for child in container.winfo_children():
            child.destroy()
        colors = PALETTES.get(self.theme_var.get(), PALETTES["default"])
        bg = colors.get("PANEL", "#0b3d2e")
        border = colors.get("BORDER", "#1e293b")
        container.configure(bg=bg, highlightbackground=border)
        if label:
            prefix = "> " if active else ""
            lbl = tk.Label(
                container,
                text=f"{prefix}{label}" + (f" [{result_text}]" if result_text else ""),
                bg=bg,
                fg=colors.get("TEXT", "#f8fafc"),
                font=("Segoe UI", 11, "bold"),
            )
            lbl.pack(anchor="w")
        cards_row = tk.Frame(container, bg=bg)
        cards_row.pack(anchor="w", pady=(2, 0))
        if not hand:
            tk.Label(cards_row, text="(empty)", bg=bg, fg=colors.get("MUTED", "#cbd5e1")).pack()
            return
        for idx, card in enumerate(hand):
            face_down = False
            if not reveal and idx == 1:
                face_down = True
            card_widget = self._create_card_widget(cards_row, card, colors=colors, face_down=face_down, active=active)
            card_widget.pack(side="left", padx=6, pady=2)
        if self.show_totals.get():
            total_text = "?"
            if reveal:
                total, _ = hand_value(hand)
                total_text = str(total)
            tk.Label(
                container,
                text=f"Total: {total_text}",
                bg=bg,
                fg=colors.get("MUTED", "#cbd5e1"),
                font=("Segoe UI", 10),
            ).pack(anchor="w", pady=(4, 0))

    def _create_card_widget(self, parent: tk.Frame, card: Card, *, colors: dict, face_down: bool, active: bool) -> tk.Frame:
        bg = colors.get("PANEL", "#0b3d2e")
        card_bg = colors.get("CARD", "#f8fafc")
        card_fg = "#e2e8f0" if face_down else colors.get("TEXT", "#0f172a")
        border = colors.get("BORDER", "#1e293b")
        suit_symbol, suit_color = self._suit_symbol_and_color(card)
        frame = tk.Frame(parent, width=70, height=100, bg=bg, highlightbackground=border, highlightthickness=(3 if active else 2))
        frame.pack_propagate(False)
        inner_bg = colors.get("BTN", "#94a3b8") if face_down else card_bg
        inner = tk.Frame(frame, bg=inner_bg, highlightthickness=0)
        inner.pack(fill="both", expand=True, padx=4, pady=4)
        if face_down:
            back = tk.Label(inner, text="###", bg=inner["bg"], fg=card_fg, font=("Segoe UI", 14, "bold"))
            back.pack(expand=True)
            return frame
        top = tk.Label(inner, text=card.rank, bg=inner["bg"], fg=suit_color, font=("Segoe UI", 11, "bold"), anchor="w")
        top.pack(anchor="nw", padx=4, pady=(2, 0))
        center = tk.Label(inner, text=suit_symbol, bg=inner["bg"], fg=suit_color, font=("Segoe UI", 22))
        center.pack(expand=True)
        bottom = tk.Label(inner, text=card.rank, bg=inner["bg"], fg=suit_color, font=("Segoe UI", 11, "bold"), anchor="e")
        bottom.pack(anchor="se", padx=4, pady=(0, 2))
        return frame

    def _suit_symbol_and_color(self, card: Card) -> tuple[str, str]:
        symbol_map = {"Hearts": "♥", "Diamonds": "♦", "Clubs": "♣", "Spades": "♠"}
        symbol = symbol_map.get(card.suit, "?")
        colors = PALETTES.get(self.theme_var.get(), PALETTES["default"])
        red = colors.get("ACCENT", "#ef4444")
        black = colors.get("TEXT", "#0f172a")
        if card.suit in {"Hearts", "Diamonds"}:
            return symbol, red
        return symbol, black

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
        self._render_hand(self.dealer_hand, self.dealer_cards_frame, reveal=show_dealer_hole, label="Dealer")
        # Clear and render player hands
        for child in self.player_cards_frame.winfo_children():
            child.destroy()
        for idx, hand in enumerate(self.player_hands):
            active = idx == self.current_hand_index and not self.round_over
            result = self.hand_results[idx]
            self._render_hand(
                hand,
                self.player_cards_frame,
                reveal=True,
                label=f"Hand {idx + 1}",
                active=active,
                result_text=result,
            )
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

    def _update_buttons(self, *, force_disable: bool = False) -> None:
        playing = not self.round_over and not force_disable
        state = "disabled" if not playing else "normal"
        self.hit_btn.config(state=state)
        self.stand_btn.config(state=state)
        self.double_btn.config(state="normal" if playing and self._can_double() else "disabled")
        self.split_btn.config(state="normal" if playing and self._can_split() else "disabled")
        self.insurance_btn.config(state="normal" if playing and self._can_offer_insurance() and not self.insurance_bet else "disabled")
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
            ("Show totals", self.show_totals, self._refresh_ui),
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
        style.configure("Panel.TFrame", background=panel, relief="solid", borderwidth=1)
        style.configure("Banner.TLabel", background=panel, foreground=text, font=("Segoe UI", 14, "bold"), padding=(2, 1))
        style.configure("Muted.TLabel", background=panel, foreground=muted, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=panel, foreground=text, font=("Segoe UI", 11, "bold"), padding=(1, 1))
        style.configure("App.TCheckbutton", background=panel, foreground=text, padding=4)
        style.configure("App.TCombobox", fieldbackground=panel, background=panel, foreground=text, padding=6, relief="flat")
        style.configure("Accent.TButton", padding=(12, 6), background=accent, foreground=text, borderwidth=0, relief="flat")
        style.map("Accent.TButton", background=[("active", accent)], foreground=[("active", bg)])

    def _load_settings(self) -> None:
        try:
            if self.settings_path.exists():
                data = json.loads(self.settings_path.read_text(encoding="utf-8"))
                theme = data.get("theme")
                if theme and theme in PALETTES:
                    self.theme_var.set(theme)
                if "show_totals" in data:
                    self.show_totals.set(bool(data["show_totals"]))
        except Exception:
            pass

    def _save_settings(self) -> None:
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(
                json.dumps(
                    {
                        "theme": self.theme_var.get(),
                        "show_totals": self.show_totals.get(),
                    }
                ),
                encoding="utf-8",
            )
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
        style.configure("BJ.TLabel", background=panel, foreground=text, font=("Segoe UI", 11))
        style.configure("BJ.Muted.TLabel", background=panel, foreground=muted, font=("Segoe UI", 10))
        style.configure(
            "BJ.TButton",
            padding=(12, 6),
            foreground=text,
            background=btn_bg,
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "BJ.TButton",
            background=[("active", accent), ("disabled", panel)],
            foreground=[("active", bg), ("disabled", muted)],
        )
        style.configure("BJ.TFrame", background=panel, relief="solid", borderwidth=1, padding=8)
        style.configure("BJ.TEntry", fieldbackground=panel, foreground=text, insertcolor=accent, padding=6, relief="flat")
        style.map("BJ.TEntry", fieldbackground=[("focus", panel)], foreground=[("disabled", muted)])

        # Apply to tk labels
        self.title_label.configure(bg=bg, fg=text)
        self.subtitle_label.configure(bg=bg, fg=muted)

        # Update frames backgrounds
        self.main_frame.configure(style="BJ.TFrame")
        self.btn_frame.configure(style="BJ.TFrame")
        self.dealer_cards_frame.configure(bg=panel, highlightbackground=colors.get("BORDER", accent), highlightthickness=1)
        self.player_cards_frame.configure(bg=panel, highlightbackground=colors.get("BORDER", accent), highlightthickness=1)
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
