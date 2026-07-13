"""Tests for the landmark coordinate store."""

import tempfile
import unittest

from bot.places import PlaceStore, mapLink


class PlaceStoreTests(unittest.TestCase):
    def testSaveListShowAndMapLink(self):
        with tempfile.TemporaryDirectory() as stateDir:
            store = PlaceStore(stateDir)
            place = store.save("Base", "overworld", 1, 64, -2, "Home", "", 123)
            self.assertEqual("Base", store.get("base").name)
            self.assertEqual([place], store.list())
            self.assertIn("x=1", mapLink("https://map.example", place))

    def testRejectsUnknownDimension(self):
        with tempfile.TemporaryDirectory() as stateDir:
            store = PlaceStore(stateDir)
            with self.assertRaises(ValueError):
                store.save("Bad", "moon", 0, 0, 0, "", "", 123)


if __name__ == "__main__":
    unittest.main()
