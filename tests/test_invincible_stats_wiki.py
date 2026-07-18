"""Tests for invincibility (#75), stats scoreboards (#68), and wiki (#71)."""

import unittest

from bot import quick_commands as qc
from bot import wiki


class InvincibilityTests(unittest.TestCase):
    def testDefaultAndBounds(self):
        self.assertEqual(5, qc.parseInvincibleSeconds(""))
        self.assertEqual(5, qc.parseInvincibleSeconds("5"))
        self.assertEqual(30, qc.parseInvincibleSeconds(30))
        with self.assertRaises(ValueError):
            qc.parseInvincibleSeconds("0")
        with self.assertRaises(ValueError):
            qc.parseInvincibleSeconds("99999")
        with self.assertRaises(ValueError):
            qc.parseInvincibleSeconds("abc")

    def testInvincibilityHidesParticlesAndCoversDamage(self):
        commands = qc.buildInvincibilityCommands("Steve", 30)
        # Every effect must hide particles (trailing "true") per issue #75.
        self.assertTrue(all(command.endswith(" true") for command in commands))
        joined = " ".join(commands)
        for effect in ("resistance", "regeneration", "fire_resistance", "saturation"):
            self.assertIn(f"minecraft:{effect}", joined)
        # Resistance must be amplifier 4 (Resistance V = full immunity).
        self.assertIn("minecraft:resistance 30 4 true", joined)
        # 포화(#89)는 무적 시간 내내 허기가 줄지 않도록 최대 증폭(255)으로 걸어
        # 매 틱 허기를 가득 채웁니다.
        self.assertIn("minecraft:saturation 30 255 true", joined)

    def testClearRemovesOnlyGrantedEffects(self):
        commands = qc.buildInvincibilityClearCommands("Steve")
        self.assertEqual(4, len(commands))
        self.assertTrue(all(command.startswith("effect clear") for command in commands))


class ScoreboardStatsTests(unittest.TestCase):
    def testSetupCreatesEveryObjective(self):
        setup = qc.buildScoreboardSetupCommands()
        self.assertEqual(len(qc.SCOREBOARD_STATS), len(setup))
        self.assertIn("scoreboard objectives add mc_deaths deathCount", setup)

    def testGetRejectsUnknownObjective(self):
        self.assertEqual(
            "scoreboard players get Steve mc_deaths",
            qc.buildScoreboardGetCommand("Steve", "mc_deaths"),
        )
        with self.assertRaises(ValueError):
            qc.buildScoreboardGetCommand("Steve", "bogus")

    def testParseHandlesValueAndMissingScore(self):
        self.assertEqual(7, qc.parseScoreboardValue("Steve has 7 [mc_deaths]"))
        self.assertEqual(0, qc.parseScoreboardValue("Steve has no score"))
        self.assertEqual(0, qc.parseScoreboardValue(""))

    def testParseNeverReadsDigitsFromPlayerName(self):
        """Regression for #84: digits in the player name must not become the score."""
        self.assertEqual(
            0,
            qc.parseScoreboardValue(
                "Can't get value of mc_deaths for QUI203; none is set"
            ),
        )
        self.assertEqual(3, qc.parseScoreboardValue("QUI203 has 3 [mc_deaths]"))
        with self.assertRaises(ValueError):
            qc.parseScoreboardValue("Unknown scoreboard objective 'mc_deaths'")


class WikiTests(unittest.TestCase):
    def testEveryPageBuildsBothLanguageUrls(self):
        for key, label, doc in wiki.WIKI_PAGES:
            self.assertEqual(label, wiki.wikiPageLabel(key))
            self.assertTrue(wiki.wikiPageUrl(key, "ko").endswith(f"/ko/{doc}"))
            self.assertTrue(wiki.wikiPageUrl(key, "en").endswith(f"/en/{doc}"))

    def testUnknownPageRejected(self):
        with self.assertRaises(ValueError):
            wiki.wikiPageUrl("does-not-exist")


if __name__ == "__main__":
    unittest.main()
