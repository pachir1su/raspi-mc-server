"""Pure helpers for interpreting Raspberry Pi/Paper performance data."""

from bot.system_metrics import stripMinecraftFormatting


def parseTps(text: str) -> float | None:
    """Extract the first plausible TPS value from Paper's /tps output."""
    clean = stripMinecraftFormatting(text)
    for token in clean.replace(",", " ").split():
        try:
            value = float(token.strip("*[]()"))
        except ValueError:
            continue
        if 0 <= value <= 20:
            return value
    return None


def shouldAlert(previous, now, cooldown) -> bool:
    """Return whether a warning should be sent after cooldown filtering."""
    return previous is None or now - previous >= cooldown
