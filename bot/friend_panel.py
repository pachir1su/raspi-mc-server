"""Button-first self-service panels for linked Minecraft players."""

import discord


class UserView(discord.ui.View):
    """Bind a private component panel to the user who opened it."""

    def __init__(self, controller, ownerId: int, timeout: float = 600):
        super().__init__(timeout=timeout)
        self.controller = controller
        self.ownerId = ownerId

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
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
        message = f"❌ 작업을 완료하지 못했습니다: {str(error)[:1500]}"
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class LinkNameModal(discord.ui.Modal, title="Minecraft 계정 연동"):
    """Ask only for the one value that cannot be selected: the player name."""

    minecraftName = discord.ui.TextInput(
        label="Minecraft 닉네임 또는 게이머태그", max_length=64
    )

    def __init__(self, controller, edition: str):
        super().__init__()
        self.controller = controller
        self.edition = edition

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.controller.panelRequestLink(
            interaction, str(self.minecraftName), self.edition
        )


class LinkEditionView(UserView):
    """Choose an edition before opening the short player-name modal."""

    @discord.ui.button(label="Java", emoji="☕", style=discord.ButtonStyle.primary)
    async def java(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(LinkNameModal(self.controller, "java"))

    @discord.ui.button(
        label="Bedrock", emoji="📱", style=discord.ButtonStyle.secondary
    )
    async def bedrock(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(LinkNameModal(self.controller, "bedrock"))


class PlaceNameModal(discord.ui.Modal, title="현재 위치 저장"):
    """Name the current in-game position; coordinates come from RCON."""

    placeName = discord.ui.TextInput(label="좌표 이름", max_length=60)
    description = discord.ui.TextInput(
        label="설명 (선택)", required=False, max_length=300
    )

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelSaveCurrentPlace(
            interaction, str(self.placeName), str(self.description)
        )


class PlaceSelect(discord.ui.Select):
    """Select an existing coordinate without typing its name."""

    def __init__(self, parentView, places):
        self.parentView = parentView
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
            placeholder="저장된 좌표 선택", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parentView.selectedName = self.values[0]
        await interaction.response.edit_message(
            content=f"선택됨: **{self.values[0]}**", view=self.parentView
        )


class PlacePanelView(UserView):
    """Coordinate lookup, deletion, and current-position capture."""

    def __init__(self, controller, ownerId: int, places):
        super().__init__(controller, ownerId)
        self.selectedName = places[0].name if places else None
        if places:
            self.add_item(PlaceSelect(self, places))

    @discord.ui.button(label="보기", emoji="👁️", style=discord.ButtonStyle.primary, row=1)
    async def show(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not self.selectedName:
            await interaction.response.send_message("저장된 좌표가 없습니다.", ephemeral=True)
            return
        await self.controller.panelShowPlace(interaction, self.selectedName)

    @discord.ui.button(
        label="현재 위치 저장", emoji="➕", style=discord.ButtonStyle.success, row=1
    )
    async def saveCurrent(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(PlaceNameModal(self.controller))

    @discord.ui.button(label="삭제", emoji="🗑️", style=discord.ButtonStyle.danger, row=1)
    async def delete(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not self.selectedName:
            await interaction.response.send_message("삭제할 좌표가 없습니다.", ephemeral=True)
            return
        await self.controller.panelDeletePlace(interaction, self.selectedName)


class DiaryModal(discord.ui.Modal, title="서버 일지 작성"):
    """Use a modal only where free-form writing is the feature itself."""

    message = discord.ui.TextInput(
        label="일지 내용", style=discord.TextStyle.paragraph, max_length=1500
    )

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelAddDiary(interaction, str(self.message))


class DiarySelect(discord.ui.Select):
    """Select a recent diary record by its short summary."""

    def __init__(self, parentView, entries):
        self.parentView = parentView
        options = [
            discord.SelectOption(
                label=f"{entry.category} · {entry.entryId}"[:100],
                value=entry.entryId,
                description=entry.message[:100],
                emoji="📖",
            )
            for entry in entries[:25]
        ]
        super().__init__(
            placeholder="최근 일지 선택", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parentView.selectedId = self.values[0]
        await interaction.response.edit_message(
            content=f"선택됨: `{self.values[0]}`", view=self.parentView
        )


class DiaryPanelView(UserView):
    """Recent diary selection plus a single writing modal."""

    def __init__(self, controller, ownerId: int, entries):
        super().__init__(controller, ownerId)
        self.selectedId = entries[0].entryId if entries else None
        if entries:
            self.add_item(DiarySelect(self, entries))

    @discord.ui.button(label="보기", emoji="👁️", style=discord.ButtonStyle.primary, row=1)
    async def show(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not self.selectedId:
            await interaction.response.send_message("서버 일지가 비어 있습니다.", ephemeral=True)
            return
        await self.controller.panelShowDiary(interaction, self.selectedId)

    @discord.ui.button(label="새 일지", emoji="✏️", style=discord.ButtonStyle.success, row=1)
    async def add(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(DiaryModal(self.controller))


class MyToolsView(UserView):
    """Single self-service entry point for linked players."""

    @discord.ui.button(label="연동 상태", emoji="🔗", style=discord.ButtonStyle.secondary, row=0)
    async def linkStatus(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.controller.panelLinkStatus(interaction)

    @discord.ui.button(label="연동 요청", emoji="📝", style=discord.ButtonStyle.success, row=0)
    async def requestLink(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_message(
            "사용하는 Minecraft 에디션을 선택하세요.",
            view=LinkEditionView(self.controller, self.ownerId),
            ephemeral=True,
        )

    @discord.ui.button(label="스폰 구조", emoji="🏠", style=discord.ButtonStyle.primary, row=1)
    async def rescue(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.controller.panelRescueSpawn(interaction)

    @discord.ui.button(label="내 위치", emoji="📍", style=discord.ButtonStyle.secondary, row=1)
    async def location(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.controller.panelWhereAmI(interaction)

    @discord.ui.button(label="서버 점수", emoji="🩺", style=discord.ButtonStyle.secondary, row=1)
    async def score(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.controller.panelServerScore(interaction)

    @discord.ui.button(label="좌표북", emoji="🗺️", style=discord.ButtonStyle.secondary, row=2)
    async def places(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not await self.controller._requireFriendAccess(interaction):
            return
        places = await self.controller.panelPlaces()
        await interaction.response.send_message(
            "좌표를 선택하거나 현재 위치를 저장하세요.",
            view=PlacePanelView(self.controller, self.ownerId, places),
            ephemeral=True,
        )

    @discord.ui.button(label="서버 일지", emoji="📖", style=discord.ButtonStyle.secondary, row=2)
    async def diary(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not await self.controller._requireFriendAccess(interaction):
            return
        entries = await self.controller.panelDiaryEntries()
        await interaction.response.send_message(
            "최근 일지를 선택하거나 새 일지를 작성하세요.",
            view=DiaryPanelView(self.controller, self.ownerId, entries),
            ephemeral=True,
        )


class LinkAdminSelect(discord.ui.Select):
    """Select a Discord-to-Minecraft link without typing a user ID."""

    def __init__(self, parentView, links):
        self.parentView = parentView
        options = [
            discord.SelectOption(
                label=link.minecraftName[:100],
                value=str(link.discordUserId),
                description=(
                    f"{'승인됨' if link.approved else '승인 대기'} · "
                    f"{link.edition} · Discord {link.discordUserId}"
                )[:100],
                emoji="✅" if link.approved else "⏳",
            )
            for link in links[:25]
        ]
        super().__init__(
            placeholder="연동 계정 선택", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parentView.selectedUserId = int(self.values[0])
        await interaction.response.edit_message(
            content=f"선택한 Discord 사용자: <@{self.values[0]}>",
            view=self.parentView,
        )


class LinkAdminView(UserView):
    """Approve or revoke a selected account link through private buttons."""

    def __init__(self, controller, ownerId: int, links):
        super().__init__(controller, ownerId)
        self.selectedUserId = links[0].discordUserId if links else None
        if links:
            self.add_item(LinkAdminSelect(self, links))

    @discord.ui.button(
        label="승인", emoji="✅", style=discord.ButtonStyle.success, row=1
    )
    async def approve(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.selectedUserId is None:
            await interaction.response.send_message(
                "연동 요청이 없습니다.", ephemeral=True
            )
            return
        await self.controller.panelApproveLink(interaction, self.selectedUserId)

    @discord.ui.button(
        label="해제", emoji="🗑️", style=discord.ButtonStyle.danger, row=1
    )
    async def revoke(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.selectedUserId is None:
            await interaction.response.send_message(
                "해제할 연동이 없습니다.", ephemeral=True
            )
            return
        await self.controller.panelRevokeLink(interaction, self.selectedUserId)
