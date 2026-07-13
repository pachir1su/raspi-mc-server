"""Persistent Discord user to Minecraft player-name links."""

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from bot.player_info import validatePlayerName


@dataclass
class PlayerLink:
    """One Discord account's Minecraft identity claim."""

    discordUserId: int
    minecraftName: str
    approved: bool = False


class PlayerLinkStore:
    """Store link requests in a small atomically-written JSON file."""

    def __init__(self, stateDir: str):
        self.stateDir = Path(stateDir)
        self.path = self.stateDir / "player-links.json"

    def _loadRaw(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
        if not isinstance(raw, dict):
            raise RuntimeError("Invalid player link store")
        return raw

    def _saveRaw(self, raw: dict[str, dict]):
        self.stateDir.mkdir(parents=True, exist_ok=True)
        descriptor, temporaryPath = tempfile.mkstemp(
            prefix="player-links-", suffix=".json", dir=self.stateDir
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                json.dump(raw, file, indent=2, sort_keys=True)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporaryPath, self.path)
        except Exception:
            try:
                os.unlink(temporaryPath)
            except OSError:
                pass
            raise

    def request(self, discordUserId: int, minecraftName: str) -> PlayerLink:
        """Create or replace a pending link request."""
        validatePlayerName(minecraftName)
        raw = self._loadRaw()
        link = PlayerLink(discordUserId, minecraftName, approved=False)
        raw[str(discordUserId)] = asdict(link)
        self._saveRaw(raw)
        return link

    def approve(self, discordUserId: int, minecraftName: str | None = None) -> PlayerLink:
        """Approve a pending request, optionally overriding the player name."""
        raw = self._loadRaw()
        key = str(discordUserId)
        if key not in raw and not minecraftName:
            raise KeyError("No link request for that Discord user")
        name = minecraftName or raw[key]["minecraftName"]
        validatePlayerName(name)
        link = PlayerLink(discordUserId, name, approved=True)
        raw[key] = asdict(link)
        self._saveRaw(raw)
        return link

    def remove(self, discordUserId: int):
        """Remove a link request or approved link."""
        raw = self._loadRaw()
        raw.pop(str(discordUserId), None)
        self._saveRaw(raw)

    def get(self, discordUserId: int) -> PlayerLink | None:
        """Return a link by Discord ID."""
        raw = self._loadRaw().get(str(discordUserId))
        return PlayerLink(**raw) if raw else None

    def list(self) -> list[PlayerLink]:
        """Return every link, pending first then approved."""
        links = [PlayerLink(**item) for item in self._loadRaw().values()]
        return sorted(links, key=lambda item: (item.approved, item.minecraftName.lower()))
