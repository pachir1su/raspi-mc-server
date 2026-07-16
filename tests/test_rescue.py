"""Tests for narrow linked-player rescue RCON commands."""

import unittest

from bot.rescue import (
    buildAutomaticSpawnCommand,
    ensureRescueSucceeded,
    parsePosition,
)
from bot.player_names import buildPlayerSelector, escapeSelectorValue


class RescueTests(unittest.TestCase):
    """Exercise safe command construction and RCON output parsing."""

    def testBuildsAutomaticWorldSpawnRescue(self):
        """The plugin command receives only one validated exact server identity."""
        self.assertEqual(
            "raspiops rescue .QUI203",
            buildAutomaticSpawnCommand(".QUI203"),
        )
        self.assertEqual(
            "raspiops rescue Friend_1",
            buildAutomaticSpawnCommand("Friend_1"),
        )
        for unsafeName in ("@a", "Friend;op", 'bad"name'):
            with self.subTest(name=unsafeName), self.assertRaises(ValueError):
                buildAutomaticSpawnCommand(unsafeName)

    def testAcceptsRealTeleportOutput(self):
        """The plugin's success reply passes the strict verification."""
        ensureRescueSucceeded(
            "Teleported Friend_1 to world spawn at 12 64 -30"
        )

    def testRejectsOfflinePlayerOutput(self):
        """이슈 #45 댓글: 미접속 플레이어가 성공으로 보이면 안 됩니다."""
        for output in (
            "Player is not online: Friend_1",
            "No entity was found",
        ):
            with self.subTest(output=output):
                with self.assertRaises(ValueError) as caught:
                    ensureRescueSucceeded(output)
                self.assertIn("접속 중이 아닙니다", str(caught.exception))

    def testRejectsOtherFailuresWithKoreanGuidance(self):
        """Every known plugin failure reply becomes a Korean, actionable error."""
        cases = {
            "Usage: /raspiops rescue <exact-player-name>": "형식",
            "Invalid exact player name.": "이름",
            "No world is loaded.": "월드",
            "Paper rejected the spawn teleport.": "거부",
            "You do not have permission to use this command.": "권한",
            "Unknown command. Type /help for help.": "플러그인",
            "Command failed safely: boom": "실패",
        }
        for output, keyword in cases.items():
            with self.subTest(output=output):
                with self.assertRaises(ValueError) as caught:
                    ensureRescueSucceeded(output)
                self.assertIn(keyword, str(caught.exception))

    def testRejectsUnknownAndEmptyOutput(self):
        """Unexpected replies fail closed instead of claiming success."""
        for output in ("", None, "something new and strange"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                ensureRescueSucceeded(output)

    def testSelectorConstructionAndEscaping(self):
        """Selectors quote validated names and escaping remains explicit."""
        self.assertEqual('@a[name=".QUI203",limit=1]', buildPlayerSelector(".QUI203"))
        self.assertEqual('A\\"B\\\\C', escapeSelectorValue('A"B\\C'))
        for unsafeName in ('bad"name', "bad]", "@a", ".bad name"):
            with self.subTest(name=unsafeName), self.assertRaises(ValueError):
                buildPlayerSelector(unsafeName)

    def testParsesWhereAmIOutput(self):
        """Position and dimension NBT replies become a compact location tuple."""
        location = parsePosition(
            "Friend_1 has the following entity data: [12.5d, 64.0d, -30.25d]",
            'Friend_1 has the following entity data: "minecraft:the_nether"',
        )
        self.assertEqual(("nether", 12.5, 64.0, -30.25), location)


if __name__ == "__main__":
    unittest.main()
