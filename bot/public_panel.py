"""Friend-safe button panel for server access and live player status."""

import discord


class PublicServerView(discord.ui.View):
    """Keep common read-only server actions one click away."""

    def __init__(self, controller, ownerId: int, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.controller = controller
        self.ownerId = ownerId

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only the user who opened the private panel may operate it."""
        if interaction.user.id == self.ownerId:
            return True
        await interaction.response.send_message(
            "이 패널은 명령을 실행한 사용자만 조작할 수 있습니다.", ephemeral=True
        )
        return False

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        """Return callback failures as a useful private response."""
        message = f"❌ 서버 정보를 불러오지 못했습니다: {str(error)[:1500]}"
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
