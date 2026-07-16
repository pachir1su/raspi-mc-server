"""Durable per-Discord-account cooldowns for player self-service actions.

Cooldowns are keyed by the Discord user id (not the Minecraft account), so a
player who links several Minecraft accounts shares one cooldown per action —
they cannot dodge a teleport cooldown by switching accounts. State is written
to a small JSON file so a bot restart does not reset timers.
"""

import json
import threading
import time
from pathlib import Path


class CooldownStore:
    """File-backed cooldown timers, safe to call from bot worker threads."""

    def __init__(self, stateDir: str, fileName: str = "cooldowns.json", now=time.time):
        self._path = Path(stateDir) / fileName
        self._now = now
        self._lock = threading.Lock()
        self._expiries: dict[str, dict[str, float]] = {}
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, OSError):
            return
        if isinstance(raw, dict):
            for userId, keys in raw.items():
                if isinstance(keys, dict):
                    self._expiries[str(userId)] = {
                        str(key): float(value)
                        for key, value in keys.items()
                        if isinstance(value, (int, float))
                    }

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._expiries), encoding="utf-8")
        tmp.replace(self._path)

    def _prune(self, userId: str) -> None:
        """Drop expired keys (and empty users) so the file cannot grow forever."""
        current = self._now()
        keys = self._expiries.get(userId)
        if not keys:
            return
        alive = {key: exp for key, exp in keys.items() if exp > current}
        if alive:
            self._expiries[userId] = alive
        else:
            self._expiries.pop(userId, None)

    def remaining(self, userId: int, key: str) -> float:
        """Seconds left on this action for this account, or 0 if ready."""
        with self._lock:
            expiry = self._expiries.get(str(userId), {}).get(key)
            if expiry is None:
                return 0.0
            return max(0.0, expiry - self._now())

    def start(self, userId: int, key: str, seconds: int) -> None:
        """Begin a cooldown of `seconds` for this account/action."""
        if seconds <= 0:
            return
        with self._lock:
            uid = str(userId)
            self._prune(uid)
            self._expiries.setdefault(uid, {})[key] = self._now() + seconds
            self._save()

    def tryStart(self, userId: int, key: str, seconds: int) -> float:
        """Atomically check-and-start. Returns 0 if allowed (and starts the
        cooldown), or the remaining seconds if still cooling down."""
        with self._lock:
            uid = str(userId)
            expiry = self._expiries.get(uid, {}).get(key)
            current = self._now()
            if expiry is not None and expiry > current:
                return expiry - current
            if seconds > 0:
                self._prune(uid)
                self._expiries.setdefault(uid, {})[key] = current + seconds
                self._save()
            return 0.0


def formatRemaining(seconds: float) -> str:
    """Human-friendly Korean cooldown text (e.g. '12분 30초')."""
    total = int(seconds + 0.5)
    minutes, secs = divmod(total, 60)
    if minutes and secs:
        return f"{minutes}분 {secs}초"
    if minutes:
        return f"{minutes}분"
    return f"{secs}초"
