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


def buildRelease(repoDir: Path, outputPath: Path, tag: str, commit: str) -> dict:
    """Create a ZIP whose manifest authenticates every deployable file."""
    if not tag.startswith("v") or len(tag) > 64:
        raise ValueError("release tag must start with v and be at most 64 characters")
    repoDir = repoDir.resolve()
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    manifestFiles = []
    trackedFiles = _trackedFiles(repoDir)
    for filePath in trackedFiles:
        relativePath = filePath.relative_to(repoDir).as_posix()
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
            for filePath in trackedFiles:
                archive.write(filePath, filePath.relative_to(repoDir).as_posix())
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
    args = parser.parse_args()
    manifest = buildRelease(args.repo, args.output, args.tag, args.commit)
    print(f"built {args.output} with {len(manifest['files'])} files")
    print(f"sha256:{_sha256(args.output)}")


if __name__ == "__main__":
    main()
