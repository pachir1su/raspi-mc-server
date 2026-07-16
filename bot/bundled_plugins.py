"""Install release-bundled Paper plugins into the live server safely."""

import hashlib
import os
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable


MAX_PLUGIN_BYTES = 10 * 1024 * 1024
# Every plugin shipped in a release ZIP's bundled-plugins/ directory, with the
# entries that prove the archive is the real, complete plugin.
BUNDLED_PLUGINS = {
    "raspi-mc-ops.jar": {
        "plugin.yml",
        "io/github/pachir1su/raspimcops/RaspiMcOpsPlugin.class",
    },
    "DeathBox.jar": {
        "plugin.yml",
        "io/github/pachir1su/deathbox/DeathBoxPlugin.class",
    },
}
REQUIRED_ENTRIES = BUNDLED_PLUGINS["raspi-mc-ops.jar"]


def _sha256(path: Path) -> str:
    """Hash one plugin without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as sourceFile:
        for chunk in iter(lambda: sourceFile.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validatePluginJar(path: Path, requiredEntries: set[str] = REQUIRED_ENTRIES) -> str:
    """Reject oversized, malformed, traversing, or incomplete plugin archives."""
    try:
        if not path.is_file() or path.stat().st_size > MAX_PLUGIN_BYTES:
            raise RuntimeError("bundled Paper plugin is missing or too large")
        with zipfile.ZipFile(path) as archive:
            names = set()
            for entry in archive.infolist():
                normalized = PurePosixPath(entry.filename)
                if normalized.is_absolute() or ".." in normalized.parts or "\\" in entry.filename:
                    raise RuntimeError("bundled Paper plugin contains an unsafe path")
                if stat.S_ISLNK(entry.external_attr >> 16):
                    raise RuntimeError("bundled Paper plugin contains a symlink")
                names.add(normalized.as_posix())
            if not requiredEntries.issubset(names):
                raise RuntimeError("bundled Paper plugin is incomplete")
    except (OSError, zipfile.BadZipFile) as error:
        raise RuntimeError(f"invalid bundled Paper plugin: {error}") from error
    return _sha256(path)


class BundledPluginManager:
    """Copy only authenticated release JARs and restart Paper when needed."""

    def __init__(
        self,
        repoDir: str | Path,
        serverDir: str | Path,
        serviceName: str,
        commandRunner: Callable = subprocess.run,
    ):
        self.sourceDir = Path(repoDir).resolve() / "bundled-plugins"
        self.pluginsDir = Path(serverDir).resolve() / "plugins"
        self.serviceName = serviceName
        self.commandRunner = commandRunner

    def ensure(self) -> bool:
        """Install every changed release JAR; source checkouts may omit them."""
        changed = False
        for fileName, requiredEntries in BUNDLED_PLUGINS.items():
            if self._ensureOne(fileName, requiredEntries):
                changed = True
        return changed

    def _ensureOne(self, fileName: str, requiredEntries: set[str]) -> bool:
        """Install one changed release JAR atomically if it is bundled."""
        sourcePath = self.sourceDir / fileName
        destinationPath = self.pluginsDir / fileName
        if not sourcePath.is_file():
            return False
        sourceDigest = validatePluginJar(sourcePath, requiredEntries)
        if destinationPath.is_file():
            try:
                if validatePluginJar(destinationPath, requiredEntries) == sourceDigest:
                    return False
            except RuntimeError:
                pass
        self.pluginsDir.mkdir(parents=True, exist_ok=True)
        descriptor, temporaryPath = tempfile.mkstemp(
            prefix=f".{Path(fileName).stem}-", suffix=".jar", dir=self.pluginsDir
        )
        try:
            with os.fdopen(descriptor, "wb") as outputFile, sourcePath.open("rb") as inputFile:
                for chunk in iter(lambda: inputFile.read(1024 * 1024), b""):
                    outputFile.write(chunk)
                outputFile.flush()
                os.fsync(outputFile.fileno())
            os.replace(temporaryPath, destinationPath)
        except Exception:
            try:
                os.unlink(temporaryPath)
            except OSError:
                pass
            raise
        return True

    def restartMinecraft(self) -> None:
        """Activate a newly installed plugin through the narrow systemd rule."""
        try:
            self.commandRunner(
                ["sudo", "systemctl", "restart", self.serviceName],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(error, "stderr", "") or str(error)
            raise RuntimeError(
                f"Paper plugin installed but {self.serviceName} restart failed: {detail.strip()}"
            ) from error
