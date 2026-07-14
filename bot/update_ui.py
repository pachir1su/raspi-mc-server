"""Owner-bound Discord confirmation controls for application updates."""

from typing import Any

import discord


class UpdateConfirmView(discord.ui.View):
    """Require the same administrator to confirm a prepared update."""

    def __init__(self, controller: Any, ownerId: int, payload: Any, label: str):
        super().__init__(timeout=300)
        self.controller = controller
        self.ownerId = ownerId
        self.payload = payload
        self.label = label

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Prevent forwarded panels from becoming an update capability."""
        if interaction.user.id == self.ownerId and self.controller.isAdmin(interaction):
            return True
        await interaction.response.send_message(
            "⛔ 이 업데이트 확인 창을 연 관리자만 사용할 수 있습니다.", ephemeral=True
        )
        return False

    @discord.ui.button(label="업데이트 설치", style=discord.ButtonStyle.danger, emoji="⬆️")
    async def applyButton(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Acknowledge first, then queue the root-owned one-shot service."""
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"⏳ `{self.label}` 업데이트를 시작합니다. 봇이 잠시 재시작됩니다.",
            embed=None,
            view=self,
        )
        await self.controller.startPreparedUpdate(interaction, self.payload)
        self.stop()

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancelButton(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Close the confirmation without creating an updater request."""
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="업데이트를 취소했습니다.", embed=None, view=self)
        self.stop()
