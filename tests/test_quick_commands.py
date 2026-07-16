"""Tests for the admin quick-command builders and the item name resolver."""

import unittest

from bot import quick_commands as qc


class ItemResolverTests(unittest.TestCase):
    """Free-form item input must resolve safely or fail with suggestions."""

    def testResolvesKoreanAliases(self):
        self.assertEqual("diamond", qc.resolveItemId("다이아"))
        self.assertEqual("iron_sword", qc.resolveItemId("철검"))
        self.assertEqual("iron_sword", qc.resolveItemId("철 검"))
        self.assertEqual("golden_apple", qc.resolveItemId("황금 사과"))

    def testPassesThroughEnglishIds(self):
        self.assertEqual("diamond", qc.resolveItemId("diamond"))
        self.assertEqual("iron_sword", qc.resolveItemId("Iron_Sword"))
        self.assertEqual("oak_log", qc.resolveItemId("minecraft:oak_log"))
        self.assertEqual("iron_sword", qc.resolveItemId("iron sword"))

    def testRejectsUnknownNamesWithSuggestions(self):
        with self.assertRaises(ValueError) as caught:
            qc.resolveItemId("다이야")
        self.assertIn("다이아", str(caught.exception))
        with self.assertRaises(ValueError):
            qc.resolveItemId("give @a diamond; op me")
        with self.assertRaises(ValueError):
            qc.resolveItemId("")

    def testParsesCounts(self):
        self.assertEqual(1, qc.parseItemCount(""))
        self.assertEqual(64, qc.parseItemCount("64"))
        for bad in ("0", "-1", "9999999", "많이"):
            with self.subTest(count=bad), self.assertRaises(ValueError):
                qc.parseItemCount(bad)


class CommandBuilderTests(unittest.TestCase):
    """Every builder must validate the player and produce one fixed command."""

    def testGive(self):
        self.assertEqual(
            'give @a[name="Friend_1",limit=1] minecraft:diamond 64',
            qc.buildGiveCommand("Friend_1", "다이아", "64"),
        )
        with self.assertRaises(ValueError):
            qc.buildGiveCommand("@a", "diamond")

    def testEffects(self):
        self.assertEqual(
            'effect give @a[name=".Pocket",limit=1] minecraft:speed 300 0',
            qc.buildEffectCommand(".Pocket", "speed"),
        )
        self.assertEqual(
            'effect clear @a[name="Friend_1",limit=1]',
            qc.buildEffectClearCommand("Friend_1"),
        )
        with self.assertRaises(ValueError):
            qc.buildEffectCommand("Friend_1", "speed; op me")

    def testEnchant(self):
        self.assertEqual(
            'enchant @a[name="Friend_1",limit=1] minecraft:sharpness 5',
            qc.buildEnchantCommand("Friend_1", "sharpness", 5),
        )

    def testGamemode(self):
        self.assertEqual(
            'gamemode creative @a[name="Friend_1",limit=1]',
            qc.buildGamemodeCommand("Friend_1", "creative"),
        )
        with self.assertRaises(ValueError):
            qc.buildGamemodeCommand("Friend_1", "hardcore")

    def testTeleport(self):
        self.assertEqual(
            'tp @a[name="Friend_1",limit=1] @a[name="Friend_2",limit=1]',
            qc.buildTeleportToPlayerCommand("Friend_1", "Friend_2"),
        )
        with self.assertRaises(ValueError):
            qc.buildTeleportToPlayerCommand("Friend_1", "Friend_1")
        self.assertEqual(
            'execute in minecraft:the_nether run tp @a[name="Friend_1",limit=1] 10 64 -20',
            qc.buildTeleportToCoordsCommand("Friend_1", "nether", 10, 64, -20),
        )
        with self.assertRaises(ValueError):
            qc.buildTeleportToCoordsCommand("Friend_1", "moon", 0, 64, 0)

    def testXpHealKick(self):
        self.assertEqual(
            'experience add @a[name="Friend_1",limit=1] 30 levels',
            qc.buildXpCommand("Friend_1", 30),
        )
        healCommands = qc.buildHealCommands("Friend_1")
        self.assertEqual(2, len(healCommands))
        self.assertIn("instant_health", healCommands[0])
        self.assertIn("saturation", healCommands[1])
        kick = qc.buildKickCommand("Friend_1", "잠깐 나가주세요\n곧 봐요")
        self.assertTrue(kick.startswith("kick Friend_1 "))
        self.assertNotIn("\n", kick)

    def testWorldSpawn(self):
        self.assertEqual(
            'execute at @a[name="Friend_1",limit=1] run setworldspawn ~ ~ ~',
            qc.buildWorldSpawnAtPlayerCommand("Friend_1"),
        )
        self.assertEqual(
            "execute in minecraft:overworld run setworldspawn 100 64 -200",
            qc.buildWorldSpawnCommand(100, 64, -200),
        )
        with self.assertRaises(ValueError):
            qc.buildWorldSpawnCommand(40_000_000, 64, 0)

    def testGamerules(self):
        self.assertEqual("gamerule keepInventory", qc.buildGameruleQueryCommand("keepInventory"))
        self.assertEqual(
            "gamerule doImmediateRespawn true",
            qc.buildGameruleSetCommand("doImmediateRespawn", True),
        )
        self.assertTrue(qc.parseGameruleValue("Gamerule keepInventory is currently set to: true"))
        self.assertFalse(qc.parseGameruleValue("Gamerule mobGriefing is now set to: false"))
        with self.assertRaises(ValueError):
            qc.parseGameruleValue("???")
        for key in qc.DEFAULT_ON_GAMERULES:
            self.assertIn(key, qc.GAMERULES)

    def testDifficultyAndDays(self):
        self.assertEqual("difficulty hard", qc.buildDifficultyCommand("hard"))
        self.assertEqual(128, qc.parseDaysPlayed("The time is 128"))
        self.assertIsNone(qc.parseDaysPlayed("no numbers here"))


class ServerReplyTests(unittest.TestCase):
    """Known rejection replies must become Korean guidance, not silent success."""

    def testKnownFailuresRaiseKorean(self):
        cases = {
            "No player was found": "접속 중이 아닙니다",
            "Unknown item 'minecraft:diamondd'": "아이템 ID",
            "Unknown effect: minecraft:sped": "포션 효과",
            "diamond_sword cannot support that enchantment": "인챈트",
            "Incorrect argument for command": "형식",
            "Unknown or incomplete command, see below for error": "지원하지 않는",
            "Unknown game rule: showDaysPlayed": "게임룰",
        }
        for output, keyword in cases.items():
            with self.subTest(output=output):
                with self.assertRaises(ValueError) as caught:
                    qc.ensureServerAccepted(output)
                self.assertIn(keyword, str(caught.exception))

    def testSuccessRepliesPassThrough(self):
        self.assertEqual(
            "Gave 64 [Diamond] to Friend_1",
            qc.ensureServerAccepted("Gave 64 [Diamond] to Friend_1"),
        )
        self.assertEqual("", qc.ensureServerAccepted(""))


if __name__ == "__main__":
    unittest.main()
