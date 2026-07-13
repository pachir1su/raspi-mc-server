"""Security-focused tests for the root-owned updater bootstrap."""

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from deploy.apply_update import ApplyError, _loadAndValidateArchive


class ApplyUpdateTests(unittest.TestCase):
    def _writeArchive(self, path: Path, fileName: str = "bot/main.py") -> None:
        content = b"print('release')\n"
        manifest = {
            "schemaVersion": 1,
            "tag": "v2.0.0",
            "commit": "def",
            "files": [
                {
                    "path": fileName,
                    "size": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            ],
        }
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("release-manifest.json", json.dumps(manifest))
            archive.writestr(fileName, content)

    def testValidatedArchiveReturnsAuthenticatedFiles(self):
        with tempfile.TemporaryDirectory() as temporaryDir:
            archivePath = Path(temporaryDir) / "release.zip"
            self._writeArchive(archivePath)
            manifest, fileNames = _loadAndValidateArchive(archivePath, "v2.0.0")
            self.assertEqual("v2.0.0", manifest["tag"])
            self.assertEqual(["bot/main.py"], fileNames)

    def testTagMismatchIsRejected(self):
        with tempfile.TemporaryDirectory() as temporaryDir:
            archivePath = Path(temporaryDir) / "release.zip"
            self._writeArchive(archivePath)
            with self.assertRaises(ApplyError):
                _loadAndValidateArchive(archivePath, "v9.9.9")

    def testPersistentDataPathIsRejected(self):
        with tempfile.TemporaryDirectory() as temporaryDir:
            archivePath = Path(temporaryDir) / "release.zip"
            self._writeArchive(archivePath, "data/player-links.json")
            with self.assertRaises(ApplyError):
                _loadAndValidateArchive(archivePath, "v2.0.0")


if __name__ == "__main__":
    unittest.main()
