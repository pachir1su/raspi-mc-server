"""Tests for deterministic on-demand server health scoring."""

import unittest

from bot.health_score import HealthInputs, calculateHealthScore


class HealthScoreTests(unittest.TestCase):
    """Exercise healthy, degraded, and bounded score paths."""

    def testHealthyServerScoresOneHundred(self):
        """Good Paper and Pi metrics keep the full score."""
        result = calculateHealthScore(
            HealthInputs(True, 20.0, 55.0, 50.0, 70.0, 0.25, False, False)
        )
        self.assertEqual(100, result.score)
        self.assertEqual("A", result.grade)
        self.assertEqual((), result.deductions)

    def testLagAndPiPressureExplainDeductions(self):
        """Every risk produces a visible reason instead of an opaque number."""
        result = calculateHealthScore(
            HealthInputs(True, 16.5, 82.0, 92.0, 4.0, 1.7, True, True)
        )
        self.assertLess(result.score, 20)
        self.assertTrue(any("TPS" in item for item in result.deductions))
        self.assertTrue(any("throttling" in item for item in result.deductions))

    def testScoreNeverDropsBelowZero(self):
        """Multiple simultaneous outages still return a valid percentage."""
        result = calculateHealthScore(
            HealthInputs(False, None, 90.0, 100.0, 0.0, 3.0, True, True)
        )
        self.assertEqual(0, result.score)
        self.assertEqual("F", result.grade)


if __name__ == "__main__":
    unittest.main()
