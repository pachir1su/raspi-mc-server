"""Tests for idle-aware automatic backup scheduling (이슈 I, #16)."""

import tempfile
import unittest
from pathlib import Path

from bot.cogs.admin import IDLE_INTERVAL_MULTIPLIER, _autoBackupDecision
from bot.world_storage import WorldStorage


class AutoBackupDecisionTests(unittest.TestCase):
    def testActivePlayersBackUpWhenDue(self):
        self.assertEqual(
            "backup", _autoBackupDecision(2, True, 30.0, 30)
        )

    def testIdleAndUnchangedSkips(self):
        self.assertEqual(
            "skip_idle_unchanged", _autoBackupDecision(0, False, 999.0, 30)
        )

    def testIdleButChangedWaitsForLongerInterval(self):
        # 접속자 0명이면 주기를 늘려 아직 때가 아닙니다.
        self.assertEqual(
            "skip_not_due", _autoBackupDecision(0, True, 30.0, 30)
        )

    def testIdleAndChangedBacksUpAfterExtendedInterval(self):
        self.assertEqual(
            "backup",
            _autoBackupDecision(0, True, 30 * IDLE_INTERVAL_MULTIPLIER, 30),
        )

    def testUnknownPlayerCountBacksUpNormally(self):
        # RCON 실패(None)면 안전하게 평소 주기대로 백업합니다.
        self.assertEqual("backup", _autoBackupDecision(None, True, 30.0, 30))
        self.assertEqual("backup", _autoBackupDecision(None, False, 30.0, 30))


class NewestWorldMtimeTests(unittest.TestCase):
    def _storage(self, serverDir: Path) -> WorldStorage:
        return WorldStorage(str(serverDir), str(serverDir), requireMount=False)

    def testReturnsNoneWithoutWorlds(self):
        with tempfile.TemporaryDirectory() as temporaryDir:
            storage = self._storage(Path(temporaryDir))
            self.assertIsNone(storage.newestWorldMtime())

    def testReturnsMtimeWhenWorldExists(self):
        with tempfile.TemporaryDirectory() as temporaryDir:
            serverDir = Path(temporaryDir)
            world = serverDir / "world"
            world.mkdir()
            (world / "level.dat").write_bytes(b"x")
            storage = self._storage(serverDir)
            self.assertIsInstance(storage.newestWorldMtime(), float)


if __name__ == "__main__":
    unittest.main()
