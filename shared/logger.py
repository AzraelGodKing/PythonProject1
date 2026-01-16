"""
Centralized logging infrastructure for all games.

Provides consistent logging setup with rotating file handlers,
configurable log levels, and structured output.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    log_dir: Optional[Path] = None,
    level: int = logging.INFO,
    console: bool = True,
    file: bool = True,
) -> logging.Logger:
    """
    Set up a logger with file and console handlers.

    Args:
        name: Logger name (usually game name, e.g., "blackjack")
        log_dir: Directory for log files (default: data/logs/)
        level: Logging level (default: INFO)
        console: Whether to log to console (default: True)
        file: Whether to log to file (default: True)

    Returns:
        Configured logger instance

    Example:
        logger = setup_logger("blackjack")
        logger.info("Game started")
        logger.warning("Low balance")
        logger.error("Failed to save", exc_info=True)
    """
    # Get or create logger
    logger = logging.getLogger(name)

    # Don't add handlers if already configured
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    simple_formatter = logging.Formatter(
        fmt="%(levelname)s: %(message)s"
    )

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)

    # File handler with rotation
    if file:
        if log_dir is None:
            # Default to data/logs/ relative to project root
            project_root = Path(__file__).parent.parent
            log_dir = project_root / "data" / "logs"

        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{name}.log"

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1024 * 1024,  # 1 MB
            backupCount=5,  # Keep 5 backup files
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    # Don't propagate to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger or create a basic one.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Create basic logger if not yet configured
        return setup_logger(name)
    return logger


def set_log_level(logger: logging.Logger, level: int) -> None:
    """
    Change log level for logger and all its handlers.

    Args:
        logger: Logger instance
        level: New logging level (e.g., logging.DEBUG)
    """
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


def enable_debug_logging(logger: logging.Logger) -> None:
    """
    Enable DEBUG level logging for a logger.

    Args:
        logger: Logger instance
    """
    set_log_level(logger, logging.DEBUG)


def disable_console_logging(logger: logging.Logger) -> None:
    """
    Remove console handlers from logger (file logging only).

    Args:
        logger: Logger instance
    """
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
            logger.removeHandler(handler)


def log_exception(logger: logging.Logger, message: str, exc: Exception) -> None:
    """
    Log an exception with full traceback.

    Args:
        logger: Logger instance
        message: Context message
        exc: Exception instance
    """
    logger.error(f"{message}: {exc}", exc_info=True)


# Pre-configure logging for common Python warnings
logging.captureWarnings(True)
warnings_logger = logging.getLogger('py.warnings')
warnings_logger.setLevel(logging.WARNING)
