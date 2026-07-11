"""Tests for dependency-free Pi metrics parsing."""

import tempfile
import unittest
from pathlib import Path

from bot.system_metrics import (
    formatDuration,
    parseThrottleFlags,
    readSystemMetrics,
    stripMinecraftFormatting,
)


class SystemMetricsTests(unittest.TestCase):
    """Exercise procfs, thermal, throttle, and text presentation helpers."""

    def testReadsFixtureProcfs(self):
        """Linux metrics are converted to bytes and degrees Celsius."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "uptime").write_text("90061.5 0.0\n", encoding="ascii")
            (root / "loadavg").write_text("0.25 0.50 0.75 1/100 1\n", encoding="ascii")
            (root / "meminfo").write_text(
                "MemTotal: 4096000 kB\nMemAvailable: 2048000 kB\n", encoding="ascii"
            )
            thermal = root / "temp"
            thermal.write_text("48750\n", encoding="ascii")
            metrics = readSystemMetrics(root, thermal)
            self.assertEqual(48.75, metrics.temperatureCelsius)
            self.assertEqual(2048000 * 1024, metrics.memoryAvailableBytes)
            self.assertEqual(0.5, metrics.load5)

    def testDecodesThrottleHistory(self):
        """Current and historical firmware bits receive distinct labels."""
        labels = parseThrottleFlags("throttled=0x50005")
        self.assertIn("현재 저전압", labels)
        self.assertIn("현재 스로틀링", labels)
        self.assertIn("과거 저전압", labels)
        self.assertIn("과거 스로틀링", labels)

    def testFormatsOutput(self):
        """Discord text is compact and Minecraft colours are stripped."""
        self.assertEqual("1d 1h 1m", formatDuration(90061))
        self.assertEqual("TPS: 20.0", stripMinecraftFormatting("TPS: §a20.0"))


if __name__ == "__main__":
    unittest.main()
