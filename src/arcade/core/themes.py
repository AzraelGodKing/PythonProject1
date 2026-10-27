"""Colour themes.

Each theme is a :class:`Palette` of named roles. The colourblind themes avoid
the colour pairs that are hard to tell apart for that kind of colour vision
and lean on the Okabe-Ito palette for status colours. Tests check that every
theme keeps text readable (WCAG contrast of at least 4.5:1).
"""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class Palette:
    bg: str  # window background
    panel: str  # raised surfaces
    border: str
    text: str
    muted: str  # secondary text
    accent: str  # headings, highlights
    button: str
    button_text: str
    good: str  # wins, safe
    bad: str  # losses, danger
    warn: str
    card_face: str
    card_back: str
    suit_red: str  # hearts and diamonds, drawn on card_face
    suit_black: str
    # Minesweeper digit colours 1-8, drawn on panel.
    digits: tuple[str, ...]


OKABE_ITO_DIGITS = ("#56b4e9", "#009e73", "#e69f00", "#cc79a7", "#f0e442", "#6cb6ff", "#d55e00", "#ffffff")

THEMES: dict[str, Palette] = {
    "default": Palette(
        bg="#0c1222",
        panel="#142039",
        border="#2c4163",
        text="#f8fafc",
        muted="#cbd5e1",
        accent="#7dd3fc",
        button="#2563eb",
        button_text="#ffffff",
        good="#4ade80",
        bad="#f87171",
        warn="#fbbf24",
        card_face="#f8fafc",
        card_back="#1e40af",
        suit_red="#b91c1c",
        suit_black="#0f172a",
        digits=("#60a5fa", "#4ade80", "#f87171", "#c084fc", "#fbbf24", "#22d3ee", "#f472b6", "#e2e8f0"),
    ),
    "dark": Palette(
        bg="#0b0f17",
        panel="#151b26",
        border="#2a3343",
        text="#e5e7eb",
        muted="#9ca3af",
        accent="#67e8f9",
        button="#0e7490",
        button_text="#ffffff",
        good="#34d399",
        bad="#fb7185",
        warn="#facc15",
        card_face="#e5e7eb",
        card_back="#334155",
        suit_red="#b91c1c",
        suit_black="#111827",
        digits=("#7dd3fc", "#6ee7b7", "#fda4af", "#d8b4fe", "#fde047", "#5eead4", "#f9a8d4", "#f3f4f6"),
    ),
    "light": Palette(
        bg="#f8fafc",
        panel="#e2e8f0",
        border="#94a3b8",
        text="#0f172a",
        muted="#334155",
        accent="#1d4ed8",
        button="#1d4ed8",
        button_text="#ffffff",
        good="#15803d",
        bad="#b91c1c",
        warn="#92400e",
        card_face="#ffffff",
        card_back="#1e3a8a",
        suit_red="#b91c1c",
        suit_black="#0f172a",
        digits=("#1d4ed8", "#15803d", "#b91c1c", "#6d28d9", "#92400e", "#0e7490", "#9d174d", "#111827"),
    ),
    "high_contrast": Palette(
        bg="#000000",
        panel="#000000",
        border="#ffffff",
        text="#ffffff",
        muted="#ffffff",
        accent="#ffff00",
        button="#ffff00",
        button_text="#000000",
        good="#00ff00",
        bad="#ff6b6b",
        warn="#ffff00",
        card_face="#ffffff",
        card_back="#0000aa",
        suit_red="#b00000",
        suit_black="#000000",
        digits=("#00ffff", "#00ff00", "#ff6b6b", "#ff00ff", "#ffff00", "#ffffff", "#ffa500", "#ffffff"),
    ),
    # Red/green confusion: status uses blue vs orange, never red vs green.
    "colorblind_protan": Palette(
        bg="#0d152a",
        panel="#16223b",
        border="#304566",
        text="#f1f5f9",
        muted="#cbd5e1",
        accent="#f0e442",
        button="#0072b2",
        button_text="#ffffff",
        good="#56b4e9",
        bad="#e69f00",
        warn="#f0e442",
        card_face="#f8fafc",
        card_back="#0072b2",
        suit_red="#0072b2",
        suit_black="#000000",
        digits=OKABE_ITO_DIGITS,
    ),
    "colorblind_deutan": Palette(
        bg="#0d1426",
        panel="#1a263c",
        border="#2c3f5c",
        text="#f1f5f9",
        muted="#cbd5e1",
        accent="#e69f00",
        button="#0072b2",
        button_text="#ffffff",
        good="#56b4e9",
        bad="#e69f00",
        warn="#f0e442",
        card_face="#f8fafc",
        card_back="#0072b2",
        suit_red="#a8580a",
        suit_black="#000000",
        digits=OKABE_ITO_DIGITS,
    ),
    # Blue/yellow confusion: status uses teal vs pink/vermillion.
    "colorblind_tritan": Palette(
        bg="#0f172a",
        panel="#1b2540",
        border="#33476b",
        text="#f1f5f9",
        muted="#cbd5e1",
        accent="#ff8ba7",
        button="#9d174d",
        button_text="#ffffff",
        good="#2dd4bf",
        bad="#ff6f61",
        warn="#ff8ba7",
        card_face="#f8fafc",
        card_back="#9d174d",
        suit_red="#c2185b",
        suit_black="#000000",
        digits=("#2dd4bf", "#ff8ba7", "#ff6f61", "#e2e8f0", "#5eead4", "#f9a8d4", "#fca5a5", "#ffffff"),
    ),
    "monochrome": Palette(
        bg="#0e1117",
        panel="#1a1f29",
        border="#4b5563",
        text="#f3f4f6",
        muted="#d1d5db",
        accent="#ffffff",
        button="#e5e7eb",
        button_text="#111827",
        good="#ffffff",
        bad="#d1d5db",
        warn="#e5e7eb",
        card_face="#f9fafb",
        card_back="#374151",
        suit_red="#4b5563",
        suit_black="#000000",
        digits=("#ffffff", "#e5e7eb", "#d1d5db", "#f3f4f6", "#ffffff", "#e5e7eb", "#d1d5db", "#ffffff"),
    ),
}

DEFAULT_THEME = "default"
ROLE_NAMES = tuple(f.name for f in fields(Palette) if f.name != "digits")


def get(name: str) -> Palette:
    return THEMES.get(name, THEMES[DEFAULT_THEME])


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(fg: str, bg: str) -> float:
    """WCAG 2 contrast ratio between two ``#rrggbb`` colours."""
    a, b = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)
