"""Install release-bundled Paper plugins into the live server safely."""

import hashlib
import os
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable


PLUGIN_FILE_NAME = "raspi-mc-ops.jar"
MAX_PLUGIN_BYTES = 10 * 1024 * 1024
REQUIRED_ENTRIES = {
    "plugin.yml",
    "io/github/pachir1su/raspimcops/RaspiMcOpsPlugin.class",
}


def _sha256(path: Path) -> str:
    """Hash one plugin without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as sourceFile:
        for chunk in iter(lambda: sourceFile.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validatePluginJar(path: Path) -> str:
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
            if not REQUIRED_ENTRIES.issubset(names):
                raise RuntimeError("bundled Paper plugin is incomplete")
    except (OSError, zipfile.BadZipFile) as error:
        raise RuntimeError(f"invalid bundled Paper plugin: {error}") from error
    return _sha256(path)


class BundledPluginManager:
    """Copy only an authenticated release JAR and restart Paper when needed."""

    def __init__(
        self,
        repoDir: str | Path,
        serverDir: str | Path,
        serviceName: str,
        commandRunner: Callable = subprocess.run,
    ):
        self.sourcePath = Path(repoDir).resolve() / "bundled-plugins" / PLUGIN_FILE_NAME
        self.pluginsDir = Path(serverDir).resolve() / "plugins"
        self.destinationPath = self.pluginsDir / PLUGIN_FILE_NAME
        self.serviceName = serviceName
        self.commandRunner = commandRunner

    def ensure(self) -> bool:
        """Install a changed release JAR atomically; source checkouts may omit it."""
        if not self.sourcePath.is_file():
            return False
        sourceDigest = validatePluginJar(self.sourcePath)
        if self.destinationPath.is_file():
            try:
                if validatePluginJar(self.destinationPath) == sourceDigest:
                    return False
            except RuntimeError:
                pass
        self.pluginsDir.mkdir(parents=True, exist_ok=True)
        descriptor, temporaryPath = tempfile.mkstemp(
            prefix=".raspi-mc-ops-", suffix=".jar", dir=self.pluginsDir
        )
        try:
            with os.fdopen(descriptor, "wb") as outputFile, self.sourcePath.open("rb") as inputFile:
                for chunk in iter(lambda: inputFile.read(1024 * 1024), b""):
                    outputFile.write(chunk)
                outputFile.flush()
                os.fsync(outputFile.fileno())
            os.replace(temporaryPath, self.destinationPath)
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
