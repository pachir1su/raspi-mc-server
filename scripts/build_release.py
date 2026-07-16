#!/usr/bin/env python3
"""Build a manifest-verified deployment ZIP for GitHub Releases."""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path, PurePosixPath


EXCLUDED_PATHS = {".env"}
EXCLUDED_PREFIXES = (
    ".git/",
    ".venv/",
    "bot/logs/",
    "data/",
    "backups/",
    "server/world",
)


def _sha256(path: Path) -> str:
    """Hash one file without loading the entire release into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as sourceFile:
        for chunk in iter(lambda: sourceFile.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _trackedFiles(repoDir: Path) -> list[Path]:
    """Return safe tracked files in stable archive order."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=repoDir,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(f"cannot list tracked release files: {error}") from error
    paths = []
    for rawPath in result.stdout.decode("utf-8").split("\0"):
        if not rawPath:
            continue
        normalizedPath = PurePosixPath(rawPath).as_posix()
        if normalizedPath in EXCLUDED_PATHS:
            continue
        if normalizedPath.startswith(EXCLUDED_PREFIXES):
            continue
        filePath = repoDir / Path(*PurePosixPath(normalizedPath).parts)
        if filePath.is_file():
            paths.append(filePath)
    return sorted(paths, key=lambda path: path.relative_to(repoDir).as_posix())


def _safeExtraTarget(rawPath: str) -> str:
    """Validate one generated artifact destination inside the release archive."""
    path = PurePosixPath(rawPath)
    normalizedPath = path.as_posix()
    if not normalizedPath or path.is_absolute() or ".." in path.parts or "\\" in rawPath:
        raise ValueError(f"unsafe generated release path: {rawPath}")
    if normalizedPath in EXCLUDED_PATHS or normalizedPath.startswith(EXCLUDED_PREFIXES):
        raise ValueError(f"protected generated release path: {normalizedPath}")
    return normalizedPath


def buildRelease(
    repoDir: Path,
    outputPath: Path,
    tag: str,
    commit: str,
    extraFiles: dict[str, Path] | None = None,
) -> dict:
    """Create a ZIP whose manifest authenticates every deployable file."""
    if not tag.startswith("v") or len(tag) > 64:
        raise ValueError("release tag must start with v and be at most 64 characters")
    repoDir = repoDir.resolve()
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    archiveFiles = {
        filePath.relative_to(repoDir).as_posix(): filePath
        for filePath in _trackedFiles(repoDir)
    }
    for rawTarget, rawSource in (extraFiles or {}).items():
        target = _safeExtraTarget(rawTarget)
        source = Path(rawSource).resolve()
        if target in archiveFiles:
            raise ValueError(f"generated release path duplicates a tracked file: {target}")
        if not source.is_file():
            raise ValueError(f"generated release file is missing: {source}")
        archiveFiles[target] = source
    manifestFiles = []
    for relativePath, filePath in sorted(archiveFiles.items()):
        manifestFiles.append(
            {
                "path": relativePath,
                "size": filePath.stat().st_size,
                "sha256": _sha256(filePath),
            }
        )
    manifest = {
        "schemaVersion": 1,
        "tag": tag,
        "commit": commit,
        "files": manifestFiles,
    }
    manifestBytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    try:
        with zipfile.ZipFile(
            outputPath, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            archive.writestr("release-manifest.json", manifestBytes)
            for relativePath, filePath in sorted(archiveFiles.items()):
                archive.write(filePath, relativePath)
    except (OSError, zipfile.BadZipFile) as error:
        raise RuntimeError(f"cannot build release ZIP: {error}") from error
    return manifest


def main() -> None:
    """Parse workflow arguments and print the resulting asset checksum."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument(
        "--extra-file",
        action="append",
        default=[],
        metavar="SOURCE=ARCHIVE_PATH",
        help="include one generated artifact at a safe archive path",
    )
    args = parser.parse_args()
    extraFiles = {}
    for value in args.extra_file:
        if "=" not in value:
            parser.error("--extra-file must use SOURCE=ARCHIVE_PATH")
        source, target = value.split("=", 1)
        if target in extraFiles:
            parser.error(f"duplicate --extra-file target: {target}")
        extraFiles[target] = Path(source)
    manifest = buildRelease(
        args.repo, args.output, args.tag, args.commit, extraFiles=extraFiles
    )
    print(f"built {args.output} with {len(manifest['files'])} files")
    print(f"sha256:{_sha256(args.output)}")


if __name__ == "__main__":
    main()
