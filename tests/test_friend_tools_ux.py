"""Offline checks for the new friend self-service buttons (TP/status/time)."""

import unittest

import discord

from bot.friend_panel import FriendTeleportView, MyToolsView


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


if __name__ == "__main__":
    unittest.main()
