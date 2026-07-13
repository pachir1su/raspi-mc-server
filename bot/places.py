"""Persistent landmark/coordinate book for the Minecraft server."""

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

_DIMENSIONS = {"overworld", "nether", "end"}


@dataclass
class Place:
    """A friend-visible saved coordinate."""

    name: str
    dimension: str
    x: int
    y: int
    z: int
    description: str
    imageUrl: str
    createdBy: int
    createdAt: str


class PlaceStore:
    """Store coordinates and optional Discord image URLs in JSON."""

    def __init__(self, stateDir: str):
        self.stateDir = Path(stateDir)
        self.path = self.stateDir / "places.json"

    def _loadRaw(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
        if not isinstance(raw, dict):
            raise RuntimeError("Invalid place store")
        return raw

    def _saveRaw(self, raw: dict[str, dict]):
        self.stateDir.mkdir(parents=True, exist_ok=True)
        descriptor, temporaryPath = tempfile.mkstemp(
            prefix="places-", suffix=".json", dir=self.stateDir
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

    def save(
        self,
        name: str,
        dimension: str,
        x: int,
        y: int,
        z: int,
        description: str,
        imageUrl: str,
        createdBy: int,
    ) -> Place:
        """Create or replace a place by case-insensitive name."""
        cleanedName = name.strip()[:80]
        if not cleanedName:
            raise ValueError("Place name is required")
        dimension = dimension.lower().strip()
        if dimension not in _DIMENSIONS:
            raise ValueError("dimension must be overworld, nether, or end")
        place = Place(
            cleanedName,
            dimension,
            x,
            y,
            z,
            description.strip()[:500],
            imageUrl.strip(),
            createdBy,
            datetime.now(timezone.utc).isoformat(),
        )
        raw = self._loadRaw()
        raw[cleanedName.lower()] = asdict(place)
        self._saveRaw(raw)
        return place

    def get(self, name: str) -> Place:
        """Return a place by name."""
        raw = self._loadRaw().get(name.strip().lower())
        if not raw:
            raise KeyError("Place not found")
        return Place(**raw)

    def delete(self, name: str):
        """Delete a place by name."""
        raw = self._loadRaw()
        if raw.pop(name.strip().lower(), None) is None:
            raise KeyError("Place not found")
        self._saveRaw(raw)

    def list(self) -> list[Place]:
        """List places alphabetically."""
        return sorted(
            (Place(**item) for item in self._loadRaw().values()),
            key=lambda item: item.name.lower(),
        )


def mapLink(baseUrl: str, place: Place) -> str:
    """Build a generic coordinate URL for an external web map."""
    if not baseUrl:
        return ""
    separator = "&" if "?" in baseUrl else "?"
    return (
        f"{baseUrl}{separator}world={place.dimension}"
        f"&x={place.x}&y={place.y}&z={place.z}&zoom=5"
    )
