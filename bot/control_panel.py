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


class QuickActionModal(discord.ui.Modal):
    """Shared error handling for the few quick actions that need typed input."""

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        message = f"❌ {describeError(error)}"
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


# ── 한 메시지 안 페이지 이동 (#58) ─────────────────────────────────
# 예전에는 버튼을 누를 때마다 새 ephemeral 메시지를 보내 채팅이 계속 쌓였습니다.
# 이제 하위 패널은 같은 메시지를 edit로 교체하고, 각 패널에 '🏠 홈' 버튼을 두어
# 되돌아갑니다. 느린 조회는 먼저 로딩 문구로 교체한 뒤 결과로 다시 편집합니다.


async def replaceScreen(
    interaction: discord.Interaction,
    *,
    content=None,
    embed=None,
    view: discord.ui.View | None = None,
):
    """현재 메시지를 새 화면으로 교체합니다(첫 응답이면 edit_message)."""
    if interaction.response.is_done():
        await interaction.edit_original_response(content=content, embed=embed, view=view)
    else:
        await interaction.response.edit_message(content=content, embed=embed, view=view)


async def replaceWithLoadingEmbed(interaction, controller, ownerId, builder):
    """느린 조회: 먼저 로딩 문구로 교체(3초 응답 한도 회피)한 뒤 결과로 재편집.

    builder는 embed를 반환하는 코루틴입니다. 결과 화면에는 '🏠 홈' 버튼만 둡니다.
    """
    await interaction.response.edit_message(content="⏳ 불러오는 중…", embed=None, view=None)
    embed = await builder()
    await interaction.edit_original_response(
        content=None, embed=embed, view=InfoScreenView(controller, ownerId)
    )


async def renderAdminHome(interaction: discord.Interaction, controller, ownerId: int):
    """대시보드 홈으로 같은 메시지에서 되돌아갑니다."""
    embed = await controller.panelOverviewEmbed()
    await replaceScreen(
        interaction,
        content=None,
        embed=embed,
        view=AdminDashboardView(controller, ownerId),
    )


class HomeButton(discord.ui.Button):
    """어느 하위 패널에서든 관리 대시보드 홈으로 돌아갑니다(#58)."""

    def __init__(self, controller, ownerId: int, *, row: int = 4, label: str = "🏠 홈"):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=row)
        self.controller = controller
        self.ownerId = ownerId

    async def callback(self, interaction: discord.Interaction):
        await renderAdminHome(interaction, self.controller, self.ownerId)


class InfoScreenView(OwnerView):
    """읽기 전용 결과 화면 — '🏠 홈' 버튼만 둡니다."""

    def __init__(self, controller, ownerId: int):
        super().__init__(controller, ownerId)
        self.add_item(HomeButton(controller, ownerId, row=0))


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
            await replaceScreen(
                interaction,
                content="현재 접속 중인 플레이어가 없습니다.",
                embed=None,
                view=InfoScreenView(self.controller, self.ownerId),
            )
            return
        view = PlayerPanelView(self.controller, self.ownerId, players)
        await replaceScreen(
            interaction, content="조회할 플레이어를 선택하세요.", embed=None, view=view
        )

    @discord.ui.button(label="서버 제어", emoji="🎛️", style=discord.ButtonStyle.primary, row=0)
    async def service(self, interaction: discord.Interaction, button: discord.ui.Button):
        await replaceScreen(
            interaction,
            content="실행할 서버 작업을 선택하세요. 정지와 재시작은 한 번 더 확인합니다.",
            embed=None,
            view=ServerActionsView(self.controller, self.ownerId),
        )

    @discord.ui.button(label="백업", emoji="💾", style=discord.ButtonStyle.success, row=0)
    async def backups(self, interaction: discord.Interaction, button: discord.ui.Button):
        backups = await self.controller.panelBackups()
        settings = await self.controller.panelBackupSettings()
        embed = await self.controller.panelBackupEmbed()
        await replaceScreen(
            interaction,
            content=None,
            embed=embed,
            view=BackupPanelView(self.controller, self.ownerId, backups, settings),
        )

    @discord.ui.button(label="빠른 명령", emoji="⚡", style=discord.ButtonStyle.danger, row=0)
    async def quickCommands(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 기존 '긴급 복구'를 흡수한 월드 빠른 명령. 플레이어 대상 명령
        # (아이템·효과·TP 등)은 '접속자 관리'에서 접속자를 고른 뒤 사용합니다.
        # 첫 열기에서 서버 버전이 지원하는 게임룰을 조회해(#59) 미지원
        # 버튼을 비활성화합니다. 조회 결과는 캐시됩니다.
        supported = await self.controller.probeSupportedGamerules()
        await replaceScreen(
            interaction,
            content="시간·날씨·난이도·게임룰·스폰을 버튼으로 바꿉니다. 서버 상태가 즉시 바뀝니다.",
            embed=None,
            view=WorldCommandsView(self.controller, self.ownerId, supported),
        )

    @discord.ui.button(label="상태 진단", emoji="🩺", style=discord.ButtonStyle.secondary, row=1)
    async def health(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.controller.panelHealthEmbed()
        await replaceScreen(
            interaction,
            content=None,
            embed=embed,
            view=InfoScreenView(self.controller, self.ownerId),
        )

    @discord.ui.button(label="친구 계정", emoji="👤", style=discord.ButtonStyle.secondary, row=1)
    async def links(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.controller.panelOpenLinkAdmin(interaction)

    @discord.ui.button(label="관리 도움말", emoji="❓", style=discord.ButtonStyle.primary, row=1)
    async def help(self, interaction: discord.Interaction, button: discord.ui.Button):
        await replaceScreen(
            interaction,
            content=None,
            embed=self.controller.panelHelpEmbed(),
            view=InfoScreenView(self.controller, self.ownerId),
        )

    @discord.ui.button(label="더보기", emoji="🧰", style=discord.ButtonStyle.secondary, row=1)
    async def more(self, interaction: discord.Interaction, button: discord.ui.Button):
        await replaceScreen(
            interaction,
            content="자주 쓰지 않는 도구와 설정입니다.",
            embed=None,
            view=MoreToolsView(self.controller, self.ownerId),
        )


class MoreToolsView(OwnerView):
    """Second-tier dashboard tools that are useful but not everyday actions."""

    def __init__(self, controller, ownerId: int, timeout: float = 600):
        super().__init__(controller, ownerId, timeout)
        self.add_item(HomeButton(controller, ownerId, row=2))

    async def _tuningEmbed(self):
        warnings, embed = await self.controller._collectPerformanceWarnings()
        if warnings:
            embed.add_field(
                name="경고",
                value="\n".join(f"• {item}" for item in warnings)[:1000],
                inline=False,
            )
        return embed

    @discord.ui.button(label="성능 상세", emoji="📊", style=discord.ButtonStyle.secondary, row=0)
    async def performance(self, interaction: discord.Interaction, button: discord.ui.Button):
        await replaceWithLoadingEmbed(
            interaction, self.controller, self.ownerId, self.controller.panelMetricsEmbed
        )

    @discord.ui.button(label="렉 원인", emoji="🧰", style=discord.ButtonStyle.secondary, row=0)
    async def tuning(self, interaction: discord.Interaction, button: discord.ui.Button):
        await replaceWithLoadingEmbed(
            interaction, self.controller, self.ownerId, self._tuningEmbed
        )

    @discord.ui.button(label="로그", emoji="📄", style=discord.ButtonStyle.secondary, row=0)
    async def logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await replaceScreen(
            interaction,
            content="확인할 로그를 선택하세요.",
            embed=None,
            view=LogPanelView(self.controller, self.ownerId),
        )

    @discord.ui.button(label="저장공간", emoji="💽", style=discord.ButtonStyle.secondary, row=0)
    async def storage(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.controller.panelStorageEmbed()
        await replaceScreen(
            interaction,
            content=None,
            embed=embed,
            view=InfoScreenView(self.controller, self.ownerId),
        )

    @discord.ui.button(label="월드", emoji="🌍", style=discord.ButtonStyle.secondary, row=1)
    async def worlds(self, interaction: discord.Interaction, button: discord.ui.Button):
        worlds = await self.controller.panelWorlds()
        await replaceScreen(
            interaction,
            content="가져온 월드를 선택하세요. 새 파일은 `/업로드 월드`로 추가합니다.",
            embed=None,
            view=WorldPanelView(self.controller, self.ownerId, worlds),
        )

    @discord.ui.button(label="업데이트", emoji="⬆️", style=discord.ButtonStyle.secondary, row=1)
    async def updates(self, interaction: discord.Interaction, button: discord.ui.Button):
        await replaceScreen(
            interaction,
            content="Release 확인과 최근 설치 결과를 조회합니다. ZIP은 `/업로드 업데이트`를 사용하세요.",
            embed=None,
            view=UpdatePanelView(self.controller, self.ownerId),
        )

    @discord.ui.button(label="고급 도구", emoji="⚙️", style=discord.ButtonStyle.secondary, row=1)
    async def advanced(self, interaction: discord.Interaction, button: discord.ui.Button):
        await replaceScreen(
            interaction,
            content=(
                "게임 공지, 인게임 명령어(마인크래프트 콘솔 명령 직접 실행), "
                "접속 허용목록과 감사 기록입니다."
            ),
            embed=None,
            view=AdvancedPanelView(self.controller, self.ownerId),
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


class DifficultySelect(discord.ui.Select):
    """난이도 4단계 — 고르는 즉시 적용됩니다."""

    def __init__(self, controller):
        self.controller = controller
        emojis = {"peaceful": "🕊️", "easy": "🙂", "normal": "⚖️", "hard": "🔥"}
        options = [
            discord.SelectOption(label=f"난이도: {label}", value=key, emoji=emojis[key])
            for key, label in DIFFICULTIES.items()
        ]
        super().__init__(placeholder="난이도 변경", min_values=1, max_values=1, options=options, row=2)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelSetDifficulty(interaction, self.values[0])


class SpawnCoordsModal(QuickActionModal):
    """예외적으로 좌표를 직접 입력해 월드 스폰을 지정할 때만 씁니다."""

    def __init__(self, controller):
        super().__init__(title="월드 스폰 좌표 직접 입력")
        self.controller = controller
        self.x = discord.ui.TextInput(label="X", max_length=9, placeholder="예: 120")
        self.y = discord.ui.TextInput(label="Y", max_length=5, placeholder="예: 64")
        self.z = discord.ui.TextInput(label="Z", max_length=9, placeholder="예: -35")
        self.add_item(self.x)
        self.add_item(self.y)
        self.add_item(self.z)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelSetSpawnCoords(
            interaction, self.x.value, self.y.value, self.z.value
        )


class SpawnPlayerSelect(discord.ui.Select):
    """접속자가 서 있는 자리를 월드 스폰으로 — 고르는 즉시 지정됩니다."""

    def __init__(self, controller, players: list[str]):
        self.controller = controller
        options = [
            discord.SelectOption(label=f"{name} 위치로 지정", value=name, emoji="🧍")
            for name in players[:25]
        ]
        super().__init__(
            placeholder="이 접속자가 서 있는 자리로 스폰 지정",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelSetSpawnFromPlayer(interaction, self.values[0])


class SpawnSetView(OwnerView):
    """월드 스폰 지정 — 죽었을 때 리스폰과 /도구 스폰 귀환이 함께 바뀝니다."""

    def __init__(self, controller, ownerId: int, players: list[str]):
        super().__init__(controller, ownerId, timeout=300)
        if players:
            self.add_item(SpawnPlayerSelect(controller, players))

    @discord.ui.button(label="좌표 직접 입력", emoji="⌨️", style=discord.ButtonStyle.secondary, row=1)
    async def coords(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SpawnCoordsModal(self.controller))


class WorldCommandsView(OwnerView):
    """시간·날씨·난이도·게임룰·스폰을 버튼으로 바꾸는 빠른 명령 패널.

    기존 '긴급 복구' 버튼(낮·맑음·평화·드롭템 정리)을 흡수·확장했습니다.
    버튼 → 명령 대응과 게임룰 목록은 bot/quick_commands.py에 있습니다.
    """

    async def _run(self, interaction: discord.Interaction, command: str, message: str, audit: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelWorldCommand(interaction, command, message, audit)

    async def _toggle(self, interaction: discord.Interaction, gameruleKey: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelToggleGamerule(interaction, gameruleKey)

    # ── 1행: 시간·드롭템 ─────────────────────────────────────
    @discord.ui.button(label="낮으로", emoji="☀️", style=discord.ButtonStyle.primary, row=0)
    async def day(self, interaction, button):
        await self._run(interaction, "time set day", "☀️ 시간을 낮으로 바꿨습니다.", "world.day")

    @discord.ui.button(label="밤으로", emoji="🌙", style=discord.ButtonStyle.secondary, row=0)
    async def night(self, interaction, button):
        await self._run(interaction, "time set night", "🌙 시간을 밤으로 바꿨습니다.", "world.night")

    @discord.ui.button(label="시간 흐름", emoji="⏰", style=discord.ButtonStyle.secondary, row=0)
    async def daylightCycle(self, interaction, button):
        await self._toggle(interaction, "doDaylightCycle")

    @discord.ui.button(label="드롭템 정리", emoji="🧹", style=discord.ButtonStyle.danger, row=0)
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

    # ── 2행: 날씨 ────────────────────────────────────────────
    @discord.ui.button(label="맑음", emoji="🌤️", style=discord.ButtonStyle.primary, row=1)
    async def clearWeather(self, interaction, button):
        await self._run(interaction, "weather clear", "🌤️ 날씨를 맑게 바꿨습니다.", "world.weather")

    @discord.ui.button(label="비", emoji="🌧️", style=discord.ButtonStyle.secondary, row=1)
    async def rain(self, interaction, button):
        await self._run(interaction, "weather rain", "🌧️ 비를 내리게 했습니다.", "world.weather")

    @discord.ui.button(label="뇌우", emoji="⛈️", style=discord.ButtonStyle.secondary, row=1)
    async def thunder(self, interaction, button):
        await self._run(interaction, "weather thunder", "⛈️ 뇌우를 내리게 했습니다.", "world.weather")

    @discord.ui.button(label="날씨 변화", emoji="🔒", style=discord.ButtonStyle.secondary, row=1)
    async def weatherCycle(self, interaction, button):
        await self._toggle(interaction, "doWeatherCycle")

    # 버튼 콜백 attr 이름 → 게임룰 키(#59 미지원 버튼 비활성화에 사용).
    _GAMERULE_BUTTONS = {
        "daylightCycle": "doDaylightCycle",
        "weatherCycle": "doWeatherCycle",
        "keepInventory": "keepInventory",
        "mobGriefing": "mobGriefing",
        "immediateRespawn": "doImmediateRespawn",
        "naturalRegeneration": "naturalRegeneration",
        "showDaysPlayed": "showDaysPlayed",
    }

    # ── 3행: 난이도 드롭다운은 __init__에서 추가 ─────────────
    def __init__(
        self,
        controller,
        ownerId: int,
        supportedGamerules: dict[str, bool] | None = None,
        timeout: float = 600,
    ):
        super().__init__(controller, ownerId, timeout)
        self.add_item(DifficultySelect(controller))
        self.add_item(HomeButton(controller, ownerId, row=3))
        # 이 서버 버전에 없는 게임룰 버튼은 눌러도 실패하므로 회색 처리.
        # 프로브가 판단하지 못한 키(True/미기록)는 그대로 살려 둡니다.
        for attrName, gameruleKey in self._GAMERULE_BUTTONS.items():
            if (supportedGamerules or {}).get(gameruleKey, True):
                continue
            buttonItem = getattr(self, attrName, None)
            if isinstance(buttonItem, discord.ui.Button):
                buttonItem.disabled = True
                buttonItem.label = f"{buttonItem.label} (버전 미지원)"

    # ── 4행: 게임룰 토글 ─────────────────────────────────────
    @discord.ui.button(label="아이템 유지", emoji="🎒", style=discord.ButtonStyle.secondary, row=3)
    async def keepInventory(self, interaction, button):
        await self._toggle(interaction, "keepInventory")

    @discord.ui.button(label="몹 그리핑", emoji="💥", style=discord.ButtonStyle.secondary, row=3)
    async def mobGriefing(self, interaction, button):
        await self._toggle(interaction, "mobGriefing")

    @discord.ui.button(label="즉시 리스폰", emoji="⚡", style=discord.ButtonStyle.secondary, row=3)
    async def immediateRespawn(self, interaction, button):
        await self._toggle(interaction, "doImmediateRespawn")

    # ── 5행: 게임룰 토글 + 스폰 지정 ─────────────────────────
    @discord.ui.button(label="자연 재생", emoji="♻️", style=discord.ButtonStyle.secondary, row=4)
    async def naturalRegeneration(self, interaction, button):
        await self._toggle(interaction, "naturalRegeneration")

    @discord.ui.button(label="플레이 일수", emoji="📅", style=discord.ButtonStyle.secondary, row=4)
    async def showDaysPlayed(self, interaction, button):
        await self._toggle(interaction, "showDaysPlayed")

    @discord.ui.button(label="스폰 지정", emoji="📍", style=discord.ButtonStyle.success, row=4)
    async def setSpawn(self, interaction: discord.Interaction, button: discord.ui.Button):
        players = await self.controller.panelOnlinePlayers()
        await interaction.response.send_message(
            "월드 스폰을 지정합니다. 죽었을 때 리스폰(침대 없을 때)과 "
            "`/도구`의 스폰 귀환이 모두 이 지점으로 바뀝니다.",
            view=SpawnSetView(self.controller, self.ownerId, players),
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

    def __init__(self, controller, ownerId: int, timeout: float = 600):
        super().__init__(controller, ownerId, timeout)
        self.add_item(HomeButton(controller, ownerId, row=1))

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
        self.level = discord.ui.TextInput(
            label="강도 (1~10, 비우면 1)", required=False, max_length=2
        )
        self.particles = discord.ui.TextInput(
            label="거품 파티클 표시? (y 입력 시 표시, 기본 숨김)",
            required=False,
            max_length=1,
        )
        self.add_item(self.effectId)
        self.add_item(self.seconds)
        self.add_item(self.level)
        self.add_item(self.particles)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        secondsText = (self.seconds.value or "").strip()
        if secondsText and not secondsText.isdigit():
            raise ValueError("지속 시간은 숫자(초)로 입력하세요.")
        levelText = (self.level.value or "").strip()
        if levelText and (not levelText.isdigit() or not 1 <= int(levelText) <= 10):
            raise ValueError("강도는 1~10 사이의 숫자로 입력하세요.")
        showParticles = (self.particles.value or "").strip().lower() == "y"
        await self.controller.panelApplyEffect(
            interaction,
            self.playerName,
            self.effectId.value,
            int(secondsText) if secondsText else 300,
            (int(levelText) - 1) if levelText else 0,
            hideParticles=not showParticles,
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


class ForceEnchantModal(QuickActionModal):
    """제한 없는 강제 인챈트(예: 곡괭이에 날카로움, 날카로움 20). #62."""

    def __init__(self, controller, playerName: str):
        super().__init__(title=f"강제 인챈트 — {playerName}"[:45])
        self.controller = controller
        self.playerName = playerName
        self.enchantId = discord.ui.TextInput(
            label="인챈트 ID (영어)", placeholder="예: sharpness, efficiency", max_length=64
        )
        self.level = discord.ui.TextInput(
            label="레벨 (1~255, 비우면 1)", required=False, max_length=3
        )
        self.add_item(self.enchantId)
        self.add_item(self.level)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        levelText = (self.level.value or "").strip()
        if levelText and (not levelText.isdigit() or not 1 <= int(levelText) <= 255):
            raise ValueError("레벨은 1~255 사이의 숫자로 입력하세요.")
        await self.controller.panelForceEnchant(
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
        options.append(
            discord.SelectOption(
                label="강제 인챈트 (제한 없음)…",
                value="__force__",
                emoji="⚡",
                description="곡괭이에 날카로움, 날카로움 20 등 바닐라 제한 무시",
            )
        )
        super().__init__(placeholder="부여할 인챈트 선택", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        if choice == "__custom__":
            await interaction.response.send_modal(
                CustomEnchantModal(self.controller, self.playerName)
            )
            return
        if choice == "__force__":
            await interaction.response.send_modal(
                ForceEnchantModal(self.controller, self.playerName)
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


class InvincibilityPanelView(OwnerView):
    """무적(#75) 지속 시간 선택과 해제를 버튼으로 제공합니다.

    실제 효과 조합은 bot/quick_commands.py의 buildInvincibilityCommands가
    담당하며, 해제는 그 세트로 건 효과만 골라 지웁니다.
    """

    def __init__(self, controller, ownerId: int, playerName: str):
        super().__init__(controller, ownerId, timeout=300)
        self.playerName = playerName

    async def _grant(self, interaction: discord.Interaction, seconds: int):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelInvincible(interaction, self.playerName, seconds)

    @discord.ui.button(label="30초", emoji="🛡️", style=discord.ButtonStyle.primary, row=0)
    async def short(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._grant(interaction, 30)

    @discord.ui.button(label="5분", emoji="🛡️", style=discord.ButtonStyle.primary, row=0)
    async def medium(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._grant(interaction, 300)

    @discord.ui.button(label="30분", emoji="🛡️", style=discord.ButtonStyle.primary, row=0)
    async def long(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._grant(interaction, 1800)

    @discord.ui.button(label="해제", emoji="⚔️", style=discord.ButtonStyle.danger, row=0)
    async def clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelMortal(interaction, self.playerName)


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
        self.add_item(HomeButton(controller, ownerId, row=4))

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

    @discord.ui.button(label="킬·데스", emoji="📊", style=discord.ButtonStyle.secondary, row=1)
    async def records(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show(interaction, "records")

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

    @discord.ui.button(label="무적", emoji="🛡️", style=discord.ButtonStyle.primary, row=3)
    async def invincible(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"**{self.selectedPlayer}** 의 무적 지속 시간을 선택하세요.",
            view=InvincibilityPanelView(self.controller, self.ownerId, self.selectedPlayer),
            ephemeral=True,
        )

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
        self.add_item(HomeButton(controller, ownerId, row=3))

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
        self.add_item(HomeButton(controller, ownerId, row=2))

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

    def __init__(self, controller, ownerId: int, timeout: float = 600):
        super().__init__(controller, ownerId, timeout)
        self.add_item(HomeButton(controller, ownerId, row=1))

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

    def __init__(self, controller, ownerId: int, timeout: float = 600):
        super().__init__(controller, ownerId, timeout)
        self.add_item(HomeButton(controller, ownerId, row=3))

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

    def __init__(self, controller, ownerId: int, timeout: float = 600):
        super().__init__(controller, ownerId, timeout)
        self.add_item(HomeButton(controller, ownerId, row=3))

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
