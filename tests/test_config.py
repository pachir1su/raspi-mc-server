"""Tests for configuration parsing helpers (이슈 G, #18)."""

import logging
import unittest

from bot.config import _guild_ids


class GuildIdParsingTests(unittest.TestCase):
    def testSingleValue(self):
        self.assertEqual([123], _guild_ids("123"))

    def testMultipleValuesWithWhitespace(self):
        self.assertEqual([111, 222, 333], _guild_ids(" 111, 222 ,333 "))

    def testEmptyValueMeansGlobal(self):
        self.assertEqual([], _guild_ids(""))
        self.assertEqual([], _guild_ids("   "))

    def testInvalidEntriesAreWarnedAndIgnored(self):
        with self.assertLogs("mc.config", level="WARNING") as captured:
            result = _guild_ids("111, abc, 222")
        self.assertEqual([111, 222], result)
        self.assertTrue(any("abc" in line for line in captured.output))

    def testAllInvalidFallsBackToGlobal(self):
        with self.assertLogs("mc.config", level="WARNING"):
            self.assertEqual([], _guild_ids("abc, xyz"))

    def testTrailingCommaIgnored(self):
        self.assertEqual([111], _guild_ids("111,"))


if __name__ == "__main__":
    unittest.main()
