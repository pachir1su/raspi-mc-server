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
    interaction.response.send_modal = AsyncMock(name="send_modal")
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

    def testDashboardExposesInGameCommand(self):
        """#79: 인게임 명령어 is reachable in one click from the dashboard."""
        view = cp.AdminDashboardView(self.controller, self.ownerId)
        button = self._findButton(view, "인게임 명령어")
        interaction = _fakeInteraction()
        interaction.response.send_modal = AsyncMock(name="send_modal")
        self._run(button.callback(interaction))
        interaction.response.send_modal.assert_awaited_once()
        modal = interaction.response.send_modal.await_args.args[0]
        self.assertIsInstance(modal, cp.TextActionModal)
        self.assertEqual("mc", modal.action)

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
            panel.teleport, panel.invincible, panel.summonMenu, panel.kick,
        ):
            with self.subTest(button=opener.label):
                interaction = _fakeInteraction()
                self._run(opener.callback(interaction))
                interaction.response.edit_message.assert_awaited_once()
                interaction.response.send_message.assert_not_called()

    def testSummonPanelButtonsDeferAndCallController(self):
        """연출·소환 서브패널의 버튼은 즉시 실행(화면 전환 없음)."""
        self.controller.panelSummonCreeper = AsyncMock()
        self.controller.panelChargedCreeper = AsyncMock()
        self.controller.panelCreeperSound = AsyncMock()
        self.controller.panelLightning = AsyncMock()
        panel = cp.SummonPanelView(self.controller, self.ownerId, "Steve")
        for button, handler in (
            (panel.creeper, self.controller.panelSummonCreeper),
            (panel.chargedCreeper, self.controller.panelChargedCreeper),
            (panel.creeperSound, self.controller.panelCreeperSound),
            (panel.lightning, self.controller.panelLightning),
        ):
            with self.subTest(button=button.label):
                interaction = _fakeInteraction()
                self._run(button.callback(interaction))
                interaction.response.defer.assert_awaited_once()
                interaction.response.edit_message.assert_not_called()
                handler.assert_awaited_once_with(interaction, "Steve")

    def testSpecialMobSelectResetsHighlightAndSummons(self):
        """특수 몹 드롭다운은 강조를 초기화해 같은 프리셋을 연달아 부를 수 있다."""
        self.controller.panelSpecialMob = AsyncMock()
        view = cp.SummonPanelView(self.controller, self.ownerId, "Steve")
        select = next(i for i in view.children if isinstance(i, cp.SpecialMobSelect))
        select._values = ["horde"]
        interaction = _fakeInteraction()
        self._run(select.callback(interaction))
        interaction.response.edit_message.assert_awaited_once_with(view=view)
        self.controller.panelSpecialMob.assert_awaited_once_with(
            interaction, "Steve", "horde"
        )

    def testVillagerGoodSelectOpensPriceModal(self):
        """상품을 고르면 가격 입력 모달이 뜨고, 제출 시 주민을 소환한다."""
        self.controller.panelSummonVillager = AsyncMock()
        view = cp.SummonPanelView(self.controller, self.ownerId, "Steve")
        select = next(i for i in view.children if isinstance(i, cp.VillagerGoodSelect))
        select._values = ["mending"]
        interaction = _fakeInteraction()
        self._run(select.callback(interaction))
        interaction.response.send_modal.assert_awaited_once()
        modal = interaction.response.send_modal.await_args.args[0]
        self.assertIsInstance(modal, cp.VillagerPriceModal)
        # 가격을 비우면 기본값으로 소환.
        modal.price._value = ""
        submit = _fakeInteraction()
        self._run(modal.on_submit(submit))
        self.controller.panelSummonVillager.assert_awaited_once()
        args = self.controller.panelSummonVillager.await_args.args
        self.assertEqual(args[1], "Steve")
        self.assertEqual(args[2], "librarian")
        self.assertEqual(args[3], "mending")

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

    # ── 같은 옵션 연속 선택 (드롭다운 강조 초기화) ────────────────

    def _findSelect(self, view):
        return next(
            item for item in view.children if isinstance(item, discord.ui.Select)
        )

    def testEffectSelectClearsHighlightSoSameEffectRepeats(self):
        """'신속'을 고른 직후 같은 화면을 다시 그려, 바로 또 고를 수 있다."""
        self.controller.panelApplyEffect = AsyncMock()
        view = cp.EffectPanelView(self.controller, self.ownerId, "Steve")
        select = self._findSelect(view)
        select._values = ["speed"]
        interaction = _fakeInteraction()
        self._run(select.callback(interaction))
        interaction.response.edit_message.assert_awaited_once_with(view=view)
        interaction.response.defer.assert_not_called()
        self.controller.panelApplyEffect.assert_awaited_once()
        self.assertTrue(all(not option.default for option in select.options))

    def testEffectClearAlsoResetsHighlight(self):
        self.controller.panelClearEffects = AsyncMock()
        view = cp.EffectPanelView(self.controller, self.ownerId, "Steve")
        select = self._findSelect(view)
        select._values = ["__clear__"]
        interaction = _fakeInteraction()
        self._run(select.callback(interaction))
        interaction.response.edit_message.assert_awaited_once_with(view=view)
        self.controller.panelClearEffects.assert_awaited_once()

    def testEnchantSelectClearsHighlightSoSameEnchantRepeats(self):
        self.controller.panelEnchant = AsyncMock()
        view = cp.EnchantPanelView(self.controller, self.ownerId, "Steve")
        select = self._findSelect(view)
        select._values = ["sharpness:5"]
        interaction = _fakeInteraction()
        self._run(select.callback(interaction))
        interaction.response.edit_message.assert_awaited_once_with(view=view)
        interaction.response.defer.assert_not_called()
        self.controller.panelEnchant.assert_awaited_once()

    def testCustomEffectModalResetsSelectHighlightOnSubmit(self):
        """'직접 입력…'으로 연 모달도 제출 시 드롭다운 강조를 지운다."""
        self.controller.panelApplyEffect = AsyncMock()
        view = cp.EffectPanelView(self.controller, self.ownerId, "Steve")
        modal = cp.CustomEffectModal(self.controller, "Steve", panelView=view)
        modal.effectId._value = "luck"
        modal.seconds._value = ""
        modal.level._value = ""
        modal.particles._value = ""
        interaction = _fakeInteraction()
        self._run(modal.on_submit(interaction))
        interaction.response.edit_message.assert_awaited_once_with(view=view)
        interaction.response.defer.assert_not_called()
        self.controller.panelApplyEffect.assert_awaited_once()

    def testModalWithoutPanelViewStillDefers(self):
        """버튼에서 연 모달(아이템 주기 등)은 기존처럼 thinking defer."""
        self.controller.panelGiveItem = AsyncMock()
        modal = cp.GiveItemModal(self.controller, "Steve")
        modal.itemName._value = "diamond"
        modal.count._value = ""
        interaction = _fakeInteraction()
        self._run(modal.on_submit(interaction))
        interaction.response.defer.assert_awaited_once()
        interaction.response.edit_message.assert_not_called()

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
