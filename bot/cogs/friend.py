"""Narrow friend-safe Discord commands backed by approved player links."""

import asyncio
import os
import shutil
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from bot import BRAND_BLUE, ERR_RED, OK_GREEN, WARN_YELLOW, log, userTag
from bot.app_settings import AppSettingsStore
from bot.config import cfg
from bot.diary import DiaryEntry, DiaryStore
from bot.health_score import HealthInputs, calculateHealthScore
from bot.friend_panel import ManagedAccountView, MyToolsView
from bot.internal_actions import InternalActionGroup, internalAction
from bot.performance_report import parseTps
from bot.places import (
    MAX_IMAGE_BYTES,
    ImageStore,
    Place,
    PlaceStore,
    buildMapLink,
)
from bot.player_links import (
    PlayerLink,
    PlayerLinkStore,
    buildWhitelistCommand,
    buildWhitelistRemoveCommand,
    serverPlayerName,
)
from bot.player_names import buildPlayerSelector
from bot.rcon import Rcon, RconError
from bot.rescue import buildAutomaticSpawnCommand, ensureRescueSucceeded, parsePosition
from bot.system_metrics import readSystemMetrics, readThrottleFlags

_log = log.get("cog.friend")


def _isAdmin(interaction: discord.Interaction) -> bool:
    """Use the same owner allowlist as every existing privileged command."""
    return interaction.user.id in cfg.admin_ids


async def _rcon(command: str) -> str:
    """Run one pre-built command through a short-lived local RCON connection."""
    async with Rcon(cfg.rcon_host, cfg.rcon_port, cfg.rcon_password) as client:
        return await client.command(command)


class Friend(commands.Cog):
    """Account linking and bounded self-service tools for trusted friends."""

    rescueGroup = InternalActionGroup()
    placeGroup = InternalActionGroup()
    diaryGroup = InternalActionGroup()

    def __init__(self, bot: commands.Bot):
        # Keep every friend-facing store outside the large admin cog.
        self.bot = bot
        self.linkStore = PlayerLinkStore(cfg.state_dir)
        self.appSettings = AppSettingsStore(cfg.state_dir).load()
        self.placeStore = PlaceStore(cfg.state_dir)
        self.diaryStore = DiaryStore(cfg.state_dir)
        self.imageStore = ImageStore(cfg.state_dir)

    @app_commands.command(
        name="my-tools", description="Choose one of your Minecraft accounts and use quick tools."
    )
    async def myTools(self, interaction: discord.Interaction) -> None:
        """Open the text-light self-service panel for the invoking user."""
        links = await asyncio.to_thread(
            self.linkStore.listForUser, interaction.user.id
        )
        if links:
            accountLines = [
                f"• `{link.minecraftName}` — "
                f"{'Java (PC)' if link.edition == 'java' else 'Bedrock (모바일/콘솔)'}"
                for link in links
            ]
            description = (
                "사용할 계정을 먼저 고른 뒤 아래 버튼을 누르세요.\n\n"
                + "\n".join(accountLines)
            )
        else:
            description = (
                "등록된 Minecraft 계정이 없습니다.\n"
                "관리자에게 Java 또는 Bedrock 계정 등록을 요청하세요."
            )
        embed = discord.Embed(
            title="🧰 내 Minecraft 도구",
            description=description,
            color=BRAND_BLUE,
        )
        await interaction.response.send_message(
            embed=embed,
            view=MyToolsView(self, interaction.user.id, links),
            ephemeral=True,
        )

    @app_commands.command(
        name="help", description="Show friend-safe Minecraft bot help."
    )
    async def helpCommand(self, interaction: discord.Interaction) -> None:
        """Explain the public command surface without exposing owner controls."""
        embed = discord.Embed(
            title="📘 Minecraft 봇 도움말",
            description="친구가 사용할 수 있는 명령은 아래 세 가지입니다.",
            color=BRAND_BLUE,
        )
        embed.add_field(
            name="`/서버` (`/server`)",
            value="접속 주소, 서버 상태와 현재 접속자를 확인합니다.",
            inline=False,
        )
        embed.add_field(
            name="`/내도구` (`/my-tools`)",
            value=(
                "관리자가 등록한 내 캐릭터를 선택해 스폰 귀환, 위치 조회, "
                "좌표북, 서버 일지와 건강 점수를 사용합니다."
            ),
            inline=False,
        )
        embed.add_field(
            name="`/도움말` (`/help`)",
            value="이 안내를 다시 표시합니다.",
            inline=False,
        )
        embed.add_field(
            name="🧭 이럴 땐 이렇게",
            value=(
                "• **서버 주소를 알고 싶다** → `/서버`\n"
                "• **죽어서 아이템을 잃었다** → `/내도구` → **데스박스 찾기** "
                "(아이템은 상자에 안전하게 보관됩니다)\n"
                "• **길을 잃었다/끼었다** → `/내도구` → **선택 계정 스폰 귀환**\n"
                "• **좋은 장소를 공유하고 싶다** → `/내도구` → **공유 좌표북** → "
                "**현재 위치 저장**\n"
                "• **서버가 느린 것 같다** → `/내도구` → **서버 상태 점수**"
            ),
            inline=False,
        )
        embed.set_footer(text="관리 기능은 ADMIN_USER_IDS에 등록된 서버장에게만 표시됩니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Allow the friend surface only when its owner-controlled switch is enabled."""
        if cfg.public_commands_enabled or _isAdmin(interaction):
            return True
        await interaction.response.send_message(
            "⛔ 친구용 명령이 비활성화되어 있습니다.", ephemeral=True
        )
        return False

    async def _requireAdmin(self, interaction: discord.Interaction) -> bool:
        """Gate approval, revocation, and global deletion behind ADMIN_USER_IDS."""
        if _isAdmin(interaction):
            return True
        message = "⛔ 관리자만 실행할 수 있습니다."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
        _log.warning("denied friend-admin command from %s", userTag(interaction.user))
        return False

    async def _approvedLink(
        self,
        interaction: discord.Interaction,
        linkId: str | None = None,
        respond: bool = True,
    ) -> PlayerLink | None:
        """Resolve one approved profile owned by the invoking Discord user."""
        if linkId:
            link = await asyncio.to_thread(self.linkStore.getById, linkId)
        else:
            link = await asyncio.to_thread(self.linkStore.get, interaction.user.id)
        if link and link.approved and link.discordUserId == interaction.user.id:
            return link
        if respond:
            message = "❌ 등록된 계정을 찾지 못했습니다. 관리자에게 등록을 요청하세요."
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        return None

    async def _requireFriendAccess(self, interaction: discord.Interaction) -> bool:
        """Allow approved friends and unlinked admins to use shared read/write tools."""
        if _isAdmin(interaction):
            return True
        return await self._approvedLink(interaction) is not None

    async def _saveAttachment(
        self, attachment: discord.Attachment | None
    ) -> str | None:
        """Download one bounded image without blocking the event loop on disk I/O."""
        if attachment is None:
            return None
        if attachment.size > MAX_IMAGE_BYTES:
            raise ValueError("사진은 5 MiB 이하여야 합니다.")
        content = await attachment.read()
        return await asyncio.to_thread(
            self.imageStore.save,
            content,
            attachment.filename,
            attachment.content_type,
        )

    @staticmethod
    def _placeEmbed(place: Place) -> discord.Embed:
        """Build one coordinate card without invoking any local map renderer."""
        description = (
            f"**차원:** `{place.dimension}`\n"
            f"**좌표:** `{place.x} {place.y} {place.z}`"
        )
        if place.description:
            description += f"\n**메모:** {place.description}"
        embed = discord.Embed(
            title=f"📍 {place.name}", description=description, color=BRAND_BLUE
        )
        try:
            mapUrl = buildMapLink(cfg.map_url_template, place)
        except ValueError as error:
            embed.add_field(name="지도 설정 오류", value=str(error), inline=False)
        else:
            if mapUrl:
                embed.add_field(name="웹 지도", value=f"[지도에서 열기]({mapUrl})", inline=False)
        embed.set_footer(text=f"등록자 Discord ID: {place.createdBy}")
        return embed

    async def _sendPlace(self, interaction: discord.Interaction, place: Place) -> None:
        """Send a place card and re-upload its durable local image when present."""
        embed = self._placeEmbed(place)
        imagePath = self.imageStore.safePath(place.imagePath)
        if imagePath and imagePath.is_file():
            file = discord.File(imagePath, filename=imagePath.name)
            embed.set_image(url=f"attachment://{imagePath.name}")
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, file=file, ephemeral=True)
            return
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @staticmethod
    def _diaryEmbed(entry: DiaryEntry) -> discord.Embed:
        """Build one compact journal card."""
        embed = discord.Embed(
            title=f"📖 {entry.category} · {entry.entryId}",
            description=entry.message,
            color=BRAND_BLUE,
        )
        embed.set_footer(text=f"작성자 Discord ID: {entry.authorId} · {entry.createdAt[:19]} UTC")
        return embed

    async def _sendDiaryEntry(
        self, interaction: discord.Interaction, entry: DiaryEntry
    ) -> None:
        """Send one journal entry with its durable local image if available."""
        embed = self._diaryEmbed(entry)
        imagePath = self.imageStore.safePath(entry.imagePath)
        if imagePath and imagePath.is_file():
            file = discord.File(imagePath, filename=imagePath.name)
            embed.set_image(url=f"attachment://{imagePath.name}")
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, file=file, ephemeral=True)
            return
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- linked-player rescue -----------------------------------------
    @rescueGroup.command(name="spawn", description="Teleport only your linked player to spawn.")
    async def rescueSpawn(
        self, interaction: discord.Interaction, linkId: str | None = None
    ) -> None:
        link = await self._approvedLink(interaction, linkId)
        if not link:
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            playerName = serverPlayerName(
                link, self.appSettings.bedrockUsernamePrefix
            )
            # 스폰 기준은 월드 스폰 하나입니다. 관리자가 관리 패널의
            # "빠른 명령 → 스폰 지정"으로 옮기면 죽었을 때 리스폰과 이 버튼이
            # 같은 곳으로 통합됩니다. (과거 MC_SPAWN_* 좌표 오버라이드는 두
            # 위치가 어긋나는 원인이라 제거 — bot/rescue.py 상단 안내 참고)
            output = await _rcon(buildAutomaticSpawnCommand(playerName))
            # 플러그인은 실패도 일반 텍스트로 답하므로 응답을 검증해야
            # 미접속 플레이어에게 허위 성공을 보여주지 않습니다(이슈 #45 댓글).
            ensureRescueSucceeded(output)
            await asyncio.to_thread(
                self.diaryStore.record,
                "rescue",
                f"{playerName} 님이 스폰으로 귀환했습니다.",
                interaction.user.id,
            )
            await interaction.followup.send(
                f"✅ `{link.minecraftName}` 님을 스폰으로 이동했습니다.",
                ephemeral=True,
            )
            _log.info("self rescue by %s -> %s", userTag(interaction.user), link.minecraftName)
        except (ValueError, RconError, OSError, RuntimeError) as error:
            await interaction.followup.send(f"❌ {error}", ephemeral=True)

    @rescueGroup.command(name="whereami", description="Show your linked player's current location.")
    async def rescueWhereAmI(
        self, interaction: discord.Interaction, linkId: str | None = None
    ) -> None:
        link = await self._approvedLink(interaction, linkId)
        if not link:
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            playerName = serverPlayerName(
                link, self.appSettings.bedrockUsernamePrefix
            )
            playerTarget = buildPlayerSelector(playerName)
            positionOutput, dimensionOutput = await asyncio.gather(
                _rcon(f"data get entity {playerTarget} Pos"),
                _rcon(f"data get entity {playerTarget} Dimension"),
            )
            dimension, x, y, z = parsePosition(positionOutput, dimensionOutput)
            await interaction.followup.send(
                f"📍 `{link.minecraftName}` · `{dimension}` · "
                f"`{x:.1f} {y:.1f} {z:.1f}`",
                ephemeral=True,
            )
        except (ValueError, RconError) as error:
            await interaction.followup.send(f"❌ {error}", ephemeral=True)

    # --- coordinate book ----------------------------------------------
    @placeGroup.command(name="add", description="Save or replace a shared coordinate.")
    @app_commands.choices(
        dimension=[
            app_commands.Choice(name="Overworld", value="overworld"),
            app_commands.Choice(name="Nether", value="nether"),
            app_commands.Choice(name="The End", value="the_end"),
        ]
    )
    async def placeAdd(
        self,
        interaction: discord.Interaction,
        name: str,
        dimension: app_commands.Choice[str],
        x: app_commands.Range[int, -30000000, 30000000],
        y: app_commands.Range[int, -2048, 2048],
        z: app_commands.Range[int, -30000000, 30000000],
        description: str = "",
        photo: discord.Attachment | None = None,
    ) -> None:
        if not await self._requireFriendAccess(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        imagePath = None
        stored = False
        try:
            imagePath = await self._saveAttachment(photo)
            place, previous = await asyncio.to_thread(
                self.placeStore.save,
                name,
                dimension.value,
                x,
                y,
                z,
                description,
                imagePath,
                interaction.user.id,
            )
            stored = True
            if previous and previous.imagePath != imagePath:
                await asyncio.to_thread(self.imageStore.remove, previous.imagePath)
            await asyncio.to_thread(
                self.diaryStore.record,
                "place",
                f"Saved {place.name} at {place.dimension} {place.x} {place.y} {place.z}.",
                interaction.user.id,
            )
            await self._sendPlace(interaction, place)
        except (ValueError, OSError, RuntimeError, discord.HTTPException) as error:
            if not stored:
                await asyncio.to_thread(self.imageStore.remove, imagePath)
            await interaction.followup.send(f"❌ {error}", ephemeral=True)

    @placeGroup.command(name="list", description="List shared coordinate names.")
    async def placeList(self, interaction: discord.Interaction) -> None:
        if not await self._requireFriendAccess(interaction):
            return
        places = await asyncio.to_thread(self.placeStore.list)
        lines = [
            f"• **{place.name}** — `{place.dimension}` `{place.x} {place.y} {place.z}`"
            for place in places[:30]
        ]
        if len(places) > 30:
            lines.append(f"…외 {len(places) - 30}곳")
        await interaction.response.send_message(
            "\n".join(lines) or "저장된 좌표가 없습니다.", ephemeral=True
        )

    @placeGroup.command(name="show", description="Open one coordinate card.")
    async def placeShow(self, interaction: discord.Interaction, name: str) -> None:
        if not await self._requireFriendAccess(interaction):
            return
        try:
            place = await asyncio.to_thread(self.placeStore.get, name)
        except ValueError as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)
            return
        if not place:
            await interaction.response.send_message("좌표를 찾지 못했습니다.", ephemeral=True)
            return
        await self._sendPlace(interaction, place)

    @placeGroup.command(name="delete", description="Delete your coordinate or any as admin.")
    async def placeDelete(self, interaction: discord.Interaction, name: str) -> None:
        if not await self._requireFriendAccess(interaction):
            return
        try:
            place = await asyncio.to_thread(self.placeStore.get, name)
            if not place:
                await interaction.response.send_message("좌표를 찾지 못했습니다.", ephemeral=True)
                return
            if not _isAdmin(interaction) and place.createdBy != interaction.user.id:
                await interaction.response.send_message(
                    "⛔ 등록자 또는 관리자만 삭제할 수 있습니다.", ephemeral=True
                )
                return
            deleted = await asyncio.to_thread(self.placeStore.delete, name)
            await asyncio.to_thread(self.imageStore.remove, deleted.imagePath if deleted else None)
            await interaction.response.send_message("✅ 좌표를 삭제했습니다.", ephemeral=True)
        except (ValueError, OSError, RuntimeError) as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    # --- server diary --------------------------------------------------
    @diaryGroup.command(name="add", description="Write a server-life journal entry.")
    async def diaryAdd(
        self,
        interaction: discord.Interaction,
        message: str,
        photo: discord.Attachment | None = None,
    ) -> None:
        if not await self._requireFriendAccess(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        imagePath = None
        stored = False
        try:
            imagePath = await self._saveAttachment(photo)
            entry = await asyncio.to_thread(
                self.diaryStore.record,
                "note",
                message,
                interaction.user.id,
                imagePath,
            )
            stored = True
            await self._sendDiaryEntry(interaction, entry)
        except (ValueError, OSError, RuntimeError, discord.HTTPException) as error:
            if not stored:
                await asyncio.to_thread(self.imageStore.remove, imagePath)
            await interaction.followup.send(f"❌ {error}", ephemeral=True)

    @diaryGroup.command(name="recent", description="Show recent server-life entries.")
    async def diaryRecent(
        self,
        interaction: discord.Interaction,
        limit: app_commands.Range[int, 1, 20] = 10,
    ) -> None:
        if not await self._requireFriendAccess(interaction):
            return
        entries = await asyncio.to_thread(self.diaryStore.recent, limit)
        lines = [
            f"• `{entry.entryId}` **{entry.category}** — {entry.message[:100]}"
            for entry in entries
        ]
        await interaction.response.send_message(
            "\n".join(lines) or "서버 일지가 비어 있습니다.", ephemeral=True
        )

    @diaryGroup.command(name="show", description="Open one server-life entry.")
    async def diaryShow(self, interaction: discord.Interaction, entry_id: str) -> None:
        if not await self._requireFriendAccess(interaction):
            return
        entry = await asyncio.to_thread(self.diaryStore.get, entry_id)
        if not entry:
            await interaction.response.send_message("일지를 찾지 못했습니다.", ephemeral=True)
            return
        await self._sendDiaryEntry(interaction, entry)

    # --- on-demand score ----------------------------------------------
    @internalAction(
        name="server-score", description="Calculate an on-demand 0-100 server health score."
    )
    async def serverScore(self, interaction: discord.Interaction) -> None:
        if not await self._requireFriendAccess(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            systemMetrics, throttleFlags = await asyncio.gather(
                asyncio.to_thread(readSystemMetrics),
                asyncio.to_thread(readThrottleFlags),
            )
            usedMemory = systemMetrics.memoryTotalBytes - systemMetrics.memoryAvailableBytes
            memoryPercent = (
                usedMemory / systemMetrics.memoryTotalBytes * 100
                if systemMetrics.memoryTotalBytes
                else 100.0
            )
            normalizedLoad = systemMetrics.load5 / max(systemMetrics.cpuCount, 1)
            throttleText = " ".join(throttleFlags).lower()
            currentThrottle = "현재" in throttleText or "current" in throttleText
            historicalThrottle = "과거" in throttleText or "past" in throttleText

            rconOnline = True
            tps = None
            try:
                tps = parseTps(await _rcon("tps"))
            except RconError:
                rconOnline = False

            diskFreePercent = None
            storagePath = Path(cfg.storage_root)
            if cfg.require_storage_mount and not os.path.ismount(storagePath):
                diskFreePercent = 0.0
            elif storagePath.exists():
                usage = await asyncio.to_thread(shutil.disk_usage, storagePath)
                diskFreePercent = usage.free / usage.total * 100 if usage.total else 0.0

            result = calculateHealthScore(
                HealthInputs(
                    rconOnline=rconOnline,
                    tps=tps,
                    temperatureCelsius=systemMetrics.temperatureCelsius,
                    memoryPercent=memoryPercent,
                    diskFreePercent=diskFreePercent,
                    normalizedLoad5=normalizedLoad,
                    currentThrottle=currentThrottle,
                    historicalThrottle=historicalThrottle,
                )
            )
            color = OK_GREEN if result.score >= 90 else WARN_YELLOW if result.score >= 60 else ERR_RED
            details = "\n".join(f"• {item}" for item in result.deductions) or "감점 요인이 없습니다."
            embed = discord.Embed(
                title=f"서버 건강 점수 {result.score}/100 · {result.grade}",
                description=details,
                color=color,
            )
            embed.add_field(name="TPS", value="n/a" if tps is None else f"{tps:.1f}")
            embed.add_field(name="메모리", value=f"{memoryPercent:.1f}%")
            embed.add_field(
                name="CPU 온도",
                value=(
                    "n/a"
                    if systemMetrics.temperatureCelsius is None
                    else f"{systemMetrics.temperatureCelsius:.1f}°C"
                ),
            )
            embed.set_footer(text="명령 실행 시 한 번만 측정하며 백그라운드 폴링하지 않습니다.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except (OSError, RuntimeError, ValueError) as error:
            await interaction.followup.send(f"❌ 건강 점수 계산 실패: {error}", ephemeral=True)

    # --- button-panel adapters ---------------------------------------
    async def panelLinkStatus(self, interaction: discord.Interaction) -> None:
        """Show every approved profile assigned to the current Discord user."""
        links = await asyncio.to_thread(
            self.linkStore.listForUser, interaction.user.id
        )
        if not links:
            await interaction.response.send_message(
                "등록된 Minecraft 계정이 없습니다. 관리자에게 등록을 요청하세요.",
                ephemeral=True,
            )
            return
        lines = [
            f"• `{link.minecraftName}` — "
            f"{'Java (PC)' if link.edition == 'java' else 'Bedrock (모바일/콘솔)'}"
            for link in links
        ]
        await interaction.response.send_message(
            "**내 계정 목록**\n" + "\n".join(lines),
            ephemeral=True,
        )

    async def panelLinksForUser(self, discordUserId: int) -> list[PlayerLink]:
        """Return every profile so the private admin panel can manage it."""
        return await asyncio.to_thread(
            self.linkStore.listForUser, discordUserId, False
        )

    async def panelAddManagedLink(
        self,
        interaction: discord.Interaction,
        discordUserId: int,
        minecraftName: str,
        edition: str,
    ) -> None:
        """Directly assign and whitelist one profile selected by an admin."""
        if not await self._requireAdmin(interaction):
            return
        link = None
        try:
            if edition == "bedrock" and self.appSettings.serverMode != "java_bedrock":
                raise ValueError(
                    "현재 서버가 Java 전용입니다. 먼저 Java + Bedrock 모드를 켜세요."
                )
            link = await asyncio.to_thread(
                self.linkStore.addManaged,
                discordUserId,
                minecraftName,
                edition,
                interaction.user.id,
            )
            whitelistOutput = await _rcon(buildWhitelistCommand(link))
            loweredOutput = whitelistOutput.casefold()
            if "unknown command" in loweredOutput or "unknown or incomplete" in loweredOutput:
                raise RuntimeError(
                    "Minecraft가 접속 허용 명령을 거부했습니다. 서버 설정을 확인하세요."
                )
            editionLabel = (
                "Java (PC)" if link.edition == "java" else "Bedrock (모바일/콘솔)"
            )
            await interaction.followup.send(
                f"✅ <@{discordUserId}>에게 **{editionLabel}** 계정 "
                f"`{link.minecraftName}`을 등록했습니다.\n"
                "같은 Discord 사용자에게 다른 계정도 계속 추가할 수 있습니다.",
                view=ManagedAccountView(
                    self,
                    interaction.user.id,
                    discordUserId,
                    await self.panelLinksForUser(discordUserId),
                ),
                ephemeral=True,
            )
            _log.info(
                "managed link added by %s for %s -> %s",
                userTag(interaction.user),
                discordUserId,
                link.minecraftName,
            )
        except (ValueError, OSError, RuntimeError, RconError) as error:
            if link is not None:
                await asyncio.to_thread(self.linkStore.removeLink, link.linkId)
            await interaction.followup.send(f"❌ 계정 등록 실패: {error}", ephemeral=True)

    async def panelRemoveManagedLink(
        self, interaction: discord.Interaction, linkId: str
    ) -> None:
        """Remove only the selected profile and its matching whitelist entry."""
        if not await self._requireAdmin(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            link = await asyncio.to_thread(self.linkStore.getById, linkId)
            if not link:
                raise KeyError("선택한 계정이 이미 삭제되었거나 없습니다.")
            whitelistOutput = await _rcon(buildWhitelistRemoveCommand(link))
            loweredOutput = whitelistOutput.casefold()
            if "unknown command" in loweredOutput or "unknown or incomplete" in loweredOutput:
                raise RuntimeError(
                    "Minecraft가 접속 허용 해제 명령을 거부했습니다. 서버 설정을 확인하세요."
                )
            removed = await asyncio.to_thread(self.linkStore.removeLink, linkId)
            if not removed:
                raise RuntimeError("계정 정보를 저장소에서 삭제하지 못했습니다.")
            await interaction.followup.send(
                f"✅ `{link.minecraftName}` 계정만 삭제했습니다. "
                "같은 Discord 사용자의 다른 계정은 유지됩니다.",
                view=ManagedAccountView(
                    self,
                    interaction.user.id,
                    link.discordUserId,
                    await self.panelLinksForUser(link.discordUserId),
                ),
                ephemeral=True,
            )
            _log.info(
                "managed link removed by %s -> %s",
                userTag(interaction.user),
                link.minecraftName,
            )
        except (KeyError, ValueError, OSError, RuntimeError, RconError) as error:
            await interaction.followup.send(f"❌ 계정 삭제 실패: {error}", ephemeral=True)

    async def panelRescueSpawn(
        self, interaction: discord.Interaction, linkId: str
    ) -> None:
        """Reuse the bounded self-rescue command from a button callback."""
        await self.rescueSpawn(interaction, linkId)

    async def panelWhereAmI(
        self, interaction: discord.Interaction, linkId: str
    ) -> None:
        """Reuse the linked-player location lookup from a button callback."""
        await self.rescueWhereAmI(interaction, linkId)

    async def panelServerScore(self, interaction: discord.Interaction) -> None:
        """Reuse the on-demand health calculation from a button callback."""
        await self.serverScore(interaction)

    async def panelPlaces(self) -> list[Place]:
        """Return coordinate choices for the panel dropdown."""
        return await asyncio.to_thread(self.placeStore.list)

    async def panelShowPlace(
        self, interaction: discord.Interaction, name: str
    ) -> None:
        """Open a selected coordinate card."""
        place = await asyncio.to_thread(self.placeStore.get, name)
        if not place:
            await interaction.response.send_message("좌표를 찾지 못했습니다.", ephemeral=True)
            return
        await self._sendPlace(interaction, place)

    async def panelDeletePlace(
        self, interaction: discord.Interaction, name: str
    ) -> None:
        """Delete a selected coordinate while preserving its ownership rule."""
        try:
            place = await asyncio.to_thread(self.placeStore.get, name)
            if not place:
                await interaction.response.send_message("좌표를 찾지 못했습니다.", ephemeral=True)
                return
            if not _isAdmin(interaction) and place.createdBy != interaction.user.id:
                await interaction.response.send_message(
                    "⛔ 등록자 또는 관리자만 삭제할 수 있습니다.", ephemeral=True
                )
                return
            deleted = await asyncio.to_thread(self.placeStore.delete, name)
            await asyncio.to_thread(
                self.imageStore.remove, deleted.imagePath if deleted else None
            )
            await interaction.response.send_message("✅ 좌표를 삭제했습니다.", ephemeral=True)
        except (ValueError, OSError, RuntimeError) as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    async def panelSaveCurrentPlace(
        self,
        interaction: discord.Interaction,
        linkId: str,
        name: str,
        description: str,
    ) -> None:
        """Read the linked player's current position and store it under a short name."""
        link = await self._approvedLink(interaction, linkId)
        if not link:
            return
        try:
            playerName = serverPlayerName(
                link, self.appSettings.bedrockUsernamePrefix
            )
            playerTarget = buildPlayerSelector(playerName)
            positionOutput, dimensionOutput = await asyncio.gather(
                _rcon(f"data get entity {playerTarget} Pos"),
                _rcon(f"data get entity {playerTarget} Dimension"),
            )
            dimension, x, y, z = parsePosition(positionOutput, dimensionOutput)
            place, previous = await asyncio.to_thread(
                self.placeStore.save,
                name,
                dimension,
                round(x),
                round(y),
                round(z),
                description,
                None,
                interaction.user.id,
            )
            if previous and previous.imagePath:
                await asyncio.to_thread(self.imageStore.remove, previous.imagePath)
            await asyncio.to_thread(
                self.diaryStore.record,
                "place",
                f"Saved {place.name} at {place.dimension} {place.x} {place.y} {place.z}.",
                interaction.user.id,
            )
            await self._sendPlace(interaction, place)
        except (ValueError, OSError, RuntimeError, RconError) as error:
            await interaction.followup.send(f"❌ {error}", ephemeral=True)

    async def panelDiaryEntries(self) -> list[DiaryEntry]:
        """Return recent diary entries for the panel dropdown."""
        return await asyncio.to_thread(self.diaryStore.recent, 25)

    async def panelShowDiary(
        self, interaction: discord.Interaction, entryId: str
    ) -> None:
        """Open one selected diary entry."""
        entry = await asyncio.to_thread(self.diaryStore.get, entryId)
        if not entry:
            await interaction.response.send_message("일지를 찾지 못했습니다.", ephemeral=True)
            return
        await self._sendDiaryEntry(interaction, entry)

    async def panelAddDiary(
        self, interaction: discord.Interaction, message: str
    ) -> None:
        """Record a text-only diary entry submitted through a modal."""
        if not await self._requireFriendAccess(interaction):
            return
        try:
            entry = await asyncio.to_thread(
                self.diaryStore.record,
                "note",
                message,
                interaction.user.id,
            )
            await self._sendDiaryEntry(interaction, entry)
        except (ValueError, OSError, RuntimeError) as error:
            await interaction.followup.send(f"❌ {error}", ephemeral=True)

    async def panelUploadPlacePhoto(
        self,
        interaction: discord.Interaction,
        name: str,
        attachment: discord.Attachment,
    ) -> None:
        """Replace the photo of a selected coordinate via the upload-only command."""
        if not await self._requireFriendAccess(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        imagePath = None
        stored = False
        try:
            place = await asyncio.to_thread(self.placeStore.get, name)
            if not place:
                raise ValueError("좌표를 찾지 못했습니다.")
            if not _isAdmin(interaction) and place.createdBy != interaction.user.id:
                raise ValueError("등록자 또는 관리자만 사진을 바꿀 수 있습니다.")
            imagePath = await self._saveAttachment(attachment)
            updated, previous = await asyncio.to_thread(
                self.placeStore.save,
                place.name,
                place.dimension,
                place.x,
                place.y,
                place.z,
                place.description,
                imagePath,
                place.createdBy,
            )
            stored = True
            if previous and previous.imagePath != imagePath:
                await asyncio.to_thread(self.imageStore.remove, previous.imagePath)
            await self._sendPlace(interaction, updated)
        except (ValueError, OSError, RuntimeError, discord.HTTPException) as error:
            if not stored:
                await asyncio.to_thread(self.imageStore.remove, imagePath)
            await interaction.followup.send(f"❌ {error}", ephemeral=True)

    async def panelUploadDiaryPhoto(
        self,
        interaction: discord.Interaction,
        message: str,
        attachment: discord.Attachment,
    ) -> None:
        """Create a photo diary entry through the attachment-only command group."""
        if not await self._requireFriendAccess(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        imagePath = None
        stored = False
        try:
            imagePath = await self._saveAttachment(attachment)
            entry = await asyncio.to_thread(
                self.diaryStore.record,
                "note",
                message,
                interaction.user.id,
                imagePath,
            )
            stored = True
            await self._sendDiaryEntry(interaction, entry)
        except (ValueError, OSError, RuntimeError, discord.HTTPException) as error:
            if not stored:
                await asyncio.to_thread(self.imageStore.remove, imagePath)
            await interaction.followup.send(f"❌ {error}", ephemeral=True)


    async def panelDeathboxLocate(
        self, interaction: discord.Interaction, linkId: str
    ) -> None:
        """Show the newest death box for the selected account via RCON."""
        link = await self._approvedLink(interaction, linkId)
        if not link:
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            playerName = serverPlayerName(
                link, self.appSettings.bedrockUsernamePrefix
            )
            reply = await _rcon(f"deathbox locate {playerName}")
            cleaned = _stripMinecraftColors(reply)
            await interaction.followup.send(f"📦 {cleaned}", ephemeral=True)
        except RconError as error:
            await interaction.followup.send(f"❌ {error}", ephemeral=True)

    async def panelDeathboxList(
        self, interaction: discord.Interaction, linkId: str
    ) -> None:
        """List all active death boxes for the selected account via RCON."""
        link = await self._approvedLink(interaction, linkId)
        if not link:
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            playerName = serverPlayerName(
                link, self.appSettings.bedrockUsernamePrefix
            )
            reply = await _rcon(f"deathbox list {playerName}")
            cleaned = _stripMinecraftColors(reply)
            await interaction.followup.send(f"📦 {cleaned}", ephemeral=True)
        except RconError as error:
            await interaction.followup.send(f"❌ {error}", ephemeral=True)


def _stripMinecraftColors(text: str) -> str:
    """Remove Minecraft section-sign colour codes from RCON output."""
    import re
    return re.sub(r"§[0-9a-fk-or]", "", text)


async def setup(bot: commands.Bot) -> None:
    """Register the isolated friend-facing command surface."""
    await bot.add_cog(Friend(bot))
