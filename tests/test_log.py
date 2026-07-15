"""Tests for the bot's console/file logging and its rotation triggers."""

import logging
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from bot import log


class LoggingSetupTests(unittest.TestCase):
    """Exercise setup, the timestamped file, and size/date rollovers."""

    def setUp(self):
        # Redirect the module to a throwaway directory and reset its state so
        # each test builds a fresh handler.
        self._tmp = tempfile.TemporaryDirectory()
        self._origDir = log._LOG_DIR
        self._origMax = log._MAX_BYTES
        log._LOG_DIR = Path(self._tmp.name)
        log._READY = False
        log._handler = None

    def tearDown(self):
        if log._handler is not None:
            log._handler.close()
        logging.getLogger("mc").handlers.clear()
        log._LOG_DIR = self._origDir
        log._MAX_BYTES = self._origMax
        log._READY = False
        log._handler = None
        self._tmp.cleanup()

    def _files(self):
        return sorted(Path(self._tmp.name).glob("bot_*.log*"))

    def testSetupWritesTimestampedFile(self):
        """setup() creates one bot_<stamp>.log and lines carry a date+time."""
        log._MAX_BYTES = 0
        log.setup()
        log.get("test").info("hello world")
        current = log.current_log_file()
        self.assertIsNotNone(current)
        self.assertTrue(current.exists())
        self.assertEqual(1, len(self._files()))
        text = current.read_text(encoding="utf-8")
        self.assertIn("hello world", text)
        # "YYYY-MM-DD HH:MM:SS" prefix from the formatter.
        self.assertRegex(text, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

    def testRollsOverOnSize(self):
        """Crossing LOG_MAX_BYTES starts a new file and moves current_log_file."""
        log._MAX_BYTES = 400
        log.setup()
        logger = log.get("test")
        first = log.current_log_file()
        for i in range(50):
            logger.info("padding line number %02d with some extra text", i)
        rolled = log.current_log_file()
        self.assertNotEqual(first, rolled)
        self.assertGreaterEqual(len(self._files()), 2)
        # No single segment blew far past the limit.
        self.assertLessEqual(first.stat().st_size, 400 * 3)

    def testRollsOverOnDateChange(self):
        """A local date change starts a new file on the next record."""
        log._MAX_BYTES = 0
        log.setup()
        logger = log.get("test")
        logger.info("day one")
        first = log.current_log_file()
        # Pretend the file was opened yesterday.
        log._handler._opened_on = date.today() - timedelta(days=1)
        logger.info("day two")
        self.assertNotEqual(first, log.current_log_file())
        self.assertEqual(2, len(self._files()))

    def testPruneRemovesOldFiles(self):
        """Files older than the retention window are deleted on setup."""
        old = Path(self._tmp.name) / "bot_20000101_000000.log"
        old.write_text("stale", encoding="utf-8")
        import os
        ancient = (date.today() - timedelta(days=log._RETENTION_DAYS + 5))
        stamp = __import__("time").mktime(ancient.timetuple())
        os.utime(old, (stamp, stamp))
        log.setup()
        self.assertFalse(old.exists())


if __name__ == "__main__":
    unittest.main()
