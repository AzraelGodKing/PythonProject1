"""Logging setup: one rotating log file per program in the data directory."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from arcade.core import paths

FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup(program: str, level: int = logging.INFO) -> logging.Logger:
    root = logging.getLogger()
    if not any(getattr(h, "_arcade", False) for h in root.handlers):
        try:
            handler: logging.Handler = RotatingFileHandler(
                paths.logs_dir() / f"{program}.log", maxBytes=512_000, backupCount=3, encoding="utf-8"
            )
        except OSError:
            handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(FORMAT))
        handler._arcade = True  # type: ignore[attr-defined]
        root.addHandler(handler)
        root.setLevel(level)
    return logging.getLogger(f"arcade.{program}")
