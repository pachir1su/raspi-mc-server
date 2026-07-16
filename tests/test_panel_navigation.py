"""Offline checks for in-message panel navigation (#58).

These construct the real views and drive their button callbacks with a fake
Discord interaction, so the single-message navigation and back-to-home paths
are exercised without a live gateway.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

import discord

from bot import control_panel as cp


def _fakeInteraction():
    """A Discord interaction whose response records edit/send calls."""
    interaction = MagicMock(name="interaction")
    interaction.response.is_done.return_value = False
    interaction.response.edit_message = AsyncMock(name="edit_message")
    interaction.response.send_message = AsyncMock(name="send_message")
    interaction.response.defer = AsyncMock(name="defer")
    interaction.edit_original_response = AsyncMock(name="edit_original_response")
    interaction.followup.send = AsyncMock(name="followup_send")
    return interaction


def _fakeController():
    """A controller stub returning cheap embeds for the panel builders."""
    controller = MagicMock(name="controller")
    embed = discord.Embed(title="stub")
    controller.panelOverviewEmbed = AsyncMock(return_value=embed)
    controller.panelHealthEmbed = AsyncMock(return_value=embed)
    controller.panelHelpEmbed = MagicMock(return_value=embed)
    controller.panelMetricsEmbed = AsyncMock(return_value=embed)
    controller.panelStorageEmbed = AsyncMock(return_value=embed)
    controller.panelBackupEmbed = AsyncMock(return_value=embed)
    controller.panelBackups = AsyncMock(return_value=[])
    controller.panelBackupSettings = AsyncMock(return_value=MagicMock(enabled=True))
    controller.panelWorlds = AsyncMock(return_value=[])
    controller.panelOnlinePlayers = AsyncMock(return_value=["Steve"])
    controller.probeSupportedGamerules = AsyncMock(return_value={})
    controller._collectPerformanceWarnings = AsyncMock(
        return_value=([], discord.Embed(title="tuning"))
    )
    return controller


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.controller = _fakeController()
        self.ownerId = 42

    def _run(self, coro):
        return asyncio.run(coro)

    def _findButton(self, view, label):
        for item in view.children:
            if isinstance(item, discord.ui.Button) and item.label == label:
                return item
        raise AssertionError(f"button not found: {label}")

    def testEveryViewStaysWithinComponentLimits(self):
        """Discord caps a view at 25 components and 5 per row."""
        views = [
            cp.AdminDashboardView(self.controller, self.ownerId),
            cp.MoreToolsView(self.controller, self.ownerId),
            cp.WorldCommandsView(self.controller, self.ownerId, {}),
            cp.ServerActionsView(self.controller, self.ownerId),
            cp.PlayerPanelView(self.controller, self.ownerId, ["Steve", "Alex"]),
            cp.BackupPanelView(self.controller, self.ownerId, [], MagicMock(enabled=True)),
            cp.WorldPanelView(self.controller, self.ownerId, []),
            cp.UpdatePanelView(self.controller, self.ownerId),
            cp.AdvancedPanelView(self.controller, self.ownerId),
            cp.LogPanelView(self.controller, self.ownerId),
        ]
        for view in views:
            with self.subTest(view=type(view).__name__):
                self.assertLessEqual(len(view.children), 25)
                perRow: dict[int, int] = {}
                for item in view.children:
                    row = item._rendered_row if item._rendered_row is not None else item.row
                    if row is not None:
                        perRow[row] = perRow.get(row, 0) + 1
                for row, count in perRow.items():
                    self.assertLessEqual(count, 5, f"row {row} overloaded")

    def testSubPanelsCarryAHomeButton(self):
        """Navigation panels can always return to the dashboard in one tap."""
        for view in (
            cp.MoreToolsView(self.controller, self.ownerId),
            cp.ServerActionsView(self.controller, self.ownerId),
            cp.PlayerPanelView(self.controller, self.ownerId, ["Steve"]),
            cp.BackupPanelView(self.controller, self.ownerId, [], MagicMock(enabled=True)),
            cp.WorldPanelView(self.controller, self.ownerId, []),
            cp.UpdatePanelView(self.controller, self.ownerId),
            cp.AdvancedPanelView(self.controller, self.ownerId),
            cp.LogPanelView(self.controller, self.ownerId),
            cp.WorldCommandsView(self.controller, self.ownerId, {}),
        ):
            with self.subTest(view=type(view).__name__):
                home = [
                    item for item in view.children
                    if isinstance(item, cp.HomeButton)
                ]
                self.assertEqual(1, len(home))

    def testDashboardOpenersEditInPlace(self):
        """Opening a sub-panel edits the current message, not a new one."""
        view = cp.AdminDashboardView(self.controller, self.ownerId)
        interaction = _fakeInteraction()
        self._run(view.players.callback(interaction))
        interaction.response.edit_message.assert_awaited_once()
        interaction.response.send_message.assert_not_called()

    def testQuickCommandsEditsInPlaceWithoutDefer(self):
        view = cp.AdminDashboardView(self.controller, self.ownerId)
        interaction = _fakeInteraction()
        self._run(view.quickCommands.callback(interaction))
        interaction.response.edit_message.assert_awaited_once()
        self.controller.probeSupportedGamerules.assert_awaited_once()

    def testHomeButtonReturnsToDashboard(self):
        """The home button re-renders the dashboard on the same message."""
        panel = cp.ServerActionsView(self.controller, self.ownerId)
        home = self._findButton(panel, "🏠 홈")
        interaction = _fakeInteraction()
        self._run(home.callback(interaction))
        interaction.response.edit_message.assert_awaited_once()
        self.controller.panelOverviewEmbed.assert_awaited_once()

    def testSlowEmbedUsesLoadingThenResult(self):
        """Performance detail shows a loading frame then edits to the result."""
        view = cp.MoreToolsView(self.controller, self.ownerId)
        interaction = _fakeInteraction()
        self._run(view.performance.callback(interaction))
        interaction.response.edit_message.assert_awaited_once()  # loading frame
        interaction.edit_original_response.assert_awaited_once()  # result


if __name__ == "__main__":
    unittest.main()
