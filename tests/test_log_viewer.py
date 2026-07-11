"""Tests for bounded log tail and important-line filtering."""

import tempfile
import unittest
from pathlib import Path

from bot.log_viewer import discordPreview, filterImportant, readTail


class LogViewerTests(unittest.TestCase):
    """Ensure large logs are bounded and useful failures remain visible."""

    def testReadsOnlyTail(self):
        """Tail reads do not require loading the entire log into memory."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "latest.log"
            path.write_text("old\n" * 1000 + "newest line\n", encoding="utf-8")
            self.assertIn("newest line", readTail(path, maxBytes=64))

    def testFiltersErrorsAndContinuation(self):
        """Exception lines retain an immediately following stack frame."""
        text = "ok\nERROR failed\n    at module.py:3\nnormal"
        filtered = filterImportant(text)
        self.assertIn("ERROR failed", filtered)
        self.assertIn("module.py", filtered)

    def testPreviewEscapesCodeFence(self):
        """Log content cannot terminate the surrounding Discord code block."""
        self.assertNotIn("```", discordPreview("bad ``` content"))


if __name__ == "__main__":
    unittest.main()
