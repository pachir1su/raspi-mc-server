"""Lightweight coordinate book and image storage for friends."""

import json
import os
import re
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


PLACE_NAME = re.compile(r"^[^\r\n]{1,40}$")
DIMENSIONS = {"overworld", "nether", "the_end"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class Place:
    """One named Minecraft location."""

    name: str
    dimension: str
    x: int
    y: int
    z: int
    description: str
    imagePath: str | None
    createdBy: int
    createdAt: str


class ImageStore:
    """Persist bounded user images under the ignored runtime state directory."""

    def __init__(self, stateDir: str | Path):
        # Use a dedicated folder so backup and cleanup policies can target media.
        self.root = Path(stateDir) / "friend-media"

    def save(self, content: bytes, filename: str, contentType: str | None) -> str:
        """Validate and save one image, returning its runtime-relative path."""
        suffix = Path(filename).suffix.lower()
        if not contentType or not contentType.lower().startswith("image/"):
            raise ValueError("Attachment must be an image")
        if suffix not in IMAGE_SUFFIXES:
            raise ValueError("Image must be PNG, JPEG, WebP, or GIF")
        if not content or len(content) > MAX_IMAGE_BYTES:
            raise ValueError("Image must be between 1 byte and 5 MiB")
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{uuid.uuid4().hex}{suffix}"
        path.write_bytes(content)
        return str(path)

    def safePath(self, imagePath: str | None) -> Path | None:
        """Resolve only files that remain inside the managed media directory."""
        if not imagePath:
            return None
        try:
            path = Path(imagePath).resolve()
            path.relative_to(self.root.resolve())
            return path
        except (OSError, ValueError):
            return None

    def remove(self, imagePath: str | None) -> None:
        """Best-effort removal without trusting a path loaded from runtime JSON."""
        path = self.safePath(imagePath)
        if path:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


class PlaceStore:
    """Atomically store a small shared coordinate book."""

    def __init__(self, stateDir: str | Path, limit: int = 250):
        # Bound the record count so list/read costs stay tiny on a Raspberry Pi.
        self.stateDir = Path(stateDir)
        self.path = self.stateDir / "places.json"
        self.limit = limit
        self.lock = threading.Lock()

    def _loadUnlocked(self) -> dict[str, dict]:
        """Load the raw place dictionary while the caller owns the lock."""
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
        if not isinstance(raw, dict):
            raise RuntimeError("Invalid coordinate book")
        return raw

    def _saveUnlocked(self, raw: dict[str, dict]) -> None:
        """Atomically replace the JSON coordinate book."""
        self.stateDir.mkdir(parents=True, exist_ok=True)
        descriptor, temporaryPath = tempfile.mkstemp(
            prefix="places-", suffix=".json", dir=self.stateDir
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
    def _key(name: str) -> str:
        """Validate a display name and return its case-insensitive key."""
        cleanedName = (name or "").strip()
        if not PLACE_NAME.fullmatch(cleanedName):
            raise ValueError("Place name must be 1-40 characters on one line")
        return cleanedName.casefold()

    def save(
        self,
        name: str,
        dimension: str,
        x: int,
        y: int,
        z: int,
        description: str,
        imagePath: str | None,
        createdBy: int,
    ) -> tuple[Place, Place | None]:
        """Create or replace a place and return the previous record if present."""
        key = self._key(name)
        cleanedName = name.strip()
        cleanedDimension = dimension.strip().lower()
        if cleanedDimension not in DIMENSIONS:
            raise ValueError("Dimension must be overworld, nether, or the_end")
        cleanedDescription = (description or "").strip()
        if len(cleanedDescription) > 500:
            raise ValueError("Description must be 500 characters or fewer")
        place = Place(
            name=cleanedName,
            dimension=cleanedDimension,
            x=int(x),
            y=int(y),
            z=int(z),
            description=cleanedDescription,
            imagePath=imagePath,
            createdBy=createdBy,
            createdAt=datetime.now(timezone.utc).isoformat(),
        )
        with self.lock:
            raw = self._loadUnlocked()
            if key not in raw and len(raw) >= self.limit:
                raise ValueError(f"Coordinate book is limited to {self.limit} places")
            previous = Place(**raw[key]) if key in raw else None
            raw[key] = asdict(place)
            self._saveUnlocked(raw)
        return place, previous

    def get(self, name: str) -> Place | None:
        """Look up one place by case-insensitive name."""
        key = self._key(name)
        with self.lock:
            item = self._loadUnlocked().get(key)
        return Place(**item) if item else None

    def list(self) -> list[Place]:
        """Return every place in name order."""
        with self.lock:
            places = [Place(**item) for item in self._loadUnlocked().values()]
        return sorted(places, key=lambda item: item.name.casefold())

    def delete(self, name: str) -> Place | None:
        """Delete a place and return it so callers can remove its image."""
        key = self._key(name)
        with self.lock:
            raw = self._loadUnlocked()
            item = raw.pop(key, None)
            if item is not None:
                self._saveUnlocked(raw)
        return Place(**item) if item else None


def buildMapLink(template: str, place: Place) -> str | None:
    """Expand a configured web-map URL template without running a renderer."""
    cleanedTemplate = (template or "").strip()
    if not cleanedTemplate:
        return None
    if not cleanedTemplate.startswith(("https://", "http://")):
        raise ValueError("MC_MAP_URL_TEMPLATE must start with http:// or https://")
    values = {
        "dimension": quote(place.dimension, safe=""),
        "x": str(place.x),
        "y": str(place.y),
        "z": str(place.z),
    }
    try:
        return cleanedTemplate.format_map(values)
    except (KeyError, ValueError) as error:
        raise ValueError("Invalid MC_MAP_URL_TEMPLATE placeholder") from error
