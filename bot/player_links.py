"""Persistent Discord-to-Minecraft account links."""

import json
import os
import re
import tempfile
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from bot.player_info import validatePlayerName


BEDROCK_NAME_PATTERN = re.compile(r"[A-Za-z0-9_ ]{1,16}")


def validateBedrockName(minecraftName: str) -> str:
    """Accept a command-safe Floodgate gamertag, including ordinary spaces."""
    cleanedName = (minecraftName or "").strip()
    if not BEDROCK_NAME_PATTERN.fullmatch(cleanedName):
        raise ValueError(
            "Bedrock name must be 1-16 characters using letters, numbers, spaces, or _"
        )
    return cleanedName


def serverPlayerName(link: "PlayerLink", usernamePrefix: str = ".") -> str:
    """Return the exact Paper entity name used by Java or Floodgate."""
    if link.edition == "java":
        return validatePlayerName(link.minecraftName)
    if link.edition == "bedrock" and usernamePrefix == ".":
        return "." + validateBedrockName(link.minecraftName).replace(" ", "_")
    raise ValueError("Unsupported Minecraft edition or Bedrock username prefix")


def buildWhitelistCommand(link: "PlayerLink") -> str:
    """Build the narrow allowlist command used during admin approval."""
    if link.edition == "java":
        return f"whitelist add {validatePlayerName(link.minecraftName)}"
    if link.edition == "bedrock":
        return f"fwhitelist add {validateBedrockName(link.minecraftName)}"
    raise ValueError("Unsupported Minecraft edition")


@dataclass(frozen=True)
class PlayerLink:
    """One pending or approved Discord-to-Minecraft link."""

    discordUserId: int
    minecraftName: str
    approved: bool
    requestedAt: str
    approvedAt: str | None = None
    approvedBy: int | None = None
    edition: str = "java"


class PlayerLinkStore:
    """Atomically persist player links in the ignored runtime state directory."""

    def __init__(self, stateDir: str | Path):
        # Keep link state separate from other bot runtime records.
        self.stateDir = Path(stateDir)
        self.path = self.stateDir / "player-links.json"
        self.lock = threading.Lock()

    @staticmethod
    def _now() -> str:
        """Return a stable UTC timestamp for audit-friendly records."""
        return datetime.now(timezone.utc).isoformat()

    def _loadUnlocked(self) -> dict[str, dict]:
        """Load and validate the on-disk object while the caller owns the lock."""
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
        if not isinstance(raw, dict):
            raise RuntimeError("Invalid player link store")
        return raw

    def _saveUnlocked(self, raw: dict[str, dict]) -> None:
        """Replace the store atomically so a power loss cannot leave partial JSON."""
        self.stateDir.mkdir(parents=True, exist_ok=True)
        descriptor, temporaryPath = tempfile.mkstemp(
            prefix="player-links-", suffix=".json", dir=self.stateDir
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                json.dump(raw, file, ensure_ascii=False, indent=2, sort_keys=True)
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

    @staticmethod
    def _assertNameAvailable(
        raw: dict[str, dict], minecraftName: str, edition: str, discordUserId: int
    ) -> None:
        """Prevent duplicate identities while allowing prefixed cross-edition names."""
        wantedName = minecraftName.casefold()
        for item in raw.values():
            if (
                int(item["discordUserId"]) != discordUserId
                and str(item.get("edition", "java")) == edition
                and str(item["minecraftName"]).casefold() == wantedName
            ):
                raise ValueError("Minecraft name is already linked or pending")

    def request(
        self, discordUserId: int, minecraftName: str, edition: str = "java"
    ) -> PlayerLink:
        """Create or replace a pending request for one Discord user."""
        cleanedEdition = (edition or "").strip().lower()
        if cleanedEdition == "java":
            safeName = validatePlayerName(minecraftName)
        elif cleanedEdition == "bedrock":
            safeName = validateBedrockName(minecraftName)
        else:
            raise ValueError("edition must be java or bedrock")
        with self.lock:
            raw = self._loadUnlocked()
            self._assertNameAvailable(raw, safeName, cleanedEdition, discordUserId)
            link = PlayerLink(
                discordUserId=discordUserId,
                minecraftName=safeName,
                approved=False,
                requestedAt=self._now(),
                edition=cleanedEdition,
            )
            raw[str(discordUserId)] = asdict(link)
            self._saveUnlocked(raw)
        return link

    def approve(self, discordUserId: int, adminUserId: int) -> PlayerLink:
        """Approve an existing request and record which admin granted access."""
        with self.lock:
            raw = self._loadUnlocked()
            key = str(discordUserId)
            if key not in raw:
                raise KeyError("No pending link request for that Discord user")
            current = PlayerLink(**raw[key])
            self._assertNameAvailable(
                raw, current.minecraftName, current.edition, discordUserId
            )
            link = PlayerLink(
                discordUserId=current.discordUserId,
                minecraftName=current.minecraftName,
                approved=True,
                requestedAt=current.requestedAt,
                approvedAt=self._now(),
                approvedBy=adminUserId,
                edition=current.edition,
            )
            raw[key] = asdict(link)
            self._saveUnlocked(raw)
        return link

    def remove(self, discordUserId: int) -> bool:
        """Remove a pending or approved link and report whether it existed."""
        with self.lock:
            raw = self._loadUnlocked()
            removed = raw.pop(str(discordUserId), None) is not None
            if removed:
                self._saveUnlocked(raw)
        return removed

    def get(self, discordUserId: int) -> PlayerLink | None:
        """Return one link without exposing mutable store data."""
        with self.lock:
            item = self._loadUnlocked().get(str(discordUserId))
        return PlayerLink(**item) if item else None

    def list(self) -> list[PlayerLink]:
        """Return pending requests first, then approved links by player name."""
        with self.lock:
            links = [PlayerLink(**item) for item in self._loadUnlocked().values()]
        return sorted(links, key=lambda item: (item.approved, item.minecraftName.casefold()))
