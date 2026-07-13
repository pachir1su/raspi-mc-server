"""Pure on-demand server health scoring for a Raspberry Pi host."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HealthInputs:
    """Metrics collected once when a user asks for the score."""

    rconOnline: bool
    tps: float | None
    temperatureCelsius: float | None
    memoryPercent: float
    diskFreePercent: float | None
    normalizedLoad5: float
    currentThrottle: bool
    historicalThrottle: bool


@dataclass(frozen=True)
class HealthResult:
    """A bounded score with concise reasons for every deduction."""

    score: int
    grade: str
    deductions: tuple[str, ...]


def _deduct(
    deductions: list[str], points: int, reason: str
) -> int:
    """Append one visible explanation and return the points to subtract."""
    deductions.append(f"-{points}: {reason}")
    return points


def calculateHealthScore(metrics: HealthInputs) -> HealthResult:
    """Calculate a conservative 0-100 score without background polling."""
    deductions: list[str] = []
    lostPoints = 0

    # Server reachability and Paper TPS carry the most gameplay weight.
    if not metrics.rconOnline:
        lostPoints += _deduct(deductions, 40, "RCON/server unavailable")
    elif metrics.tps is None:
        lostPoints += _deduct(deductions, 10, "TPS unavailable")
    elif metrics.tps < 15:
        lostPoints += _deduct(deductions, 35, f"critical TPS {metrics.tps:.1f}")
    elif metrics.tps < 18:
        lostPoints += _deduct(deductions, 22, f"low TPS {metrics.tps:.1f}")
    elif metrics.tps < 19.5:
        lostPoints += _deduct(deductions, 8, f"TPS below ideal ({metrics.tps:.1f})")

    # Temperature, memory, and load reflect Pi resource pressure.
    if metrics.temperatureCelsius is not None:
        if metrics.temperatureCelsius >= 80:
            lostPoints += _deduct(
                deductions, 20, f"CPU hot ({metrics.temperatureCelsius:.1f}°C)"
            )
        elif metrics.temperatureCelsius >= 70:
            lostPoints += _deduct(
                deductions, 10, f"CPU warm ({metrics.temperatureCelsius:.1f}°C)"
            )
    if metrics.memoryPercent >= 90:
        lostPoints += _deduct(
            deductions, 15, f"memory usage {metrics.memoryPercent:.1f}%"
        )
    elif metrics.memoryPercent >= 80:
        lostPoints += _deduct(
            deductions, 7, f"memory usage {metrics.memoryPercent:.1f}%"
        )
    if metrics.normalizedLoad5 >= 1.5:
        lostPoints += _deduct(
            deductions, 10, f"5m CPU load {metrics.normalizedLoad5:.2f}× cores"
        )
    elif metrics.normalizedLoad5 >= 1.0:
        lostPoints += _deduct(
            deductions, 5, f"5m CPU load {metrics.normalizedLoad5:.2f}× cores"
        )

    # Disk and firmware flags catch operational risks before they become lag.
    if metrics.diskFreePercent is None:
        lostPoints += _deduct(deductions, 5, "HDD usage unavailable")
    elif metrics.diskFreePercent < 5:
        lostPoints += _deduct(
            deductions, 20, f"HDD free {metrics.diskFreePercent:.1f}%"
        )
    elif metrics.diskFreePercent < 10:
        lostPoints += _deduct(
            deductions, 10, f"HDD free {metrics.diskFreePercent:.1f}%"
        )
    if metrics.currentThrottle:
        lostPoints += _deduct(deductions, 20, "current undervoltage/throttling")
    elif metrics.historicalThrottle:
        lostPoints += _deduct(deductions, 5, "past undervoltage/throttling")

    score = max(0, 100 - lostPoints)
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"
    return HealthResult(score=score, grade=grade, deductions=tuple(deductions))
