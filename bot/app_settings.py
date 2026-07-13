"""First-run application settings stored outside environment variables."""

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from typing import Callable


@dataclass(frozen=True)
class AppSettings:
    """Operator choices that are safe to persist as ordinary JSON."""

    language: str = "ko"
    serverMode: str = "java"
    bedrockPort: int = 19132
    bedrockUsernamePrefix: str = "."
    setupVersion: int = 1

    def validate(self):
        """Reject unsupported choices and unsafe network or name values."""
        if self.language not in {"ko", "en"}:
            raise ValueError("language must be ko or en")
        if self.serverMode not in {"java", "java_bedrock"}:
            raise ValueError("serverMode must be java or java_bedrock")
        if not 1 <= self.bedrockPort <= 65535:
            raise ValueError("bedrockPort must be between 1 and 65535")
        if self.bedrockUsernamePrefix != ".":
            raise ValueError("bedrockUsernamePrefix must be .")
        if self.setupVersion != 1:
            raise ValueError("unsupported setupVersion")


class AppSettingsStore:
    """Read and atomically replace the first-run settings file."""

    def __init__(self, stateDir: str):
        self.stateDir = os.path.abspath(stateDir)
        self.path = os.path.join(self.stateDir, "app-settings.json")

    def exists(self) -> bool:
        """Return whether first-run setup has already completed."""
        return os.path.isfile(self.path)

    def load(self) -> AppSettings:
        """Load validated settings; setup must create the file first."""
        try:
            with open(self.path, "r", encoding="utf-8") as settingsFile:
                raw = json.load(settingsFile)
            settings = AppSettings(**raw)
            settings.validate()
            return settings
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Invalid app settings: {error}") from error

    def save(self, settings: AppSettings):
        """Persist validated settings without leaving partial JSON behind."""
        settings.validate()
        os.makedirs(self.stateDir, exist_ok=True)
        descriptor, temporaryPath = tempfile.mkstemp(
            prefix="app-settings-", suffix=".json", dir=self.stateDir
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as settingsFile:
                json.dump(asdict(settings), settingsFile, indent=2)
                settingsFile.write("\n")
                settingsFile.flush()
                os.fsync(settingsFile.fileno())
            os.replace(temporaryPath, self.path)
        except Exception:
            try:
                os.unlink(temporaryPath)
            except OSError:
                pass
            raise


def _choose(
    prompt: str,
    options: dict[str, str],
    inputFn: Callable[[str], str],
    outputFn: Callable[[str], None],
) -> str:
    """Ask until the operator selects one of the displayed menu numbers."""
    while True:
        selected = inputFn(prompt).strip()
        if selected in options:
            return options[selected]
        outputFn("Please choose a listed number. / 표시된 번호를 선택하세요.")


def runFirstSetupMenu(
    inputFn: Callable[[str], str] = input,
    outputFn: Callable[[str], None] = print,
) -> AppSettings:
    """Collect language and crossplay choices in a bilingual terminal menu."""
    outputFn("=== raspi-mc-server first setup / 최초 설정 ===")
    outputFn("1. 한국어")
    outputFn("2. English")
    language = _choose("Select / 선택 [1-2]: ", {"1": "ko", "2": "en"}, inputFn, outputFn)

    if language == "ko":
        outputFn("\n서버 접속 방식을 선택하세요.")
        outputFn("1. Java만")
        outputFn("2. Java + 모바일/Windows 베드락 (권장)")
        modePrompt = "선택 [1-2]: "
        portPrompt = "베드락 UDP 포트 [19132]: "
    else:
        outputFn("\nChoose how players connect.")
        outputFn("1. Java only")
        outputFn("2. Java + mobile/Windows Bedrock (recommended)")
        modePrompt = "Select [1-2]: "
        portPrompt = "Bedrock UDP port [19132]: "

    serverMode = _choose(
        modePrompt, {"1": "java", "2": "java_bedrock"}, inputFn, outputFn
    )
    bedrockPort = 19132
    if serverMode == "java_bedrock":
        while True:
            rawPort = inputFn(portPrompt).strip()
            try:
                bedrockPort = int(rawPort or "19132")
                if 1 <= bedrockPort <= 65535:
                    break
            except ValueError:
                pass
            outputFn("Enter a port from 1 to 65535. / 1~65535 포트를 입력하세요.")

    settings = AppSettings(
        language=language,
        serverMode=serverMode,
        bedrockPort=bedrockPort,
    )
    settings.validate()
    return settings


def ensureFirstRunSetup(
    stateDir: str,
    force: bool = False,
    interactive: bool = True,
    inputFn: Callable[[str], str] = input,
    outputFn: Callable[[str], None] = print,
) -> AppSettings:
    """Load existing settings or run the menu before starting services."""
    store = AppSettingsStore(stateDir)
    if store.exists() and not force:
        return store.load()
    if not interactive:
        raise SystemExit(
            "First setup is required. Run `.venv/bin/python -m bot.main` "
            "once in a terminal, then start the service again."
        )
    settings = runFirstSetupMenu(inputFn=inputFn, outputFn=outputFn)
    store.save(settings)
    return settings
