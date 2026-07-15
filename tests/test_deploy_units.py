"""Static safety checks for rendered Raspberry Pi service templates."""

import unittest
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]


class DeployUnitTests(unittest.TestCase):
    def testBotWriteAccessIsLimitedToRuntimeDirectories(self):
        unit = (REPO_DIR / "deploy" / "mc-discord-bot.service").read_text(
            encoding="utf-8"
        )
        writeLine = next(
            line for line in unit.splitlines() if line.startswith("ReadWritePaths=")
        )
        self.assertIn("@STATE_DIR@", writeLine)
        self.assertIn("@REPO_DIR@/bot/logs", writeLine)
        self.assertNotIn("ReadWritePaths=@REPO_DIR@ ", writeLine)

    def testSetupRendersStateDirectoryPlaceholder(self):
        setup = (REPO_DIR / "deploy" / "setup_raspberrypi.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('s|@STATE_DIR@|$STATE_DIR|g', setup)


if __name__ == "__main__":
    unittest.main()
