"""Tests for low-churn Geyser and Floodgate setup."""

import os
import tempfile
import unittest
from types import SimpleNamespace

from bot.app_settings import AppSettings
from bot.crossplay import CrossplayManager, patchFloodgateConfig, patchGeyserConfig


class CrossplayTests(unittest.TestCase):
    """Verify safe config edits and no-op behavior for established servers."""

    def testPatchesGeneratedConfigs(self):
        """The setup selects Floodgate and the chosen Bedrock UDP port."""
        with tempfile.TemporaryDirectory() as serverDir:
            geyserPath = os.path.join(serverDir, "geyser.yml")
            floodgatePath = os.path.join(serverDir, "floodgate.yml")
            with open(geyserPath, "w", encoding="utf-8") as configFile:
                configFile.write(
                    "java:\n  port: 25565\nbedrock:\n  port: 19132\n"
                    "remote:\n  auth-type: online\n"
                )
            with open(floodgatePath, "w", encoding="utf-8") as configFile:
                configFile.write("username-prefix: '*'\n")

            self.assertTrue(patchGeyserConfig(geyserPath, 19133))
            self.assertTrue(patchFloodgateConfig(floodgatePath))
            with open(geyserPath, "r", encoding="utf-8") as configFile:
                geyserText = configFile.read()
            with open(floodgatePath, "r", encoding="utf-8") as configFile:
                floodgateText = configFile.read()

        self.assertIn("port: 19133", geyserText)
        self.assertIn("port: 25565", geyserText)
        self.assertIn("auth-type: floodgate", geyserText)
        self.assertIn('username-prefix: "."', floodgateText)

    def testConfiguredCrossplayDoesNoNetworkOrRestartWork(self):
        """Normal bot launches do not update plugins or restart Paper."""
        with tempfile.TemporaryDirectory() as serverDir:
            pluginsDir = os.path.join(serverDir, "plugins")
            geyserDir = os.path.join(pluginsDir, "Geyser-Spigot")
            floodgateDir = os.path.join(pluginsDir, "floodgate")
            os.makedirs(geyserDir)
            os.makedirs(floodgateDir)
            for jarName in ("Geyser-Spigot.jar", "floodgate-spigot.jar"):
                with open(os.path.join(pluginsDir, jarName), "wb") as jarFile:
                    jarFile.write(b"existing")
            with open(os.path.join(geyserDir, "config.yml"), "w", encoding="utf-8") as configFile:
                configFile.write("bedrock:\n  port: 19132\nremote:\n  auth-type: floodgate\n")
            with open(os.path.join(floodgateDir, "config.yml"), "w", encoding="utf-8") as configFile:
                configFile.write('username-prefix: "."\n')

            manager = CrossplayManager(
                serverDir,
                "minecraft.service",
                urlOpen=lambda *_args, **_kwargs: self.fail("network unexpectedly used"),
                commandRunner=lambda *_args, **_kwargs: self.fail("restart unexpectedly used"),
            )
            changed = manager.ensure(AppSettings(serverMode="java_bedrock"))

        self.assertFalse(changed)

    def testJavaOnlySkipsCrossplayWork(self):
        """A Java-only choice leaves the Paper directory untouched."""
        with tempfile.TemporaryDirectory() as serverDir:
            manager = CrossplayManager(serverDir, "minecraft.service")
            changed = manager.ensure(AppSettings(serverMode="java"))
            self.assertFalse(os.path.exists(os.path.join(serverDir, "plugins")))

        self.assertFalse(changed)

    def testStartsMinecraftOnlyWhenInactive(self):
        """The main launcher starts Paper without restarting a healthy service."""
        commands = []

        def commandRunner(command, **_kwargs):
            commands.append(command)
            return SimpleNamespace(returncode=3 if "is-active" in command else 0)

        manager = CrossplayManager(".", "minecraft.service", commandRunner=commandRunner)
        self.assertTrue(manager.ensureMinecraftRunning())
        self.assertEqual("is-active", commands[0][2])
        self.assertEqual("start", commands[1][2])

    def testJavaModeReversiblyDisablesInstalledPlugins(self):
        """Changing the menu to Java-only stops Bedrock without deleting jars."""
        commands = []
        with tempfile.TemporaryDirectory() as serverDir:
            pluginsDir = os.path.join(serverDir, "plugins")
            os.makedirs(pluginsDir)
            for jarName in ("Geyser-Spigot.jar", "floodgate-spigot.jar"):
                with open(os.path.join(pluginsDir, jarName), "wb") as jarFile:
                    jarFile.write(b"existing")
            manager = CrossplayManager(
                serverDir,
                "minecraft.service",
                commandRunner=lambda command, **_kwargs: commands.append(command),
            )
            changed = manager.ensure(AppSettings(serverMode="java"))

            self.assertTrue(changed)
            self.assertTrue(
                os.path.isfile(os.path.join(pluginsDir, "Geyser-Spigot.jar.disabled"))
            )
        self.assertEqual("restart", commands[0][2])


if __name__ == "__main__":
    unittest.main()
