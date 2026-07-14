"""Failure-path tests for the shell world restore workflow."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]


def _writeExecutable(path: Path, content: str) -> None:
    """Create one executable command used by the isolated shell fixture."""
    path.write_text(content, encoding="utf-8", newline="\n")
    path.chmod(0o755)


def testExtractionFailureRollsBackMovedWorld():
    """A failed extraction must replace partial data with the original world."""
    bashExecutable = os.environ.get("BASH", "bash")
    with tempfile.TemporaryDirectory(dir=REPO_DIR) as temporaryDir:
        fixtureDir = Path(temporaryDir)
        scriptsDir = fixtureDir / "scripts"
        fakeBinDir = fixtureDir / "fake-bin"
        worldDir = fixtureDir / "storage" / "live" / "world"
        scriptsDir.mkdir()
        fakeBinDir.mkdir()
        worldDir.mkdir(parents=True)
        (worldDir / "original.marker").write_text("original\n", encoding="utf-8")
        archivePath = fixtureDir / "storage" / "backups" / "world_test.tar.gz"
        archivePath.parent.mkdir(parents=True)
        archivePath.write_bytes(b"fixture")

        shutil.copy2(REPO_DIR / "scripts" / "restore.sh", scriptsDir / "restore.sh")
        shutil.copy2(REPO_DIR / "scripts" / "lib.sh", scriptsDir / "lib.sh")
        (fixtureDir / ".env").write_text(
            "\n".join(
                (
                    "MC_STORAGE_ROOT=./storage",
                    "MC_SERVER_DIR=./storage/live",
                    "MC_BACKUP_DIR=./storage/backups",
                    "MC_REQUIRE_STORAGE_MOUNT=true",
                    "",
                )
            ),
            encoding="utf-8",
            newline="\n",
        )
        _writeExecutable(fakeBinDir / "mountpoint", "#!/usr/bin/env bash\nexit 0\n")
        _writeExecutable(fakeBinDir / "systemctl", "#!/usr/bin/env bash\nexit 1\n")
        _writeExecutable(
            fakeBinDir / "tar",
            """#!/usr/bin/env bash
printf "%s\\n" "$1" >> ./tar.log
if [ "$1" = "-tzf" ]; then
  exit 0
fi
mkdir -p ./storage/live/world
printf "partial\\n" > ./storage/live/world/partial.marker
exit 42
""",
        )

        result = subprocess.run(
            [
                bashExecutable,
                "-c",
                'PATH="$PWD/fake-bin:$PATH" scripts/restore.sh '
                'storage/backups/world_test.tar.gz',
            ],
            cwd=fixtureDir,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 42
        assert (worldDir / "original.marker").read_text(encoding="utf-8") == "original\n"
        assert not (worldDir / "partial.marker").exists()
        assert not list(worldDir.parent.glob("world.bak_*"))
        assert (fixtureDir / "tar.log").read_text(encoding="utf-8").splitlines() == [
            "-tzf",
            "-xzf",
        ]
        assert "rolling back previous worlds" in result.stderr
