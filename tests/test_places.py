"""Tests for the lightweight shared coordinate book."""

import tempfile
import unittest
from pathlib import Path

from bot.places import ImageStore, PlaceStore, buildMapLink


class PlaceStoreTests(unittest.TestCase):
    """Exercise place CRUD, map links, bounds, and local images."""

    def testSaveReplaceListAndDelete(self):
        """Names are case-insensitive and replacements expose old media."""
        with tempfile.TemporaryDirectory() as stateDir:
            store = PlaceStore(stateDir)
            first, previous = store.save("Base", "overworld", 1, 64, -2, "Home", "old.png", 1)
            self.assertIsNone(previous)
            second, previous = store.save("base", "overworld", 2, 65, -3, "New", None, 2)
            self.assertEqual(first, previous)
            self.assertEqual(second, store.get("BASE"))
            self.assertEqual([second], store.list())
            self.assertEqual(second, store.delete("Base"))

    def testBuildsConfiguredMapLink(self):
        """Map rendering stays external while coordinates are encoded in the URL."""
        with tempfile.TemporaryDirectory() as stateDir:
            place, _ = PlaceStore(stateDir).save("Home", "nether", 8, 70, -16, "", None, 1)
            link = buildMapLink(
                "https://map.example/?world={dimension}&x={x}&y={y}&z={z}", place
            )
            self.assertEqual(
                "https://map.example/?world=nether&x=8&y=70&z=-16", link
            )

    def testRejectsInvalidDimensionAndRecordOverflow(self):
        """Unbounded or malformed coordinate books are rejected."""
        with tempfile.TemporaryDirectory() as stateDir:
            store = PlaceStore(stateDir, limit=1)
            with self.assertRaises(ValueError):
                store.save("Moon", "moon", 0, 0, 0, "", None, 1)
            store.save("One", "overworld", 0, 64, 0, "", None, 1)
            with self.assertRaises(ValueError):
                store.save("Two", "overworld", 1, 64, 1, "", None, 1)

    def testImageStoreEnforcesTypeAndSize(self):
        """Only small image attachments are written to runtime storage."""
        with tempfile.TemporaryDirectory() as stateDir:
            store = ImageStore(stateDir)
            path = store.save(b"image", "home.png", "image/png")
            self.assertTrue(Path(path).is_file())
            with self.assertRaises(ValueError):
                store.save(b"text", "note.txt", "text/plain")
            outsidePath = Path(stateDir, "outside.png")
            outsidePath.write_bytes(b"keep")
            store.remove(str(outsidePath))
            self.assertTrue(outsidePath.exists())
            store.remove(path)
            self.assertFalse(Path(path).exists())


if __name__ == "__main__":
    unittest.main()
