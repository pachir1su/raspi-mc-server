"""Network-free tests for the Paper Fill v3 installer."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
API_ROOT = "https://fill.papermc.io/v3/projects/paper"


def _writeExecutable(path: Path, content: str) -> None:
    """Create one executable command used by the isolated shell fixture."""
    path.write_text(content, encoding="utf-8", newline="\n")
    path.chmod(0o755)


def _build(buildId: int, channel: str, url: str, content: bytes) -> dict:
    """Return a minimal Fill v3 build object."""
    return {
        "id": buildId,
        "channel": channel,
        "downloads": {
            "server:default": {
                "name": url.rsplit("/", 1)[-1],
                "checksums": {"sha256": hashlib.sha256(content).hexdigest()},
                "url": url,
            }
        },
    }


def _prepareInstallerFixture(fixtureDir: Path, fillData: dict) -> None:
    """Create an isolated installer repository and deterministic fake tools."""
    scriptsDir = fixtureDir / "scripts"
    serverDir = fixtureDir / "server"
    fakeBinDir = fixtureDir / "fake-bin"
    scriptsDir.mkdir()
    serverDir.mkdir()
    fakeBinDir.mkdir()

    shutil.copy2(REPO_DIR / "scripts" / "install_server.sh", scriptsDir)
    shutil.copy2(REPO_DIR / "scripts" / "lib.sh", scriptsDir)
    shutil.copy2(
        REPO_DIR / "server" / "server.properties.template",
        serverDir / "server.properties.template",
    )
    (fixtureDir / ".env").write_text(
        "MC_SERVER_DIR=./server-live\n",
        encoding="utf-8",
        newline="\n",
    )
    (fixtureDir / "fill-data.json").write_text(
        json.dumps(fillData),
        encoding="utf-8",
        newline="\n",
    )

    _writeExecutable(
        fakeBinDir / "curl",
        """#!/usr/bin/env bash
exec "$TEST_PYTHON" "$PWD/fake-curl.py" "$@"
""",
    )
    (fixtureDir / "fake-curl.py").write_text(
        """import json
import os
import sys
from pathlib import Path

arguments = sys.argv[1:]
outputPath = None
url = ""
index = 0
while index < len(arguments):
    argument = arguments[index]
    if argument in {"-H", "-o"}:
        if argument == "-o":
            outputPath = arguments[index + 1]
        index += 2
        continue
    if not argument.startswith("-"):
        url = argument
    index += 1

with Path(os.environ["CURL_LOG"]).open("a", encoding="utf-8") as logFile:
    logFile.write(url + "\\n")
fillData = json.loads(Path(os.environ["FILL_DATA"]).read_text(encoding="utf-8"))
if outputPath is not None:
    content = fillData["downloads"].get(url)
    if content is None:
        raise SystemExit(22)
    Path(outputPath).write_bytes(content.encode("utf-8"))
else:
    response = fillData["responses"].get(url)
    if response is None:
        raise SystemExit(22)
    print(json.dumps(response))
""",
        encoding="utf-8",
        newline="\n",
    )

    _writeExecutable(
        fakeBinDir / "jq",
        """#!/usr/bin/env bash
exec "$TEST_PYTHON" "$PWD/fake-jq.py" "$@"
""",
    )
    (fixtureDir / "fake-jq.py").write_text(
        """import json
import sys

sys.stdout.reconfigure(newline="\\n")
arguments = sys.argv[1:]
filterExpression = arguments[-1]
exitOnFalse = any("e" in argument for argument in arguments[:-1] if argument.startswith("-"))
data = json.load(sys.stdin)
result = None

if filterExpression == ".versions | to_entries | map(.value) | add | .[]":
    for versions in data["versions"].values():
        for version in versions:
            print(version)
    raise SystemExit(0)
if 'select(.channel == "STABLE")' in filterExpression:
    stableBuilds = [build for build in data if build.get("channel") == "STABLE"]
    result = max(stableBuilds, key=lambda build: build["id"]) if stableBuilds else None
elif filterExpression == ".id":
    result = data.get("id")
elif filterExpression == '.downloads["server:default"].name':
    result = data.get("downloads", {}).get("server:default", {}).get("name")
elif filterExpression == '.downloads["server:default"].url':
    result = data.get("downloads", {}).get("server:default", {}).get("url")
elif filterExpression == '.downloads["server:default"].checksums.sha256':
    result = data.get("downloads", {}).get("server:default", {}).get("checksums", {}).get("sha256")
elif filterExpression == ".version.java.version.minimum":
    result = data.get("version", {}).get("java", {}).get("version", {}).get("minimum")
else:
    raise SystemExit(3)

if result is None:
    raise SystemExit(1 if exitOnFalse else 0)
if isinstance(result, (dict, list)):
    print(json.dumps(result, separators=(",", ":")))
else:
    print(result)
""",
        encoding="utf-8",
        newline="\n",
    )
    _writeExecutable(
        fakeBinDir / "java",
        '#!/usr/bin/env bash\necho \'openjdk version "25.0.1"\' >&2\n',
    )


def _runInstaller(
    fixtureDir: Path, mcVersion: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the isolated installer with fake network, jq, and Java commands."""
    environment = os.environ.copy()
    environment.update(
        {
            "TEST_PYTHON": sys.executable,
            "FILL_DATA": str(fixtureDir / "fill-data.json"),
            "CURL_LOG": str(fixtureDir / "curl.log"),
        }
    )
    if mcVersion is not None:
        environment["MC_VERSION"] = mcVersion
    else:
        environment.pop("MC_VERSION", None)
    bashExecutable = os.environ.get("BASH", "bash")
    return subprocess.run(
        [bashExecutable, "-c", 'PATH="$PWD/fake-bin:$PATH" scripts/install_server.sh'],
        cwd=fixtureDir,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _metadata(minimumJava: int = 25) -> dict:
    """Return the Fill v3 Java requirement shape used by the installer."""
    return {"version": {"java": {"version": {"minimum": minimumJava}}}}


def testAutomaticSelectionUsesNewestVersionWithStableBuild():
    """Auto selection must skip a newer version that only has ALPHA builds."""
    stableJar = b"stable-26.1.2"
    stableUrl = "https://fill-data.papermc.io/stable-26.1.2.jar"
    fillData = {
        "responses": {
            API_ROOT: {"versions": {"26.2": ["26.2"], "26.1": ["26.1.2", "26.1.1"]}},
            f"{API_ROOT}/versions/26.2/builds": [
                _build(10, "ALPHA", "https://fill-data.papermc.io/alpha-26.2.jar", b"alpha")
            ],
            f"{API_ROOT}/versions/26.1.2/builds": [_build(9, "STABLE", stableUrl, stableJar)],
            f"{API_ROOT}/versions/26.1.2": _metadata(),
        },
        "downloads": {stableUrl: stableJar.decode()},
    }
    with tempfile.TemporaryDirectory(dir=REPO_DIR) as temporaryDir:
        fixtureDir = Path(temporaryDir)
        _prepareInstallerFixture(fixtureDir, fillData)
        result = _runInstaller(fixtureDir)

        assert result.returncode == 0, result.stderr
        assert "mc version : 26.1.2" in result.stdout
        assert (fixtureDir / "server-live" / "paper.jar").read_bytes() == stableJar


def testExperimentalBuildIsNeverSelectedOverStableBuild():
    """A higher-id experimental build must not replace a lower-id STABLE build."""
    stableJar = b"stable-build"
    stableUrl = "https://fill-data.papermc.io/stable.jar"
    alphaUrl = "https://fill-data.papermc.io/alpha.jar"
    fillData = {
        "responses": {
            f"{API_ROOT}/versions/26.1.2/builds": [
                _build(12, "STABLE", stableUrl, stableJar),
                _build(99, "ALPHA", alphaUrl, b"alpha-build"),
            ],
            f"{API_ROOT}/versions/26.1.2": _metadata(),
        },
        "downloads": {stableUrl: stableJar.decode(), alphaUrl: "alpha-build"},
    }
    with tempfile.TemporaryDirectory(dir=REPO_DIR) as temporaryDir:
        fixtureDir = Path(temporaryDir)
        _prepareInstallerFixture(fixtureDir, fillData)
        result = _runInstaller(fixtureDir, "26.1.2")
        curlLog = (fixtureDir / "curl.log").read_text(encoding="utf-8")

        assert result.returncode == 0, result.stderr
        assert stableUrl in curlLog
        assert alphaUrl not in curlLog


def testChecksumMismatchPreservesExistingJar():
    """A failed SHA-256 check must leave the current paper.jar untouched."""
    downloadUrl = "https://fill-data.papermc.io/corrupt.jar"
    build = _build(3, "STABLE", downloadUrl, b"expected-content")
    fillData = {
        "responses": {
            f"{API_ROOT}/versions/26.1.2/builds": [build],
            f"{API_ROOT}/versions/26.1.2": _metadata(),
        },
        "downloads": {downloadUrl: "corrupt-content"},
    }
    with tempfile.TemporaryDirectory(dir=REPO_DIR) as temporaryDir:
        fixtureDir = Path(temporaryDir)
        _prepareInstallerFixture(fixtureDir, fillData)
        liveDir = fixtureDir / "server-live"
        liveDir.mkdir()
        (liveDir / "paper.jar").write_bytes(b"existing-jar")
        result = _runInstaller(fixtureDir, "26.1.2")

        assert result.returncode != 0
        assert "SHA-256 mismatch" in result.stderr
        assert (liveDir / "paper.jar").read_bytes() == b"existing-jar"


def testSpecifiedVersionUsesThatStableBuild():
    """MC_VERSION must bypass auto selection and download that version."""
    selectedJar = b"selected-26.1.1"
    selectedUrl = "https://fill-data.papermc.io/selected-26.1.1.jar"
    fillData = {
        "responses": {
            f"{API_ROOT}/versions/26.1.1/builds": [
                _build(7, "STABLE", selectedUrl, selectedJar)
            ],
            f"{API_ROOT}/versions/26.1.1": _metadata(),
        },
        "downloads": {selectedUrl: selectedJar.decode()},
    }
    with tempfile.TemporaryDirectory(dir=REPO_DIR) as temporaryDir:
        fixtureDir = Path(temporaryDir)
        _prepareInstallerFixture(fixtureDir, fillData)
        result = _runInstaller(fixtureDir, "26.1.1")
        curlLog = (fixtureDir / "curl.log").read_text(encoding="utf-8")

        assert result.returncode == 0, result.stderr
        assert f"{API_ROOT}/versions/26.1.1/builds" in curlLog
        assert f"{API_ROOT}\n" not in curlLog
        assert (fixtureDir / "server-live" / "paper.jar").read_bytes() == selectedJar
