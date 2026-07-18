"""Button-first Discord administration views for routine server operations."""

import discord

from bot.config import cfg
from bot.error_text import describeError
from bot.i18n import t
from bot.quick_commands import (
    COMMON_EFFECTS,
    COMMON_ENCHANTS,
    DIFFICULTIES,
    GAMERULES,
    SPECIAL_MOB_PRESETS,
    VILLAGER_GOODS,
)


# 만료된 패널의 버튼을 누르면 디스코드가 "상호작용 실패"만 띄우고 이유를
# 알려주지 않습니다. 만료 시점에 버튼을 회색 처리하고 다시 여는 방법을
# 안내해, 죽은 버튼을 눌러 보는 일이 없게 합니다.
PANEL_EXPIRED_NOTICE = "⏰ 패널이 만료되었습니다. `/admin` 을 다시 실행해 새 패널을 여세요."


class OwnerView(discord.ui.View):
    """Restrict ephemeral controls to the administrator who opened them."""

    expiredNotice = PANEL_EXPIRED_NOTICE

    def __init__(self, controller, ownerId: int, timeout: float = 600):
        super().__init__(timeout=timeout)
        self.controller = controller
        self.ownerId = ownerId
        # 만료 시 자기 메시지를 편집할 수 있게 sendScreen/replaceScreen이 채웁니다.
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Reject shared-message component use by anyone outside the allowlist."""
        if interaction.user.id == self.ownerId and interaction.user.id in cfg.admin_ids:
            return True
        await interaction.response.send_message(
            "⛔ 이 관리 패널을 사용할 권한이 없습니다.", ephemeral=True
        )
        return False

    async def on_timeout(self) -> None:
        """Grey out expired buttons and say how to reopen the panel."""
        for item in self.children:
            item.disabled = True
        if self.message is None:
            return
        try:
            await self.message.edit(content=self.expiredNotice, view=self)
        except discord.HTTPException:
            pass

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

    def __init__(self, *, panelView: discord.ui.View | None = None, **kwargs):
        super().__init__(**kwargs)
        # 드롭다운에서 연 모달이면, 제출 시 그 드롭다운의 선택 강조를 지울 수
        # 있게 패널 뷰를 기억해 둡니다(resetSelectHighlight 참고).
        self.panelView = panelView

    async def acknowledge(self, interaction: discord.Interaction) -> None:
        """첫 응답: 드롭다운에서 열렸으면 선택 강조를 지우고, 아니면 defer."""
        if self.panelView is not None:
            await resetSelectHighlight(interaction, self.panelView)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)

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
        message = await interaction.edit_original_response(
            content=content, embed=embed, view=view
        )
    else:
        await interaction.response.edit_message(content=content, embed=embed, view=view)
        message = interaction.message
    # 새 화면이 만료될 때 스스로 버튼을 비활성화할 수 있게 메시지를 연결합니다.
    if view is not None:
        view.message = message


async def sendScreen(
    interaction: discord.Interaction,
    *,
    content=None,
    embed=None,
    view: discord.ui.View | None = None,
):
    """새 ephemeral 메시지로 화면을 열고, 만료 처리를 위해 메시지를 연결합니다."""
    await interaction.response.send_message(
        content=content, embed=embed, view=view, ephemeral=True
    )
    if view is not None:
        try:
            view.message = await interaction.original_response()
        except discord.HTTPException:
            pass


async def resetSelectHighlight(
    interaction: discord.Interaction, view: discord.ui.View
) -> None:
    """드롭다운의 선택 강조를 지워 같은 옵션을 연달아 다시 고를 수 있게 합니다.

    디스코드 클라이언트는 이미 선택돼 강조된 옵션을 다시 눌러도 새 상호작용을
    보내지 않습니다. 그래서 예전에는 '신속'을 두 번 연속 적용하려면 다른
    옵션을 한 번 거쳐야 했습니다. 매 선택 직후 같은 화면을 다시 그려(첫
    응답을 edit_message로 사용) 강조를 지우면 같은 효과·인챈트를 바로 다시
    선택할 수 있습니다.
    """
    await interaction.response.edit_message(view=view)


async def replaceWithLoadingEmbed(
    interaction, controller, ownerId, builder, *, backRenderer=None, backLabel="↩️ 뒤로"
):
    """느린 조회: 먼저 로딩 문구로 교체(3초 응답 한도 회피)한 뒤 결과로 재편집.

    builder는 embed를 반환하는 코루틴입니다. 결과 화면에는 상위 화면
    '뒤로'(선택)와 '🏠 홈' 버튼을 둡니다.
    """
    await interaction.response.edit_message(content="⏳ 불러오는 중…", embed=None, view=None)
    embed = await builder()
    view = InfoScreenView(
        controller, ownerId, backRenderer=backRenderer, backLabel=backLabel
    )
    view.message = await interaction.edit_original_response(
        content=None, embed=embed, view=view
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


# ── 구역별 화면 렌더러 ──────────────────────────────────────────
# 하위 화면의 '↩️ 뒤로' 버튼이 상위 구역을 같은 메시지에 다시 그릴 때 쓰는
# 코루틴들입니다. 대시보드 버튼과 뒤로 버튼이 똑같은 렌더러를 공유해,
# 어느 경로로 들어와도 화면이 동일합니다.


async def renderPlayerPanel(
    interaction: discord.Interaction, controller, ownerId: int, selected: str | None = None
):
    """접속자 관리 화면. selected 가 아직 접속 중이면 선택을 유지합니다."""
    players = await controller.panelOnlinePlayers()
    if not players:
        await replaceScreen(
            interaction,
            content="현재 접속 중인 플레이어가 없습니다.",
            embed=None,
            view=InfoScreenView(controller, ownerId),
        )
        return
    view = PlayerPanelView(controller, ownerId, players)
    if selected in players:
        view.selectedPlayer = selected
    await replaceScreen(
        interaction,
        content=(
            f"선택됨: **{view.selectedPlayer}** — 아래 조회·조작 버튼이 이 플레이어에게 적용됩니다."
            if selected in players
            else "조회할 플레이어를 선택하세요."
        ),
        embed=None,
        view=view,
    )


async def renderWorldCommands(interaction: discord.Interaction, controller, ownerId: int):
    """빠른 명령(시간·날씨·게임룰·스폰) 화면."""
    supported = await controller.probeSupportedGamerules()
    await replaceScreen(
        interaction,
        content="시간·날씨·난이도·게임룰·스폰을 버튼으로 바꿉니다. 서버 상태가 즉시 바뀝니다.",
        embed=None,
        view=WorldCommandsView(controller, ownerId, supported),
    )


async def renderLogPanel(interaction: discord.Interaction, controller, ownerId: int):
    """로그 선택 화면."""
    await replaceScreen(
        interaction,
        content="확인할 로그를 선택하세요.",
        embed=None,
        view=LogPanelView(controller, ownerId),
    )


async def renderMoreTools(interaction: discord.Interaction, controller, ownerId: int):
    """더보기(2차 도구) 화면."""
    await replaceScreen(
        interaction,
        content="자주 쓰지 않는 도구와 설정입니다.",
        embed=None,
        view=MoreToolsView(controller, ownerId),
    )


def playerBackRenderer(controller, ownerId: int, playerName: str):
    """선택한 플레이어를 유지한 채 접속자 관리로 돌아가는 렌더러."""

    async def render(interaction: discord.Interaction):
        await renderPlayerPanel(interaction, controller, ownerId, playerName)

    return render


class PlayerSubScreenView(OwnerView):
    """접속자 관리 하위 화면 공통 — '↩️ 접속자 관리'와 '🏠 홈'을 함께 둡니다."""

    def __init__(
        self, controller, ownerId: int, playerName: str, *, navRow: int = 4,
        timeout: float = 300,
    ):
        super().__init__(controller, ownerId, timeout=timeout)
        self.playerName = playerName
        self.add_item(BackButton(
            playerBackRenderer(controller, ownerId, playerName),
            row=navRow,
            label="↩️ 접속자 관리",
        ))
        self.add_item(HomeButton(controller, ownerId, row=navRow))


class HomeButton(discord.ui.Button):
    """어느 하위 패널에서든 관리 대시보드 홈으로 돌아갑니다(#58)."""

    def __init__(self, controller, ownerId: int, *, row: int = 4, label: str = "🏠 홈"):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=row)
        self.controller = controller
        self.ownerId = ownerId

    async def callback(self, interaction: discord.Interaction):
        await renderAdminHome(interaction, self.controller, self.ownerId)


class BackButton(discord.ui.Button):
    """한 단계 위 화면으로 같은 메시지 안에서 돌아갑니다.

    renderer 는 interaction 하나를 받아 상위 화면을 다시 그리는 코루틴
    함수입니다. 홈까지 되돌아가지 않고도 같은 구역을 계속 쓸 수 있게 해,
    '기능 하나 쓰고 나면 /admin 을 다시 쳐야 한다'는 불편을 없앱니다.
    """

    def __init__(self, renderer, *, row: int = 4, label: str = "↩️ 뒤로"):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=row)
        self.renderer = renderer

    async def callback(self, interaction: discord.Interaction):
        await self.renderer(interaction)


class InfoScreenView(OwnerView):
    """읽기 전용 결과 화면 — 상위 화면 '뒤로'(선택)와 '🏠 홈' 버튼."""

    def __init__(
        self,
        controller,
        ownerId: int,
        *,
        backRenderer=None,
        backLabel: str = "↩️ 뒤로",
    ):
        super().__init__(controller, ownerId)
        if backRenderer is not None:
            self.add_item(BackButton(backRenderer, row=0, label=backLabel))
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
        await renderPlayerPanel(interaction, self.controller, self.ownerId)

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
        await renderWorldCommands(interaction, self.controller, self.ownerId)

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

    @discord.ui.button(label="인게임 명령어", emoji="⌨️", style=discord.ButtonStyle.danger, row=1)
    async def rcon(self, interaction: discord.Interaction, button: discord.ui.Button):
        # #79: 원격 치트 콘솔을 대시보드 첫 화면에서 바로 열 수 있게 합니다.
        # 예전에는 더보기 → 고급 도구 → 인게임 명령어로 세 단계를 거쳐야 했습니다.
        # (고급 도구 화면에도 같은 버튼이 그대로 남아 있습니다.)
        await interaction.response.send_modal(
            TextActionModal(
                self.controller,
                "인게임 명령어 실행",
                "마인크래프트 콘솔 명령 (/ 없이 입력)",
                "mc",
                "예: time set day, gamemode creative 닉네임",
            )
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

    def _backToMore(self):
        async def render(interaction: discord.Interaction):
            await renderMoreTools(interaction, self.controller, self.ownerId)

        return render

    @discord.ui.button(label="성능 상세", emoji="📊", style=discord.ButtonStyle.secondary, row=0)
    async def performance(self, interaction: discord.Interaction, button: discord.ui.Button):
        await replaceWithLoadingEmbed(
            interaction, self.controller, self.ownerId,
            self.controller.panelMetricsEmbed,
            backRenderer=self._backToMore(), backLabel="↩️ 더보기",
        )

    @discord.ui.button(label="렉 원인", emoji="🧰", style=discord.ButtonStyle.secondary, row=0)
    async def tuning(self, interaction: discord.Interaction, button: discord.ui.Button):
        await replaceWithLoadingEmbed(
            interaction, self.controller, self.ownerId, self._tuningEmbed,
            backRenderer=self._backToMore(), backLabel="↩️ 더보기",
        )

    @discord.ui.button(label="로그", emoji="📄", style=discord.ButtonStyle.secondary, row=0)
    async def logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await renderLogPanel(interaction, self.controller, self.ownerId)

    @discord.ui.button(label="저장공간", emoji="💽", style=discord.ButtonStyle.secondary, row=0)
    async def storage(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.controller.panelStorageEmbed()
        await replaceScreen(
            interaction,
            content=None,
            embed=embed,
            view=InfoScreenView(
                self.controller, self.ownerId,
                backRenderer=self._backToMore(), backLabel="↩️ 더보기",
            ),
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

        async def back(interaction: discord.Interaction):
            await renderWorldCommands(interaction, controller, ownerId)

        self.add_item(BackButton(back, row=2, label="↩️ 빠른 명령"))
        self.add_item(HomeButton(controller, ownerId, row=2))

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
        await sendScreen(
            interaction,
            content=t("incident_clear_drops_prompt"),
            view=ConfirmIncidentView(
                self.controller,
                self.ownerId,
                "kill @e[type=item]",
                "incident_kill_items",
            ),
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
        await replaceScreen(
            interaction,
            content=(
                "월드 스폰을 지정합니다. 죽었을 때 리스폰(침대 없을 때)과 "
                "`/도구`의 스폰 귀환이 모두 이 지점으로 바뀝니다."
            ),
            embed=None,
            view=SpawnSetView(self.controller, self.ownerId, players),
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
        await sendScreen(
            interaction,
            content=f"마인크래프트 서버를 **{koreanName}**할까요?",
            view=ConfirmServiceView(self.controller, self.ownerId, action),
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

    def __init__(self, controller, playerName: str, *, panelView=None):
        super().__init__(
            title=f"포션 효과 직접 입력 — {playerName}"[:45], panelView=panelView
        )
        self.controller = controller
        self.playerName = playerName
        self.effectId = discord.ui.TextInput(
            label="효과 (한글 별칭 또는 영어 ID)",
            placeholder="예: 재생, 신속, speed, absorption",
            max_length=64,
        )
        self.seconds = discord.ui.TextInput(
            label="지속 시간(초, 비우면 300)", required=False, max_length=7
        )
        self.level = discord.ui.TextInput(
            label="강도 (1~256, 비우면 1)", required=False, max_length=3
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
        await self.acknowledge(interaction)
        secondsText = (self.seconds.value or "").strip()
        if secondsText and not secondsText.isdigit():
            raise ValueError("지속 시간은 숫자(초)로 입력하세요.")
        levelText = (self.level.value or "").strip()
        # 강도는 게임 실제 한계까지 허용합니다(#증폭치는 바이트라 최대 255 =
        # 256단계). buildEffectCommand가 증폭치를 0~255로 다시 clamp합니다.
        if levelText and (not levelText.isdigit() or not 1 <= int(levelText) <= 256):
            raise ValueError("강도는 1~256 사이의 숫자로 입력하세요.")
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

    def __init__(self, controller, playerName: str, *, panelView=None):
        super().__init__(
            title=f"인챈트 직접 입력 — {playerName}"[:45], panelView=panelView
        )
        self.controller = controller
        self.playerName = playerName
        self.enchantId = discord.ui.TextInput(
            label="인챈트 (한글 별칭 또는 영어 ID)",
            placeholder="예: 넉백, 가시, knockback, thorns",
            max_length=64,
        )
        self.level = discord.ui.TextInput(
            label="레벨 (비우면 1)", required=False, max_length=3
        )
        self.add_item(self.enchantId)
        self.add_item(self.level)

    async def on_submit(self, interaction: discord.Interaction):
        await self.acknowledge(interaction)
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

    def __init__(self, controller, playerName: str, *, panelView=None):
        super().__init__(
            title=f"강제 인챈트 — {playerName}"[:45], panelView=panelView
        )
        self.controller = controller
        self.playerName = playerName
        self.enchantId = discord.ui.TextInput(
            label="인챈트 (한글 별칭 또는 영어 ID)",
            placeholder="예: 날카로움, 효율, sharpness, efficiency",
            max_length=64,
        )
        self.level = discord.ui.TextInput(
            label="레벨 (1~255, 비우면 1)", required=False, max_length=3
        )
        self.add_item(self.enchantId)
        self.add_item(self.level)

    async def on_submit(self, interaction: discord.Interaction):
        await self.acknowledge(interaction)
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
                CustomEffectModal(self.controller, self.playerName, panelView=self.view)
            )
            return
        await resetSelectHighlight(interaction, self.view)
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


class EffectPanelView(PlayerSubScreenView):
    def __init__(self, controller, ownerId: int, playerName: str):
        super().__init__(controller, ownerId, playerName)
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
                CustomEnchantModal(self.controller, self.playerName, panelView=self.view)
            )
            return
        if choice == "__force__":
            await interaction.response.send_modal(
                ForceEnchantModal(self.controller, self.playerName, panelView=self.view)
            )
            return
        await resetSelectHighlight(interaction, self.view)
        enchantId, level = choice.rsplit(":", 1)
        await self.controller.panelEnchant(
            interaction, self.playerName, enchantId, int(level)
        )


class EnchantPanelView(PlayerSubScreenView):
    def __init__(self, controller, ownerId: int, playerName: str):
        super().__init__(controller, ownerId, playerName)
        self.add_item(EnchantSelect(controller, playerName))


class GamemodePanelView(PlayerSubScreenView):
    """선택한 접속자의 게임모드를 버튼 한 번으로 변경."""

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


class TeleportPanelView(PlayerSubScreenView):
    """접속자·좌표북·스폰 세 종류의 순간이동 목적지를 한 화면에."""

    def __init__(self, controller, ownerId: int, playerName: str, otherPlayers, places):
        super().__init__(controller, ownerId, playerName)
        if otherPlayers:
            self.add_item(TeleportTargetSelect(controller, playerName, otherPlayers))
        if places:
            self.add_item(TeleportPlaceSelect(controller, playerName, places))

    @discord.ui.button(label="스폰으로", emoji="🏠", style=discord.ButtonStyle.primary, row=2)
    async def toSpawn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelTeleportToSpawn(interaction, self.playerName)


class InvincibilityPanelView(PlayerSubScreenView):
    """무적(#75) 지속 시간 선택과 해제를 버튼으로 제공합니다.

    실제 효과 조합은 bot/quick_commands.py의 buildInvincibilityCommands가
    담당하며, 해제는 그 세트로 건 효과만 골라 지웁니다.
    """

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


class SpecialMobSelect(discord.ui.Select):
    """특수 몹 프리셋 드롭다운 — 같은 프리셋을 연달아 또 부를 수 있습니다."""

    def __init__(self, controller, playerName: str):
        self.controller = controller
        self.playerName = playerName
        options = [
            discord.SelectOption(label=label, value=key, emoji="👹")
            for key, label in SPECIAL_MOB_PRESETS
        ]
        super().__init__(
            placeholder="특수 몹 선택 (안전한 자리에 소환)",
            min_values=1, max_values=1, options=options, row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        await resetSelectHighlight(interaction, self.view)
        await self.controller.panelSpecialMob(interaction, self.playerName, choice)


class VillagerGoodSelect(discord.ui.Select):
    """주민이 팔 상품 드롭다운 — 고르면 가격 입력 모달이 뜹니다."""

    def __init__(self, controller, playerName: str):
        self.controller = controller
        self.playerName = playerName
        options = [
            discord.SelectOption(label=label, value=good)
            for good, _prof, label, _price in VILLAGER_GOODS
        ]
        super().__init__(
            placeholder="주민 소환 — 팔 상품 선택",
            min_values=1, max_values=1, options=options, row=2,
        )

    async def callback(self, interaction: discord.Interaction):
        good, profession, label, defaultPrice = next(
            (g, p, l, pr) for g, p, l, pr in VILLAGER_GOODS if g == self.values[0]
        )
        await interaction.response.send_modal(
            VillagerPriceModal(
                self.controller, self.playerName, good, profession, label,
                defaultPrice, panelView=self.view,
            )
        )


class VillagerPriceModal(QuickActionModal):
    """주민 거래 가격(에메랄드)을 정하고 소환합니다."""

    def __init__(
        self, controller, playerName: str, good: str, profession: str,
        label: str, defaultPrice: int, *, panelView=None,
    ):
        super().__init__(title=f"주민 가격 — {label}"[:45], panelView=panelView)
        self.controller = controller
        self.playerName = playerName
        self.good = good
        self.profession = profession
        self.label = label
        self.defaultPrice = defaultPrice
        self.price = discord.ui.TextInput(
            label=f"에메랄드 가격 (1~64, 비우면 {defaultPrice})",
            required=False, max_length=2,
        )
        self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction):
        await self.acknowledge(interaction)
        priceText = (self.price.value or "").strip()
        if priceText and not priceText.isdigit():
            raise ValueError("가격은 숫자로 입력하세요.")
        price = int(priceText) if priceText else self.defaultPrice
        await self.controller.panelSummonVillager(
            interaction, self.playerName, self.profession, self.good, price, self.label
        )


class SummonPanelView(PlayerSubScreenView):
    """연출·소환 모음 — 몹은 전부 벽에 안 끼는 안전한 자리에 소환됩니다.

    번개는 비/뇌우일 때만, 충전 크리퍼는 뇌우 중 주변에 실제 크리퍼가 있을
    때만 동작합니다(그 판정은 controller/플러그인이 합니다).
    """

    def __init__(self, controller, ownerId: int, playerName: str):
        super().__init__(controller, ownerId, playerName)
        self.add_item(SpecialMobSelect(controller, playerName))
        self.add_item(VillagerGoodSelect(controller, playerName))

    @discord.ui.button(label="크리퍼 소환", emoji="💥", style=discord.ButtonStyle.secondary, row=0)
    async def creeper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelSummonCreeper(interaction, self.playerName)

    @discord.ui.button(label="충전 크리퍼", emoji="⚡", style=discord.ButtonStyle.secondary, row=0)
    async def chargedCreeper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelChargedCreeper(interaction, self.playerName)

    @discord.ui.button(label="크리퍼 소리", emoji="🔊", style=discord.ButtonStyle.secondary, row=0)
    async def creeperSound(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelCreeperSound(interaction, self.playerName)

    @discord.ui.button(label="번개", emoji="🌩️", style=discord.ButtonStyle.secondary, row=0)
    async def lightning(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelLightning(interaction, self.playerName)


class ConfirmKickView(PlayerSubScreenView):
    """추방 전에 한 번 더 확인합니다."""

    @discord.ui.button(label="추방 확인", emoji="🥾", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # stop() 하지 않아야 실행 후에도 '뒤로/홈' 버튼으로 이동할 수 있습니다.
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelKick(interaction, self.playerName)

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await renderPlayerPanel(
            interaction, self.controller, self.ownerId, self.playerName
        )


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
        # 조회 결과도 같은 메시지에서 보여 주고, '↩️ 접속자 관리'로 바로
        # 되돌아갈 수 있게 합니다 — 새 ephemeral 메시지가 쌓이지 않습니다.
        embed = await self.controller.panelPlayerEmbed(self.selectedPlayer, detailType)
        await replaceScreen(
            interaction,
            content=None,
            embed=embed,
            view=PlayerSubScreenView(self.controller, self.ownerId, self.selectedPlayer),
        )

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
        await replaceScreen(
            interaction,
            content=f"**{self.selectedPlayer}** 에게 적용할 효과를 선택하세요.",
            embed=None,
            view=EffectPanelView(self.controller, self.ownerId, self.selectedPlayer),
        )

    @discord.ui.button(label="인챈트", emoji="🗡️", style=discord.ButtonStyle.primary, row=2)
    async def enchant(self, interaction: discord.Interaction, button: discord.ui.Button):
        await replaceScreen(
            interaction,
            content=f"**{self.selectedPlayer}** 가 들고 있는 아이템에 부여할 인챈트를 선택하세요.",
            embed=None,
            view=EnchantPanelView(self.controller, self.ownerId, self.selectedPlayer),
        )

    @discord.ui.button(label="게임모드", emoji="🎮", style=discord.ButtonStyle.secondary, row=2)
    async def gamemode(self, interaction: discord.Interaction, button: discord.ui.Button):
        await replaceScreen(
            interaction,
            content=f"**{self.selectedPlayer}** 의 게임모드를 선택하세요.",
            embed=None,
            view=GamemodePanelView(self.controller, self.ownerId, self.selectedPlayer),
        )

    @discord.ui.button(label="TP", emoji="🚀", style=discord.ButtonStyle.secondary, row=2)
    async def teleport(self, interaction: discord.Interaction, button: discord.ui.Button):
        otherPlayers = [name for name in self.players if name != self.selectedPlayer]
        places = await self.controller.panelSharedPlaces()
        await replaceScreen(
            interaction,
            content=f"**{self.selectedPlayer}** 를 어디로 이동시킬까요?",
            embed=None,
            view=TeleportPanelView(
                self.controller, self.ownerId, self.selectedPlayer, otherPlayers, places
            ),
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
        await replaceScreen(
            interaction,
            content=f"**{self.selectedPlayer}** 의 무적 지속 시간을 선택하세요.",
            embed=None,
            view=InvincibilityPanelView(self.controller, self.ownerId, self.selectedPlayer),
        )

    @discord.ui.button(label="추방", emoji="🥾", style=discord.ButtonStyle.danger, row=3)
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        await replaceScreen(
            interaction,
            content=f"**{self.selectedPlayer}** 를 서버에서 추방할까요?",
            embed=None,
            view=ConfirmKickView(self.controller, self.ownerId, self.selectedPlayer),
        )

    @discord.ui.button(label="연출·소환", emoji="🎭", style=discord.ButtonStyle.secondary, row=4)
    async def summonMenu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await replaceScreen(
            interaction,
            content=(
                f"**{self.selectedPlayer}** 주변에 소환할 것을 고르세요. "
                "몹은 벽에 안 끼는 안전한 자리에 나타나고, 게임 채팅엔 출력되지 않습니다."
            ),
            embed=None,
            view=SummonPanelView(self.controller, self.ownerId, self.selectedPlayer),
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
        await sendScreen(
            interaction,
            content=f"⚠️ `{self.selectedName}` 백업으로 복구할까요? 현재 월드는 교체됩니다.",
            view=ConfirmLegacyActionView(
                self.controller,
                self.ownerId,
                "backupRestore",
                (self.selectedName, "RESTORE"),
                "백업 복구",
            ),
        )

    @discord.ui.button(label="삭제", emoji="🗑️", style=discord.ButtonStyle.danger, row=2)
    async def delete(self, interaction, button):
        if not self.selectedName:
            await interaction.response.send_message("선택한 백업이 없습니다.", ephemeral=True)
            return
        await sendScreen(
            interaction,
            content=f"⚠️ `{self.selectedName}` 백업을 영구 삭제할까요?",
            view=ConfirmLegacyActionView(
                self.controller,
                self.ownerId,
                "backupDelete",
                (self.selectedName, "DELETE"),
                "백업 삭제",
            ),
        )

    @discord.ui.button(label="정리", emoji="🧹", style=discord.ButtonStyle.secondary, row=2)
    async def prune(self, interaction, button):
        await self.controller.panelLegacyCommand("backupPrune", interaction)

    @discord.ui.button(label="정책 설정", emoji="⚙️", style=discord.ButtonStyle.primary, row=2)
    async def policy(self, interaction, button):
        # 정책 화면은 드롭다운 5개가 5행을 전부 차지해 뒤로 버튼을 둘 수
        # 없으므로, 백업 패널을 남겨 둔 채 별도 메시지로 엽니다.
        await sendScreen(
            interaction,
            content="각 항목을 선택하면 즉시 저장됩니다.",
            view=BackupPolicyView(self.controller, self.ownerId, self.settings),
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
        await sendScreen(
            interaction,
            content=f"⚠️ `{self.selectedName}` 월드를 적용할까요? 서버 월드가 교체됩니다.",
            view=ConfirmLegacyActionView(
                self.controller,
                self.ownerId,
                "worldActivate",
                (self.selectedName, "ACTIVATE"),
                "월드 적용",
            ),
        )

    @discord.ui.button(label="다운로드", emoji="⬇️", style=discord.ButtonStyle.secondary, row=1)
    async def download(self, interaction, button):
        await self._selected(interaction, "worldDownload")

    @discord.ui.button(label="삭제", emoji="🗑️", style=discord.ButtonStyle.danger, row=1)
    async def delete(self, interaction, button):
        if not self.selectedName:
            await interaction.response.send_message("가져온 월드가 없습니다.", ephemeral=True)
            return
        await sendScreen(
            interaction,
            content=f"⚠️ `{self.selectedName}` 가져온 월드를 삭제할까요?",
            view=ConfirmLegacyActionView(
                self.controller,
                self.ownerId,
                "worldDelete",
                (self.selectedName, "DELETE"),
                "월드 삭제",
            ),
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

        async def back(backInteraction: discord.Interaction):
            await renderLogPanel(backInteraction, self.controller, self.ownerId)

        await replaceScreen(
            interaction,
            content=None,
            embed=embed,
            view=InfoScreenView(
                self.controller, self.ownerId, backRenderer=back, backLabel="↩️ 로그"
            ),
        )

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
