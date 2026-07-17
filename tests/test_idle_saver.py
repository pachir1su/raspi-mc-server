"""Tests for the idle power-saver state machine and gamerule helpers (#91)."""

import unittest

from bot import quick_commands as qc
from bot.idle_saver import ENTER, EXIT, NONE, decideIdleAction


class IdleDecisionTests(unittest.TestCase):
    def testEntersOnlyAfterThresholdWhileEmpty(self):
        self.assertEqual(NONE, decideIdleAction(0, 5, False, 10))
        self.assertEqual(ENTER, decideIdleAction(0, 10, False, 10))
        self.assertEqual(ENTER, decideIdleAction(0, 30, False, 10))

    def testDoesNotReEnterWhileAlreadyEco(self):
        self.assertEqual(NONE, decideIdleAction(0, 60, True, 10))

    def testExitsAsSoonAsSomeoneJoins(self):
        self.assertEqual(EXIT, decideIdleAction(1, 0, True, 10))
        self.assertEqual(NONE, decideIdleAction(1, 0, False, 10))

    def testUnknownCountLeavesStateUntouched(self):
        self.assertEqual(NONE, decideIdleAction(None, 99, True, 10))
        self.assertEqual(NONE, decideIdleAction(None, 99, False, 10))


class IntGameruleHelperTests(unittest.TestCase):
    def testBuildsAndClampsValues(self):
        self.assertEqual(
            "gamerule randomTickSpeed", qc.buildIntGameruleQuery("randomTickSpeed")
        )
        self.assertEqual(
            "gamerule randomTickSpeed 0", qc.buildIntGameruleSet("randomTickSpeed", 0)
        )
        self.assertEqual(
            "gamerule spawnChunkRadius 0", qc.buildIntGameruleSet("spawnChunkRadius", -5)
        )
        self.assertEqual(
            "gamerule randomTickSpeed 4096",
            qc.buildIntGameruleSet("randomTickSpeed", 999999),
        )

    def testRejectsUnmanagedGamerules(self):
        with self.assertRaises(ValueError):
            qc.buildIntGameruleQuery("keepInventory")
        with self.assertRaises(ValueError):
            qc.buildIntGameruleSet("doDaylightCycle", 0)

    def testParsesIntReplyAndMissingValue(self):
        self.assertEqual(
            3, qc.parseGameruleInt("Gamerule randomTickSpeed is currently set to: 3")
        )
        self.assertEqual(
            0, qc.parseGameruleInt("Gamerule randomTickSpeed is now set to: 0")
        )
        # 구버전에서 spawnChunkRadius 미지원 응답 → None(건너뜀).
        self.assertIsNone(
            qc.parseGameruleInt("Incorrect argument for command at position 9")
        )
        self.assertIsNone(qc.parseGameruleInt(""))


if __name__ == "__main__":
    unittest.main()
