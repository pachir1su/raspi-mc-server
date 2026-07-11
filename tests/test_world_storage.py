"""Filesystem tests for backup, restore, and hostile map uploads."""

import asyncio
import tempfile
import unittest
import zipfile
from pathlib import Path

from bot.backup_settings import BackupSettings
from bot.world_storage import StorageError, WorldStorage


class WorldStorageTests(unittest.TestCase):
    """Use temporary directories so tests never need or alter a real HDD."""

    def setUp(self):
        """Create a minimal Paper world and a mount-check-disabled manager."""
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.serverDir = self.root / "live"
        worldDir = self.serverDir / "world"
        worldDir.mkdir(parents=True)
        (worldDir / "level.dat").write_bytes(b"level-one")
        (worldDir / "region").mkdir()
        (worldDir / "region" / "r.0.0.mca").write_bytes(b"chunks")
        self.storage = WorldStorage(str(self.root), str(self.serverDir), requireMount=False)

    def tearDown(self):
        """Release every temporary test file."""
        self.temporary.cleanup()

    def testBackupAndRestore(self):
        """A complete archive restores the original level data."""
        settings = BackupSettings(minFreeGb=1, maxUsagePercent=95)
        archivePath = asyncio.run(self.storage.createBackup(settings, "test"))
        self.assertTrue(archivePath.is_file())
        self.assertTrue(archivePath.with_suffix(archivePath.suffix + ".sha256").is_file())
        self.assertEqual(64, len(self.storage.verifyBackup(archivePath.name)))
        (self.serverDir / "world" / "level.dat").write_bytes(b"changed")
        asyncio.run(self.storage.restoreBackup(archivePath.name))
        self.assertEqual(b"level-one", (self.serverDir / "world" / "level.dat").read_bytes())

    def testCorruptBackupBlocksRestore(self):
        """Changing an archive after creation causes checksum verification to fail."""
        settings = BackupSettings(minFreeGb=1, maxUsagePercent=95)
        archivePath = asyncio.run(self.storage.createBackup(settings, "test"))
        with archivePath.open("ab") as archive:
            archive.write(b"corruption")
        with self.assertRaisesRegex(StorageError, "checksum mismatch"):
            self.storage.verifyBackup(archivePath.name)
        with self.assertRaises(StorageError):
            asyncio.run(self.storage.restoreBackup(archivePath.name))

    def testMissingChecksumBlocksRestore(self):
        """Legacy or incomplete archives without sidecars cannot be restored silently."""
        settings = BackupSettings(minFreeGb=1, maxUsagePercent=95)
        archivePath = asyncio.run(self.storage.createBackup(settings, "test"))
        archivePath.with_suffix(archivePath.suffix + ".sha256").unlink()
        with self.assertRaisesRegex(StorageError, "sidecar is missing"):
            self.storage.verifyBackup(archivePath.name)

    def testImportsVanillaWorld(self):
        """A single level.dat wrapped in one directory is accepted."""
        self.storage.ensureReady()
        archivePath = self.root / "map.zip"
        with zipfile.ZipFile(archivePath, "w") as archive:
            archive.writestr("My World/level.dat", b"map")
            archive.writestr("My World/region/r.0.0.mca", b"chunks")
        targetPath = self.storage.importWorldArchive(archivePath, "survival-map")
        self.assertTrue((targetPath / "level.dat").is_file())

    def testRejectsZipTraversal(self):
        """Uploaded archives cannot write outside their staging directory."""
        self.storage.ensureReady()
        archivePath = self.root / "hostile.zip"
        with zipfile.ZipFile(archivePath, "w") as archive:
            archive.writestr("../escape.txt", b"bad")
            archive.writestr("level.dat", b"map")
        with self.assertRaises(StorageError):
            self.storage.importWorldArchive(archivePath, "bad-map")
        self.assertFalse((self.root.parent / "escape.txt").exists())


if __name__ == "__main__":
    unittest.main()
