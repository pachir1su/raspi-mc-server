"""Tests for release-bundled Paper plugin validation and installation."""

import tempfile
import unittest
import zipfile
from pathlib import Path

from bot.bundled_plugins import BundledPluginManager, validatePluginJar


def _writePlugin(path: Path, extra: str = "") -> None:
    """Create the minimum valid plugin JAR fixture."""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("plugin.yml", "name: RaspiMcOps\n" + extra)
        archive.writestr(
            "io/github/pachir1su/raspimcops/RaspiMcOpsPlugin.class",
            b"fixture-bytecode",
        )


class BundledPluginTests(unittest.TestCase):
    def testInstallsOnlyChangedValidatedJar(self):
        """A release plugin is copied once and identical restarts are no-ops."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sourceDir = root / "repo" / "bundled-plugins"
            sourceDir.mkdir(parents=True)
            _writePlugin(sourceDir / "raspi-mc-ops.jar")
            manager = BundledPluginManager(root / "repo", root / "server", "minecraft.service")
            self.assertTrue(manager.ensure())
            self.assertFalse(manager.ensure())
            self.assertEqual(
                validatePluginJar(sourceDir / "raspi-mc-ops.jar"),
                validatePluginJar(root / "server" / "plugins" / "raspi-mc-ops.jar"),
            )

    def testRejectsTraversalAndIncompleteJar(self):
        """Release packaging cannot smuggle paths or a non-plugin ZIP."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unsafePath = root / "unsafe.jar"
            with zipfile.ZipFile(unsafePath, "w") as archive:
                archive.writestr("../escape", "bad")
            with self.assertRaises(RuntimeError):
                validatePluginJar(unsafePath)
            incompletePath = root / "incomplete.jar"
            with zipfile.ZipFile(incompletePath, "w") as archive:
                archive.writestr("plugin.yml", "name: missing classes")
            with self.assertRaises(RuntimeError):
                validatePluginJar(incompletePath)


if __name__ == "__main__":
    unittest.main()
