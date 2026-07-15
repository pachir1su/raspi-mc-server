"""Tests for the first-run application settings menu."""

import tempfile
import unittest

from bot.app_settings import EX_CONFIG, AppSettingsStore, ensureFirstRunSetup


class AppSettingsTests(unittest.TestCase):
    """Verify menu choices, persistence, and unattended startup safety."""

    def testCrossplayMenuPersistsChoices(self):
        """A Korean crossplay setup keeps its language and UDP port."""
        answers = iter(["1", "2", "19133"])
        with tempfile.TemporaryDirectory() as stateDir:
            settings = ensureFirstRunSetup(
                stateDir,
                inputFn=lambda _prompt: next(answers),
                outputFn=lambda _message: None,
            )
            loaded = AppSettingsStore(stateDir).load()

        self.assertEqual("ko", settings.language)
        self.assertEqual("java_bedrock", loaded.serverMode)
        self.assertEqual(19133, loaded.bedrockPort)

    def testExistingSettingsSkipMenu(self):
        """Later launches load settings without asking questions again."""
        answers = iter(["2", "1"])
        with tempfile.TemporaryDirectory() as stateDir:
            first = ensureFirstRunSetup(
                stateDir,
                inputFn=lambda _prompt: next(answers),
                outputFn=lambda _message: None,
            )
            second = ensureFirstRunSetup(
                stateDir,
                inputFn=lambda _prompt: self.fail("menu unexpectedly reopened"),
                outputFn=lambda _message: None,
            )

        self.assertEqual(first, second)
        self.assertEqual("en", second.language)
        self.assertEqual("java", second.serverMode)

    def testNonInteractiveFirstLaunchStopsClearly(self):
        """systemd cannot silently choose an unintended server mode."""
        with tempfile.TemporaryDirectory() as stateDir:
            with self.assertRaises(SystemExit) as context:
                ensureFirstRunSetup(stateDir, interactive=False)

        # 재시작을 멈추도록 EX_CONFIG(78)로 종료해야 합니다(이슈 C).
        self.assertEqual(EX_CONFIG, context.exception.code)


if __name__ == "__main__":
    unittest.main()
