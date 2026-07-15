"""Tests for Discord-to-Minecraft account link persistence."""

import json
import tempfile
import unittest
from pathlib import Path

from bot.player_links import (
    PlayerLink,
    PlayerLinkStore,
    buildWhitelistCommand,
    buildWhitelistRemoveCommand,
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

    def testAdminCanAssignMultipleProfilesToOneDiscordUser(self):
        """One Discord user can own separate Java and Bedrock profiles."""
        with tempfile.TemporaryDirectory() as stateDir:
            store = PlayerLinkStore(stateDir)
            javaLink = store.addManaged(100, "DeskPlayer", "java", 999)
            bedrockLink = store.addManaged(100, "Pocket Player", "bedrock", 999)

            links = store.listForUser(100)

        self.assertEqual(2, len(links))
        self.assertEqual({javaLink.linkId, bedrockLink.linkId}, {item.linkId for item in links})
        self.assertTrue(all(item.approved for item in links))

    def testRemovingOneProfileKeepsTheOthers(self):
        """The admin delete action targets a stable profile ID, not the user."""
        with tempfile.TemporaryDirectory() as stateDir:
            store = PlayerLinkStore(stateDir)
            javaLink = store.addManaged(100, "DeskPlayer", "java", 999)
            bedrockLink = store.addManaged(100, "Pocket Player", "bedrock", 999)

            removed = store.removeLink(javaLink.linkId)
            remaining = store.listForUser(100)

        self.assertEqual(javaLink, removed)
        self.assertEqual([bedrockLink], remaining)

    def testDuplicateProfileCannotBeAssignedTwice(self):
        """The same edition and name cannot belong to two Discord users."""
        with tempfile.TemporaryDirectory() as stateDir:
            store = PlayerLinkStore(stateDir)
            store.addManaged(100, "DeskPlayer", "java", 999)

            with self.assertRaises(ValueError):
                store.addManaged(200, "deskplayer", "java", 999)

    def testLegacySingleUserRecordGetsStableProfileId(self):
        """Old one-record-per-user JSON loads without a manual migration step."""
        with tempfile.TemporaryDirectory() as stateDir:
            path = Path(stateDir) / "player-links.json"
            path.write_text(
                json.dumps(
                    {
                        "100": {
                            "discordUserId": 100,
                            "minecraftName": "Legacy",
                            "approved": True,
                            "requestedAt": "2026-01-01T00:00:00+00:00",
                        }
                    }
                ),
                encoding="utf-8",
            )
            store = PlayerLinkStore(stateDir)

            first = store.listForUser(100)[0]
            second = store.listForUser(100)[0]

        self.assertTrue(first.linkId)
        self.assertEqual(first.linkId, second.linkId)

    def testWhitelistRemovalMatchesEdition(self):
        """Removing a profile uses the correct Java or Floodgate command."""
        javaLink = PlayerLink(100, "DeskPlayer", True, "now", edition="java")
        bedrockLink = PlayerLink(100, "Pocket Player", True, "now", edition="bedrock")

        self.assertEqual("whitelist remove DeskPlayer", buildWhitelistRemoveCommand(javaLink))
        self.assertEqual(
            "fwhitelist remove Pocket Player",
            buildWhitelistRemoveCommand(bedrockLink),
        )


if __name__ == "__main__":
    unittest.main()
