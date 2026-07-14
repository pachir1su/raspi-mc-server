"""Regression tests for shell-compatible placeholder environment settings."""

import os
import subprocess
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
