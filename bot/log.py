"""Logging — console + per-run log files with rotation and retention.

Design goals (mirrors what a long-running Pi service needs):
  - A fresh log file each time the bot starts (timestamp in the name), so a
    run's output is self-contained and easy to attach to Discord.
  - Rotate at midnight if the bot runs for days.
  - Prune logs older than LOG_RETENTION_DAYS on startup so the 32GB SD card
    never fills with logs.
  - Helpers to read the current file and tail recent lines (for the
    Discord /logs command).
"""

import logging
import logging.handlers
import os
import sys
import time
from datetime import datetime
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent / "logs"
_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "14"))
_READY = False
_current_file = None  # path of this run's log file (for Discord attachment)


def _prune_old():
    """Delete log files older than the retention window."""
    if not _LOG_DIR.exists():
        return
    cutoff = time.time() - _RETENTION_DAYS * 86400
    for p in _LOG_DIR.glob("bot_*.log*"):
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink()
        except OSError:
            pass


def setup():
    """Initialise logging once. Idempotent."""
    global _READY, _current_file
    if _READY:
        return
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _prune_old()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _current_file = _LOG_DIR / f"bot_{stamp}.log"

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger("mc")
    root.setLevel(logging.INFO)
    root.handlers.clear()

    # Console.
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # File, rotating at midnight, keeping retention days of history.
    fh = logging.handlers.TimedRotatingFileHandler(
        _current_file, when="midnight", backupCount=_RETENTION_DAYS, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    _READY = True


def get(name: str) -> logging.Logger:
    """Get a child logger under the 'mc' namespace."""
    if not _READY:
        setup()
    return logging.getLogger(f"mc.{name}")


def current_log_file():
    """Path of this run's log file (or None if logging isn't set up)."""
    return _current_file


def recent_lines(n: int = 30) -> str:
    """Return the last n lines of the current log file as text (may be empty)."""
    if not _current_file or not Path(_current_file).exists():
        return ""
    try:
        with open(_current_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return "".join(lines[-n:])
    except OSError:
        return ""
