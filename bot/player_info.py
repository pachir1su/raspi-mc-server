"""Parsing and presentation helpers for player data returned by RCON."""

import re

from bot.player_names import (
    FLOODGATE_SERVER_NAME,
    JAVA_PLAYER_NAME,
    validateJavaName,
)

PLAYER_NAME = JAVA_PLAYER_NAME
ONLINE_PLAYER_NAME = re.compile(
    rf"(?:{JAVA_PLAYER_NAME.pattern}|{FLOODGATE_SERVER_NAME.pattern})"
)
ITEM_PATTERN = re.compile(
    r"Slot:\s*(-?\d+)b?.*?id:\s*[\"'](?:minecraft:)?([^\"']+)[\"']"
    r".*?(?:count|Count):\s*(\d+)b?",
    re.IGNORECASE | re.DOTALL,
)


def validatePlayerName(name: str) -> str:
    """Return a safe Java username or reject command-injection characters."""
    return validateJavaName(name)


def parseOnlinePlayers(output: str) -> list[str]:
    """Parse Paper's `list` response while preserving valid usernames only."""
    if ":" not in output:
        return []
    namesPart = output.rsplit(":", 1)[1].strip()
    if not namesPart:
        return []
    return [
        name for rawName in namesPart.split(",")
        if ONLINE_PLAYER_NAME.fullmatch(name := rawName.strip())
    ]


def slotLabel(slot: int) -> str:
    """Map Java inventory slot numbers to concise player-facing labels."""
    if 0 <= slot <= 8:
        return f"Hotbar {slot + 1}"
    if 9 <= slot <= 35:
        return f"Inventory {slot - 8}"
    return {
        100: "Boots",
        101: "Leggings",
        102: "Chestplate",
        103: "Helmet",
        -106: "Offhand",
    }.get(slot, f"Slot {slot}")


def summarizeInventory(output: str, limit: int = 40) -> str:
    """Turn common legacy and modern SNBT item fields into readable lines."""
    matches = ITEM_PATTERN.findall(output)
    if not matches:
        cleaned = " ".join(output.split())
        return cleaned[:1800] or "Inventory is empty or unavailable."
    lines = [
        f"**{slotLabel(int(slot))}** — `{itemId}` × {count}"
        for slot, itemId, count in matches[:limit]
    ]
    if len(matches) > limit:
        lines.append(f"…and {len(matches) - limit} more stack(s)")
    return "\n".join(lines)
