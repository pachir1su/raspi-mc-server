"""Tests for Discord-to-Minecraft link persistence."""

import tempfile
import unittest

from bot.player_links import PlayerLinkStore


class PlayerLinkStoreTests(unittest.TestCase):
    def testRequestApproveAndList(self):
        with tempfile.TemporaryDirectory() as stateDir:
            store = PlayerLinkStore(stateDir)
            requested = store.request(123, "Steve")
            self.assertFalse(requested.approved)
            approved = store.approve(123)
            self.assertTrue(approved.approved)
            self.assertEqual("Steve", store.get(123).minecraftName)
            self.assertEqual([approved], store.list())

    def testRejectsInvalidMinecraftName(self):
        with tempfile.TemporaryDirectory() as stateDir:
            store = PlayerLinkStore(stateDir)
            with self.assertRaises(ValueError):
                store.request(123, "bad;op")


if __name__ == "__main__":
    unittest.main()
