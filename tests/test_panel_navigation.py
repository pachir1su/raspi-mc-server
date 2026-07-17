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
    interaction.original_response = AsyncMock(name="original_response")
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
    controller.panelPlayerEmbed = AsyncMock(return_value=embed)
    controller.panelLogEmbed = AsyncMock(return_value=embed)
    controller.panelSharedPlaces = AsyncMock(return_value=[])
    controller.panelKick = AsyncMock()
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

    # ── 접속자 관리 하위 화면 네비게이션 ──────────────────────────

    def _playerSubViews(self):
        return [
            cp.EffectPanelView(self.controller, self.ownerId, "Steve"),
            cp.EnchantPanelView(self.controller, self.ownerId, "Steve"),
            cp.GamemodePanelView(self.controller, self.ownerId, "Steve"),
            cp.TeleportPanelView(self.controller, self.ownerId, "Steve", ["Alex"], []),
            cp.InvincibilityPanelView(self.controller, self.ownerId, "Steve"),
            cp.ConfirmKickView(self.controller, self.ownerId, "Steve"),
            cp.PlayerSubScreenView(self.controller, self.ownerId, "Steve"),
        ]

    def testPlayerSubScreensCarryBackAndHome(self):
        """Every player sub-screen returns to the player list or the dashboard."""
        for view in self._playerSubViews():
            with self.subTest(view=type(view).__name__):
                backs = [i for i in view.children if isinstance(i, cp.BackButton)]
                homes = [i for i in view.children if isinstance(i, cp.HomeButton)]
                self.assertEqual(1, len(backs))
                self.assertEqual(1, len(homes))
                self.assertEqual("↩️ 접속자 관리", backs[0].label)

    def testPlayerSubScreensStayWithinComponentLimits(self):
        for view in self._playerSubViews() + [
            cp.SpawnSetView(self.controller, self.ownerId, ["Steve"]),
        ]:
            with self.subTest(view=type(view).__name__):
                self.assertLessEqual(len(view.children), 25)
                perRow: dict[int, int] = {}
                for item in view.children:
                    row = item._rendered_row if item._rendered_row is not None else item.row
                    if row is not None:
                        perRow[row] = perRow.get(row, 0) + 1
                for row, count in perRow.items():
                    self.assertLessEqual(count, 5, f"row {row} overloaded")

    def testPlayerInfoAndSubPanelsEditInPlace(self):
        """Lookups and action pickers replace the panel message, never stack."""
        panel = cp.PlayerPanelView(self.controller, self.ownerId, ["Steve", "Alex"])
        for opener in (
            panel.inventory, panel.position, panel.stats, panel.effects,
            panel.records, panel.applyEffect, panel.enchant, panel.gamemode,
            panel.teleport, panel.invincible, panel.kick,
        ):
            with self.subTest(button=opener.label):
                interaction = _fakeInteraction()
                self._run(opener.callback(interaction))
                interaction.response.edit_message.assert_awaited_once()
                interaction.response.send_message.assert_not_called()

    def testBackButtonReturnsToPlayerListKeepingSelection(self):
        """'↩️ 접속자 관리' re-renders the list with the player still selected."""
        view = cp.EffectPanelView(self.controller, self.ownerId, "Steve")
        back = next(i for i in view.children if isinstance(i, cp.BackButton))
        interaction = _fakeInteraction()
        self._run(back.callback(interaction))
        interaction.response.edit_message.assert_awaited_once()
        sentView = interaction.response.edit_message.await_args.kwargs["view"]
        self.assertIsInstance(sentView, cp.PlayerPanelView)
        self.assertEqual("Steve", sentView.selectedPlayer)

    def testLogScreenEditsInPlaceWithBack(self):
        panel = cp.LogPanelView(self.controller, self.ownerId)
        interaction = _fakeInteraction()
        self._run(panel.botLog.callback(interaction))
        interaction.response.edit_message.assert_awaited_once()
        interaction.response.send_message.assert_not_called()
        sentView = interaction.response.edit_message.await_args.kwargs["view"]
        self.assertTrue(
            any(isinstance(i, cp.BackButton) for i in sentView.children)
        )

    def testKickCancelReturnsToPlayerList(self):
        view = cp.ConfirmKickView(self.controller, self.ownerId, "Steve")
        interaction = _fakeInteraction()
        self._run(view.cancel.callback(interaction))
        sentView = interaction.response.edit_message.await_args.kwargs["view"]
        self.assertIsInstance(sentView, cp.PlayerPanelView)


class TimeoutTests(unittest.TestCase):
    """만료된 패널은 버튼을 비활성화하고 다시 여는 방법을 안내해야 한다."""

    def _run(self, coro):
        return asyncio.run(coro)

    def testTimeoutDisablesButtonsAndExplains(self):
        controller = _fakeController()
        view = cp.AdminDashboardView(controller, 42)
        view.message = MagicMock(name="message")
        view.message.edit = AsyncMock(name="edit")
        self._run(view.on_timeout())
        self.assertTrue(all(item.disabled for item in view.children))
        view.message.edit.assert_awaited_once()
        self.assertIn("만료", view.message.edit.await_args.kwargs["content"])

    def testTimeoutWithoutTrackedMessageIsSilent(self):
        view = cp.AdminDashboardView(_fakeController(), 42)
        self._run(view.on_timeout())  # must not raise
        self.assertTrue(all(item.disabled for item in view.children))

    def testReplaceScreenBindsMessageForTimeout(self):
        controller = _fakeController()
        view = cp.InfoScreenView(controller, 42)
        interaction = _fakeInteraction()
        self._run(cp.replaceScreen(interaction, content="x", embed=None, view=view))
        self.assertIs(view.message, interaction.message)

    def testSendScreenBindsMessageForTimeout(self):
        controller = _fakeController()
        view = cp.InfoScreenView(controller, 42)
        interaction = _fakeInteraction()
        sent = MagicMock(name="sentMessage")
        interaction.original_response.return_value = sent
        self._run(cp.sendScreen(interaction, content="x", view=view))
        self.assertIs(view.message, sent)


if __name__ == "__main__":
    unittest.main()
