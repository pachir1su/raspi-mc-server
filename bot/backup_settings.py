"""Persistent, administrator-editable backup policy."""

import json
import os
import tempfile
from dataclasses import asdict, dataclass


@dataclass
class BackupSettings:
    """Values that survive bot and Raspberry Pi restarts."""

    intervalMinutes: int = 30
    retentionHours: int = 48
    dailyRetentionDays: int = 30
    maxUsagePercent: int = 80
    minFreeGb: int = 30
    enabled: bool = True

    def validate(self):
        """Reject settings that could flood or immediately erase storage."""
        if not 10 <= self.intervalMinutes <= 10080:
            raise ValueError("intervalMinutes must be between 10 and 10080")
        if not 24 <= self.retentionHours <= 8760:
            raise ValueError("retentionHours must be between 24 and 8760")
        if not 1 <= self.dailyRetentionDays <= 3650:
            raise ValueError("dailyRetentionDays must be between 1 and 3650")
        if not 50 <= self.maxUsagePercent <= 95:
            raise ValueError("maxUsagePercent must be between 50 and 95")
        if not 1 <= self.minFreeGb <= 1000:
            raise ValueError("minFreeGb must be between 1 and 1000")


class SettingsStore:
    """Read and atomically persist the backup policy as JSON."""

    def __init__(self, stateDir: str):
        self.stateDir = os.path.abspath(stateDir)
        self.path = os.path.join(self.stateDir, "backup-settings.json")

    def load(self) -> BackupSettings:
        """Return defaults when no settings file exists yet."""
        if not os.path.exists(self.path):
            return BackupSettings()
        try:
            with open(self.path, "r", encoding="utf-8") as settingsFile:
                raw = json.load(settingsFile)
            settings = BackupSettings(**raw)
            settings.validate()
            return settings
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Invalid backup settings: {error}") from error

    def save(self, settings: BackupSettings):
        """Validate and replace the settings file without partial writes."""
        settings.validate()
        os.makedirs(self.stateDir, exist_ok=True)
        descriptor, temporaryPath = tempfile.mkstemp(
            prefix="backup-settings-", suffix=".json", dir=self.stateDir
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as settingsFile:
                json.dump(asdict(settings), settingsFile, indent=2)
                settingsFile.write("\n")
                settingsFile.flush()
                os.fsync(settingsFile.fileno())
            os.replace(temporaryPath, self.path)
        except Exception:
            try:
                os.unlink(temporaryPath)
            except OSError:
                pass
            raise
