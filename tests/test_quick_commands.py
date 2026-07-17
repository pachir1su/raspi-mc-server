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


class EffectEnchantResolverTests(unittest.TestCase):
    """Korean aliases for effects/enchants must resolve or fail with hints (#92)."""

    def testResolvesKoreanEffects(self):
        self.assertEqual("regeneration", qc.resolveEffectId("재생"))
        self.assertEqual("fire_resistance", qc.resolveEffectId("화염 저항"))
        self.assertEqual("saturation", qc.resolveEffectId("포만감"))

    def testResolvesKoreanEnchants(self):
        self.assertEqual("sharpness", qc.resolveEnchantId("날카로움"))
        self.assertEqual("silk_touch", qc.resolveEnchantId("섬세한 손길"))
        self.assertEqual("mending", qc.resolveEnchantId("수선"))

    def testEnglishIdsPassThrough(self):
        self.assertEqual("speed", qc.resolveEffectId("speed"))
        self.assertEqual("efficiency", qc.resolveEnchantId("minecraft:efficiency"))

    def testUnknownNamesRejected(self):
        with self.assertRaises(ValueError):
            qc.resolveEffectId("재생; op me")
        with self.assertRaises(ValueError):
            qc.resolveEnchantId("")

    def testBuildersAcceptKorean(self):
        self.assertEqual(
            'effect give @a[name="Friend_1",limit=1] minecraft:regeneration 300 0 true',
            qc.buildEffectCommand("Friend_1", "재생"),
        )
        self.assertEqual(
            'enchant @a[name="Friend_1",limit=1] minecraft:sharpness 5',
            qc.buildEnchantCommand("Friend_1", "날카로움", 5),
        )
        self.assertEqual(
            "enchantheld Friend_1 efficiency 10",
            qc.buildForceEnchantCommand("Friend_1", "효율", 10),
        )


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
            'effect give @a[name=".Pocket",limit=1] minecraft:speed 300 0 true',
            qc.buildEffectCommand(".Pocket", "speed"),
        )
        self.assertEqual(
            'effect give @a[name=".Pocket",limit=1] minecraft:speed 120 4 false',
            qc.buildEffectCommand(".Pocket", "speed", 120, 4, hideParticles=False),
        )
        self.assertEqual(
            'effect clear @a[name="Friend_1",limit=1]',
            qc.buildEffectClearCommand("Friend_1"),
        )
        with self.assertRaises(ValueError):
            qc.buildEffectCommand("Friend_1", "speed; op me")

    def testGameruleUnsupportedMessage(self):
        """An unknown gamerule maps to the version guidance, not a format error."""
        with self.assertRaises(ValueError) as caught:
            qc.ensureGameruleAccepted(
                "Incorrect argument for command at position 9: gamerule <--[HERE]"
            )
        self.assertEqual(qc.GAMERULE_UNSUPPORTED_MESSAGE, str(caught.exception))
        self.assertEqual(
            "Gamerule keepInventory is currently set to: false",
            qc.ensureGameruleAccepted(
                "Gamerule keepInventory is currently set to: false"
            ),
        )

    def testEnchant(self):
        self.assertEqual(
            'enchant @a[name="Friend_1",limit=1] minecraft:sharpness 5',
            qc.buildEnchantCommand("Friend_1", "sharpness", 5),
        )

    def testForceEnchant(self):
        # 플러그인은 선택자가 아니라 정확한 이름을 받습니다.
        self.assertEqual(
            "enchantheld Friend_1 sharpness 20",
            qc.buildForceEnchantCommand("Friend_1", "sharpness", 20),
        )
        self.assertEqual(
            "enchantheld .Pocket efficiency 5",
            qc.buildForceEnchantCommand(".Pocket", "minecraft:efficiency", 5),
        )
        self.assertEqual(  # 255 상한으로 clamp
            "enchantheld Friend_1 sharpness 255",
            qc.buildForceEnchantCommand("Friend_1", "sharpness", 9999),
        )
        with self.assertRaises(ValueError):
            qc.buildForceEnchantCommand("@a", "sharpness", 5)

    def testSummonPresetGoesThroughPlugin(self):
        self.assertEqual(
            "raspiops summon Friend_1 creeper",
            qc.buildSummonPresetCommand("Friend_1", "creeper"),
        )
        self.assertEqual(
            "raspiops summon .Pocket horde",
            qc.buildSummonPresetCommand(".Pocket", "horde"),
        )
        # 프리셋 화이트리스트 밖은 거부.
        with self.assertRaises(ValueError):
            qc.buildSummonPresetCommand("Friend_1", "wither")
        with self.assertRaises(ValueError):
            qc.buildSummonPresetCommand("@a", "creeper")
        # 특수 몹 드롭다운 키는 전부 허용 프리셋이어야 한다.
        for key, _label in qc.SPECIAL_MOB_PRESETS:
            self.assertIn(key, qc.SUMMON_PRESETS)

    def testCreeperSoundPlaysBehindWithoutSummoning(self):
        command = qc.buildCreeperSoundCommand("Friend_1")
        self.assertEqual(
            'execute at @a[name="Friend_1",limit=1] rotated ~ 0 run '
            "playsound minecraft:entity.creeper.primed hostile "
            '@a[name="Friend_1",limit=1] ^ ^ ^-3 1 1',
            command,
        )
        self.assertNotIn("summon", command)
        with self.assertRaises(ValueError):
            qc.buildCreeperSoundCommand("@a")

    def testLightningStrikesRandomOffsetEachCall(self):
        import random as _random

        command = qc.buildLightningCommand("Friend_1", rng=_random.Random(0))
        self.assertTrue(
            command.startswith(
                'execute at @a[name="Friend_1",limit=1] run '
                "summon minecraft:lightning_bolt ~"
            )
        )
        # 오프셋은 항상 반경 안(각 축 |offset| <= 최대 반경).
        offsets = command.rsplit("lightning_bolt ", 1)[1].split()
        dx = int(offsets[0].lstrip("~") or "0")
        dz = int(offsets[2].lstrip("~") or "0")
        self.assertLessEqual(dx * dx + dz * dz, qc._LIGHTNING_MAX_RADIUS**2 + 2)
        with self.assertRaises(ValueError):
            qc.buildLightningCommand("@a")

    def testVillagerSummonGoesThroughPlugin(self):
        self.assertEqual(
            "raspiops villager Friend_1 librarian mending 15",
            qc.buildVillagerSummonCommand("Friend_1", "librarian", "mending", 15),
        )
        with self.assertRaises(ValueError):  # 알 수 없는 상품
            qc.buildVillagerSummonCommand("Friend_1", "librarian", "nether_star", 5)
        with self.assertRaises(ValueError):  # 가격 범위 밖
            qc.buildVillagerSummonCommand("Friend_1", "librarian", "mending", 999)
        with self.assertRaises(ValueError):  # 이름 검증
            qc.buildVillagerSummonCommand("@a", "librarian", "mending", 5)
        # 드롭다운의 모든 상품/직업이 빌더 화이트리스트와 일치해야 한다.
        for good, profession, _label, price in qc.VILLAGER_GOODS:
            self.assertEqual(
                f"raspiops villager Friend_1 {profession} {good} {price}",
                qc.buildVillagerSummonCommand("Friend_1", profession, good, price),
            )

    def testWeatherReply(self):
        self.assertEqual("thunder", qc.parseWeatherReply("weather: thunder"))
        self.assertEqual("rain", qc.parseWeatherReply("Weather: RAIN"))
        self.assertEqual("clear", qc.parseWeatherReply("weather: clear"))
        with self.assertRaises(ValueError):
            qc.parseWeatherReply("Usage: /raspiops rescue <exact-player-name>")

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
