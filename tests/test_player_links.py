"""Tests for Discord-to-Minecraft account link persistence."""

import tempfile
import unittest

from bot.player_links import PlayerLinkStore


class PlayerLinkStoreTests(unittest.TestCase):
    """Exercise requests, approvals, revocation, and name ownership."""

    def testRequestApproveAndRemove(self):
        """An admin can approve and later revoke a pending request."""
        with tempfile.TemporaryDirectory() as stateDir:
            store = PlayerLinkStore(stateDir)
            pending = store.request(100, "Friend_1")
            self.assertFalse(pending.approved)
            approved = store.approve(100, 999)
            self.assertTrue(approved.approved)
            self.assertEqual(999, approved.approvedBy)
            self.assertTrue(store.remove(100))
            self.assertIsNone(store.get(100))

    def testRejectsDuplicateAndUnsafeNames(self):
        """Minecraft names are unique and cannot inject RCON commands."""
        with tempfile.TemporaryDirectory() as stateDir:
            store = PlayerLinkStore(stateDir)
            store.request(100, "Friend_1")
            with self.assertRaises(ValueError):
                store.request(200, "friend_1")
            with self.assertRaises(ValueError):
                store.request(200, "bad;op")

    def testListShowsPendingFirst(self):
        """Pending approvals remain visible at the top of the admin list."""
        with tempfile.TemporaryDirectory() as stateDir:
            store = PlayerLinkStore(stateDir)
            store.request(100, "Zulu")
            store.request(200, "Alpha")
            store.approve(100, 999)
            self.assertEqual(["Alpha", "Zulu"], [item.minecraftName for item in store.list()])


if __name__ == "__main__":
    unittest.main()
