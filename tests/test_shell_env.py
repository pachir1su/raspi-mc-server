"""Regression tests for shell-compatible placeholder environment settings."""

import os
import subprocess
import tempfile
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]


def testTrackedEnvCanBeSourcedByStrictBash():
    """The shipped placeholder .env must not abort strict shell scripts."""
    bashExecutable = os.environ.get("BASH", "bash")
    result = subprocess.run(
        [
            bashExecutable,
            "-c",
            "set -euo pipefail; set -a; . ./.env; set +a",
        ],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def testSharedLoaderReportsInvalidEnvFileAndLine():
    """The shared loader must identify a broken environment assignment."""
    bashExecutable = os.environ.get("BASH", "bash")
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=REPO_DIR,
        prefix=".invalid-env-",
        suffix=".tmp",
        encoding="utf-8",
        delete=False,
    ) as invalidEnv:
        invalidEnv.write("VALID=value\nBROKEN=value with spaces\n")
        invalidEnvPath = Path(invalidEnv.name)

    try:
        result = subprocess.run(
            [
                bashExecutable,
                "-c",
                '. scripts/lib.sh; load_env_file "$1"',
                "_",
                invalidEnvPath.name,
            ],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        invalidEnvPath.unlink(missing_ok=True)

    assert result.returncode != 0
    assert invalidEnvPath.name in result.stderr
    assert ": line 2:" in result.stderr
    assert "Failed to load environment file" in result.stderr
