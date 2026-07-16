"""Button-first self-service panels for linked Minecraft players."""

import discord

from bot.error_text import describeError


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
        message = f"❌ {describeError(error)}"
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class TeleportTargetSelect(discord.ui.Select):
    """Pick an online player to teleport the friend's own account to."""

    def __init__(self, controller, ownerId: int, linkId: str, targets: list[str]):
        self.controller = controller
        self.ownerId = ownerId
        self.linkId = linkId
        options = [
            discord.SelectOption(label=name[:100], value=name, emoji="🧍")
            for name in targets[:25]
        ]
        super().__init__(
            placeholder="이동할 플레이어 선택",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.controller.panelPlayerTeleport(
            interaction, self.linkId, self.values[0]
        )


class FriendTeleportView(UserView):
    """Online-player picker for the friend teleport action."""

    def __init__(self, controller, ownerId: int, linkId: str, targets: list[str]):
        super().__init__(controller, ownerId, timeout=120)
        self.add_item(TeleportTargetSelect(controller, ownerId, linkId, targets))


class PlayerAccountSelect(discord.ui.Select):
    """Choose which administrator-managed Minecraft profile an action targets."""

    def __init__(self, parentView, links):
        self.parentView = parentView
        options = [
            discord.SelectOption(
                label=f"{'Java (PC)' if link.edition == 'java' else 'Bedrock (모바일/콘솔)'} · {link.minecraftName}"[:100],
                value=link.linkId,
                description="아래 구조·위치·좌표 버튼이 이 계정에 적용됩니다.",
                emoji="☕" if link.edition == "java" else "📱",
                default=index == 0,
            )
            for index, link in enumerate(links[:25])
        ]
        super().__init__(
            placeholder="사용할 Minecraft 계정 선택",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parentView.selectedLinkId = self.values[0]
        link = next(
            item for item in self.parentView.links if item.linkId == self.values[0]
        )
        await interaction.response.edit_message(
            content=(
                f"선택된 계정: **{link.minecraftName}** "
                f"({'Java · PC' if link.edition == 'java' else 'Bedrock · 모바일/콘솔'})"
            ),
            view=self.parentView,
        )


class PlaceNameModal(discord.ui.Modal, title="현재 위치 저장"):
    """Name the current in-game position; coordinates come from RCON."""

    placeName = discord.ui.TextInput(label="좌표 이름", max_length=60)
    description = discord.ui.TextInput(
        label="설명 (선택)", required=False, max_length=300
    )

    def __init__(self, controller, linkId: str):
        super().__init__()
        self.controller = controller
        self.linkId = linkId

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelSaveCurrentPlace(
            interaction, self.linkId, self.placeName.value, self.description.value
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

    def __init__(self, controller, ownerId: int, places, linkId: str):
        super().__init__(controller, ownerId)
        self.selectedName = places[0].name if places else None
        self.linkId = linkId
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
        await interaction.response.send_modal(
            PlaceNameModal(self.controller, self.linkId)
        )

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
        await self.controller.panelAddDiary(interaction, self.message.value)


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

    def __init__(self, controller, ownerId: int, links):
        super().__init__(controller, ownerId)
        self.links = links
        self.selectedLinkId = links[0].linkId if links else None
        if links:
            self.add_item(PlayerAccountSelect(self, links))

    async def _requireSelection(self, interaction: discord.Interaction) -> bool:
        if self.selectedLinkId:
            return True
        await interaction.response.send_message(
            "등록된 Minecraft 계정이 없습니다. 관리자에게 계정 등록을 요청하세요.",
            ephemeral=True,
        )
        return False

    @discord.ui.button(label="내 계정 목록", emoji="👤", style=discord.ButtonStyle.secondary, row=1)
    async def linkStatus(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.controller.panelLinkStatus(interaction)

    @discord.ui.button(label="선택 계정 스폰 귀환", emoji="🏠", style=discord.ButtonStyle.primary, row=1)
    async def rescue(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if await self._requireSelection(interaction):
            await self.controller.panelRescueSpawn(interaction, self.selectedLinkId)

    @discord.ui.button(label="선택 계정 위치", emoji="📍", style=discord.ButtonStyle.secondary, row=1)
    async def location(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if await self._requireSelection(interaction):
            await self.controller.panelWhereAmI(interaction, self.selectedLinkId)

    @discord.ui.button(label="서버 상태 점수", emoji="🩺", style=discord.ButtonStyle.secondary, row=2)
    async def score(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.controller.panelServerScore(interaction)

    @discord.ui.button(label="공유 좌표북", emoji="🗺️", style=discord.ButtonStyle.secondary, row=2)
    async def places(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not await self._requireSelection(interaction):
            return
        places = await self.controller.panelPlaces()
        await interaction.response.send_message(
            "저장된 좌표를 보거나, 선택한 Minecraft 계정의 현재 위치를 저장합니다.",
            view=PlacePanelView(
                self.controller, self.ownerId, places, self.selectedLinkId
            ),
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

    @discord.ui.button(label="데스박스 찾기", emoji="📦", style=discord.ButtonStyle.secondary, row=3)
    async def deathboxLocate(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if await self._requireSelection(interaction):
            await self.controller.panelDeathboxLocate(interaction, self.selectedLinkId)

    @discord.ui.button(label="데스박스 목록", emoji="🗃️", style=discord.ButtonStyle.secondary, row=3)
    async def deathboxList(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if await self._requireSelection(interaction):
            await self.controller.panelDeathboxList(interaction, self.selectedLinkId)

    @discord.ui.button(label="내 상태", emoji="❤️", style=discord.ButtonStyle.secondary, row=3)
    async def myStatus(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if await self._requireSelection(interaction):
            await self.controller.panelMyStatus(interaction, self.selectedLinkId)

    @discord.ui.button(label="플레이어에게 이동", emoji="🚀", style=discord.ButtonStyle.primary, row=4)
    async def teleport(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not await self._requireSelection(interaction):
            return
        targets = await self.controller.panelTeleportTargets(interaction)
        if not targets:
            await interaction.response.send_message(
                "이동할 수 있는 다른 접속자가 없습니다.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            "이동할 접속 중인 플레이어를 선택하세요. (30분에 한 번)",
            view=FriendTeleportView(
                self.controller, self.ownerId, self.selectedLinkId, targets
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="서버 시간", emoji="🕰️", style=discord.ButtonStyle.secondary, row=4)
    async def serverTime(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self.controller.panelServerTime(interaction)


class ManagedAccountModal(discord.ui.Modal):
    """Ask an administrator only for the Minecraft name being assigned."""

    minecraftName = discord.ui.TextInput(
        label="Minecraft 닉네임 / Xbox 게이머태그", max_length=64
    )

    def __init__(self, controller, discordUserId: int, edition: str):
        title = "Java(PC) 계정 등록" if edition == "java" else "Bedrock(모바일/콘솔) 계정 등록"
        super().__init__(title=title)
        self.controller = controller
        self.discordUserId = discordUserId
        self.edition = edition

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.controller.panelAddManagedLink(
            interaction,
            self.discordUserId,
            self.minecraftName.value,
            self.edition,
        )


class ManagedDiscordUserSelect(discord.ui.UserSelect):
    """Choose the Discord account whose Minecraft profiles are managed."""

    def __init__(self, parentView):
        super().__init__(
            placeholder="1단계: Discord 사용자 선택",
            min_values=1,
            max_values=1,
            row=0,
        )
        self.parentView = parentView

    async def callback(self, interaction: discord.Interaction) -> None:
        user = self.values[0]
        links = await self.parentView.controller.panelLinksForUser(user.id)
        await interaction.response.edit_message(
            content=(
                f"관리 대상: {user.mention}\n"
                "2단계: 기존 계정을 선택하거나 아래에서 새 계정을 등록하세요."
            ),
            view=ManagedAccountView(
                self.parentView.controller,
                self.parentView.ownerId,
                user.id,
                links,
            ),
        )


class ManagedProfileSelect(discord.ui.Select):
    """Choose one of a Discord user's multiple Minecraft profiles."""

    def __init__(self, parentView, links):
        self.parentView = parentView
        options = [
            discord.SelectOption(
                label=link.minecraftName[:100],
                value=link.linkId,
                description=(
                    ("Java · PC" if link.edition == "java" else "Bedrock · 모바일/콘솔")
                    if link.approved
                    else "이전 승인 대기 기록 · 삭제 후 다시 등록"
                ),
                emoji="☕" if link.edition == "java" else "📱",
                default=index == 0,
            )
            for index, link in enumerate(links[:25])
        ]
        super().__init__(
            placeholder="등록된 Minecraft 계정 선택",
            min_values=1,
            max_values=1,
            options=options,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parentView.selectedLinkId = self.values[0]
        await interaction.response.edit_message(view=self.parentView)


class ConfirmManagedRemovalView(UserView):
    """Require one explicit confirmation before deleting a selected profile."""

    def __init__(self, controller, ownerId: int, linkId: str):
        super().__init__(controller, ownerId, timeout=120)
        self.linkId = linkId

    @discord.ui.button(label="이 계정만 삭제", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        await self.controller.panelRemoveManagedLink(interaction, self.linkId)

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(content="계정 삭제를 취소했습니다.", view=None)


class ManagedAccountView(UserView):
    """Administrator-owned direct multi-profile account management."""

    def __init__(self, controller, ownerId: int, discordUserId=None, links=None):
        super().__init__(controller, ownerId)
        self.discordUserId = discordUserId
        self.links = links or []
        self.selectedLinkId = self.links[0].linkId if self.links else None
        self.add_item(ManagedDiscordUserSelect(self))
        if self.links:
            self.add_item(ManagedProfileSelect(self, self.links))

    async def _requireUser(self, interaction: discord.Interaction) -> bool:
        if self.discordUserId is not None:
            return True
        await interaction.response.send_message(
            "먼저 위 메뉴에서 Discord 사용자를 선택하세요.", ephemeral=True
        )
        return False

    @discord.ui.button(label="Java(PC) 추가", emoji="☕", style=discord.ButtonStyle.success, row=2)
    async def addJava(self, interaction, button):
        if await self._requireUser(interaction):
            await interaction.response.send_modal(
                ManagedAccountModal(self.controller, self.discordUserId, "java")
            )

    @discord.ui.button(label="Bedrock(모바일) 추가", emoji="📱", style=discord.ButtonStyle.success, row=2)
    async def addBedrock(self, interaction, button):
        if await self._requireUser(interaction):
            await interaction.response.send_modal(
                ManagedAccountModal(self.controller, self.discordUserId, "bedrock")
            )

    @discord.ui.button(label="선택 계정 삭제", emoji="🗑️", style=discord.ButtonStyle.danger, row=2)
    async def remove(self, interaction, button):
        if not self.selectedLinkId:
            await interaction.response.send_message(
                "삭제할 Minecraft 계정을 선택하세요.", ephemeral=True
            )
            return
        selected = next(
            link for link in self.links if link.linkId == self.selectedLinkId
        )
        editionLabel = (
            "Java (PC)" if selected.edition == "java" else "Bedrock (모바일/콘솔)"
        )
        await interaction.response.send_message(
            f"**{editionLabel}** `{selected.minecraftName}` 계정만 삭제할까요? "
            "같은 Discord 사용자의 다른 계정은 유지됩니다.",
            view=ConfirmManagedRemovalView(
                self.controller, self.ownerId, self.selectedLinkId
            ),
            ephemeral=True,
        )
