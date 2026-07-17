"""Friend-safe button panel for server access and live player status."""

import discord

from bot.error_text import describeError


class PublicServerView(discord.ui.View):
    """Keep common read-only server actions one click away."""

    expiredNotice = "⏰ 패널이 만료되었습니다. `/server` 를 다시 실행해 새 패널을 여세요."

    def __init__(self, controller, ownerId: int, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.controller = controller
        self.ownerId = ownerId
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only the user who opened the private panel may operate it."""
        if interaction.user.id == self.ownerId:
            return True
        await interaction.response.send_message(
            "이 패널은 명령을 실행한 사용자만 조작할 수 있습니다.", ephemeral=True
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
    ) -> None:
        """Return callback failures as a useful private response."""
        message = f"❌ 서버 정보를 불러오지 못했습니다: {describeError(error)}"
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    @discord.ui.button(
        label="접속 정보", emoji="🎮", style=discord.ButtonStyle.primary, row=0
    )
    async def accessInfo(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        embed = await self.controller.publicServerEmbed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="접속자", emoji="👥", style=discord.ButtonStyle.secondary, row=0
    )
    async def onlinePlayers(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        players = await self.controller.panelOnlinePlayers()
        text = ", ".join(players) if players else "현재 접속 중인 플레이어가 없습니다."
        await interaction.response.send_message(text, ephemeral=True)

    @discord.ui.button(
        label="새로고침", emoji="🔄", style=discord.ButtonStyle.secondary, row=0
    )
    async def refresh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        embed = await self.controller.publicServerEmbed()
        await interaction.response.edit_message(embed=embed, view=self)
