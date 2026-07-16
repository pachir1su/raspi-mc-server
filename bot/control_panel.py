"""Button-first Discord administration views for routine server operations."""

import discord

from bot.config import cfg
from bot.error_text import describeError
from bot.i18n import t
from bot.quick_commands import COMMON_EFFECTS, COMMON_ENCHANTS, DIFFICULTIES, GAMERULES


class OwnerView(discord.ui.View):
    """Restrict ephemeral controls to the administrator who opened them."""

    def __init__(self, controller, ownerId: int, timeout: float = 600):
        super().__init__(timeout=timeout)
        self.controller = controller
        self.ownerId = ownerId

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Reject shared-message component use by anyone outside the allowlist."""
        if interaction.user.id == self.ownerId and interaction.user.id in cfg.admin_ids:
            return True
        await interaction.response.send_message(
            "⛔ 이 관리 패널을 사용할 권한이 없습니다.", ephemeral=True
        )
        return False

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ):
        """Convert callback failures into an ephemeral message instead of a dead button."""
        message = f"❌ {describeError(error)}"
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class AdminDashboardView(OwnerView):
    """Main dashboard with the most common tasks reachable in one click.

    Only everyday actions live here; everything else moves behind 더보기 so
    the first screen stays two short rows instead of a wall of buttons.
    """

    @discord.ui.button(label="새로고침", emoji="🔄", style=discord.ButtonStyle.secondary, row=0)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.controller.panelOverviewEmbed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="접속자 관리", emoji="👥", style=discord.ButtonStyle.primary, row=0)
    async def players(self, interaction: discord.Interaction, button: discord.ui.Button):
        players = await self.controller.panelOnlinePlayers()
        if not players:
            await interaction.response.send_message("현재 접속 중인 플레이어가 없습니다.", ephemeral=True)
            return
        view = PlayerPanelView(self.controller, self.ownerId, players)
        await interaction.response.send_message(
            "조회할 플레이어를 선택하세요.", view=view, ephemeral=True
        )

    @discord.ui.button(label="서버 제어", emoji="🎛️", style=discord.ButtonStyle.primary, row=0)
    async def service(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "실행할 서버 작업을 선택하세요. 정지와 재시작은 한 번 더 확인합니다.",
            view=ServerActionsView(self.controller, self.ownerId),
            ephemeral=True,
        )

    @discord.ui.button(label="백업", emoji="💾", style=discord.ButtonStyle.success, row=0)
    async def backups(self, interaction: discord.Interaction, button: discord.ui.Button):
        backups = await self.controller.panelBackups()
        settings = await self.controller.panelBackupSettings()
        embed = await self.controller.panelBackupEmbed()
        await interaction.response.send_message(
            embed=embed,
            view=BackupPanelView(self.controller, self.ownerId, backups, settings),
            ephemeral=True,
        )

    @discord.ui.button(label="긴급 복구", emoji="🚑", style=discord.ButtonStyle.danger, row=0)
    async def incident(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "자주 쓰는 사고 대응 작업입니다. 서버 상태를 바꿀 수 있습니다.",
            view=IncidentActionsView(self.controller, self.ownerId),
            ephemeral=True,
        )

    @discord.ui.button(label="상태 진단", emoji="🩺", style=discord.ButtonStyle.secondary, row=1)
    async def health(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.controller.panelHealthEmbed()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="친구 계정", emoji="👤", style=discord.ButtonStyle.secondary, row=1)
    async def links(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.controller.panelOpenLinkAdmin(interaction)

    @discord.ui.button(label="관리 도움말", emoji="❓", style=discord.ButtonStyle.primary, row=1)
    async def help(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=self.controller.panelHelpEmbed(), ephemeral=True
        )

    @discord.ui.button(label="더보기", emoji="🧰", style=discord.ButtonStyle.secondary, row=1)
    async def more(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "자주 쓰지 않는 도구와 설정입니다.",
            view=MoreToolsView(self.controller, self.ownerId),
            ephemeral=True,
        )


class MoreToolsView(OwnerView):
    """Second-tier dashboard tools that are useful but not everyday actions."""

    @discord.ui.button(label="성능 상세", emoji="📊", style=discord.ButtonStyle.secondary, row=0)
    async def performance(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        embed = await self.controller.panelMetricsEmbed()
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="렉 원인", emoji="🧰", style=discord.ButtonStyle.secondary, row=0)
    async def tuning(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        warnings, embed = await self.controller._collectPerformanceWarnings()
        if warnings:
            embed.add_field(name="경고", value="\n".join(f"• {item}" for item in warnings)[:1000], inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="로그", emoji="📄", style=discord.ButtonStyle.secondary, row=0)
    async def logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "확인할 로그를 선택하세요.", view=LogPanelView(self.controller, self.ownerId), ephemeral=True
        )

    @discord.ui.button(label="저장공간", emoji="💽", style=discord.ButtonStyle.secondary, row=0)
    async def storage(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.controller.panelStorageEmbed()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="월드", emoji="🌍", style=discord.ButtonStyle.secondary, row=1)
    async def worlds(self, interaction: discord.Interaction, button: discord.ui.Button):
        worlds = await self.controller.panelWorlds()
        await interaction.response.send_message(
            "가져온 월드를 선택하세요. 새 파일은 `/업로드 월드`로 추가합니다.",
            view=WorldPanelView(self.controller, self.ownerId, worlds),
            ephemeral=True,
        )

    @discord.ui.button(label="업데이트", emoji="⬆️", style=discord.ButtonStyle.secondary, row=1)
    async def updates(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Release 확인과 최근 설치 결과를 조회합니다. ZIP은 `/업로드 업데이트`를 사용하세요.",
            view=UpdatePanelView(self.controller, self.ownerId),
            ephemeral=True,
        )

    @discord.ui.button(label="고급 도구", emoji="⚙️", style=discord.ButtonStyle.secondary, row=1)
    async def advanced(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "게임 공지, 인게임 명령어(마인크래프트 콘솔 명령 직접 실행), "
            "접속 허용목록과 감사 기록입니다.",
            view=AdvancedPanelView(self.controller, self.ownerId),
            ephemeral=True,
        )

    @discord.ui.button(label="스폰 보호", emoji="🛡️", style=discord.ButtonStyle.secondary, row=2)
    async def spawnProtection(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelToggleSpawnProtection(interaction)

    @discord.ui.button(label="상자 잠금", emoji="🔒", style=discord.ButtonStyle.secondary, row=2)
    async def chestLock(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelToggleChestLock(interaction)


class IncidentActionsView(OwnerView):
    """One-click emergency shortcuts for common small-server accidents."""

    async def _run(self, interaction: discord.Interaction, command: str, label: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller._incidentCommand(interaction, command, label)

    @discord.ui.button(label="낮으로", emoji="☀️", style=discord.ButtonStyle.primary)
    async def day(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._run(interaction, "time set day", "incident_day")

    @discord.ui.button(label="맑게", emoji="🌤️", style=discord.ButtonStyle.primary)
    async def clearWeather(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._run(interaction, "weather clear", "incident_clear")

    @discord.ui.button(label="평화 난이도", emoji="🛡️", style=discord.ButtonStyle.danger)
    async def peaceful(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._run(interaction, "difficulty peaceful", "incident_peaceful")

    @discord.ui.button(label="드롭템 정리", emoji="🧹", style=discord.ButtonStyle.danger)
    async def clearDrops(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            t("incident_clear_drops_prompt"),
            view=ConfirmIncidentView(
                self.controller,
                self.ownerId,
                "kill @e[type=item]",
                "incident_kill_items",
            ),
            ephemeral=True,
        )


class ConfirmIncidentView(OwnerView):
    """Second-step confirmation for destructive incident helpers."""

    def __init__(self, controller, ownerId: int, command: str, label: str):
        super().__init__(controller, ownerId, timeout=60)
        self.command = command
        self.label = label
        self.confirm.label = t("confirm")
        self.cancel.label = t("cancel")

    @discord.ui.button(label="확인", emoji="✅", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller._incidentCommand(interaction, self.command, self.label)
        self.stop()

    @discord.ui.button(label="취소", emoji="✖️", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=t("cancelled"), view=None)
        self.stop()


class ConfirmServiceView(OwnerView):
    """Second-step confirmation for disruptive systemd actions."""

    def __init__(self, controller, ownerId: int, action: str):
        super().__init__(controller, ownerId, timeout=60)
        self.action = action

    @discord.ui.button(label="확인", emoji="✅", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelServiceAction(interaction, self.action)
        self.stop()

    @discord.ui.button(label="취소", emoji="✖️", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="취소했습니다.", view=None)
        self.stop()


class ServerActionsView(OwnerView):
    """Server lifecycle shortcuts; disruptive actions open confirmation views."""

    async def _confirm(self, interaction: discord.Interaction, action: str, koreanName: str):
        await interaction.response.send_message(
            f"마인크래프트 서버를 **{koreanName}**할까요?",
            view=ConfirmServiceView(self.controller, self.ownerId, action),
            ephemeral=True,
        )

    @discord.ui.button(label="시작", emoji="▶️", style=discord.ButtonStyle.success)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelServiceAction(interaction, "start")

    @discord.ui.button(label="재시작", emoji="🔁", style=discord.ButtonStyle.primary)
    async def restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._confirm(interaction, "restart", "재시작")

    @discord.ui.button(label="정지", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._confirm(interaction, "stop", "정지")


class PlayerSelect(discord.ui.Select):
    """Dropdown populated from the live Paper player list."""

    def __init__(self, parentView, players: list[str]):
        self.parentView = parentView
        options = [discord.SelectOption(label=name, value=name, emoji="🎮") for name in players[:25]]
        super().__init__(placeholder="플레이어 선택", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.parentView.selectedPlayer = self.values[0]
        await interaction.response.edit_message(
            content=f"선택됨: **{self.values[0]}** — 아래 조회·조작 버튼이 이 플레이어에게 적용됩니다.",
            view=self.parentView,
        )


class QuickActionModal(discord.ui.Modal):
    """Shared error handling for the few quick actions that need typed input."""

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        message = f"❌ {describeError(error)}"
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class GiveItemModal(QuickActionModal):
    """아이템 주기 — 텍스트 입력은 아이템 이름(과 선택적 수량)뿐입니다."""

    def __init__(self, controller, playerName: str):
        super().__init__(title=f"아이템 주기 — {playerName}"[:45])
        self.controller = controller
        self.playerName = playerName
        self.itemName = discord.ui.TextInput(
            label="아이템 이름 (한글 별칭 또는 영어 ID)",
            placeholder="예: 다이아, 철검, iron_sword",
            max_length=64,
        )
        self.count = discord.ui.TextInput(
            label="수량 (비우면 1)", required=False, max_length=5
        )
        self.add_item(self.itemName)
        self.add_item(self.count)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelGiveItem(
            interaction, self.playerName, self.itemName.value, self.count.value
        )


class CustomEffectModal(QuickActionModal):
    """드롭다운에 없는 포션 효과를 ID로 직접 지정할 때만 씁니다."""

    def __init__(self, controller, playerName: str):
        super().__init__(title=f"포션 효과 직접 입력 — {playerName}"[:45])
        self.controller = controller
        self.playerName = playerName
        self.effectId = discord.ui.TextInput(
            label="효과 ID (영어)", placeholder="예: speed, luck, absorption", max_length=64
        )
        self.seconds = discord.ui.TextInput(
            label="지속 시간(초, 비우면 300)", required=False, max_length=7
        )
        self.add_item(self.effectId)
        self.add_item(self.seconds)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        secondsText = (self.seconds.value or "").strip()
        if secondsText and not secondsText.isdigit():
            raise ValueError("지속 시간은 숫자(초)로 입력하세요.")
        await self.controller.panelApplyEffect(
            interaction,
            self.playerName,
            self.effectId.value,
            int(secondsText) if secondsText else 300,
            0,
        )


class CustomEnchantModal(QuickActionModal):
    """드롭다운에 없는 인챈트를 ID와 레벨로 직접 지정할 때만 씁니다."""

    def __init__(self, controller, playerName: str):
        super().__init__(title=f"인챈트 직접 입력 — {playerName}"[:45])
        self.controller = controller
        self.playerName = playerName
        self.enchantId = discord.ui.TextInput(
            label="인챈트 ID (영어)", placeholder="예: knockback, thorns", max_length=64
        )
        self.level = discord.ui.TextInput(
            label="레벨 (비우면 1)", required=False, max_length=3
        )
        self.add_item(self.enchantId)
        self.add_item(self.level)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        levelText = (self.level.value or "").strip()
        if levelText and not levelText.isdigit():
            raise ValueError("레벨은 숫자로 입력하세요.")
        await self.controller.panelEnchant(
            interaction,
            self.playerName,
            self.enchantId.value,
            int(levelText) if levelText else 1,
        )


class EffectSelect(discord.ui.Select):
    """자주 쓰는 포션 효과 + 효과 해제 + 직접 입력."""

    def __init__(self, controller, playerName: str):
        self.controller = controller
        self.playerName = playerName
        options = [
            discord.SelectOption(
                label=f"{label} ({seconds // 60}분)", value=effectId, emoji="✨"
            )
            for effectId, label, seconds, _amplifier in COMMON_EFFECTS
        ]
        options.append(
            discord.SelectOption(label="효과 전부 해제", value="__clear__", emoji="🚿")
        )
        options.append(
            discord.SelectOption(label="직접 입력…", value="__custom__", emoji="⌨️")
        )
        super().__init__(placeholder="적용할 포션 효과 선택", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        if choice == "__custom__":
            await interaction.response.send_modal(
                CustomEffectModal(self.controller, self.playerName)
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        if choice == "__clear__":
            await self.controller.panelClearEffects(interaction, self.playerName)
            return
        seconds, amplifier = next(
            (seconds, amplifier)
            for effectId, _label, seconds, amplifier in COMMON_EFFECTS
            if effectId == choice
        )
        await self.controller.panelApplyEffect(
            interaction, self.playerName, choice, seconds, amplifier
        )


class EffectPanelView(OwnerView):
    def __init__(self, controller, ownerId: int, playerName: str):
        super().__init__(controller, ownerId, timeout=300)
        self.add_item(EffectSelect(controller, playerName))


class EnchantSelect(discord.ui.Select):
    """자주 쓰는 인챈트 + 직접 입력. 들고 있는 아이템에 적용됩니다."""

    def __init__(self, controller, playerName: str):
        self.controller = controller
        self.playerName = playerName
        options = [
            discord.SelectOption(label=label, value=f"{enchantId}:{level}", emoji="🗡️")
            for enchantId, label, level in COMMON_ENCHANTS
        ]
        options.append(
            discord.SelectOption(label="직접 입력…", value="__custom__", emoji="⌨️")
        )
        super().__init__(placeholder="부여할 인챈트 선택", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        if choice == "__custom__":
            await interaction.response.send_modal(
                CustomEnchantModal(self.controller, self.playerName)
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        enchantId, level = choice.rsplit(":", 1)
        await self.controller.panelEnchant(
            interaction, self.playerName, enchantId, int(level)
        )


class EnchantPanelView(OwnerView):
    def __init__(self, controller, ownerId: int, playerName: str):
        super().__init__(controller, ownerId, timeout=300)
        self.add_item(EnchantSelect(controller, playerName))


class GamemodePanelView(OwnerView):
    """선택한 접속자의 게임모드를 버튼 한 번으로 변경."""

    def __init__(self, controller, ownerId: int, playerName: str):
        super().__init__(controller, ownerId, timeout=300)
        self.playerName = playerName

    async def _apply(self, interaction: discord.Interaction, mode: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelGamemode(interaction, self.playerName, mode)

    @discord.ui.button(label="서바이벌", emoji="⛏️", style=discord.ButtonStyle.primary)
    async def survival(self, interaction, button):
        await self._apply(interaction, "survival")

    @discord.ui.button(label="크리에이티브", emoji="🪄", style=discord.ButtonStyle.success)
    async def creative(self, interaction, button):
        await self._apply(interaction, "creative")

    @discord.ui.button(label="관전", emoji="👻", style=discord.ButtonStyle.secondary)
    async def spectator(self, interaction, button):
        await self._apply(interaction, "spectator")


class TeleportTargetSelect(discord.ui.Select):
    """다른 접속자에게 순간이동 — 고르는 즉시 실행됩니다."""

    def __init__(self, controller, playerName: str, otherPlayers: list[str]):
        self.controller = controller
        self.playerName = playerName
        options = [
            discord.SelectOption(label=name, value=name, emoji="🎮")
            for name in otherPlayers[:25]
        ]
        super().__init__(
            placeholder="이 접속자에게 이동", min_values=1, max_values=1, options=options, row=0
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelTeleportToPlayer(
            interaction, self.playerName, self.values[0]
        )


class TeleportPlaceSelect(discord.ui.Select):
    """공유 좌표북의 저장 좌표로 순간이동 — 고르는 즉시 실행됩니다."""

    def __init__(self, controller, playerName: str, places):
        self.controller = controller
        self.playerName = playerName
        options = [
            discord.SelectOption(
                label=place.name[:100],
                value=place.name,
                description=f"{place.dimension} · {place.x} {place.y} {place.z}"[:100],
                emoji="📍",
            )
            for place in places[:25]
        ]
        super().__init__(
            placeholder="저장된 좌표로 이동", min_values=1, max_values=1, options=options, row=1
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelTeleportToPlace(
            interaction, self.playerName, self.values[0]
        )


class TeleportPanelView(OwnerView):
    """접속자·좌표북·스폰 세 종류의 순간이동 목적지를 한 화면에."""

    def __init__(self, controller, ownerId: int, playerName: str, otherPlayers, places):
        super().__init__(controller, ownerId, timeout=300)
        self.playerName = playerName
        if otherPlayers:
            self.add_item(TeleportTargetSelect(controller, playerName, otherPlayers))
        if places:
            self.add_item(TeleportPlaceSelect(controller, playerName, places))

    @discord.ui.button(label="스폰으로", emoji="🏠", style=discord.ButtonStyle.primary, row=2)
    async def toSpawn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelTeleportToSpawn(interaction, self.playerName)


class ConfirmKickView(OwnerView):
    """추방 전에 한 번 더 확인합니다."""

    def __init__(self, controller, ownerId: int, playerName: str):
        super().__init__(controller, ownerId, timeout=60)
        self.playerName = playerName

    @discord.ui.button(label="추방 확인", emoji="🥾", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelKick(interaction, self.playerName)
        self.stop()

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="추방을 취소했습니다.", view=None)
        self.stop()


class PlayerPanelView(OwnerView):
    """접속자 선택 + 조회(인벤토리·위치·체력·효과) + 조작(지급·효과·인챈트 등).

    조회 버튼은 서버 상태를 바꾸지 않고, 조작 버튼은 전부 감사 기록을 남깁니다.
    버튼 → 명령 대응은 bot/quick_commands.py에 있습니다.
    """

    def __init__(self, controller, ownerId: int, players: list[str]):
        super().__init__(controller, ownerId)
        self.players = players
        self.selectedPlayer = players[0]
        self.add_item(PlayerSelect(self, players))

    async def _show(self, interaction: discord.Interaction, detailType: str):
        embed = await self.controller.panelPlayerEmbed(self.selectedPlayer, detailType)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="인벤토리", emoji="🎒", style=discord.ButtonStyle.primary, row=1)
    async def inventory(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show(interaction, "inventory")

    @discord.ui.button(label="위치", emoji="🧭", style=discord.ButtonStyle.secondary, row=1)
    async def position(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show(interaction, "position")

    @discord.ui.button(label="체력·경험치", emoji="❤️", style=discord.ButtonStyle.secondary, row=1)
    async def stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show(interaction, "stats")

    @discord.ui.button(label="효과 보기", emoji="🔍", style=discord.ButtonStyle.secondary, row=1)
    async def effects(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show(interaction, "effects")

    @discord.ui.button(label="아이템 주기", emoji="🎁", style=discord.ButtonStyle.success, row=2)
    async def giveItem(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            GiveItemModal(self.controller, self.selectedPlayer)
        )

    @discord.ui.button(label="포션 효과", emoji="✨", style=discord.ButtonStyle.primary, row=2)
    async def applyEffect(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"**{self.selectedPlayer}** 에게 적용할 효과를 선택하세요.",
            view=EffectPanelView(self.controller, self.ownerId, self.selectedPlayer),
            ephemeral=True,
        )

    @discord.ui.button(label="인챈트", emoji="🗡️", style=discord.ButtonStyle.primary, row=2)
    async def enchant(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"**{self.selectedPlayer}** 가 들고 있는 아이템에 부여할 인챈트를 선택하세요.",
            view=EnchantPanelView(self.controller, self.ownerId, self.selectedPlayer),
            ephemeral=True,
        )

    @discord.ui.button(label="게임모드", emoji="🎮", style=discord.ButtonStyle.secondary, row=2)
    async def gamemode(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"**{self.selectedPlayer}** 의 게임모드를 선택하세요.",
            view=GamemodePanelView(self.controller, self.ownerId, self.selectedPlayer),
            ephemeral=True,
        )

    @discord.ui.button(label="TP", emoji="🚀", style=discord.ButtonStyle.secondary, row=2)
    async def teleport(self, interaction: discord.Interaction, button: discord.ui.Button):
        otherPlayers = [name for name in self.players if name != self.selectedPlayer]
        places = await self.controller.panelSharedPlaces()
        await interaction.response.send_message(
            f"**{self.selectedPlayer}** 를 어디로 이동시킬까요?",
            view=TeleportPanelView(
                self.controller, self.ownerId, self.selectedPlayer, otherPlayers, places
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="경험치 +10", emoji="⭐", style=discord.ButtonStyle.secondary, row=3)
    async def xpSmall(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelXp(interaction, self.selectedPlayer, 10)

    @discord.ui.button(label="경험치 +30", emoji="🌟", style=discord.ButtonStyle.secondary, row=3)
    async def xpLarge(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelXp(interaction, self.selectedPlayer, 30)

    @discord.ui.button(label="회복", emoji="💖", style=discord.ButtonStyle.success, row=3)
    async def heal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelHeal(interaction, self.selectedPlayer)

    @discord.ui.button(label="추방", emoji="🥾", style=discord.ButtonStyle.danger, row=3)
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"**{self.selectedPlayer}** 를 서버에서 추방할까요?",
            view=ConfirmKickView(self.controller, self.ownerId, self.selectedPlayer),
            ephemeral=True,
        )


class StoredFileSelect(discord.ui.Select):
    """Dropdown shared by backup and imported-world panels."""

    def __init__(self, parentView, items, placeholder: str, emoji: str):
        self.parentView = parentView
        options = [
            discord.SelectOption(
                label=item.name[:100],
                value=item.name,
                description=f"{item.size / 1024 / 1024:.1f} MiB · {item.modifiedAt:%Y-%m-%d %H:%M}"[:100],
                emoji=emoji,
            )
            for item in items[:25]
        ]
        super().__init__(placeholder=placeholder, options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        self.parentView.selectedName = self.values[0]
        await interaction.response.edit_message(
            content=f"선택됨: **{self.values[0]}**", view=self.parentView
        )


class ConfirmLegacyActionView(OwnerView):
    """Require a second button press before a destructive legacy action."""

    def __init__(
        self,
        controller,
        ownerId: int,
        commandName: str,
        arguments: tuple,
        confirmLabel: str,
    ):
        super().__init__(controller, ownerId, timeout=120)
        self.commandName = commandName
        self.arguments = arguments
        self.confirm.label = confirmLabel

    @discord.ui.button(label="확인", emoji="⚠️", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        await self.controller.panelLegacyCommand(
            self.commandName, interaction, *self.arguments
        )
        self.stop()

    @discord.ui.button(label="취소", emoji="↩️", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(content="작업을 취소했습니다.", view=None)
        self.stop()


class BackupPanelView(OwnerView):
    """Backup creation, selection, verification, restore, deletion, and policy."""

    def __init__(self, controller, ownerId: int, backups, settings):
        super().__init__(controller, ownerId)
        self.selectedName = backups[0].name if backups else None
        self.settings = settings
        self.toggle.label = f"자동 백업: {'켜짐' if settings.enabled else '꺼짐'}"
        self.toggle.style = (
            discord.ButtonStyle.success
            if settings.enabled
            else discord.ButtonStyle.secondary
        )
        if backups:
            self.add_item(StoredFileSelect(self, backups, "백업 선택", "💾"))

    async def _selected(self, interaction, action: str, *args):
        if not self.selectedName:
            await interaction.response.send_message("선택할 백업이 없습니다.", ephemeral=True)
            return
        await self.controller.panelLegacyCommand(
            action, interaction, self.selectedName, *args
        )

    @discord.ui.button(label="지금 백업", emoji="💾", style=discord.ButtonStyle.success, row=1)
    async def create(self, interaction, button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelCreateBackup(interaction)

    @discord.ui.button(label="자동 백업", emoji="🔔", style=discord.ButtonStyle.secondary, row=1)
    async def toggle(self, interaction, button):
        enabled = await self.controller.panelToggleBackup(interaction)
        button.label = f"자동 백업: {'켜짐' if enabled else '꺼짐'}"
        button.style = discord.ButtonStyle.success if enabled else discord.ButtonStyle.secondary
        embed = await self.controller.panelBackupEmbed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="검증", emoji="✅", style=discord.ButtonStyle.secondary, row=1)
    async def verify(self, interaction, button):
        await self._selected(interaction, "backupVerify")

    @discord.ui.button(label="다운로드", emoji="⬇️", style=discord.ButtonStyle.secondary, row=1)
    async def download(self, interaction, button):
        await self._selected(interaction, "backupDownload")

    @discord.ui.button(label="복구", emoji="♻️", style=discord.ButtonStyle.danger, row=2)
    async def restore(self, interaction, button):
        if not self.selectedName:
            await interaction.response.send_message("선택한 백업이 없습니다.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"⚠️ `{self.selectedName}` 백업으로 복구할까요? 현재 월드는 교체됩니다.",
            view=ConfirmLegacyActionView(
                self.controller,
                self.ownerId,
                "backupRestore",
                (self.selectedName, "RESTORE"),
                "백업 복구",
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="삭제", emoji="🗑️", style=discord.ButtonStyle.danger, row=2)
    async def delete(self, interaction, button):
        if not self.selectedName:
            await interaction.response.send_message("선택한 백업이 없습니다.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"⚠️ `{self.selectedName}` 백업을 영구 삭제할까요?",
            view=ConfirmLegacyActionView(
                self.controller,
                self.ownerId,
                "backupDelete",
                (self.selectedName, "DELETE"),
                "백업 삭제",
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="정리", emoji="🧹", style=discord.ButtonStyle.secondary, row=2)
    async def prune(self, interaction, button):
        await self.controller.panelLegacyCommand("backupPrune", interaction)

    @discord.ui.button(label="정책 설정", emoji="⚙️", style=discord.ButtonStyle.primary, row=2)
    async def policy(self, interaction, button):
        await interaction.response.send_message(
            "각 항목을 선택하면 즉시 저장됩니다.",
            view=BackupPolicyView(self.controller, self.ownerId, self.settings),
            ephemeral=True,
        )


class BackupSettingSelect(discord.ui.Select):
    """Persist one backup policy field immediately after selection."""

    def __init__(self, parentView, field: str, label: str, values: list[int], current: int, row: int):
        self.parentView = parentView
        self.field = field
        options = [
            discord.SelectOption(
                label=str(value), value=str(value), default=value == current
            )
            for value in values
        ]
        super().__init__(placeholder=label, options=options, row=row)

    async def callback(self, interaction: discord.Interaction):
        settings = await self.parentView.controller.panelUpdateBackupSetting(
            self.field, int(self.values[0])
        )
        await interaction.response.edit_message(
            content=(
                "✅ 백업 정책 저장됨 · "
                f"{settings.intervalMinutes}분 / {settings.retentionHours}시간 / "
                f"일일 {settings.dailyRetentionDays}일 / "
                f"사용률 {settings.maxUsagePercent}% / 여유 {settings.minFreeGb}GB"
            ),
            view=self.parentView,
        )


class BackupPolicyView(OwnerView):
    """Common backup values as selects so routine configuration needs no typing."""

    def __init__(self, controller, ownerId: int, settings):
        super().__init__(controller, ownerId)
        self.add_item(BackupSettingSelect(self, "intervalMinutes", "백업 주기(분)", [30, 60, 120, 240, 360], settings.intervalMinutes, 0))
        self.add_item(BackupSettingSelect(self, "retentionHours", "단기 보관(시간)", [24, 48, 72, 168, 336], settings.retentionHours, 1))
        self.add_item(BackupSettingSelect(self, "dailyRetentionDays", "일일 보관(일)", [7, 14, 30, 60, 90], settings.dailyRetentionDays, 2))
        self.add_item(BackupSettingSelect(self, "maxUsagePercent", "최대 HDD 사용률(%)", [70, 75, 80, 85, 90, 95], settings.maxUsagePercent, 3))
        self.add_item(BackupSettingSelect(self, "minFreeGb", "최소 여유 공간(GB)", [5, 10, 20, 30, 50, 100], settings.minFreeGb, 4))


class WorldPanelView(OwnerView):
    """Select imported worlds and perform bounded file actions."""

    def __init__(self, controller, ownerId: int, worlds):
        super().__init__(controller, ownerId)
        self.selectedName = worlds[0].name if worlds else None
        if worlds:
            self.add_item(StoredFileSelect(self, worlds, "가져온 월드 선택", "🌍"))

    async def _selected(self, interaction, action: str, *args):
        if not self.selectedName:
            await interaction.response.send_message("가져온 월드가 없습니다.", ephemeral=True)
            return
        await self.controller.panelLegacyCommand(action, interaction, self.selectedName, *args)

    @discord.ui.button(label="적용", emoji="✅", style=discord.ButtonStyle.danger, row=1)
    async def activate(self, interaction, button):
        if not self.selectedName:
            await interaction.response.send_message("가져온 월드가 없습니다.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"⚠️ `{self.selectedName}` 월드를 적용할까요? 서버 월드가 교체됩니다.",
            view=ConfirmLegacyActionView(
                self.controller,
                self.ownerId,
                "worldActivate",
                (self.selectedName, "ACTIVATE"),
                "월드 적용",
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="다운로드", emoji="⬇️", style=discord.ButtonStyle.secondary, row=1)
    async def download(self, interaction, button):
        await self._selected(interaction, "worldDownload")

    @discord.ui.button(label="삭제", emoji="🗑️", style=discord.ButtonStyle.danger, row=1)
    async def delete(self, interaction, button):
        if not self.selectedName:
            await interaction.response.send_message("가져온 월드가 없습니다.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"⚠️ `{self.selectedName}` 가져온 월드를 삭제할까요?",
            view=ConfirmLegacyActionView(
                self.controller,
                self.ownerId,
                "worldDelete",
                (self.selectedName, "DELETE"),
                "월드 삭제",
            ),
            ephemeral=True,
        )


class UpdatePanelView(OwnerView):
    """Release check and recent updater result without typed subcommands."""

    @discord.ui.button(label="새 버전 확인", emoji="🔍", style=discord.ButtonStyle.primary)
    async def check(self, interaction, button):
        await self.controller.panelLegacyCommand("updateCheck", interaction)

    @discord.ui.button(label="최근 결과", emoji="📊", style=discord.ButtonStyle.secondary)
    async def status(self, interaction, button):
        await self.controller.panelLegacyCommand("updateStatus", interaction)


class TextActionModal(discord.ui.Modal):
    """Single-field modal for the few operations that inherently require text."""

    def __init__(self, controller, title: str, label: str, action: str, placeholder: str = ""):
        super().__init__(title=title)
        self.controller = controller
        self.action = action
        self.value = discord.ui.TextInput(label=label, placeholder=placeholder, max_length=1500)
        self.add_item(self.value)

    async def on_submit(self, interaction: discord.Interaction):
        await self.controller.panelTextAction(interaction, self.action, self.value.value)


class AdvancedPanelView(OwnerView):
    """Keep unavoidable text entry and audit lookup out of the routine dashboard."""

    @discord.ui.button(label="게임 공지", emoji="📣", style=discord.ButtonStyle.primary)
    async def announce(self, interaction, button):
        await interaction.response.send_modal(
            TextActionModal(self.controller, "게임 공지", "공지 내용", "say")
        )

    @discord.ui.button(label="인게임 명령어", emoji="⌨️", style=discord.ButtonStyle.danger)
    async def rcon(self, interaction, button):
        # 마인크래프트 콘솔 명령을 입력한 그대로 실행하는 자유 입력 채널.
        # 자주 쓰는 명령은 접속자 관리·빠른 명령 버튼을 먼저 확인하세요.
        await interaction.response.send_modal(
            TextActionModal(
                self.controller,
                "인게임 명령어 실행",
                "마인크래프트 콘솔 명령 (/ 없이 입력)",
                "mc",
                "예: time set day, gamemode creative 닉네임",
            )
        )

    @discord.ui.button(label="허용 추가", emoji="➕", style=discord.ButtonStyle.success, row=1)
    async def whitelistAdd(self, interaction, button):
        await interaction.response.send_modal(
            TextActionModal(self.controller, "허용목록 추가", "Minecraft 닉네임", "wl_add")
        )

    @discord.ui.button(label="허용 제거", emoji="➖", style=discord.ButtonStyle.secondary, row=1)
    async def whitelistRemove(self, interaction, button):
        await interaction.response.send_modal(
            TextActionModal(self.controller, "허용목록 제거", "Minecraft 닉네임", "wl_remove")
        )

    @discord.ui.button(label="감사 기록", emoji="🧾", style=discord.ButtonStyle.secondary, row=2)
    async def audit(self, interaction, button):
        await self.controller.panelLegacyCommand("audit", interaction, 10)


class LogPanelView(OwnerView):
    """Choose bot/Paper logs, filtered failures, or direct attachments."""

    async def _show(self, interaction: discord.Interaction, source: str, errorsOnly: bool = False):
        embed = await self.controller.panelLogEmbed(source, errorsOnly)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="봇 로그", emoji="🤖", style=discord.ButtonStyle.primary)
    async def botLog(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show(interaction, "bot")

    @discord.ui.button(label="마크 로그", emoji="⛏️", style=discord.ButtonStyle.primary)
    async def serverLog(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show(interaction, "server")

    @discord.ui.button(label="봇 오류", emoji="⚠️", style=discord.ButtonStyle.danger, row=1)
    async def botErrors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show(interaction, "bot", True)

    @discord.ui.button(label="마크 오류", emoji="⚠️", style=discord.ButtonStyle.danger, row=1)
    async def errors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show(interaction, "server", True)

    @discord.ui.button(label="봇 파일", emoji="⬇️", style=discord.ButtonStyle.secondary, row=2)
    async def botDownload(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.controller.panelLogDownload(interaction, "bot")

    @discord.ui.button(label="마크 파일", emoji="⬇️", style=discord.ButtonStyle.secondary, row=2)
    async def serverDownload(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.controller.panelLogDownload(interaction, "server")
