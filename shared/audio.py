"""Shared audio utilities (stubbed for simple click cues)."""

from __future__ import annotations

import os
import wave
import struct
import math
import tempfile
from pathlib import Path
from typing import Optional

try:
    import winsound  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    winsound = None  # type: ignore[assignment]


def _generate_click(path: Path, duration_ms: int = 60, freq: int = 1000) -> None:
    """Generate a simple sine wave wav file."""
    framerate = 44100
    amp = 32767
    samples = int(framerate * duration_ms / 1000)
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(framerate)
        for i in range(samples):
            val = int(amp * math.sin(2 * math.pi * freq * (i / framerate)))
            wav.writeframes(struct.pack("<h", val))


class ClickPlayer:
    """Tiny helper to play a click sound if available."""

    def __init__(self) -> None:
        self._click_path: Optional[Path] = None

    def _ensure_click(self) -> Optional[Path]:
        if self._click_path and self._click_path.exists():
            return self._click_path
        tmp = Path(tempfile.gettempdir()) / "launcher_click.wav"
        try:
            _generate_click(tmp)
            self._click_path = tmp
            return tmp
        except Exception:
            return None

    def play_click(self) -> None:
        if not winsound:
            return
        path = self._ensure_click()
        if not path:
            return
        try:
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass
