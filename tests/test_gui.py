"""Smoke tests that build every window and drive it through a few moves.

They run under a virtual display in CI (xvfb) and skip when no display exists.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from arcade.core import scores, themes
from arcade.core.cards import Shoe, cards
from arcade.core.settings import hub_settings

pytestmark = pytest.mark.gui


def pump(root):
    root.update_idletasks()
    root.update()


def cycle_preferences(app):
    """Theme and language changes rebuild every widget; make sure that works from any state."""
    root = app.root
    for theme in themes.THEMES:
        app.set_theme(theme)
        pump(root)
    for language in ("ja", "ru", "de", "en"):
        app.set_language(language)
        pump(root)
    app.show_options()
    app.show_scores()
    app.show_rules()
    app.show_about()
    pump(root)
    app.new_game()
    pump(root)


def test_tictactoe(tk_root):
    from arcade.games.tictactoe.gui import AI, HUMAN, TicTacToeApp

    app = TicTacToeApp(tk_root)
    app.game.starter = HUMAN
    app.hint()
    assert app.hint_cell is not None
    app.human_move(4)
    assert app.game.board[4] == HUMAN
    app._ai_move()
    assert app.game.board.count(AI) == 1
    app.undo()
    assert app.game.moves == []
    # Play complete games against Easy until a result is recorded.
    app._change("difficulty", "easy")
    while not app.game.over:
        if app.game.to_move == HUMAN:
            app.human_move(next(i for i, c in enumerate(app.game.board) if not c))
        else:
            app._ai_move()
    assert app.stats.get("games") == 1
    app.toggle_watch()
    app._ai_move()
    assert app.watching
    app.toggle_watch()
    assert app.score_sections()
    cycle_preferences(app)
    app.reset_scores()


def test_blackjack(tk_root):
    from arcade.games.blackjack.gui import BlackjackApp
    from arcade.games.blackjack.logic import Action, Phase

    app = BlackjackApp(tk_root)
    app.table.shoe = Shoe.stacked(cards("8S 10H 8H 7D 3C 2C 10S 10D 10C 10S"))
    app.bet_var.set(25)
    app.deal()
    assert app.table.phase is Phase.PLAYER
    app.hint()
    assert "split" in app.message.lower() or app.message
    app.act(Action.SPLIT)
    app.act(Action.STAND)
    app.act(Action.STAND)
    assert app.table.phase is Phase.DONE
    assert app.stats.get("hands") == 2
    app.show_hints.set(True)
    app._save_toggles()
    app.table.shoe = Shoe.stacked(cards("10S AH 9H KD"))
    app.deal()
    assert app.table.phase is Phase.INSURANCE
    app.insure(True)
    assert app.table.phase is Phase.DONE
    app._add_bet(100)
    app.cash_out()
    assert app.leaderboard.load() or app.table.bank.balance == 500
    cycle_preferences(app)


def test_solitaire(tk_root):
    from arcade.games.solitaire.gui import SolitaireApp

    app = SolitaireApp(tk_root)
    stock_click = type("E", (), {"x": 20, "y": 30})()
    app._on_click(stock_click)
    assert app.game.waste
    app.undo()
    assert not app.game.waste
    # Click a tableau card, then another column.
    col_click = type("E", (), {"x": app._col_x(6) + 5, "y": app._tableau_y(6, 6) + 5})()
    app._on_click(col_click)
    assert app.selected == ("tableau", 6, 6)
    app._on_double(col_click)
    assert app.selected is None
    assert app._hit(5000, 5000) is None
    cycle_preferences(app)


def test_solitaire_win_records_time(tk_root):
    from arcade.core.cards import SUITS, Card
    from arcade.games.solitaire.gui import SolitaireApp

    app = SolitaireApp(tk_root)
    g = app.game
    g.stock, g.waste, g.hidden = [], [], [0] * 7
    g.tableau = [[] for _ in range(7)]
    for i, suit in enumerate(SUITS):
        g.foundations[i] = [Card(r, suit) for r in ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q")]
        g.tableau[i] = [Card("K", suit)]
    app.autocomplete()
    assert g.won
    assert app.times.load()[0].name == "Tester"


def test_yahtzee(tk_root):
    from arcade.games.yahtzee.gui import YahtzeeApp
    from arcade.games.yahtzee.logic import CATEGORIES

    app = YahtzeeApp(tk_root)
    app.roll()
    for _ in range(10):
        pump(tk_root)
        app._animate()
    app.toggle(0)
    assert app.game.held[0]
    for category in CATEGORIES:
        if not app.game.turn_started:
            app.game.roll()
        app._animating = 0
        app.score(category)
    assert app.game.over
    assert app.leaderboard.load()[0].name == "Tester"
    cycle_preferences(app)


def test_minesweeper(tk_root):
    from arcade.games.minesweeper.gui import CELL, MinesweeperApp
    from arcade.games.minesweeper.logic import State

    app = MinesweeperApp(tk_root)
    click = type("E", (), {"x": CELL * 4 + 2, "y": CELL * 4 + 2})()
    app._click(click, "reveal")
    assert app.board.state in (State.PLAYING, State.WON)
    app._move_cursor(1, 1)
    app._act("flag", 0, 0)
    app._act("chord", 4, 4)
    # Reveal every safe cell to win.
    for r, row in enumerate(app.board.cells):
        for c, cell in enumerate(row):
            if not cell.mine and not cell.revealed:
                if cell.flagged:
                    app.board.toggle_flag(r, c)
                app._act("reveal", r, c)
    assert app.board.state is State.WON
    assert app.best_times("beginner").load()
    app._set_difficulty("expert")
    assert app.board.cols == 30
    assert app.board.state is State.READY
    app._act("reveal", 0, 0)
    mine = next((r, c) for r, row in enumerate(app.board.cells) for c, cell in enumerate(row) if cell.mine)
    app._act("reveal", *mine)
    assert app.board.state is State.LOST
    cycle_preferences(app)


def test_gofish(tk_root):
    from arcade.games.gofish.gui import GoFishApp
    from arcade.games.gofish.logic import AI, PLAYER

    app = GoFishApp(tk_root)
    for _ in range(400):
        if app.game.over:
            break
        if app.game.turn == PLAYER:
            x0, y0, *_rest = app._card_boxes[0]
            app._on_click(type("E", (), {"x": x0 + 2, "y": y0 + 2})())
        else:
            app._ai_step()
    assert app.game.over
    assert app.stats.get("games") == 1
    assert app.game.log
    assert app.game.turn in (PLAYER, AI)
    cycle_preferences(app)


def test_launcher(tk_root, monkeypatch):
    from arcade import launcher
    from arcade.core.locking import InstanceLock

    launched = []
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda cmd: launched.append(cmd))
    app = launcher.Launcher(tk_root)
    _status, button = app.cards["blackjack"]
    assert button.instate(["!disabled"])
    app.launch(launcher.GAMES[1])
    assert launched and launched[0][-1] == "arcade.games.blackjack"

    other = InstanceLock()
    assert other.acquire("tictactoe")
    try:
        app._poll()
        assert app.running == "tictactoe"
        assert button.instate(["disabled"])
        assert app.cards["tictactoe"][0].cget("text") == app.t("launcher.status.running")
        app.launch(launcher.GAMES[1])
        assert len(launched) == 1
    finally:
        other.release()
    app._poll()
    assert app.running is None
    app.set_theme("light")
    app.set_language("es")
    pump(tk_root)
    assert hub_settings()["language"] == "es"


def test_game_refuses_to_start_while_another_runs(tk_root, monkeypatch):
    from arcade.core import ui
    from arcade.core.locking import InstanceLock
    from arcade.games.yahtzee.gui import YahtzeeApp

    alerts = []
    monkeypatch.setattr(ui, "_alert_blocked", lambda t, game, owner: alerts.append((game, owner)))
    monkeypatch.setattr(ui.time, "sleep", lambda _s: None)
    holder = InstanceLock()
    holder.acquire("blackjack")
    try:
        assert ui.run_game(YahtzeeApp) == 1
    finally:
        holder.release()
    assert alerts == [("yahtzee", "blackjack")]


def test_alert_wording(tk_root, monkeypatch):
    from arcade.core import i18n, ui

    shown = []
    monkeypatch.setattr(ui.messagebox, "showwarning", lambda title, body, **k: shown.append(body))
    t = i18n.Translator("en")
    ui._alert_blocked(t, "yahtzee", "yahtzee")
    ui._alert_blocked(t, "yahtzee", "blackjack")
    assert shown == ["Yahtzee is already open.", "Blackjack is still open. Close it before starting Yahtzee."]


def test_error_reporter_logs_and_shows(tk_root):
    from arcade.games.yahtzee.gui import YahtzeeApp

    app = YahtzeeApp(tk_root)
    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        app._report_error(type(exc), exc, exc.__traceback__)


def test_modules_run_headless_without_crashing():
    """``python -m`` entry points import cleanly (the GUI part is covered above)."""
    for module in ("arcade.games.tictactoe.sim",):
        result = subprocess.run([sys.executable, "-m", module, "--rounds", "2"], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


def test_score_sections_render_with_data(tk_root):
    from arcade.games.blackjack.gui import BlackjackApp

    scores.HighScores.named("blackjack_bankroll").add("Ada", 900)
    app = BlackjackApp(tk_root)
    sections = app.score_sections()
    assert sections[0].rows[0][1] == "Ada"
    app.show_scores()
    pump(tk_root)
