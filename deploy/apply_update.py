#!/usr/bin/env python3
"""Root-owned transactional updater installed by setup_raspberrypi.sh.

Do not execute the repository copy through sudo. Provisioning copies this file
to /usr/local/lib/raspi-mc-server so a compromised bot cannot rewrite the code
that later runs as root.
"""

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


REPOSITORY = "pachir1su/raspi-mc-server"
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_EXTRACTED_BYTES = 200 * 1024 * 1024
MAX_FILES = 2_000
PROTECTED_PATHS = {".env"}
PROTECTED_PREFIXES = (
    ".git/",
    ".venv/",
    "data/",
    "bot/logs/",
    "backups/",
    "server/world",
)


class ApplyError(RuntimeError):
    """Raised when a release cannot be applied without risking the host."""


def _writeJson(path: Path, payload: dict) -> None:
    """Atomically publish updater state for the restarted Discord bot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporaryPath = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as outputFile:
            json.dump(payload, outputFile, indent=2)
            outputFile.write("\n")
            outputFile.flush()
            os.fsync(outputFile.fileno())
        os.replace(temporaryPath, path)
    except Exception:
        try:
            os.unlink(temporaryPath)
        except OSError:
            pass
        raise


def _sha256(path: Path) -> str:
    """Hash one archive with bounded memory."""
    digest = hashlib.sha256()
    with path.open("rb") as sourceFile:
        for chunk in iter(lambda: sourceFile.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safePath(rawPath: str) -> str:
    """Reject paths that escape the repo or target persistent data."""
    path = PurePosixPath(rawPath)
    normalized = path.as_posix()
    if not normalized or path.is_absolute() or ".." in path.parts or "\\" in rawPath:
        raise ApplyError(f"unsafe release path: {rawPath}")
    if normalized in PROTECTED_PATHS or normalized.startswith(PROTECTED_PREFIXES):
        raise ApplyError(f"protected release path: {normalized}")
    return normalized


def _loadAndValidateArchive(archivePath: Path, expectedTag: str) -> tuple[dict, list[str]]:
    """Validate the release manifest and return its authenticated file list."""
    if archivePath.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ApplyError("archive exceeds 50 MiB")
    try:
        with zipfile.ZipFile(archivePath) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_FILES:
                raise ApplyError("archive has too many files")
            if sum(entry.file_size for entry in entries) > MAX_EXTRACTED_BYTES:
                raise ApplyError("expanded archive exceeds 200 MiB")
            archiveNames = set()
            for entry in entries:
                archiveNames.add(_safePath(entry.filename))
                if stat.S_ISLNK(entry.external_attr >> 16):
                    raise ApplyError(f"release contains a symlink: {entry.filename}")
            manifest = json.loads(archive.read("release-manifest.json"))
            if manifest.get("schemaVersion") != 1 or manifest.get("tag") != expectedTag:
                raise ApplyError("release manifest schema or tag mismatch")
            fileNames = []
            for item in manifest.get("files", []):
                fileName = _safePath(str(item.get("path", "")))
                if fileName in fileNames:
                    raise ApplyError(f"duplicate release path: {fileName}")
                content = archive.read(fileName)
                if len(content) != item.get("size"):
                    raise ApplyError(f"release size mismatch: {fileName}")
                if hashlib.sha256(content).hexdigest() != item.get("sha256"):
                    raise ApplyError(f"release checksum mismatch: {fileName}")
                fileNames.append(fileName)
            if archiveNames - {"release-manifest.json"} != set(fileNames):
                raise ApplyError("release includes undeclared files")
            return manifest, fileNames
    except (OSError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        raise ApplyError(f"invalid release archive: {error}") from error


def _download(request: dict, stagingDir: Path) -> Path:
    """Download only the exact official GitHub Release asset URL."""
    tag = str(request.get("tag", ""))
    assetName = f"raspi-mc-server-{tag}.zip"
    downloadUrl = str(request.get("downloadUrl", ""))
    parsed = urllib.parse.urlparse(downloadUrl)
    expectedPath = f"/{REPOSITORY}/releases/download/{tag}/{assetName}"
    if parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.path != expectedPath:
        raise ApplyError("download URL is not the expected official GitHub Release asset")
    stagingDir.mkdir(parents=True, exist_ok=True)
    destination = stagingDir / assetName
    temporaryPath = stagingDir / f".{assetName}.download"
    requestObject = urllib.request.Request(
        downloadUrl, headers={"User-Agent": "raspi-mc-server-updater"}
    )
    try:
        with urllib.request.urlopen(requestObject, timeout=30) as response, temporaryPath.open("wb") as outputFile:
            downloadedBytes = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                downloadedBytes += len(chunk)
                if downloadedBytes > MAX_ARCHIVE_BYTES:
                    raise ApplyError("download exceeds 50 MiB")
                outputFile.write(chunk)
        os.replace(temporaryPath, destination)
        return destination
    except Exception:
        temporaryPath.unlink(missing_ok=True)
        raise


def _resolveArchive(request: dict, stagingDir: Path) -> Path:
    """Resolve either GitHub download or a Discord-staged local ZIP."""
    if request.get("source") == "github":
        return _download(request, stagingDir)
    if request.get("source") != "upload":
        raise ApplyError("unsupported update source")
    archivePath = Path(str(request.get("archivePath", ""))).resolve()
    try:
        archivePath.relative_to(stagingDir.resolve())
    except ValueError as error:
        raise ApplyError("uploaded archive is outside HDD staging") from error
    if not archivePath.is_file():
        raise ApplyError("uploaded archive is missing")
    return archivePath


def _run(command: list[str], timeoutSeconds: int = 300) -> None:
    """Run one fixed maintenance command and surface bounded diagnostics."""
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeoutSeconds,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ApplyError(f"cannot run {command[0]}: {error}") from error
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip()[-2_000:]
        raise ApplyError(f"{command[0]} failed: {detail}")


def _prepareVenv(repoDir: Path, extractDir: Path) -> Path:
    """Build and validate dependencies before stopping the running bot."""
    nextVenv = repoDir / ".venv-update"
    if nextVenv.exists():
        shutil.rmtree(nextVenv)
    _run(["python3", "-m", "venv", str(nextVenv)])
    pythonPath = nextVenv / "bin" / "python"
    _run([str(pythonPath), "-m", "pip", "install", "--upgrade", "pip"], 600)
    _run(
        [str(pythonPath), "-m", "pip", "install", "-r", str(extractDir / "requirements.txt")],
        900,
    )
    _run([str(pythonPath), "-m", "compileall", "-q", str(extractDir / "bot")])
    return nextVenv


def _backupFiles(repoDir: Path, backupDir: Path, fileNames: set[str]) -> set[str]:
    """Copy every file that may be overwritten or removed into rollback storage."""
    existingNames = set()
    for fileName in sorted(fileNames):
        source = repoDir / Path(*PurePosixPath(fileName).parts)
        if not source.is_file():
            continue
        destination = backupDir / Path(*PurePosixPath(fileName).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        existingNames.add(fileName)
    return existingNames


def _copyRelease(extractDir: Path, repoDir: Path, newNames: set[str], oldNames: set[str]) -> None:
    """Atomically replace release files and remove only old manifested files."""
    for fileName in sorted(newNames):
        source = extractDir / Path(*PurePosixPath(fileName).parts)
        destination = repoDir / Path(*PurePosixPath(fileName).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporaryPath = destination.with_name(f".{destination.name}.update")
        shutil.copy2(source, temporaryPath)
        os.replace(temporaryPath, destination)
    for fileName in sorted(oldNames - newNames):
        destination = repoDir / Path(*PurePosixPath(fileName).parts)
        if destination.is_file():
            destination.unlink()


def _restoreFiles(repoDir: Path, backupDir: Path, touchedNames: set[str], existingNames: set[str]) -> None:
    """Restore backed-up files and remove files that did not exist before."""
    for fileName in sorted(touchedNames):
        destination = repoDir / Path(*PurePosixPath(fileName).parts)
        if fileName not in existingNames:
            destination.unlink(missing_ok=True)
            continue
        source = backupDir / Path(*PurePosixPath(fileName).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def applyUpdate(args: argparse.Namespace) -> None:
    """Apply one queued release and roll back if the bot cannot restart."""
    repoDir = args.repo_dir.resolve()
    stateDir = args.state_dir.resolve()
    storageRoot = args.storage_root.resolve()
    stagingDir = storageRoot / "staging" / "app-updates"
    statusPath = stateDir / "update-status.json"
    requestPath = stateDir / "update-request.json"
    startedAt = datetime.now(timezone.utc).isoformat()
    request = json.loads(requestPath.read_text(encoding="utf-8"))
    tag = str(request.get("tag", ""))
    if not tag.startswith("v") or len(tag) > 64:
        raise ApplyError("invalid requested release tag")
    _writeJson(statusPath, {"state": "preparing", "tag": tag, "startedAt": startedAt})

    archivePath = _resolveArchive(request, stagingDir)
    expectedDigest = str(request.get("sha256", ""))
    if expectedDigest and _sha256(archivePath) != expectedDigest:
        raise ApplyError("outer archive SHA-256 mismatch")
    manifest, fileNames = _loadAndValidateArchive(archivePath, tag)
    with tempfile.TemporaryDirectory(prefix="raspi-mc-update-", dir=stagingDir) as temporaryDir:
        extractDir = Path(temporaryDir)
        with zipfile.ZipFile(archivePath) as archive:
            for fileName in fileNames:
                destination = extractDir / Path(*PurePosixPath(fileName).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(fileName))
        nextVenv = _prepareVenv(repoDir, extractDir)
        previousManifestPath = stateDir / "installed-release-manifest.json"
        try:
            previousManifest = json.loads(previousManifestPath.read_text(encoding="utf-8"))
            oldNames = {_safePath(str(item["path"])) for item in previousManifest.get("files", [])}
        except (OSError, KeyError, json.JSONDecodeError, ApplyError):
            oldNames = set()
        newNames = set(fileNames)
        touchedNames = oldNames | newNames
        backupDir = storageRoot / "backups" / "app-updates" / f"{int(time.time())}-{tag}"
        existingNames = _backupFiles(repoDir, backupDir, touchedNames)
        currentVenv = repoDir / ".venv"
        rollbackVenv = repoDir / ".venv-rollback"
        if rollbackVenv.exists():
            shutil.rmtree(rollbackVenv)

        _run(["systemctl", "stop", args.bot_service])
        try:
            _copyRelease(extractDir, repoDir, newNames, oldNames)
            if currentVenv.exists():
                os.replace(currentVenv, rollbackVenv)
            os.replace(nextVenv, currentVenv)
            _writeJson(previousManifestPath, manifest)
            _run(["systemctl", "start", args.bot_service])
            time.sleep(8)
            _run(["systemctl", "is-active", "--quiet", args.bot_service], 30)
        except Exception as error:
            subprocess.run(["systemctl", "stop", args.bot_service], check=False)
            _restoreFiles(repoDir, backupDir, touchedNames, existingNames)
            if currentVenv.exists():
                shutil.rmtree(currentVenv)
            if rollbackVenv.exists():
                os.replace(rollbackVenv, currentVenv)
            subprocess.run(["systemctl", "start", args.bot_service], check=False)
            _writeJson(
                statusPath,
                {"state": "rolled_back", "tag": tag, "error": str(error), "startedAt": startedAt},
            )
            raise
        if rollbackVenv.exists():
            shutil.rmtree(rollbackVenv)
        _writeJson(
            statusPath,
            {
                "state": "success",
                "tag": tag,
                "commit": manifest.get("commit", ""),
                "startedAt": startedAt,
                "finishedAt": datetime.now(timezone.utc).isoformat(),
                "backupPath": str(backupDir),
            },
        )
        requestPath.unlink(missing_ok=True)


def main() -> None:
    """Parse only provisioning-rendered paths and report failures to status JSON."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--bot-service", default="mc-discord-bot.service")
    args = parser.parse_args()
    statusPath = args.state_dir.resolve() / "update-status.json"
    try:
        if os.geteuid() != 0:
            raise ApplyError("updater must run as root through its systemd service")
        applyUpdate(args)
    except Exception as error:
        try:
            _writeJson(
                statusPath,
                {"state": "failed", "error": str(error), "finishedAt": datetime.now(timezone.utc).isoformat()},
            )
        except OSError:
            pass
        raise SystemExit(f"update failed: {error}") from error


if __name__ == "__main__":
    main()
