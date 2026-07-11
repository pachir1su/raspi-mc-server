"""Dependency-free Linux and Raspberry Pi health metrics."""

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SystemMetrics:
    """Small stable snapshot suitable for Discord and tests."""

    uptimeSeconds: float
    load1: float
    load5: float
    load15: float
    memoryTotalBytes: int
    memoryAvailableBytes: int
    temperatureCelsius: float | None
    cpuCount: int


def _readMemory(meminfoPath: Path) -> tuple[int, int]:
    """Read total and available memory from Linux procfs."""
    values = {}
    for line in meminfoPath.read_text(encoding="ascii").splitlines():
        if ":" not in line:
            continue
        key, rawValue = line.split(":", 1)
        match = re.search(r"(\d+)", rawValue)
        if match:
            values[key] = int(match.group(1)) * 1024
    if "MemTotal" not in values or "MemAvailable" not in values:
        raise RuntimeError("MemTotal or MemAvailable is missing from meminfo")
    return values["MemTotal"], values["MemAvailable"]


def readSystemMetrics(
    procRoot: str | Path = "/proc",
    thermalPath: str | Path = "/sys/class/thermal/thermal_zone0/temp",
) -> SystemMetrics:
    """Read one metrics snapshot without adding a psutil dependency."""
    procPath = Path(procRoot)
    uptimeSeconds = float((procPath / "uptime").read_text(encoding="ascii").split()[0])
    loadParts = (procPath / "loadavg").read_text(encoding="ascii").split()
    if len(loadParts) < 3:
        raise RuntimeError("Invalid loadavg")
    memoryTotal, memoryAvailable = _readMemory(procPath / "meminfo")
    temperature = None
    temperatureFile = Path(thermalPath)
    if temperatureFile.is_file():
        rawTemperature = float(temperatureFile.read_text(encoding="ascii").strip())
        temperature = rawTemperature / 1000 if rawTemperature > 1000 else rawTemperature
    return SystemMetrics(
        uptimeSeconds=uptimeSeconds,
        load1=float(loadParts[0]),
        load5=float(loadParts[1]),
        load15=float(loadParts[2]),
        memoryTotalBytes=memoryTotal,
        memoryAvailableBytes=memoryAvailable,
        temperatureCelsius=temperature,
        cpuCount=os.cpu_count() or 1,
    )


def parseThrottleFlags(output: str) -> list[str]:
    """Decode Raspberry Pi `vcgencmd get_throttled` current and historical bits."""
    match = re.search(r"0x([0-9a-fA-F]+)", output)
    if not match:
        return ["상태 확인 불가"]
    value = int(match.group(1), 16)
    labels = []
    bitLabels = {
        0: "현재 저전압",
        1: "현재 주파수 제한",
        2: "현재 스로틀링",
        3: "현재 온도 제한",
        16: "과거 저전압",
        17: "과거 주파수 제한",
        18: "과거 스로틀링",
        19: "과거 온도 제한",
    }
    for bit, label in bitLabels.items():
        if value & (1 << bit):
            labels.append(label)
    return labels or ["정상"]


def readThrottleFlags() -> list[str]:
    """Run the Pi firmware utility when available and fail softly elsewhere."""
    try:
        result = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if result.returncode != 0:
            return ["상태 확인 불가"]
        return parseThrottleFlags(result.stdout)
    except (OSError, subprocess.SubprocessError):
        return ["상태 확인 불가"]


def formatDuration(totalSeconds: float) -> str:
    """Format uptime without locale or external libraries."""
    seconds = max(0, int(totalSeconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def stripMinecraftFormatting(text: str) -> str:
    """Remove section-sign formatting codes from RCON command output."""
    return re.sub(r"§[0-9A-FK-ORa-fk-or]", "", text)
