"""Tests for the intentionally small Discord command surface."""

import unittest

import discord
from discord import app_commands

from bot.command_surface import VISIBLE_TOP_LEVEL_COMMANDS, pruneCommandTree


class CommandSurfaceTests(unittest.TestCase):
    def testPrunesARealDiscordCommandTreeToFourRoots(self):
        client = discord.Client(intents=discord.Intents.none())
        tree = app_commands.CommandTree(client)

        async def callback(interaction: discord.Interaction) -> None:
            pass

        for name in (*VISIBLE_TOP_LEVEL_COMMANDS, "status", "backup", "link"):
            tree.add_command(
                app_commands.Command(
                    name=name,
                    description=f"{name} command",
                    callback=callback,
                )
            )

        removedNames = pruneCommandTree(tree)

        self.assertEqual(
            VISIBLE_TOP_LEVEL_COMMANDS,
            {command.name for command in tree.get_commands()},
        )
        self.assertCountEqual(["status", "backup", "link"], removedNames)

    def testPublishedRootsAreStable(self):
        self.assertEqual(
            {"server", "admin", "my-tools", "upload"},
            VISIBLE_TOP_LEVEL_COMMANDS,
        )


if __name__ == "__main__":
    unittest.main()
