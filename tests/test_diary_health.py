"""Tests for diary and health-score helpers."""

import tempfile
import unittest

from bot.diary import Diary
from bot.health_score import calculateHealthScore


class DiaryAndHealthTests(unittest.TestCase):
    def testDiaryRecentNewestFirst(self):
        with tempfile.TemporaryDirectory() as stateDir:
            diary = Diary(stateDir)
            diary.record("place", "Saved base", 1)
            diary.record("rescue", "Teleported Steve", 2)
            recent = diary.recent(2)
            self.assertEqual("rescue", recent[0].category)
            self.assertEqual("place", recent[1].category)

    def testHealthScoreDeductions(self):
        score = calculateHealthScore(
            memoryPercent=91,
            temperatureCelsius=81,
            freeGb=5,
            tps=17,
            backupAgeMinutes=None,
        )
        self.assertLess(score.score, 40)
        self.assertGreaterEqual(len(score.deductions), 4)


if __name__ == "__main__":
    unittest.main()
