"""Tests for Discord-to-Minecraft account link persistence."""

import tempfile
import unittest

from bot.player_links import (
    PlayerLink,
    PlayerLinkStore,
    buildWhitelistCommand,
    serverPlayerName,
)


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

    def testBedrockNamesRemainDistinctAndCommandSafe(self):
        """Floodgate names may contain spaces but cannot inject an RCON command."""
        with tempfile.TemporaryDirectory() as stateDir:
            store = PlayerLinkStore(stateDir)
            javaLink = store.request(100, "Alex", "java")
            bedrockLink = store.request(200, "Alex", "bedrock")
            spacedLink = store.request(300, "Pocket Friend", "bedrock")
            with self.assertRaises(ValueError):
                store.request(400, "bad;op", "bedrock")

        self.assertEqual("Alex", serverPlayerName(javaLink))
        self.assertEqual(".Alex", serverPlayerName(bedrockLink))
        self.assertEqual(".Pocket_Friend", serverPlayerName(spacedLink))
        self.assertEqual("fwhitelist add Pocket Friend", buildWhitelistCommand(spacedLink))

    def testOldJavaRecordLoadsWithoutEdition(self):
        """Links created before crossplay continue to represent Java accounts."""
        link = PlayerLink(
            discordUserId=100,
            minecraftName="Legacy",
            approved=True,
            requestedAt="2026-01-01T00:00:00+00:00",
        )
        self.assertEqual("java", link.edition)


if __name__ == "__main__":
    unittest.main()
