"""Safe HDD-backed Minecraft world backup, upload, and restore operations."""

import asyncio
import hashlib
import os
import shutil
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

from bot.backup_settings import BackupSettings


WORLD_NAMES = ("world", "world_nether", "world_the_end")
ARCHIVE_SUFFIXES = (".tar.gz", ".tgz", ".zip")
MAX_EXTRACTED_BYTES = 100 * 1024 ** 3
MAX_ARCHIVE_MEMBERS = 1_000_000


@dataclass
class StoredFile:
    """Display-safe metadata for a backup or uploaded map."""

    name: str
    size: int
    modifiedAt: datetime


class StorageError(RuntimeError):
    """An expected and user-displayable storage failure."""


class WorldStorage:
    """Serialize destructive jobs and keep all large data on the HDD."""

    def __init__(self, storageRoot: str, serverDir: str, requireMount: bool = True):
        self.storageRoot = Path(storageRoot).resolve()
        self.serverDir = Path(serverDir).resolve()
        self.backupDir = self.storageRoot / "backups"
        self.worldsDir = self.storageRoot / "worlds"
        self.uploadsDir = self.storageRoot / "uploads"
        self.stagingDir = self.storageRoot / "staging"
        self.quarantineDir = self.storageRoot / "quarantine"
        self.requireMount = requireMount
        self.jobLock = asyncio.Lock()

    def ensureReady(self):
        """Fail closed instead of silently writing backups to the microSD."""
        if self.requireMount and not os.path.ismount(self.storageRoot):
            raise StorageError(f"HDD is not mounted at {self.storageRoot}")
        if not self.storageRoot.exists():
            raise StorageError(f"Storage root does not exist: {self.storageRoot}")
        for directory in (
            self.backupDir, self.worldsDir, self.uploadsDir,
            self.stagingDir, self.quarantineDir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def storageUsage(self) -> tuple[int, int, int]:
        """Return total, used, and free byte counts for the HDD."""
        self.ensureReady()
        usage = shutil.disk_usage(self.storageRoot)
        return usage.total, usage.used, usage.free

    def _checkCapacity(self, settings: BackupSettings):
        """Reserve free space and stop before the configured usage ceiling."""
        total, used, free = self.storageUsage()
        usedPercent = (used / total) * 100 if total else 100
        if usedPercent >= settings.maxUsagePercent:
            raise StorageError(f"HDD usage is {usedPercent:.1f}% (limit {settings.maxUsagePercent}%)")
        minimumBytes = settings.minFreeGb * 1024 ** 3
        if free < minimumBytes:
            raise StorageError(f"HDD free space is below {settings.minFreeGb} GB")

    def _worldDirectories(self) -> list[Path]:
        """Find the standard Paper world dimensions that currently exist."""
        worlds = [self.serverDir / name for name in WORLD_NAMES]
        existing = [path for path in worlds if path.is_dir()]
        if not existing:
            raise StorageError(f"No world directories found in {self.serverDir}")
        return existing

    async def createBackup(self, settings: BackupSettings, label: str = "auto") -> Path:
        """Create a compressed archive in a worker thread under the job lock."""
        async with self.jobLock:
            return await asyncio.to_thread(self._createBackupSync, settings, label)

    def _createBackupSync(self, settings: BackupSettings, label: str) -> Path:
        """Write to a temporary file and publish only a complete archive."""
        self.ensureReady()
        self.pruneBackups(settings)
        self._checkCapacity(settings)
        worlds = self._worldDirectories()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        safeLabel = "".join(character for character in label if character.isalnum() or character in "-_")
        archivePath = self.backupDir / f"world_{stamp}_{safeLabel or 'manual'}.tar.gz"
        temporaryPath = archivePath.with_suffix(archivePath.suffix + ".partial")
        try:
            with tarfile.open(temporaryPath, "w:gz", compresslevel=3) as archive:
                for worldPath in worlds:
                    archive.add(worldPath, arcname=worldPath.name, recursive=True)
            os.replace(temporaryPath, archivePath)
            self._writeChecksum(archivePath)
            self.pruneBackups(settings)
            return archivePath
        except Exception as error:
            temporaryPath.unlink(missing_ok=True)
            raise StorageError(f"Backup failed: {error}") from error

    def _writeChecksum(self, filePath: Path):
        """Write a SHA-256 sidecar so corruption can be detected before restore."""
        digest = hashlib.sha256()
        with filePath.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        filePath.with_suffix(filePath.suffix + ".sha256").write_text(
            f"{digest.hexdigest()}  {filePath.name}\n", encoding="ascii"
        )

    def listBackups(self) -> list[StoredFile]:
        """List newest valid backup archives first."""
        self.ensureReady()
        files = []
        for path in self.backupDir.glob("world_*.tar.gz"):
            stat = path.stat()
            files.append(StoredFile(path.name, stat.st_size, datetime.fromtimestamp(stat.st_mtime, timezone.utc)))
        return sorted(files, key=lambda item: item.modifiedAt, reverse=True)

    def resolveBackup(self, name: str) -> Path:
        """Resolve a backup by basename without allowing path traversal."""
        if Path(name).name != name:
            raise StorageError("Invalid backup name")
        path = (self.backupDir / name).resolve()
        if path.parent != self.backupDir or not path.is_file():
            raise StorageError("Backup not found")
        return path

    def pruneBackups(self, settings: BackupSettings) -> int:
        """Keep all recent backups plus one newest-per-day retention sample."""
        now = datetime.now(timezone.utc)
        denseCutoff = now - timedelta(hours=settings.retentionHours)
        dailyCutoff = now - timedelta(days=settings.dailyRetentionDays)
        dailySeen = set()
        deletedCount = 0
        for item in self.listBackups():
            if item.modifiedAt >= denseCutoff:
                continue
            dayKey = item.modifiedAt.date()
            if item.modifiedAt >= dailyCutoff and dayKey not in dailySeen:
                dailySeen.add(dayKey)
                continue
            path = self.resolveBackup(item.name)
            path.unlink(missing_ok=True)
            path.with_suffix(path.suffix + ".sha256").unlink(missing_ok=True)
            deletedCount += 1
        return deletedCount

    def verifyBackup(self, name: str) -> str:
        """Verify SHA-256 and archive structure before a backup can be restored."""
        self.ensureReady()
        path = self.resolveBackup(name)
        checksumPath = path.with_suffix(path.suffix + ".sha256")
        if not checksumPath.is_file():
            raise StorageError("Backup checksum sidecar is missing")
        try:
            expected = checksumPath.read_text(encoding="ascii").split()[0].lower()
        except (OSError, IndexError, UnicodeError) as error:
            raise StorageError(f"Backup checksum is unreadable: {error}") from error
        if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
            raise StorageError("Backup checksum has an invalid format")
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        actual = digest.hexdigest()
        if actual != expected:
            raise StorageError("Backup checksum mismatch; restore is blocked")
        try:
            with tarfile.open(path, "r:gz") as archive:
                members = archive.getmembers()
                self._safeMembers([member.name for member in members])
                self._checkArchiveLimits(len(members), sum(member.size for member in members))
                if any(member.issym() or member.islnk() or member.isdev() for member in members):
                    raise StorageError("Backup contains an unsafe archive member")
                if not any(member.name == "world/level.dat" for member in members):
                    raise StorageError("Backup does not contain world/level.dat")
        except (tarfile.TarError, OSError) as error:
            raise StorageError(f"Backup archive is unreadable: {error}") from error
        return actual

    def _safeMembers(self, names: list[str]):
        """Reject absolute paths, traversal, and suspicious archive members."""
        for name in names:
            purePath = PurePosixPath(name.replace("\\", "/"))
            if purePath.is_absolute() or ".." in purePath.parts:
                raise StorageError(f"Unsafe archive path: {name}")

    def importWorldArchive(self, sourcePath: Path, displayName: str) -> Path:
        """Extract an uploaded archive into staging, validate, then publish it."""
        self.ensureReady()
        safeName = "".join(character for character in displayName if character.isalnum() or character in "-_")[:64]
        if not safeName:
            raise StorageError("Map name contains no usable characters")
        targetPath = self.worldsDir / safeName
        if targetPath.exists():
            raise StorageError("A stored map with that name already exists")
        with tempfile.TemporaryDirectory(dir=self.stagingDir, prefix="import-") as temporaryDir:
            stagingPath = Path(temporaryDir)
            self._extractArchive(sourcePath, stagingPath)
            worldRoot = self._findWorldRoot(stagingPath)
            shutil.copytree(worldRoot, targetPath)
        return targetPath

    def _extractArchive(self, sourcePath: Path, destination: Path):
        """Extract ZIP or tar archives after validating member paths and links."""
        lowerName = sourcePath.name.lower()
        if lowerName.endswith(".zip"):
            with zipfile.ZipFile(sourcePath) as archive:
                members = archive.infolist()
                self._safeMembers([member.filename for member in members])
                self._checkArchiveLimits(len(members), sum(member.file_size for member in members))
                if any((member.external_attr >> 16) & 0o170000 == 0o120000 for member in members):
                    raise StorageError("Archive symbolic links are not allowed")
                archive.extractall(destination)
            return
        if lowerName.endswith((".tar.gz", ".tgz")):
            with tarfile.open(sourcePath, "r:gz") as archive:
                members = archive.getmembers()
                self._safeMembers([member.name for member in members])
                self._checkArchiveLimits(len(members), sum(member.size for member in members))
                if any(member.issym() or member.islnk() or member.isdev() for member in members):
                    raise StorageError("Archive links and device files are not allowed")
                archive.extractall(destination, members=members, filter="data")
            return
        raise StorageError("Only .zip, .tar.gz, and .tgz map files are supported")

    def _checkArchiveLimits(self, memberCount: int, extractedBytes: int):
        """Reject archive bombs before they consume the HDD or millions of inodes."""
        if memberCount > MAX_ARCHIVE_MEMBERS:
            raise StorageError("Archive contains too many files")
        if extractedBytes > MAX_EXTRACTED_BYTES:
            raise StorageError("Archive expands beyond the 100 GiB safety limit")
        _, _, free = self.storageUsage()
        if extractedBytes > free // 2:
            raise StorageError("Archive would consume more than half of remaining HDD space")

    def deleteBackup(self, name: str):
        """Delete one explicitly selected archive and its checksum."""
        path = self.resolveBackup(name)
        path.unlink()
        path.with_suffix(path.suffix + ".sha256").unlink(missing_ok=True)

    def deleteWorld(self, name: str):
        """Delete one imported map after basename and structure validation."""
        if Path(name).name != name:
            raise StorageError("Invalid map name")
        path = (self.worldsDir / name).resolve()
        if path.parent != self.worldsDir or not (path / "level.dat").is_file():
            raise StorageError("Stored map not found or invalid")
        shutil.rmtree(path)

    def _findWorldRoot(self, stagingPath: Path) -> Path:
        """Accept a root world or one wrapping directory containing level.dat."""
        candidates = [stagingPath] + [path for path in stagingPath.iterdir() if path.is_dir()]
        matches = [path for path in candidates if (path / "level.dat").is_file()]
        if len(matches) != 1:
            raise StorageError("Archive must contain exactly one Java world with level.dat")
        return matches[0]

    def listWorlds(self) -> list[StoredFile]:
        """List validated stored maps with their recursive sizes."""
        self.ensureReady()
        items = []
        for path in self.worldsDir.iterdir():
            if path.is_dir() and (path / "level.dat").is_file():
                size = sum(file.stat().st_size for file in path.rglob("*") if file.is_file())
                stat = path.stat()
                items.append(StoredFile(path.name, size, datetime.fromtimestamp(stat.st_mtime, timezone.utc)))
        return sorted(items, key=lambda item: item.modifiedAt, reverse=True)

    async def exportWorld(self, name: str) -> Path:
        """Create a temporary ZIP of an imported map for Discord download."""
        async with self.jobLock:
            return await asyncio.to_thread(self._exportWorldSync, name)

    def _exportWorldSync(self, name: str) -> Path:
        """Archive a validated stored map and return its path in uploads."""
        self.ensureReady()
        if Path(name).name != name:
            raise StorageError("Invalid map name")
        sourcePath = (self.worldsDir / name).resolve()
        if sourcePath.parent != self.worldsDir or not (sourcePath / "level.dat").is_file():
            raise StorageError("Stored map not found or invalid")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        outputPath = self.uploadsDir / f"{name}-{stamp}.zip"
        temporaryPath = outputPath.with_suffix(".zip.partial")
        try:
            with zipfile.ZipFile(temporaryPath, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
                for filePath in sourcePath.rglob("*"):
                    if filePath.is_file():
                        archive.write(filePath, arcname=str(Path(name) / filePath.relative_to(sourcePath)))
            os.replace(temporaryPath, outputPath)
            return outputPath
        except Exception as error:
            temporaryPath.unlink(missing_ok=True)
            raise StorageError(f"Map export failed: {error}") from error

    async def restoreBackup(self, name: str):
        """Restore a known backup while the caller keeps Minecraft stopped."""
        async with self.jobLock:
            await asyncio.to_thread(self._restoreBackupSync, name)

    def _restoreBackupSync(self, name: str):
        """Validate a backup, stage it, and roll back directory swaps on failure."""
        self.ensureReady()
        self.verifyBackup(name)
        archivePath = self.resolveBackup(name)
        with tempfile.TemporaryDirectory(dir=self.stagingDir, prefix="restore-") as temporaryDir:
            stagingPath = Path(temporaryDir)
            self._extractArchive(archivePath, stagingPath)
            incoming = [stagingPath / worldName for worldName in WORLD_NAMES]
            incoming = [path for path in incoming if path.is_dir()]
            if not incoming or not (stagingPath / "world" / "level.dat").is_file():
                raise StorageError("Backup does not contain a valid world")
            self._replaceLiveWorlds(incoming)

    async def activateWorld(self, name: str):
        """Activate an imported map while the caller keeps Minecraft stopped."""
        async with self.jobLock:
            await asyncio.to_thread(self._activateWorldSync, name)

    def _activateWorldSync(self, name: str):
        """Convert a vanilla map layout to Paper's three-world directory layout."""
        self.ensureReady()
        if Path(name).name != name:
            raise StorageError("Invalid map name")
        sourcePath = (self.worldsDir / name).resolve()
        if sourcePath.parent != self.worldsDir or not (sourcePath / "level.dat").is_file():
            raise StorageError("Stored map not found or invalid")
        with tempfile.TemporaryDirectory(dir=self.stagingDir, prefix="activate-") as temporaryDir:
            stagingPath = Path(temporaryDir)
            mainWorld = stagingPath / "world"
            shutil.copytree(sourcePath, mainWorld)
            incoming = [mainWorld]
            for dimensionDir, paperName in (("DIM-1", "world_nether"), ("DIM1", "world_the_end")):
                dimensionPath = mainWorld / dimensionDir
                if not dimensionPath.is_dir():
                    continue
                paperPath = stagingPath / paperName
                paperPath.mkdir()
                shutil.copy2(mainWorld / "level.dat", paperPath / "level.dat")
                shutil.move(str(dimensionPath), str(paperPath / dimensionDir))
                incoming.append(paperPath)
            self._replaceLiveWorlds(incoming)

    def _replaceLiveWorlds(self, incoming: list[Path]):
        """Swap all live world directories and restore the old set if a move fails."""
        self.serverDir.mkdir(parents=True, exist_ok=True)
        rollbackRoot = self.stagingDir / f"rollback-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        rollbackRoot.mkdir(parents=True)
        movedOld = []
        movedNew = []
        try:
            for worldName in WORLD_NAMES:
                livePath = self.serverDir / worldName
                if livePath.exists():
                    rollbackPath = rollbackRoot / worldName
                    os.replace(livePath, rollbackPath)
                    movedOld.append((rollbackPath, livePath))
            for sourcePath in incoming:
                livePath = self.serverDir / sourcePath.name
                os.replace(sourcePath, livePath)
                movedNew.append(livePath)
            shutil.rmtree(rollbackRoot)
        except Exception as error:
            for livePath in movedNew:
                if livePath.exists():
                    shutil.rmtree(livePath, ignore_errors=True)
            for rollbackPath, livePath in movedOld:
                if rollbackPath.exists():
                    os.replace(rollbackPath, livePath)
            shutil.rmtree(rollbackRoot, ignore_errors=True)
            raise StorageError(f"World replacement failed and was rolled back: {error}") from error
