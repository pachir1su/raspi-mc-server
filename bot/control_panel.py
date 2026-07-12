"""Button-first Discord administration views for routine server operations."""

import discord

from bot.config import cfg


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
        message = f"❌ 작업을 완료하지 못했습니다: {str(error)[:1500]}"
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class AdminDashboardView(OwnerView):
    """Main dashboard with the most common tasks reachable in one click."""

    @discord.ui.button(label="새로고침", emoji="🔄", style=discord.ButtonStyle.secondary, row=0)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.controller.panelOverviewEmbed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="플레이어", emoji="👥", style=discord.ButtonStyle.primary, row=0)
    async def players(self, interaction: discord.Interaction, button: discord.ui.Button):
        players = await self.controller.panelOnlinePlayers()
        if not players:
            await interaction.response.send_message("현재 접속 중인 플레이어가 없습니다.", ephemeral=True)
            return
        view = PlayerPanelView(self.controller, self.ownerId, players)
        await interaction.response.send_message(
            "조회할 플레이어를 선택하세요.", view=view, ephemeral=True
        )

    @discord.ui.button(label="지금 백업", emoji="💾", style=discord.ButtonStyle.success, row=0)
    async def backup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelCreateBackup(interaction)

    @discord.ui.button(label="서버 제어", emoji="🎛️", style=discord.ButtonStyle.primary, row=0)
    async def service(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "실행할 서버 작업을 선택하세요. 정지와 재시작은 한 번 더 확인합니다.",
            view=ServerActionsView(self.controller, self.ownerId),
            ephemeral=True,
        )

    @discord.ui.button(label="로그", emoji="📄", style=discord.ButtonStyle.secondary, row=0)
    async def logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "확인할 로그를 선택하세요.", view=LogPanelView(self.controller, self.ownerId), ephemeral=True
        )

    @discord.ui.button(label="자동 백업 토글", emoji="⏱️", style=discord.ButtonStyle.secondary, row=1)
    async def toggleBackup(self, interaction: discord.Interaction, button: discord.ui.Button):
        enabled = await self.controller.panelToggleBackup(interaction)
        button.style = discord.ButtonStyle.success if enabled else discord.ButtonStyle.danger
        button.label = "자동 백업 켜짐" if enabled else "자동 백업 꺼짐"
        embed = await self.controller.panelOverviewEmbed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="저장공간", emoji="💽", style=discord.ButtonStyle.secondary, row=1)
    async def storage(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.controller.panelStorageEmbed()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="상태 진단", emoji="🩺", style=discord.ButtonStyle.secondary, row=1)
    async def health(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.controller.panelHealthEmbed()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="성능", emoji="📊", style=discord.ButtonStyle.secondary, row=1)
    async def performance(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        embed = await self.controller.panelMetricsEmbed()
        await interaction.followup.send(embed=embed, ephemeral=True)


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
            content=f"선택됨: **{self.values[0]}** — 아래 버튼으로 조회하세요.",
            view=self.parentView,
        )


class PlayerPanelView(OwnerView):
    """Player selection plus inventory, position, stats, and effects shortcuts."""

    def __init__(self, controller, ownerId: int, players: list[str]):
        super().__init__(controller, ownerId)
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

    @discord.ui.button(label="효과", emoji="✨", style=discord.ButtonStyle.secondary, row=1)
    async def effects(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show(interaction, "effects")


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
