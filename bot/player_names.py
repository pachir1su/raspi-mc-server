"""Minecraft identity normalization and safe RCON target construction."""

import re
import unicodedata


JAVA_PLAYER_NAME = re.compile(r"[A-Za-z0-9_]{1,16}")
BEDROCK_STORED_NAME = re.compile(r"[A-Za-z0-9_ ]{1,16}")
FLOODGATE_SERVER_NAME = re.compile(r"\.[A-Za-z0-9_]{1,32}")
INVISIBLE_NAME_CHARS = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")


def validateJavaName(value: str) -> str:
    """Return one command-safe Java account name."""
    if not JAVA_PLAYER_NAME.fullmatch(value or ""):
        raise ValueError("Invalid Java player name")
    return value


def validateBedrockName(value: str) -> str:
    """Normalize a Discord gamertag into the prefix-free stored identity."""
    cleanedName = unicodedata.normalize("NFKC", value or "")
    cleanedName = INVISIBLE_NAME_CHARS.sub("", cleanedName).strip()
    if cleanedName.startswith("."):
        cleanedName = cleanedName[1:].strip()
    if not BEDROCK_STORED_NAME.fullmatch(cleanedName):
        raise ValueError(
            "Bedrock name must be 1-16 characters using letters, numbers, spaces, or _"
        )
    return cleanedName


def validateServerPlayerName(value: str) -> str:
    """Accept a Java name or the exact dot-prefixed Floodgate entity name."""
    cleanedName = (value or "").strip()
    if FLOODGATE_SERVER_NAME.fullmatch(cleanedName):
        return cleanedName
    return validateJavaName(cleanedName)


def toServerPlayerName(
    storedName: str, edition: str, usernamePrefix: str = "."
) -> str:
    """Convert a stored account identity into its Paper/Floodgate entity name."""
    cleanedEdition = (edition or "").strip().lower()
    if cleanedEdition == "java":
        return validateJavaName(storedName)
    if cleanedEdition == "bedrock" and usernamePrefix == ".":
        return "." + validateBedrockName(storedName).replace(" ", "_")
    raise ValueError("Unsupported Minecraft edition or Bedrock username prefix")


def escapeSelectorValue(value: str) -> str:
    """Escape one already validated string for a quoted Minecraft selector value."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def buildPlayerSelector(serverName: str) -> str:
    """Build a single-player selector without allowing selector injection."""
    safeName = validateServerPlayerName(serverName)
    return f'@a[name="{escapeSelectorValue(safeName)}",limit=1]'
