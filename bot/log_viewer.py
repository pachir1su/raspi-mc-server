"""Efficient bot and Paper log previews for Discord."""

from pathlib import Path


ERROR_MARKERS = (" error", "[error]", "exception", "traceback", "failed", "fatal")
WARNING_MARKERS = ERROR_MARKERS + (" warning", "[warn]", "warn:")


def readTail(path: str | Path, maxBytes: int = 256 * 1024) -> str:
    """Read only the tail of a potentially large UTF-8 log file."""
    logPath = Path(path)
    if not logPath.is_file():
        raise FileNotFoundError(str(logPath))
    with logPath.open("rb") as logFile:
        logFile.seek(0, 2)
        size = logFile.tell()
        logFile.seek(max(0, size - maxBytes))
        data = logFile.read()
    return data.decode("utf-8", errors="replace")


def filterImportant(text: str, includeWarnings: bool = True, limit: int = 40) -> str:
    """Return newest error/warning lines with a little continuation context."""
    markers = WARNING_MARKERS if includeWarnings else ERROR_MARKERS
    lines = text.splitlines()
    selected = []
    for index, line in enumerate(lines):
        lowered = f" {line.lower()}"
        if any(marker in lowered for marker in markers):
            selected.append(line)
            for continuation in lines[index + 1:index + 3]:
                if continuation.startswith((" ", "\t", "at ", "Caused by:")):
                    selected.append(continuation)
    return "\n".join(selected[-limit:]) or "No matching warning/error lines."


def discordPreview(text: str, limit: int = 1800) -> str:
    """Fit a readable log tail into one Discord message code block."""
    normalized = text.replace("```", "''' ").strip()
    return normalized[-limit:] or "No log content."
