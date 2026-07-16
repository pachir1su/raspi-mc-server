"""Tests for Discord slash-command localization tables."""

import unittest

from bot.command_i18n import KOREAN_DESCRIPTIONS, KOREAN_NAMES


class CommandI18nTests(unittest.TestCase):
    def testCoreFriendCommandsHaveKoreanNames(self):
        self.assertEqual("서버", KOREAN_NAMES["server"])
        self.assertEqual("관리자", KOREAN_NAMES["admin"])
        self.assertEqual("내도구", KOREAN_NAMES["my-tools"])
        self.assertEqual("도움말", KOREAN_NAMES["help"])
        self.assertEqual("업로드", KOREAN_NAMES["upload"])

    def testLocalizedNamesFitDiscordLimit(self):
        for localizedName in KOREAN_NAMES.values():
            self.assertLessEqual(len(localizedName), 32)

    def testFriendDescriptionsAreLocalized(self):
        canonical = "Teleport only your linked player to spawn."
        self.assertIn("본인", KOREAN_DESCRIPTIONS[canonical])


if __name__ == "__main__":
    unittest.main()
