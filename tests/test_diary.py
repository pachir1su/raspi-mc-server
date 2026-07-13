"""Tests for the bounded append-only server diary."""

import tempfile
import unittest
from pathlib import Path

from bot.diary import DiaryStore


class DiaryStoreTests(unittest.TestCase):
    """Exercise diary ordering, lookup, validation, and compaction."""

    def testRecordsNewestFirstAndLooksUpById(self):
        """Friends see recent events first and can open one entry."""
        with tempfile.TemporaryDirectory() as stateDir:
            store = DiaryStore(stateDir)
            first = store.record("note", "Built a house", 1)
            second = store.record("rescue", "Returned to spawn", 2, "spawn.png")
            self.assertEqual([second, first], store.recent(10))
            self.assertEqual(first, store.get(first.entryId))

    def testRejectsEmptyAndOversizedMessages(self):
        """Invalid records never reach the JSONL file."""
        with tempfile.TemporaryDirectory() as stateDir:
            store = DiaryStore(stateDir)
            with self.assertRaises(ValueError):
                store.record("note", "", 1)
            with self.assertRaises(ValueError):
                store.record("note", "x" * 1001, 1)

    def testCompactsToRecentEntries(self):
        """The diary stays bounded when its configured byte cap is crossed."""
        with tempfile.TemporaryDirectory() as stateDir:
            store = DiaryStore(stateDir, maxBytes=1, retainedEntries=2)
            store.record("note", "one", 1)
            store.record("note", "two", 1)
            store.record("note", "three", 1)
            self.assertEqual(["three", "two"], [item.message for item in store.recent(10)])
            self.assertLessEqual(
                len(Path(stateDir, "server-diary.jsonl").read_text(encoding="utf-8").splitlines()),
                2,
            )


if __name__ == "__main__":
    unittest.main()
