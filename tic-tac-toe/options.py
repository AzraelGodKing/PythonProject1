import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import shared.*
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared import options as shared_options


def show_options_popup(gui) -> None:
    """Display the options popup using the shared builder so other games can reuse it."""
    toggles = [
        ("Require confirmations", gui.confirm_moves, gui._toggle_confirm),
        ("Auto-start next game", gui.auto_start, gui._toggle_auto_start),
        ("Larger fonts", gui.large_fonts, gui._toggle_font_size),
        ("Animations", gui.animations_enabled, gui._toggle_animations),
        ("Sound cues", gui.sound_enabled, gui._toggle_sound),
        ("Show board coordinates", gui.show_coords, gui._toggle_show_coords),
        ("Show AI heatmap", gui.show_heatmap, gui._toggle_heatmap),
        ("Show welcome overlay at launch", gui.show_intro_overlay, gui._save_settings),
        ("Human-like Normal AI (occasional mistakes)", gui.humanish_normal, gui._save_settings),
        ("AI commentary", gui.show_commentary, gui._save_settings),
    ]
    presets = [
        ("No animation/sound preset", gui._disable_motion_sound),
        ("Reset toggles to default", gui._reset_toggles),
    ]
    shared_options.show_options_popup(
        gui,
        toggles=toggles,
        preset_actions=presets,
        title="Options",
        subtitle="Tweak visuals, sounds, and behavior to your liking.",
    )
