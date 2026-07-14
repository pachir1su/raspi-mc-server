"""Safe update discovery, archive validation, and updater request storage."""

import hashlib
import json
import os
import stat
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


REPOSITORY = "pachir1su/raspi-mc-server"
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_EXTRACTED_BYTES = 200 * 1024 * 1024
MAX_ARCHIVE_FILES = 2_000
PROTECTED_PATHS = {".env"}
PROTECTED_PREFIXES = (
    ".git/",
    ".venv/",
    "data/",
    "bot/logs/",
    "backups/",
    "server/world",
)


class UpdateError(RuntimeError):
    """Raised when an update cannot be trusted or safely staged."""


@dataclass(frozen=True)
class ReleaseInfo:
    """The one deployment asset selected from a GitHub Release."""

    tag: str
    assetName: str
    downloadUrl: str
    digest: str
    size: int
    pageUrl: str


def fileSha256(path: Path) -> str:
    """Hash a potentially large archive with bounded memory."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as sourceFile:
            for chunk in iter(lambda: sourceFile.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise UpdateError(f"cannot read update archive: {error}") from error
    return digest.hexdigest()


def _safeArchivePath(rawPath: str) -> str:
    """Normalize one ZIP path while rejecting traversal and protected data."""
    path = PurePosixPath(rawPath)
    normalized = path.as_posix()
    if not normalized or path.is_absolute() or ".." in path.parts or "\\" in rawPath:
        raise UpdateError(f"unsafe archive path: {rawPath}")
    if normalized in PROTECTED_PATHS or normalized.startswith(PROTECTED_PREFIXES):
        raise UpdateError(f"release attempts to replace protected path: {normalized}")
    return normalized


def validateReleaseArchive(path: Path, expectedTag: str | None = None) -> dict:
    """Verify paths, sizes, manifest membership, and every file checksum."""
    try:
        archiveSize = path.stat().st_size
    except OSError as error:
        raise UpdateError(f"update archive is unavailable: {error}") from error
    if archiveSize > MAX_ARCHIVE_BYTES:
        raise UpdateError("update archive exceeds 50 MiB")
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ARCHIVE_FILES:
                raise UpdateError("update archive contains too many files")
            totalSize = sum(entry.file_size for entry in entries)
            if totalSize > MAX_EXTRACTED_BYTES:
                raise UpdateError("expanded update exceeds 200 MiB")
            entryNames = set()
            for entry in entries:
                normalized = _safeArchivePath(entry.filename)
                entryNames.add(normalized)
                unixMode = entry.external_attr >> 16
                if stat.S_ISLNK(unixMode):
                    raise UpdateError(f"symbolic links are not allowed: {normalized}")
            if "release-manifest.json" not in entryNames:
                raise UpdateError("release-manifest.json is missing")
            try:
                manifest = json.loads(archive.read("release-manifest.json"))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise UpdateError(f"invalid release manifest: {error}") from error
            if manifest.get("schemaVersion") != 1:
                raise UpdateError("unsupported release manifest schema")
            tag = manifest.get("tag")
            if not isinstance(tag, str) or not tag.startswith("v"):
                raise UpdateError("invalid release tag")
            if expectedTag and tag != expectedTag:
                raise UpdateError(f"release tag mismatch: expected {expectedTag}, got {tag}")
            fileItems = manifest.get("files")
            if not isinstance(fileItems, list):
                raise UpdateError("release manifest files must be a list")
            manifestNames = set()
            for item in fileItems:
                if not isinstance(item, dict):
                    raise UpdateError("invalid release manifest entry")
                fileName = _safeArchivePath(str(item.get("path", "")))
                if fileName in manifestNames:
                    raise UpdateError(f"duplicate manifest path: {fileName}")
                manifestNames.add(fileName)
                try:
                    content = archive.read(fileName)
                except KeyError as error:
                    raise UpdateError(f"manifest file is missing: {fileName}") from error
                if len(content) != item.get("size"):
                    raise UpdateError(f"size mismatch: {fileName}")
                if hashlib.sha256(content).hexdigest() != item.get("sha256"):
                    raise UpdateError(f"checksum mismatch: {fileName}")
            if entryNames - {"release-manifest.json"} != manifestNames:
                raise UpdateError("archive contains files not declared by the manifest")
            return manifest
    except (OSError, zipfile.BadZipFile) as error:
        raise UpdateError(f"invalid update ZIP: {error}") from error


def fetchLatestRelease(timeoutSeconds: int = 15) -> ReleaseInfo:
    """Fetch the latest official deployment asset with a short timeout."""
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/releases/latest",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "raspi-mc-server-updater",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeoutSeconds) as response:
            payload = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise UpdateError(f"cannot check GitHub Releases: {error}") from error
    tag = payload.get("tag_name", "")
    expectedName = f"raspi-mc-server-{tag}.zip"
    for asset in payload.get("assets", []):
        if asset.get("name") != expectedName:
            continue
        size = int(asset.get("size", 0))
        if size <= 0 or size > MAX_ARCHIVE_BYTES:
            raise UpdateError("GitHub release asset has an invalid size")
        return ReleaseInfo(
            tag=tag,
            assetName=expectedName,
            downloadUrl=str(asset.get("browser_download_url", "")),
            digest=str(asset.get("digest") or ""),
            size=size,
            pageUrl=str(payload.get("html_url", "")),
        )
    raise UpdateError(f"release {tag or '(unknown)'} has no deployment ZIP")


class UpdateStore:
    """Atomically stage update requests for the root-owned updater service."""

    def __init__(self, stateDir: str, storageRoot: str):
        self.stateDir = Path(stateDir).resolve()
        self.stagingDir = (Path(storageRoot).resolve() / "staging" / "app-updates")
        self.requestPath = self.stateDir / "update-request.json"
        self.statusPath = self.stateDir / "update-status.json"

    @staticmethod
    def _writeJson(path: Path, payload: dict) -> None:
        """Replace one state file without exposing a partially written request."""
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporaryPath = tempfile.mkstemp(
            prefix=f".{path.name}-", dir=path.parent
        )
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

    def stageUploadedArchive(self, temporaryPath: Path) -> dict:
        """Validate and move one Discord upload into the HDD staging area."""
        manifest = validateReleaseArchive(temporaryPath)
        self.stagingDir.mkdir(parents=True, exist_ok=True)
        destination = self.stagingDir / f"raspi-mc-server-{manifest['tag']}.zip"
        try:
            os.replace(temporaryPath, destination)
        except OSError as error:
            raise UpdateError(f"cannot stage uploaded update: {error}") from error
        return {
            "source": "upload",
            "tag": manifest["tag"],
            "archivePath": str(destination),
            "sha256": fileSha256(destination),
        }

    def requestRelease(self, release: ReleaseInfo) -> dict:
        """Create a latest-release request consumed by the updater service."""
        payload = {
            "source": "github",
            "tag": release.tag,
            "downloadUrl": release.downloadUrl,
            "sha256": release.digest.removeprefix("sha256:"),
        }
        self._writeJson(self.requestPath, payload)
        return payload

    def requestUpload(self, stagedPayload: dict) -> None:
        """Persist a previously validated uploaded-archive request."""
        self._writeJson(self.requestPath, stagedPayload)

    def readStatus(self) -> dict:
        """Return updater status without failing the Discord command."""
        try:
            with self.statusPath.open("r", encoding="utf-8") as statusFile:
                payload = json.load(statusFile)
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}
