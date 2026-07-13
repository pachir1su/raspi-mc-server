"""Tests for low-churn Geyser and Floodgate setup."""

import os
import tempfile
import unittest

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
                configFile.write("bedrock:\n  port: 19132\nremote:\n  auth-type: online\n")
            with open(floodgatePath, "w", encoding="utf-8") as configFile:
                configFile.write("username-prefix: '*'\n")

            self.assertTrue(patchGeyserConfig(geyserPath, 19133))
            self.assertTrue(patchFloodgateConfig(floodgatePath))
            with open(geyserPath, "r", encoding="utf-8") as configFile:
                geyserText = configFile.read()
            with open(floodgatePath, "r", encoding="utf-8") as configFile:
                floodgateText = configFile.read()

        self.assertIn("port: 19133", geyserText)
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


if __name__ == "__main__":
    unittest.main()
