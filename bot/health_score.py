"""Score server health from already-collected metrics."""

from dataclasses import dataclass


@dataclass
class HealthScore:
    """A simple 0-100 score plus human-readable deductions."""

    score: int
    deductions: list[str]


def calculateHealthScore(
    memoryPercent: float,
    temperatureCelsius: float | None,
    freeGb: float | None,
    tps: float | None,
    backupAgeMinutes: int | None,
) -> HealthScore:
    """Calculate a small-server health score without extra probing."""
    score = 100
    deductions = []
    if tps is None:
        score -= 10
        deductions.append("TPS unavailable")
    elif tps < 18:
        score -= 25
        deductions.append(f"TPS is low ({tps:.1f})")
    elif tps < 19.5:
        score -= 10
        deductions.append(f"TPS is slightly low ({tps:.1f})")
    if temperatureCelsius is not None and temperatureCelsius >= 80:
        score -= 20
        deductions.append(f"CPU is hot ({temperatureCelsius:.1f}°C)")
    elif temperatureCelsius is not None and temperatureCelsius >= 75:
        score -= 10
        deductions.append(f"CPU is warm ({temperatureCelsius:.1f}°C)")
    if memoryPercent >= 90:
        score -= 20
        deductions.append(f"Memory usage is high ({memoryPercent:.1f}%)")
    elif memoryPercent >= 85:
        score -= 10
        deductions.append(f"Memory usage is elevated ({memoryPercent:.1f}%)")
    if freeGb is not None and freeGb < 10:
        score -= 20
        deductions.append(f"HDD free space is low ({freeGb:.1f} GiB)")
    elif freeGb is not None and freeGb < 20:
        score -= 10
        deductions.append(f"HDD free space is getting low ({freeGb:.1f} GiB)")
    if backupAgeMinutes is None:
        score -= 10
        deductions.append("No backup found")
    elif backupAgeMinutes > 120:
        score -= 10
        deductions.append(f"Latest backup is {backupAgeMinutes} minutes old")
    return HealthScore(max(0, score), deductions)
