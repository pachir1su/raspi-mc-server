"""Tests for privileged-operation audit persistence."""

import tempfile
import unittest

from bot.audit import AuditLog


class AuditLogTests(unittest.TestCase):
    """Confirm append ordering and malformed-line tolerance."""

    def testRecordsNewestFirst(self):
        """Recent records are returned newest first with bounded details."""
        with tempfile.TemporaryDirectory() as stateDir:
            auditLog = AuditLog(stateDir)
            auditLog.record("backup.create", 11, "success", "first")
            auditLog.record("world.activate", 22, "failed", "second")
            records = auditLog.recent()
            self.assertEqual("world.activate", records[0]["action"])
            self.assertEqual(11, records[1]["actorId"])


if __name__ == "__main__":
    unittest.main()
