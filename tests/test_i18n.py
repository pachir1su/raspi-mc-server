"""Tests for configured Discord-facing language strings."""

import unittest
from unittest.mock import patch

from bot.i18n import t


class I18nTests(unittest.TestCase):
    def testKoreanAndEnglishMessages(self):
        with patch("bot.i18n.cfg.language", "ko"):
            self.assertIn("친구용", t("portal_title"))
        with patch("bot.i18n.cfg.language", "en"):
            self.assertIn("Friend", t("portal_title"))

    def testUnknownLanguageFallsBackToEnglish(self):
        with patch("bot.i18n.cfg.language", "jp"):
            self.assertEqual("Confirm", t("confirm"))

    def testUnknownKeyReturnsKey(self):
        with patch("bot.i18n.cfg.language", "en"):
            self.assertEqual("missing.key", t("missing.key"))


if __name__ == "__main__":
    unittest.main()
