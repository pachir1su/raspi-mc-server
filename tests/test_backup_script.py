"""Failure-path tests for the shell world backup workflow."""

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


def testBackupFailureRestoresAutoSave():
    """A tar failure after save-off must still issue save-on at shell exit."""
    bashExecutable = os.environ.get("BASH", "bash")
    with tempfile.TemporaryDirectory(dir=REPO_DIR) as temporaryDir:
        fixtureDir = Path(temporaryDir)
        scriptsDir = fixtureDir / "scripts"
        fakeBinDir = fixtureDir / "fake-bin"
        worldDir = fixtureDir / "storage" / "live" / "world"
        scriptsDir.mkdir()
        fakeBinDir.mkdir()
        worldDir.mkdir(parents=True)

        shutil.copy2(REPO_DIR / "scripts" / "backup.sh", scriptsDir / "backup.sh")
        shutil.copy2(REPO_DIR / "scripts" / "lib.sh", scriptsDir / "lib.sh")
        (fixtureDir / ".env").write_text(
            "\n".join(
                (
                    "MC_STORAGE_ROOT=./storage",
                    "MC_SERVER_DIR=./storage/live",
                    "MC_BACKUP_DIR=./storage/backups",
                    "MC_REQUIRE_STORAGE_MOUNT=true",
                    "RCON_PASSWORD=placeholder",
                    "RCON_LOG=./rcon.log",
                    "",
                )
            ),
            encoding="utf-8",
            newline="\n",
        )
        _writeExecutable(fakeBinDir / "mountpoint", "#!/usr/bin/env bash\nexit 0\n")
        _writeExecutable(
            fakeBinDir / "mcrcon",
            '#!/usr/bin/env bash\nprintf "%s\\n" "${@: -1}" >> "$RCON_LOG"\n',
        )
        _writeExecutable(fakeBinDir / "sleep", "#!/usr/bin/env bash\nexit 0\n")
        _writeExecutable(fakeBinDir / "tar", "#!/usr/bin/env bash\nexit 42\n")

        result = subprocess.run(
            [
                bashExecutable,
                "-c",
                'PATH="$PWD/fake-bin:$PATH" scripts/backup.sh',
            ],
            cwd=fixtureDir,
            capture_output=True,
            text=True,
            check=False,
        )

        commands = (fixtureDir / "rcon.log").read_text(encoding="utf-8").splitlines()
        assert result.returncode == 42
        assert "save-off" in commands
        assert commands[-1] == "save-on"
