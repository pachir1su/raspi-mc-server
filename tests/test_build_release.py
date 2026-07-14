"""Tests for the deployment release packager."""

import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_release import buildRelease


class BuildReleaseTests(unittest.TestCase):
    def testManifestIncludesTrackedFilesButNeverEnv(self):
        with tempfile.TemporaryDirectory() as temporaryDir:
            repoDir = Path(temporaryDir) / "repo"
            repoDir.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repoDir, check=True)
            (repoDir / "bot").mkdir()
            (repoDir / "bot" / "main.py").write_text("print('ok')\n", encoding="utf-8")
            (repoDir / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repoDir, check=True)
            outputPath = Path(temporaryDir) / "release.zip"

            manifest = buildRelease(repoDir, outputPath, "v1.2.3", "abc123")

            paths = {item["path"] for item in manifest["files"]}
            self.assertEqual({"bot/main.py"}, paths)
            with zipfile.ZipFile(outputPath) as archive:
                archivedPaths = set(archive.namelist())
                parsedManifest = json.loads(archive.read("release-manifest.json"))
            self.assertNotIn(".env", archivedPaths)
            self.assertEqual("v1.2.3", parsedManifest["tag"])


if __name__ == "__main__":
    unittest.main()
