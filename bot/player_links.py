"""Persistent Discord-to-Minecraft account links."""

import json
import os
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from bot.player_names import toServerPlayerName, validateBedrockName, validateJavaName


def serverPlayerName(link: "PlayerLink", usernamePrefix: str = ".") -> str:
    """Return the exact Paper entity name used by Java or Floodgate."""
    return toServerPlayerName(link.minecraftName, link.edition, usernamePrefix)


def buildWhitelistCommand(link: "PlayerLink") -> str:
    """Build the narrow allowlist command used during admin approval."""
    if link.edition == "java":
        return f"whitelist add {validateJavaName(link.minecraftName)}"
    if link.edition == "bedrock":
        return f"fwhitelist add {validateBedrockName(link.minecraftName)}"
    raise ValueError("Unsupported Minecraft edition")


def buildWhitelistRemoveCommand(link: "PlayerLink") -> str:
    """Build the matching safe whitelist removal command for one profile."""
    if link.edition == "java":
        return f"whitelist remove {validateJavaName(link.minecraftName)}"
    if link.edition == "bedrock":
        return f"fwhitelist remove {validateBedrockName(link.minecraftName)}"
    raise ValueError("Unsupported Minecraft edition")


@dataclass(frozen=True)
class PlayerLink:
    """One Minecraft profile managed for a Discord user."""

    discordUserId: int
    minecraftName: str
    approved: bool
    requestedAt: str
    approvedAt: str | None = None
    approvedBy: int | None = None
    edition: str = "java"
    linkId: str = ""


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
        """Load records and normalize the old one-account-per-user format."""
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
        if not isinstance(raw, dict):
            raise RuntimeError("Invalid player link store")
        normalized = {}
        for oldKey, item in raw.items():
            if not isinstance(item, dict):
                raise RuntimeError("Invalid player link record")
            discordUserId = int(item["discordUserId"])
            edition = str(item.get("edition", "java"))
            linkId = str(item.get("linkId") or self._legacyLinkId(oldKey, discordUserId, edition))
            normalized[linkId] = {**item, "linkId": linkId, "edition": edition}
        return normalized

    @staticmethod
    def _legacyLinkId(oldKey: str, discordUserId: int, edition: str) -> str:
        """Derive a stable ID for records written before multi-account support."""
        value = f"raspi-mc-server:{oldKey}:{discordUserId}:{edition}"
        return uuid.uuid5(uuid.NAMESPACE_URL, value).hex[:12]

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
        raw: dict[str, dict], minecraftName: str, edition: str, excludeLinkId: str = ""
    ) -> None:
        """Prevent one Minecraft identity from being assigned more than once."""
        wantedName = minecraftName.casefold()
        for linkId, item in raw.items():
            if (
                linkId != excludeLinkId
                and str(item.get("edition", "java")) == edition
                and str(item["minecraftName"]).casefold() == wantedName
            ):
                raise ValueError("Minecraft name is already assigned")

    @staticmethod
    def _validateName(minecraftName: str, edition: str) -> tuple[str, str]:
        """Validate one edition/name pair before it reaches RCON or disk."""
        cleanedEdition = (edition or "").strip().lower()
        if cleanedEdition == "java":
            return validateJavaName(minecraftName), cleanedEdition
        if cleanedEdition == "bedrock":
            return validateBedrockName(minecraftName), cleanedEdition
        raise ValueError("edition must be java or bedrock")

    def addManaged(
        self,
        discordUserId: int,
        minecraftName: str,
        edition: str,
        adminUserId: int,
    ) -> PlayerLink:
        """Add an immediately approved profile configured by an administrator."""
        safeName, cleanedEdition = self._validateName(minecraftName, edition)
        now = self._now()
        with self.lock:
            raw = self._loadUnlocked()
            self._assertNameAvailable(raw, safeName, cleanedEdition)
            link = PlayerLink(
                discordUserId=int(discordUserId),
                minecraftName=safeName,
                approved=True,
                requestedAt=now,
                approvedAt=now,
                approvedBy=int(adminUserId),
                edition=cleanedEdition,
                linkId=uuid.uuid4().hex[:12],
            )
            raw[link.linkId] = asdict(link)
            self._saveUnlocked(raw)
        return link

    def request(
        self, discordUserId: int, minecraftName: str, edition: str = "java"
    ) -> PlayerLink:
        """Create or replace a pending request for one Discord user."""
        safeName, cleanedEdition = self._validateName(minecraftName, edition)
        with self.lock:
            raw = self._loadUnlocked()
            self._assertNameAvailable(raw, safeName, cleanedEdition)
            link = PlayerLink(
                discordUserId=discordUserId,
                minecraftName=safeName,
                approved=False,
                requestedAt=self._now(),
                edition=cleanedEdition,
                linkId=uuid.uuid4().hex[:12],
            )
            raw[link.linkId] = asdict(link)
            self._saveUnlocked(raw)
        return link

    def approve(self, discordUserId: int, adminUserId: int) -> PlayerLink:
        """Approve an existing request and record which admin granted access."""
        with self.lock:
            raw = self._loadUnlocked()
            current = next(
                (
                    PlayerLink(**item)
                    for item in raw.values()
                    if int(item["discordUserId"]) == int(discordUserId)
                    and not bool(item.get("approved"))
                ),
                None,
            )
            if current is None:
                raise KeyError("No pending link request for that Discord user")
            self._assertNameAvailable(
                raw, current.minecraftName, current.edition, current.linkId
            )
            link = PlayerLink(
                discordUserId=current.discordUserId,
                minecraftName=current.minecraftName,
                approved=True,
                requestedAt=current.requestedAt,
                approvedAt=self._now(),
                approvedBy=adminUserId,
                edition=current.edition,
                linkId=current.linkId,
            )
            raw[link.linkId] = asdict(link)
            self._saveUnlocked(raw)
        return link

    def remove(self, discordUserId: int) -> bool:
        """Remove a pending or approved link and report whether it existed."""
        with self.lock:
            raw = self._loadUnlocked()
            keys = [
                linkId
                for linkId, item in raw.items()
                if int(item["discordUserId"]) == int(discordUserId)
            ]
            for linkId in keys:
                raw.pop(linkId)
            removed = bool(keys)
            if removed:
                self._saveUnlocked(raw)
        return removed

    def removeLink(self, linkId: str) -> PlayerLink | None:
        """Remove one selected profile without affecting the user's other profiles."""
        with self.lock:
            raw = self._loadUnlocked()
            item = raw.pop(str(linkId), None)
            if item is not None:
                self._saveUnlocked(raw)
        return PlayerLink(**item) if item else None

    def getById(self, linkId: str) -> PlayerLink | None:
        """Return one profile by its stable panel selection ID."""
        with self.lock:
            item = self._loadUnlocked().get(str(linkId))
        return PlayerLink(**item) if item else None

    def get(self, discordUserId: int) -> PlayerLink | None:
        """Return one link without exposing mutable store data."""
        links = self.listForUser(discordUserId, approvedOnly=False)
        return next((link for link in links if link.approved), links[0] if links else None)

    def listForUser(
        self, discordUserId: int, approvedOnly: bool = True
    ) -> list[PlayerLink]:
        """Return all profiles assigned to one Discord account."""
        with self.lock:
            links = [
                PlayerLink(**item)
                for item in self._loadUnlocked().values()
                if int(item["discordUserId"]) == int(discordUserId)
                and (not approvedOnly or bool(item.get("approved")))
            ]
        return sorted(links, key=lambda item: (item.edition, item.minecraftName.casefold()))

    def list(self) -> list[PlayerLink]:
        """Return pending requests first, then approved links by player name."""
        with self.lock:
            links = [PlayerLink(**item) for item in self._loadUnlocked().values()]
        return sorted(links, key=lambda item: (item.approved, item.minecraftName.casefold()))
