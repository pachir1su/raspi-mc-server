"""Security-focused tests for the root-owned updater bootstrap."""

import hashlib
import json
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import argparse

from deploy.apply_update import (
    ApplyError,
    _loadAndValidateArchive,
    _officialDigest,
    applyUpdate,
)


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

    def testOfficialReleaseDigestIsRequiredForUploads(self):
        payload = {
            "assets": [
                {
                    "name": "raspi-mc-server-v2.0.0.zip",
                    "digest": "sha256:" + "a" * 64,
                }
            ]
        }
        with patch(
            "deploy.apply_update.urllib.request.urlopen",
            return_value=BytesIO(json.dumps(payload).encode("utf-8")),
        ):
            self.assertEqual("a" * 64, _officialDigest("v2.0.0"))

    def testMissingOfficialDigestIsRejected(self):
        payload = {
            "assets": [
                {"name": "raspi-mc-server-v2.0.0.zip", "digest": None}
            ]
        }
        with patch(
            "deploy.apply_update.urllib.request.urlopen",
            return_value=BytesIO(json.dumps(payload).encode("utf-8")),
        ):
            with self.assertRaises(ApplyError):
                _officialDigest("v2.0.0")


class UpdateRequestHandlingTests(unittest.TestCase):
    """이슈 D: 요청 파일 없음 / 있음 / 손상된 JSON 처리."""

    def _args(self, root: Path) -> argparse.Namespace:
        stateDir = root / "data"
        storageRoot = root / "storage"
        stateDir.mkdir()
        storageRoot.mkdir()
        return argparse.Namespace(
            repo_dir=root,
            state_dir=stateDir,
            storage_root=storageRoot,
            bot_service="mc-discord-bot.service",
        )

    def testMissingRequestExitsCleanly(self):
        with tempfile.TemporaryDirectory() as temporaryDir:
            args = self._args(Path(temporaryDir))
            # 요청 파일이 없으면 예외 없이 조용히 종료하고 상태 파일도 남기지 않습니다.
            self.assertIsNone(applyUpdate(args))
            self.assertFalse((args.state_dir / "update-status.json").exists())

    def testCorruptRequestRaisesApplyError(self):
        with tempfile.TemporaryDirectory() as temporaryDir:
            args = self._args(Path(temporaryDir))
            (args.state_dir / "update-request.json").write_text("{ not json", encoding="utf-8")
            with self.assertRaises(ApplyError):
                applyUpdate(args)

    def testPresentRequestIsReadAndValidated(self):
        with tempfile.TemporaryDirectory() as temporaryDir:
            args = self._args(Path(temporaryDir))
            # 태그가 잘못된 유효 요청 → 파일은 읽혔고 태그 검증에서 걸립니다.
            (args.state_dir / "update-request.json").write_text(
                json.dumps({"tag": "not-a-version", "source": "github"}), encoding="utf-8"
            )
            with self.assertRaises(ApplyError) as caught:
                applyUpdate(args)
            self.assertIn("tag", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
