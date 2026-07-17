"""Offline checks for the new friend self-service buttons (TP/status/time)."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

import discord

from bot.control_panel import BackButton
from bot.friend_panel import (
    DiaryPanelView,
    FriendTeleportView,
    MyToolsView,
    PlacePanelView,
    WikiPanelView,
)


class _Link:
    def __init__(self, linkId):
        self.linkId = linkId
        self.edition = "java"
        self.minecraftName = "Steve"


class FriendToolsUxTests(unittest.TestCase):
    def _labels(self, view):
        return {
            item.label
            for item in view.children
            if isinstance(item, discord.ui.Button)
        }

    def testMyToolsExposesNewSelfServiceButtons(self):
        view = MyToolsView(controller=None, ownerId=1, links=[_Link("a")])
        labels = self._labels(view)
        for label in ("플레이어에게 이동", "내 상태", "서버 시간", "선택 계정 스폰 귀환"):
            self.assertIn(label, labels)

    def testMyToolsStaysWithinComponentLimits(self):
        view = MyToolsView(controller=None, ownerId=1, links=[_Link("a")])
        self.assertLessEqual(len(view.children), 25)
        perRow: dict[int, int] = {}
        for item in view.children:
            row = item._rendered_row if item._rendered_row is not None else item.row
            if row is not None:
                perRow[row] = perRow.get(row, 0) + 1
        for row, count in perRow.items():
            self.assertLessEqual(count, 5, f"row {row} overloaded")

    def testTeleportViewListsOnlineTargets(self):
        view = FriendTeleportView(None, 1, "a", ["Alex", "Notch"])
        select = next(
            item for item in view.children if isinstance(item, discord.ui.Select)
        )
        self.assertEqual(["Alex", "Notch"], [option.value for option in select.options])

    def testSubScreensCarryBackToTools(self):
        """좌표북·일지·위키·TP 화면에서 '↩️ 내 도구'로 되돌아갈 수 있다."""
        for view in (
            PlacePanelView(None, 1, [], "a"),
            DiaryPanelView(None, 1, []),
            WikiPanelView(None, 1),
            FriendTeleportView(None, 1, "a", ["Alex"]),
        ):
            with self.subTest(view=type(view).__name__):
                backs = [i for i in view.children if isinstance(i, BackButton)]
                self.assertEqual(1, len(backs))
                self.assertEqual("↩️ 내 도구", backs[0].label)

    def testSubScreenOpenersEditInPlace(self):
        """하위 화면은 새 메시지를 쌓지 않고 /tools 메시지를 교체한다."""
        controller = MagicMock(name="controller")
        controller.panelPlaces = AsyncMock(return_value=[])
        controller.panelDiaryEntries = AsyncMock(return_value=[])
        controller._requireFriendAccess = AsyncMock(return_value=True)
        controller.panelTeleportTargets = AsyncMock(return_value=["Alex"])
        view = MyToolsView(controller, 1, [_Link("a")])
        for opener in (view.places, view.diary, view.wiki, view.teleport):
            with self.subTest(button=opener.label):
                interaction = MagicMock(name="interaction")
                interaction.response.is_done.return_value = False
                interaction.response.edit_message = AsyncMock()
                interaction.response.send_message = AsyncMock()
                asyncio.run(opener.callback(interaction))
                interaction.response.edit_message.assert_awaited_once()
                interaction.response.send_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
