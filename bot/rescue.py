"""Strict builders and parsers for linked-player rescue commands."""

import math
import re
from dataclasses import dataclass

from bot.player_names import buildPlayerSelector, validateServerPlayerName


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
        raise ValueError("MC_SPAWN_DIMENSION은 overworld, nether, the_end 중 하나여야 합니다")
    coordinates = tuple(float(value) for value in (x, y, z))
    if not all(math.isfinite(value) for value in coordinates):
        raise ValueError("MC_SPAWN 좌표는 유한한 숫자여야 합니다")
    if abs(coordinates[0]) > 30_000_000 or abs(coordinates[2]) > 30_000_000:
        raise ValueError("MC_SPAWN X/Z가 마인크래프트 월드 경계를 벗어납니다")
    if not -2048 <= coordinates[1] <= 2048:
        raise ValueError("MC_SPAWN Y가 안전한 설정 범위를 벗어납니다")
    return RescueDestination(cleanedDimension, *coordinates)


def buildSpawnCommand(playerName: str, destination: RescueDestination) -> str:
    """Build only the fixed self-teleport command accepted by the friend cog."""
    playerTarget = buildPlayerSelector(validateServerPlayerName(playerName))
    dimensionId = DIMENSION_IDS[destination.dimension]
    coordinates = " ".join(f"{value:g}" for value in (destination.x, destination.y, destination.z))
    return f"execute in {dimensionId} run tp {playerTarget} {coordinates}"


def buildAutomaticSpawnCommand(playerName: str) -> str:
    """Ask the bundled Paper plugin to use the live world's configured spawn."""
    safeName = validateServerPlayerName(playerName)
    return f"raspiops rescue {safeName}"


def parsePosition(positionOutput: str, dimensionOutput: str) -> tuple[str, float, float, float]:
    """Parse Paper's entity NBT replies for the linked player's own location."""
    positionMatch = POSITION_PATTERN.search(positionOutput or "")
    dimensionMatch = DIMENSION_PATTERN.search(dimensionOutput or "")
    if not positionMatch or not dimensionMatch:
        raise ValueError("플레이어 위치를 확인할 수 없습니다. 오프라인일 수 있습니다")
    dimension = {
        "the_nether": "nether",
        "the_end": "the_end",
        "overworld": "overworld",
    }[dimensionMatch.group(1)]
    x, y, z = (float(value) for value in positionMatch.groups())
    return dimension, x, y, z
