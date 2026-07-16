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

    def testIncludesGeneratedPluginAtAuthenticatedTarget(self):
        """CI-built plugin JARs join the same per-file manifest as tracked code."""
        with tempfile.TemporaryDirectory() as temporaryDir:
            root = Path(temporaryDir)
            repoDir = root / "repo"
            repoDir.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repoDir, check=True)
            (repoDir / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repoDir, check=True)
            pluginPath = root / "raspi-mc-ops.jar"
            pluginPath.write_bytes(b"plugin fixture")
            outputPath = root / "release.zip"

            manifest = buildRelease(
                repoDir,
                outputPath,
                "v1.2.3",
                "abc123",
                {"bundled-plugins/raspi-mc-ops.jar": pluginPath},
            )

            paths = {item["path"] for item in manifest["files"]}
            self.assertIn("bundled-plugins/raspi-mc-ops.jar", paths)
            with zipfile.ZipFile(outputPath) as archive:
                self.assertEqual(
                    b"plugin fixture",
                    archive.read("bundled-plugins/raspi-mc-ops.jar"),
                )

    def testRejectsUnsafeGeneratedTarget(self):
        """Generated artifacts cannot target secrets or escape the archive."""
        with tempfile.TemporaryDirectory() as temporaryDir:
            root = Path(temporaryDir)
            repoDir = root / "repo"
            repoDir.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repoDir, check=True)
            pluginPath = root / "plugin.jar"
            pluginPath.write_bytes(b"fixture")
            for target in ("../escape.jar", ".env", "server/world/plugin.jar"):
                with self.subTest(target=target), self.assertRaises(ValueError):
                    buildRelease(
                        repoDir,
                        root / "release.zip",
                        "v1.2.3",
                        "abc123",
                        {target: pluginPath},
                    )


if __name__ == "__main__":
    unittest.main()
