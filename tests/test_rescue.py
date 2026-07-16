"""Tests for narrow linked-player rescue RCON commands."""

import unittest

from bot.rescue import (
    buildAutomaticSpawnCommand,
    buildSpawnCommand,
    parsePosition,
    validateDestination,
)
from bot.player_names import buildPlayerSelector, escapeSelectorValue


class RescueTests(unittest.TestCase):
    """Exercise safe command construction and RCON output parsing."""

    def testBuildsFixedSelfTeleport(self):
        """Only a validated player and configured destination enter the command."""
        destination = validateDestination("overworld", 0.5, 80, -2.5)
        self.assertEqual(
            'execute in minecraft:overworld run tp @a[name="Friend_1",limit=1] 0.5 80 -2.5',
            buildSpawnCommand("Friend_1", destination),
        )

    def testBuildsFloodgateSelfTeleport(self):
        """A linked Bedrock entity can use the same bounded rescue command."""
        destination = validateDestination("overworld", 0, 80, 0)
        self.assertEqual(
            'execute in minecraft:overworld run tp @a[name=".Pocket_Friend",limit=1] 0 80 0',
            buildSpawnCommand(".Pocket_Friend", destination),
        )

    def testBuildsAutomaticWorldSpawnFallback(self):
        """The plugin fallback receives only one validated exact server identity."""
        self.assertEqual(
            "raspiops rescue .QUI203",
            buildAutomaticSpawnCommand(".QUI203"),
        )
        with self.assertRaises(ValueError):
            buildAutomaticSpawnCommand("@a")

    def testRejectsInjectionAndInvalidDestination(self):
        """Free-form RCON text and invalid dimensions cannot reach the builder."""
        destination = validateDestination("overworld", 0, 80, 0)
        with self.assertRaises(ValueError):
            buildSpawnCommand("Friend;op", destination)
        with self.assertRaises(ValueError):
            validateDestination("moon", 0, 80, 0)
        with self.assertRaises(ValueError):
            validateDestination("overworld", float("nan"), 80, 0)

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
