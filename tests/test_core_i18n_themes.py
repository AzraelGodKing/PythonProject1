import colorsys
import json
import re
import string
from importlib import resources
from pathlib import Path

import pytest

from arcade.core import i18n, themes
from arcade.games import GAMES
from arcade.games.blackjack.logic import Action, Outcome
from arcade.games.minesweeper.logic import DIFFICULTIES as MINE_DIFFICULTIES
from arcade.games.tictactoe.logic import ACHIEVEMENTS, DIFFICULTIES, PERSONALITIES
from arcade.games.yahtzee.logic import CATEGORIES

SRC = Path(__file__).resolve().parents[1] / "src" / "arcade"
LANGUAGES = ("en", "es", "fr", "de", "it", "pt", "ru", "ja", "no")


def catalog(code):
    return json.loads((resources.files("arcade") / "locales" / f"{code}.json").read_text(encoding="utf-8"))


def placeholders(text):
    return {field for _, field, _, _ in string.Formatter().parse(text) if field}


def test_nine_languages_available():
    assert tuple(i18n.available_languages()) == LANGUAGES
    assert set(i18n.LANGUAGE_NAMES) == set(LANGUAGES)


@pytest.mark.parametrize("code", LANGUAGES[1:])
def test_locale_matches_english(code):
    english, other = catalog("en"), catalog(code)
    assert set(other) == set(english), f"{code}: keys differ from en.json"
    for key, text in english.items():
        assert placeholders(other[key]) == placeholders(text), f"{code}:{key} placeholders"
        assert other[key].strip(), f"{code}:{key} is empty"


def source_text():
    return "".join(path.read_text(encoding="utf-8") for path in SRC.rglob("*.py"))


def literal_keys_in_source():
    """Keys passed straight to a translator call, or to a Toggle/labelled combo that translates them."""
    pattern = re.compile(r"""\b(?:t|Toggle|labelled_combo)\(\s*(?:\d+,\s*)?"([a-z_]+\.[a-z0-9_.]+)\"""")
    return set(pattern.findall(source_text()))


def dynamic_keys():
    keys = set()
    for game in GAMES:
        keys |= {f"{game.id}.name", f"{game.id}.description", f"{game.id}.rules"}
    keys |= {f"theme.{name}" for name in themes.THEMES}
    keys |= {f"tictactoe.difficulty.{d}" for d in DIFFICULTIES}
    keys |= {f"tictactoe.personality.{p}" for p in PERSONALITIES}
    keys |= {f"tictactoe.badge.{b}" for b in ACHIEVEMENTS}
    keys |= {f"blackjack.{a.value}" for a in Action}
    keys |= {f"blackjack.outcome.{o.value}" for o in Outcome} | {f"blackjack.result.{o.value}" for o in Outcome}
    keys |= {f"blackjack.stat.{s}" for s in ("hands", "wins", "blackjacks", "pushes", "losses", "peak_bank")}
    keys |= {f"yahtzee.cat.{c}" for c in CATEGORIES}
    keys |= {f"minesweeper.difficulty.{d}" for d in MINE_DIFFICULTIES}
    keys |= {f"scores.{k}" for k in ("games", "wins", "losses", "draws")}
    for event in ("took", "go_fish", "lucky", "book", "empty_draw"):
        keys |= {f"gofish.log.{event}.player", f"gofish.log.{event}.ai"}
    return keys


def test_every_key_used_by_the_code_exists():
    english = catalog("en")
    used = literal_keys_in_source() | dynamic_keys()
    assert used - set(english) == set()


def test_no_unused_keys():
    english = catalog("en")
    text = source_text()
    unused = {key for key in english if f'"{key}"' not in text} - dynamic_keys()
    assert unused == set()


def test_translator_fallbacks():
    t = i18n.Translator("fr")
    assert t("menu.quit") == "Quitter"
    assert t("missing.key") == "missing.key"
    assert t("scores.ranked", rank=2) == "Nouveau record : n° 2 !"
    assert t("scores.ranked") == catalog("fr")["scores.ranked"]
    assert t("scores.ranked", wrong=1) == catalog("fr")["scores.ranked"]
    assert i18n.Translator("xx").language == "en"
    assert t.has("menu.quit")
    assert not t.has("nope")


def test_every_theme_is_readable():
    for name, p in themes.THEMES.items():
        assert themes.contrast(p.text, p.bg) >= 4.5, name
        assert themes.contrast(p.text, p.panel) >= 4.5, name
        assert themes.contrast(p.muted, p.bg) >= 4.5, name
        assert themes.contrast(p.button_text, p.button) >= 4.5, name
        assert themes.contrast(p.suit_red, p.card_face) >= 3, name
        assert themes.contrast(p.suit_black, p.card_face) >= 4.5, name
        assert themes.contrast(p.accent, p.bg) >= 3, name
        for colour in (p.good, p.bad, p.warn):
            assert themes.contrast(colour, p.panel) >= 3, name
        assert len(p.digits) == 8
        for digit in p.digits:
            assert themes.contrast(digit, p.panel) >= 3, (name, digit)


def hue(hex_color):
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hsv(r, g, b)[0] * 360


@pytest.mark.parametrize("name", ["colorblind_protan", "colorblind_deutan"])
def test_red_green_themes_avoid_red_vs_green_status(name):
    p = themes.THEMES[name]
    # Win/loss colours must not be a green/red pair, which these viewers can't separate.
    assert not 75 <= hue(p.good) <= 160
    assert not (hue(p.bad) < 20 or hue(p.bad) > 340)


def test_contrast_maths():
    assert themes.contrast("#000000", "#ffffff") == pytest.approx(21)
    assert themes.contrast("#123456", "#123456") == pytest.approx(1)
    assert themes.get("nope") is themes.THEMES["default"]
