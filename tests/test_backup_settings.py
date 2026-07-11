"""Tests for durable administrator backup settings."""

import tempfile
import unittest
from dataclasses import replace

from bot.backup_settings import BackupSettings, SettingsStore


class BackupSettingsTests(unittest.TestCase):
    """Exercise defaults, persistence, and dangerous-value rejection."""

    def testDefaultsAndRoundTrip(self):
        """A new install defaults to 30 minutes and persists edits."""
        with tempfile.TemporaryDirectory() as stateDir:
            store = SettingsStore(stateDir)
            settings = store.load()
            self.assertEqual(30, settings.intervalMinutes)
            store.save(replace(settings, intervalMinutes=45, dailyRetentionDays=60))
            loaded = store.load()
            self.assertEqual(45, loaded.intervalMinutes)
            self.assertEqual(60, loaded.dailyRetentionDays)

    def testRejectsUnsafeInterval(self):
        """Sub-ten-minute schedules are rejected to protect the Pi and HDD."""
        settings = BackupSettings(intervalMinutes=1)
        with self.assertRaises(ValueError):
            settings.validate()


if __name__ == "__main__":
    unittest.main()
