"""Tests for update archive validation and request staging."""

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from bot.update_manager import UpdateError, UpdateStore, validateReleaseArchive


def _releaseZip(path: Path, fileName: str = "bot/example.py") -> None:
    content = b"print('safe')\n"
    manifest = {
        "schemaVersion": 1,
        "tag": "v1.2.3",
        "commit": "abc",
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


class UpdateManagerTests(unittest.TestCase):
    def testValidManifestArchivePasses(self):
        with tempfile.TemporaryDirectory() as temporaryDir:
            archivePath = Path(temporaryDir) / "release.zip"
            _releaseZip(archivePath)
            manifest = validateReleaseArchive(archivePath, "v1.2.3")
            self.assertEqual("v1.2.3", manifest["tag"])

    def testProtectedEnvIsRejected(self):
        with tempfile.TemporaryDirectory() as temporaryDir:
            archivePath = Path(temporaryDir) / "release.zip"
            _releaseZip(archivePath, ".env")
            with self.assertRaises(UpdateError):
                validateReleaseArchive(archivePath)

    def testUndeclaredFileIsRejected(self):
        with tempfile.TemporaryDirectory() as temporaryDir:
            archivePath = Path(temporaryDir) / "release.zip"
            _releaseZip(archivePath)
            with zipfile.ZipFile(archivePath, "a") as archive:
                archive.writestr("extra.txt", "not declared")
            with self.assertRaises(UpdateError):
                validateReleaseArchive(archivePath)

    def testUploadedRequestUsesHddStagingAndChecksum(self):
        with tempfile.TemporaryDirectory() as temporaryDir:
            root = Path(temporaryDir)
            archivePath = root / "incoming.zip"
            _releaseZip(archivePath)
            store = UpdateStore(str(root / "state"), str(root / "storage"))
            payload = store.stageUploadedArchive(archivePath)
            store.requestUpload(payload)
            saved = json.loads(store.requestPath.read_text(encoding="utf-8"))
            self.assertEqual("upload", saved["source"])
            self.assertTrue(Path(saved["archivePath"]).is_file())
            self.assertEqual(64, len(saved["sha256"]))


if __name__ == "__main__":
    unittest.main()
