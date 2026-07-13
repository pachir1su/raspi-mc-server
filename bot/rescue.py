"""Strict builders and parsers for linked-player rescue commands."""

import math
import re
from dataclasses import dataclass

from bot.player_info import validatePlayerName


DIMENSION_IDS = {
    "overworld": "minecraft:overworld",
    "nether": "minecraft:the_nether",
    "the_end": "minecraft:the_end",
}
POSITION_PATTERN = re.compile(
    r"\[\s*(-?\d+(?:\.\d+)?)[dDfF]?,\s*"
    r"(-?\d+(?:\.\d+)?)[dDfF]?,\s*"
    r"(-?\d+(?:\.\d+)?)[dDfF]?\s*\]"
)
DIMENSION_PATTERN = re.compile(r"minecraft:(overworld|the_nether|the_end)")
FLOODGATE_PLAYER_PATTERN = re.compile(r"\.[A-Za-z0-9_]{1,32}")


def validateServerPlayerName(playerName: str) -> str:
    """Accept either a Java name or a dot-prefixed Floodgate entity name."""
    cleanedName = (playerName or "").strip()
    if FLOODGATE_PLAYER_PATTERN.fullmatch(cleanedName):
        return cleanedName
    return validatePlayerName(cleanedName)


@dataclass(frozen=True)
class RescueDestination:
    """One configured, admin-controlled teleport destination."""

    dimension: str
    x: float
    y: float
    z: float


def validateDestination(
    dimension: str, x: float, y: float, z: float
) -> RescueDestination:
    """Reject unsafe, non-finite, or out-of-world rescue coordinates."""
    cleanedDimension = (dimension or "").strip().lower()
    if cleanedDimension not in DIMENSION_IDS:
        raise ValueError("MC_SPAWN_DIMENSION must be overworld, nether, or the_end")
    coordinates = tuple(float(value) for value in (x, y, z))
    if not all(math.isfinite(value) for value in coordinates):
        raise ValueError("MC_SPAWN coordinates must be finite numbers")
    if abs(coordinates[0]) > 30_000_000 or abs(coordinates[2]) > 30_000_000:
        raise ValueError("MC_SPAWN X/Z exceeds the Minecraft world border")
    if not -2048 <= coordinates[1] <= 2048:
        raise ValueError("MC_SPAWN Y is outside the safe configuration range")
    return RescueDestination(cleanedDimension, *coordinates)


def buildSpawnCommand(playerName: str, destination: RescueDestination) -> str:
    """Build only the fixed self-teleport command accepted by the friend cog."""
    safeName = validateServerPlayerName(playerName)
    dimensionId = DIMENSION_IDS[destination.dimension]
    coordinates = " ".join(f"{value:g}" for value in (destination.x, destination.y, destination.z))
    return f"execute in {dimensionId} run tp {safeName} {coordinates}"


def parsePosition(positionOutput: str, dimensionOutput: str) -> tuple[str, float, float, float]:
    """Parse Paper's entity NBT replies for the linked player's own location."""
    positionMatch = POSITION_PATTERN.search(positionOutput or "")
    dimensionMatch = DIMENSION_PATTERN.search(dimensionOutput or "")
    if not positionMatch or not dimensionMatch:
        raise ValueError("Player position is unavailable; the player may be offline")
    dimension = {
        "the_nether": "nether",
        "the_end": "the_end",
        "overworld": "overworld",
    }[dimensionMatch.group(1)]
    x, y, z = (float(value) for value in positionMatch.groups())
    return dimension, x, y, z
