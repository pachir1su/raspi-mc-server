"""Tests for durable per-Discord-account cooldowns."""

import tempfile
import unittest
from pathlib import Path

from bot.cooldowns import CooldownStore, formatRemaining


class FakeClock:
    def __init__(self):
        self.value = 1000.0

    def __call__(self):
        return self.value


class CooldownStoreTests(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.clock = FakeClock()

    def _store(self):
        return CooldownStore(self._dir.name, now=self.clock)

    def testTryStartAllowsThenBlocks(self):
        store = self._store()
        self.assertEqual(0.0, store.tryStart(42, "tp", 1800))
        remaining = store.tryStart(42, "tp", 1800)
        self.assertAlmostEqual(1800.0, remaining, delta=1)

    def testCooldownExpiresAfterTime(self):
        store = self._store()
        store.tryStart(42, "tp", 300)
        self.clock.value += 299
        self.assertGreater(store.remaining(42, "tp"), 0)
        self.clock.value += 2
        self.assertEqual(0.0, store.remaining(42, "tp"))
        self.assertEqual(0.0, store.tryStart(42, "tp", 300))

    def testSharedAcrossKeysButNotActions(self):
        store = self._store()
        store.tryStart(42, "tp", 300)
        # 다른 액션(rescue)은 독립적인 타이머입니다.
        self.assertEqual(0.0, store.tryStart(42, "rescue", 300))
        # 같은 계정의 같은 액션은 막힙니다.
        self.assertGreater(store.tryStart(42, "tp", 300), 0)

    def testPersistsAcrossRestart(self):
        store = self._store()
        store.tryStart(7, "tp", 600)
        # 새 인스턴스가 같은 파일을 읽어 타이머를 이어받습니다.
        reopened = self._store()
        self.assertAlmostEqual(600.0, reopened.remaining(7, "tp"), delta=1)

    def testZeroSecondsDisablesCooldown(self):
        store = self._store()
        self.assertEqual(0.0, store.tryStart(42, "tp", 0))
        self.assertEqual(0.0, store.remaining(42, "tp"))

    def testCorruptFileIsIgnored(self):
        Path(self._dir.name, "cooldowns.json").write_text("not json", encoding="utf-8")
        store = self._store()  # must not raise
        self.assertEqual(0.0, store.remaining(1, "tp"))

    def testFormatRemaining(self):
        self.assertEqual("30초", formatRemaining(30))
        self.assertEqual("1분", formatRemaining(60))
        self.assertEqual("12분 30초", formatRemaining(750))


if __name__ == "__main__":
    unittest.main()
