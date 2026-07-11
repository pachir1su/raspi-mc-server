"""Tests for safe player parsing and inventory presentation."""

import unittest

from bot.player_info import parseOnlinePlayers, summarizeInventory, validatePlayerName


class PlayerInfoTests(unittest.TestCase):
    """Cover Paper list output, injection rejection, and SNBT item formats."""

    def testParsesOnlinePlayers(self):
        """Only valid Java usernames survive list parsing."""
        output = "There are 2 of a max of 6 players online: Steve, Alex_01"
        self.assertEqual(["Steve", "Alex_01"], parseOnlinePlayers(output))

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
        self.assertIn("Hotbar 1", summary)
        self.assertIn("diamond_sword", summary)
        self.assertIn("Offhand", summary)


if __name__ == "__main__":
    unittest.main()
