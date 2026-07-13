"""Install and configure Geyser/Floodgate for low-maintenance crossplay."""

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from typing import Callable

from bot.app_settings import AppSettings


DOWNLOAD_ROOT = "https://download.geysermc.org/v2/projects"


@dataclass(frozen=True)
class PluginSpec:
    """Official download API project and stable local jar name."""

    project: str
    localName: str
    configParts: tuple[str, ...]


PLUGIN_SPECS = (
    PluginSpec("geyser", "Geyser-Spigot.jar", ("Geyser-Spigot", "config.yml")),
    PluginSpec("floodgate", "floodgate-spigot.jar", ("floodgate", "config.yml")),
)


def _replaceYamlValue(text: str, key: str, value: str) -> tuple[str, bool]:
    """Replace the first scalar YAML key while preserving indentation."""
    pattern = re.compile(rf"^(?P<indent>\s*){re.escape(key)}\s*:\s*.*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        raise RuntimeError(f"Could not find `{key}` in generated plugin config")
    replacement = f"{match.group('indent')}{key}: {value}"
    updated = text[: match.start()] + replacement + text[match.end() :]
    return updated, updated != text


def _replaceYamlSectionValue(
    text: str, section: str, key: str, value: str
) -> tuple[str, bool]:
    """Replace a direct child key only inside the named YAML section."""
    lines = text.splitlines(keepends=True)
    sectionPattern = re.compile(rf"^(?P<indent>\s*){re.escape(section)}\s*:\s*(?:#.*)?$")
    keyPattern = re.compile(rf"^(?P<indent>\s*){re.escape(key)}\s*:\s*.*$")
    sectionIndent = None
    for index, line in enumerate(lines):
        sectionMatch = sectionPattern.match(line.rstrip("\r\n"))
        if sectionMatch:
            sectionIndent = len(sectionMatch.group("indent"))
            continue
        if sectionIndent is None:
            continue
        stripped = line.strip()
        lineIndent = len(line) - len(line.lstrip())
        if stripped and not stripped.startswith("#") and lineIndent <= sectionIndent:
            break
        keyMatch = keyPattern.match(line.rstrip("\r\n"))
        if keyMatch and len(keyMatch.group("indent")) > sectionIndent:
            newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            replacement = f"{keyMatch.group('indent')}{key}: {value}{newline}"
            changed = replacement != line
            lines[index] = replacement
            return "".join(lines), changed
    raise RuntimeError(f"Could not find `{section}.{key}` in generated plugin config")


def patchGeyserConfig(path: str, bedrockPort: int) -> bool:
    """Set the Bedrock UDP listener and Floodgate authentication."""
    try:
        with open(path, "r", encoding="utf-8") as configFile:
            text = configFile.read()
        updated, portChanged = _replaceYamlSectionValue(
            text, "bedrock", "port", str(bedrockPort)
        )
        updated, authChanged = _replaceYamlValue(updated, "auth-type", "floodgate")
        if portChanged or authChanged:
            _atomicWriteText(path, updated)
        return portChanged or authChanged
    except OSError as error:
        raise RuntimeError(f"Could not update Geyser config: {error}") from error


def patchFloodgateConfig(path: str, usernamePrefix: str = ".") -> bool:
    """Keep Bedrock identities distinct from Java account names."""
    try:
        with open(path, "r", encoding="utf-8") as configFile:
            text = configFile.read()
        updated, changed = _replaceYamlValue(text, "username-prefix", json.dumps(usernamePrefix))
        if changed:
            _atomicWriteText(path, updated)
        return changed
    except OSError as error:
        raise RuntimeError(f"Could not update Floodgate config: {error}") from error


def _atomicWriteText(path: str, text: str):
    """Replace a text config without exposing a partially written file."""
    directory = os.path.dirname(os.path.abspath(path))
    descriptor, temporaryPath = tempfile.mkstemp(prefix="crossplay-", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as outputFile:
            outputFile.write(text)
            outputFile.flush()
            os.fsync(outputFile.fileno())
        os.replace(temporaryPath, path)
    except Exception:
        try:
            os.unlink(temporaryPath)
        except OSError:
            pass
        raise


class CrossplayManager:
    """Provision crossplay only when selected and not already configured."""

    def __init__(
        self,
        serverDir: str,
        serviceName: str,
        urlOpen: Callable = urllib.request.urlopen,
        commandRunner: Callable = subprocess.run,
        sleepFn: Callable[[float], None] = time.sleep,
    ):
        self.serverDir = os.path.abspath(serverDir)
        self.pluginsDir = os.path.join(self.serverDir, "plugins")
        self.serviceName = serviceName
        self.urlOpen = urlOpen
        self.commandRunner = commandRunner
        self.sleepFn = sleepFn

    def ensure(self, settings: AppSettings) -> bool:
        """Install missing plugins and make generated configs match choices."""
        if settings.serverMode != "java_bedrock":
            return self._disablePlugins()
        os.makedirs(self.pluginsDir, exist_ok=True)
        installed = False
        activated = False
        for plugin in PLUGIN_SPECS:
            jarPath = os.path.join(self.pluginsDir, plugin.localName)
            disabledPath = jarPath + ".disabled"
            if not os.path.isfile(jarPath) and os.path.isfile(disabledPath):
                os.replace(disabledPath, jarPath)
                activated = True
            if not os.path.isfile(jarPath):
                self._downloadPlugin(plugin, jarPath)
                installed = True

        configPaths = [os.path.join(self.pluginsDir, *item.configParts) for item in PLUGIN_SPECS]
        if installed or activated or not all(os.path.isfile(path) for path in configPaths):
            self._restartMinecraft()
            self._waitForConfigs(configPaths)

        changed = patchGeyserConfig(configPaths[0], settings.bedrockPort)
        changed = patchFloodgateConfig(
            configPaths[1], settings.bedrockUsernamePrefix
        ) or changed
        if changed:
            self._restartMinecraft()
        return installed or activated or changed

    def _disablePlugins(self) -> bool:
        """Reversibly disable crossplay jars when Java-only mode is selected."""
        changed = False
        for plugin in PLUGIN_SPECS:
            jarPath = os.path.join(self.pluginsDir, plugin.localName)
            if os.path.isfile(jarPath):
                os.replace(jarPath, jarPath + ".disabled")
                changed = True
        if changed:
            self._restartMinecraft()
        return changed

    def ensureMinecraftRunning(self) -> bool:
        """Start Paper when needed so main.py is the only routine entry point."""
        try:
            status = self.commandRunner(
                ["sudo", "systemctl", "is-active", self.serviceName],
                check=False,
                capture_output=True,
                text=True,
            )
            if status.returncode == 0:
                return False
            self.commandRunner(
                ["sudo", "systemctl", "start", self.serviceName],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(error, "stderr", "") or str(error)
            raise RuntimeError(f"Could not start {self.serviceName}: {detail.strip()}") from error

    def _downloadPlugin(self, plugin: PluginSpec, destination: str):
        """Download a latest official Spigot jar and verify its published hash."""
        metadataUrl = (
            f"{DOWNLOAD_ROOT}/{plugin.project}/versions/latest/builds/latest"
        )
        downloadUrl = f"{metadataUrl}/downloads/spigot"
        try:
            with self.urlOpen(metadataUrl, timeout=30) as response:
                metadata = json.load(response)
            expectedHash = metadata["downloads"]["spigot"]["sha256"].lower()
            with self.urlOpen(downloadUrl, timeout=120) as response:
                payload = response.read()
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Could not download {plugin.project}: {error}") from error
        actualHash = hashlib.sha256(payload).hexdigest()
        if actualHash != expectedHash:
            raise RuntimeError(f"SHA-256 mismatch for {plugin.project} download")

        descriptor, temporaryPath = tempfile.mkstemp(
            prefix=f"{plugin.project}-", suffix=".jar", dir=self.pluginsDir
        )
        try:
            with os.fdopen(descriptor, "wb") as jarFile:
                jarFile.write(payload)
                jarFile.flush()
                os.fsync(jarFile.fileno())
            os.replace(temporaryPath, destination)
        except Exception:
            try:
                os.unlink(temporaryPath)
            except OSError:
                pass
            raise

    def _restartMinecraft(self):
        """Restart Paper through the narrowly allowed systemd operation."""
        try:
            self.commandRunner(
                ["sudo", "systemctl", "restart", self.serviceName],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(error, "stderr", "") or str(error)
            raise RuntimeError(f"Could not restart {self.serviceName}: {detail.strip()}") from error

    def _waitForConfigs(self, configPaths: list[str], timeoutSeconds: int = 90):
        """Wait briefly for Paper to generate both plugin configurations."""
        deadline = time.monotonic() + timeoutSeconds
        while time.monotonic() < deadline:
            if all(os.path.isfile(path) for path in configPaths):
                return
            self.sleepFn(1)
        missing = [path for path in configPaths if not os.path.isfile(path)]
        raise RuntimeError("Paper did not generate crossplay configs: " + ", ".join(missing))
