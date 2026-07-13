"""Tests for Discord slash-command localization tables."""

import unittest

from bot.command_i18n import KOREAN_DESCRIPTIONS, KOREAN_NAMES


class CommandI18nTests(unittest.TestCase):
    def testCoreFriendCommandsHaveKoreanNames(self):
        self.assertEqual("연동", KOREAN_NAMES["link"])
        self.assertEqual("요청", KOREAN_NAMES["request"])
        self.assertEqual("구조", KOREAN_NAMES["rescue"])
        self.assertEqual("내위치", KOREAN_NAMES["whereami"])

    def testLocalizedNamesFitDiscordLimit(self):
        for localizedName in KOREAN_NAMES.values():
            self.assertLessEqual(len(localizedName), 32)

    def testFriendDescriptionsAreLocalized(self):
        canonical = "Teleport only your linked player to spawn."
        self.assertIn("본인", KOREAN_DESCRIPTIONS[canonical])


if __name__ == "__main__":
    unittest.main()
