"""Logging — console + per-run log files with rotation and retention.

Design goals (mirrors what a long-running Pi service needs):
  - A fresh log file each time the bot starts (timestamp in the name), so a
    run's output is self-contained and easy to attach to Discord.
  - Roll over to a new timestamped file when the current one crosses a size
    limit (LOG_MAX_BYTES) or the local date changes, so neither a busy day nor
    a multi-day run produces one unwieldy file.
  - Every line is timestamped (date + time) so events can be placed exactly.
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
from datetime import date, datetime
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent / "logs"
_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "14"))
# Roll to a new file once the current one would exceed this many bytes.
# 0 disables the size trigger and leaves only the daily (date-change) roll.
_MAX_BYTES = max(0, int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024))))
_READY = False
_handler = None  # the active file handler (its baseFilename is the live file)


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


def _new_log_path():
    """A unique bot_<timestamp>.log path (adds a counter on same-second collisions)."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = _LOG_DIR / f"bot_{stamp}.log"
    counter = 1
    while candidate.exists():
        candidate = _LOG_DIR / f"bot_{stamp}_{counter}.log"
        counter += 1
    return candidate


class SizedTimedRotatingFileHandler(logging.handlers.BaseRotatingHandler):
    """Roll to a fresh timestamped file on a size limit or a local date change.

    Unlike the stdlib handlers this keeps the project's ``bot_<stamp>.log``
    naming for every segment instead of renaming the active file with a numeric
    or date suffix, so each file stays self-contained and easy to attach.
    """

    def __init__(self, max_bytes=0, encoding="utf-8"):
        self._max_bytes = max(0, int(max_bytes))
        super().__init__(str(_new_log_path()), mode="a", encoding=encoding, delay=False)
        self._opened_on = date.today()

    def shouldRollover(self, record):
        # Never roll an empty file — a rollover here would just make another empty one.
        if self.stream is None:
            self.stream = self._open()
        if self._max_bytes > 0:
            message = f"{self.format(record)}\n"
            self.stream.seek(0, os.SEEK_END)
            if self.stream.tell() > 0 and self.stream.tell() + len(message.encode(self.encoding or "utf-8")) > self._max_bytes:
                return True
        if date.today() != self._opened_on:
            # Only roll on a date change if something has been written.
            self.stream.seek(0, os.SEEK_END)
            if self.stream.tell() > 0:
                return True
        return False

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        self.baseFilename = os.path.abspath(str(_new_log_path()))
        self.stream = self._open()
        self._opened_on = date.today()


def setup():
    """Initialise logging once. Idempotent."""
    global _READY, _handler
    if _READY:
        return
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _prune_old()

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

    # File, rolling on size or a date change, keeping retention days of history.
    _handler = SizedTimedRotatingFileHandler(max_bytes=_MAX_BYTES)
    _handler.setFormatter(fmt)
    root.addHandler(_handler)

    _READY = True


def get(name: str) -> logging.Logger:
    """Get a child logger under the 'mc' namespace."""
    if not _READY:
        setup()
    return logging.getLogger(f"mc.{name}")


def current_log_file():
    """Path of the log file currently being written (or None if not set up)."""
    if _handler is None:
        return None
    return Path(_handler.baseFilename)


def recent_lines(n: int = 30) -> str:
    """Return the last n lines of the current log file as text (may be empty)."""
    current = current_log_file()
    if not current or not current.exists():
        return ""
    try:
        with open(current, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return "".join(lines[-n:])
    except OSError:
        return ""
