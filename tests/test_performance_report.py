"""Tests for pure performance-report helpers."""

from datetime import datetime, timedelta, timezone
import unittest

from bot.performance_report import parseTps, shouldAlert


class PerformanceReportTests(unittest.TestCase):
    def testParsePaperTpsOutput(self):
        self.assertEqual(19.97, parseTps("TPS from last 1m, 5m, 15m: 19.97, 20.0, 20.0"))

    def testParseFormattedTpsOutput(self):
        self.assertEqual(17.25, parseTps("§aTPS from last 1m: §c*17.25"))

    def testParseTpsRejectsMissingValues(self):
        self.assertIsNone(parseTps("No TPS here"))

    def testCooldownAllowsFirstAndExpiredWarnings(self):
        now = datetime.now(timezone.utc)
        cooldown = timedelta(minutes=30)
        self.assertTrue(shouldAlert(None, now, cooldown))
        self.assertFalse(shouldAlert(now - timedelta(minutes=5), now, cooldown))
        self.assertTrue(shouldAlert(now - timedelta(minutes=30), now, cooldown))


if __name__ == "__main__":
    unittest.main()
