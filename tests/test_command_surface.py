"""Verify that cogs define only the four intentionally public command roots."""

import unittest

from bot.cogs.admin import Admin
from bot.cogs.friend import Friend
from bot.main import syncCommandTree


class CommandSurfaceTests(unittest.TestCase):
    def testCogsDefineOnlyIntentionalTopLevelCommands(self):
        commandNames = {
            command.name
            for cog in (Admin, Friend)
            for command in cog.__cog_app_commands__
        }

        self.assertEqual(
            {"server", "admin", "tools", "help", "upload"},
            commandNames,
        )

    def testUploadIsTheOnlyPublishedCommandGroup(self):
        groups = [
            command
            for cog in (Admin, Friend)
            for command in cog.__cog_app_commands__
            if hasattr(command, "commands")
        ]

        self.assertEqual(["upload"], [group.name for group in groups])
        self.assertEqual(
            {"world", "update", "place-photo", "diary"},
            {command.name for command in groups[0].commands},
        )


class CommandSyncTests(unittest.IsolatedAsyncioTestCase):
    async def testGuildSyncDeletesStaleGlobalCommands(self):
        class FakeTree:
            def __init__(self):
                self.calls = []

            def copy_global_to(self, *, guild):
                self.calls.append(("copy", guild.id))

            async def sync(self, *, guild=None):
                self.calls.append(("sync", guild.id if guild else None))

            def clear_commands(self, *, guild):
                self.calls.append(("clear", guild))

        tree = FakeTree()
        await syncCommandTree(tree, [101, 202])

        self.assertEqual(
            [
                ("copy", 101),
                ("sync", 101),
                ("copy", 202),
                ("sync", 202),
                ("clear", None),
                ("sync", None),
            ],
            tree.calls,
        )


if __name__ == "__main__":
    unittest.main()
