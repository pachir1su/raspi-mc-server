"""Tests for safe player parsing and inventory presentation."""

import unittest

from bot.player_info import (
    parseInventoryItems,
    parseNumericData,
    parseOnlinePlayers,
    summarizeEffects,
    summarizeEnderChest,
    summarizeInventory,
    summarizeInventorySections,
    summarizePlayerStats,
    validatePlayerName,
)


class PlayerInfoTests(unittest.TestCase):
    """Cover Paper list output, injection rejection, and SNBT item formats."""

    def testParsesOnlinePlayers(self):
        """Valid Java and Floodgate names survive one mixed list response."""
        output = (
            "There are 4 of a max of 6 players online: "
            "Steve, Alex_01, .QUI203, .Friend_1"
        )
        self.assertEqual(
            ["Steve", "Alex_01", ".QUI203", ".Friend_1"],
            parseOnlinePlayers(output),
        )

    def testDropsMalformedOnlineNames(self):
        """List parsing still discards selector and command injection text."""
        output = "There are 3 of a max of 6 players online: Steve, @a, .bad;op"
        self.assertEqual(["Steve"], parseOnlinePlayers(output))

    def testRejectsUnsafePlayerName(self):
        """RCON command separators and spaces cannot enter a player query."""
        with self.assertRaises(ValueError):
            validatePlayerName("Steve run kill @a")

    def testSummarizesInventory(self):
        """Modern count and legacy Count fields produce friendly slot labels."""
        output = (
            'Steve has the following entity data: [{Slot: 0b, id: "minecraft:diamond_sword", count: 1}, '
            '{Slot: -106b, id: "minecraft:torch", Count: 32b}]'
        )
        summary = summarizeInventory(output)
        self.assertIn("핫바 1", summary)
        self.assertIn("diamond_sword", summary)
        self.assertIn("왼손", summary)

    def testParsesCountBeforeSlot(self):
        """Field order must not matter — the #56 bug skipped these items."""
        output = (
            ".QUI203 has the following entity data: ["
            '{count: 2, Slot: 0b, id: "minecraft:birch_log"}, '
            '{count: 34, Slot: 1b, id: "minecraft:cobblestone"}, '
            '{count: 1, Slot: 103b, id: "minecraft:iron_helmet"}]'
        )
        items = parseInventoryItems(output)
        self.assertEqual(
            [(0, "birch_log", 2), (1, "cobblestone", 34), (103, "iron_helmet", 1)],
            items,
        )

    def testIgnoresNestedContainerContents(self):
        """A shulker box counts as one item; its contents stay hidden."""
        output = (
            'Steve has the following entity data: [{count: 1, Slot: 9b, '
            'id: "minecraft:shulker_box", components: {"minecraft:container": '
            '[{item: {count: 64, id: "minecraft:diamond"}, slot: 0}]}}]'
        )
        items = parseInventoryItems(output)
        self.assertEqual([(9, "shulker_box", 1)], items)

    def testGroupsInventorySections(self):
        """Armor, hotbar, and backpack land in separate embed sections."""
        output = (
            "Steve has the following entity data: ["
            '{count: 1, Slot: 102b, id: "minecraft:iron_chestplate"}, '
            '{count: 3, Slot: 4b, id: "minecraft:bread"}, '
            '{count: 12, Slot: 20b, id: "minecraft:oak_planks"}]'
        )
        sections = dict(summarizeInventorySections(output))
        self.assertIn("🛡️ 장비 (갑옷·왼손)", sections)
        self.assertIn("흉갑", sections["🛡️ 장비 (갑옷·왼손)"])
        self.assertIn("🔥 핫바", sections)
        self.assertIn("핫바 5", sections["🔥 핫바"])
        self.assertIn("🎒 인벤토리", sections)
        self.assertIn("인벤토리 12", sections["🎒 인벤토리"])

    def testSummarizesEnderChest(self):
        """EnderItems replies become numbered slots starting at one."""
        output = (
            "Steve has the following entity data: ["
            '{count: 5, Slot: 2b, id: "minecraft:emerald"}]'
        )
        summary = summarizeEnderChest(output)
        self.assertIn("칸 3", summary)
        self.assertIn("emerald", summary)

    def testEmptyEnderChestGivesEmptyBody(self):
        self.assertEqual("", summarizeEnderChest("Steve has the following entity data: []"))

    def testParsesNumericData(self):
        """Health floats and integer levels both parse from raw replies."""
        self.assertEqual(19.0, parseNumericData("Steve has the following entity data: 19.0f"))
        self.assertEqual(30.0, parseNumericData("Steve has the following entity data: 30"))
        self.assertIsNone(parseNumericData("No entity was found"))

    def testSummarizesPlayerStats(self):
        summary = summarizePlayerStats(
            "Steve has the following entity data: 19.0f",
            "Steve has the following entity data: 18",
            "Steve has the following entity data: 30",
            "Steve has the following entity data: 0",
        )
        self.assertIn("체력** 19/20", summary)
        self.assertIn("하트 9.5개", summary)
        self.assertIn("허기** 18/20", summary)
        self.assertIn("레벨** 30", summary)
        self.assertIn("서바이벌", summary)

    def testSummarizesEffects(self):
        """Effect ids map to Korean names with level and remaining time."""
        output = (
            "Steve has the following entity data: ["
            '{ambient: 0b, amplifier: 1b, duration: 5040, id: "minecraft:speed", '
            "show_icon: 1b, show_particles: 1b}, "
            '{amplifier: 0b, duration: -1, id: "minecraft:night_vision"}]'
        )
        summary = summarizeEffects(output)
        self.assertIn("신속 II", summary)
        self.assertIn("4분 12초 남음", summary)
        self.assertIn("야간 투시 I", summary)
        self.assertIn("무한", summary)

    def testNoEffectsMessage(self):
        self.assertIn(
            "없습니다", summarizeEffects("Steve has the following entity data: []")
        )


if __name__ == "__main__":
    unittest.main()
