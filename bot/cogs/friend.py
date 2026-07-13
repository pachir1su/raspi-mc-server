"""Narrow friend-safe Discord commands backed by approved player links."""

import asyncio
import os
import shutil
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from bot import BRAND_BLUE, ERR_RED, OK_GREEN, WARN_YELLOW, log, userTag
from bot.config import cfg
from bot.diary import DiaryEntry, DiaryStore
from bot.health_score import HealthInputs, calculateHealthScore
from bot.performance_report import parseTps
from bot.places import (
    MAX_IMAGE_BYTES,
    ImageStore,
    Place,
    PlaceStore,
    buildMapLink,
)
from bot.player_links import PlayerLink, PlayerLinkStore
from bot.rcon import Rcon, RconError
from bot.rescue import buildSpawnCommand, parsePosition
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

    linkGroup = app_commands.Group(
        name="link", description="Link Discord to one Minecraft account."
    )
    rescueGroup = app_commands.Group(
        name="rescue", description="Self-service help for your linked player."
    )
    placeGroup = app_commands.Group(
        name="place", description="Shared coordinate book with photos and map links."
    )
    diaryGroup = app_commands.Group(
        name="diary", description="Shared server-life journal."
    )

    def __init__(self, bot: commands.Bot):
        # Keep every friend-facing store outside the large admin cog.
        self.bot = bot
        self.linkStore = PlayerLinkStore(cfg.state_dir)
        self.placeStore = PlaceStore(cfg.state_dir)
        self.diaryStore = DiaryStore(cfg.state_dir)
        self.imageStore = ImageStore(cfg.state_dir)

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
        await interaction.response.send_message(
            "⛔ 관리자만 실행할 수 있습니다.", ephemeral=True
        )
        _log.warning("denied friend-admin command from %s", userTag(interaction.user))
        return False

    async def _approvedLink(
        self, interaction: discord.Interaction, respond: bool = True
    ) -> PlayerLink | None:
        """Resolve the approved Minecraft identity for this Discord user."""
        link = await asyncio.to_thread(self.linkStore.get, interaction.user.id)
        if link and link.approved:
            return link
        if respond:
            message = (
                "⏳ 관리자의 연동 승인을 기다리는 중입니다."
                if link
                else "❌ 먼저 `/link request <마크닉>`으로 연동을 요청하세요."
            )
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

    # --- Discord ↔ Minecraft links ------------------------------------
    @linkGroup.command(name="request", description="Request a link to your Minecraft name.")
    @app_commands.describe(minecraft_name="Your exact Java Edition player name")
    async def linkRequest(
        self, interaction: discord.Interaction, minecraft_name: str
    ) -> None:
        try:
            link = await asyncio.to_thread(
                self.linkStore.request, interaction.user.id, minecraft_name
            )
            await interaction.response.send_message(
                f"✅ `{link.minecraftName}` 연동을 요청했습니다. 관리자 승인을 기다려 주세요.",
                ephemeral=True,
            )
            _log.info("link requested by %s -> %s", userTag(interaction.user), link.minecraftName)
        except (ValueError, OSError, RuntimeError) as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @linkGroup.command(name="status", description="Show your current link status.")
    async def linkStatus(self, interaction: discord.Interaction) -> None:
        link = await asyncio.to_thread(self.linkStore.get, interaction.user.id)
        if not link:
            await interaction.response.send_message("연동 요청이 없습니다.", ephemeral=True)
            return
        state = "승인됨" if link.approved else "승인 대기"
        await interaction.response.send_message(
            f"**마크닉:** `{link.minecraftName}`\n**상태:** {state}", ephemeral=True
        )

    @linkGroup.command(name="approve", description="Approve one pending player link (admin).")
    async def linkApprove(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        if not await self._requireAdmin(interaction):
            return
        try:
            link = await asyncio.to_thread(
                self.linkStore.approve, user.id, interaction.user.id
            )
            await interaction.response.send_message(
                f"✅ {user.mention} ↔ `{link.minecraftName}` 연동을 승인했습니다.",
                ephemeral=True,
            )
            _log.info("link approved by %s for %s", userTag(interaction.user), user.id)
        except (KeyError, ValueError, OSError, RuntimeError) as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @linkGroup.command(name="revoke", description="Revoke a player link (admin).")
    async def linkRevoke(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        if not await self._requireAdmin(interaction):
            return
        removed = await asyncio.to_thread(self.linkStore.remove, user.id)
        message = "✅ 연동을 해제했습니다." if removed else "해제할 연동이 없습니다."
        await interaction.response.send_message(message, ephemeral=True)
        _log.info("link revoke by %s for %s -> %s", userTag(interaction.user), user.id, removed)

    @linkGroup.command(name="list", description="List pending and approved links (admin).")
    async def linkList(self, interaction: discord.Interaction) -> None:
        if not await self._requireAdmin(interaction):
            return
        links = await asyncio.to_thread(self.linkStore.list)
        lines = [
            f"{'✅' if item.approved else '⏳'} <@{item.discordUserId}> ↔ `{item.minecraftName}`"
            for item in links[:40]
        ]
        if len(links) > 40:
            lines.append(f"…외 {len(links) - 40}개")
        await interaction.response.send_message(
            "\n".join(lines) or "연동 요청이 없습니다.", ephemeral=True
        )

    # --- linked-player rescue -----------------------------------------
    @rescueGroup.command(name="spawn", description="Teleport only your linked player to spawn.")
    async def rescueSpawn(self, interaction: discord.Interaction) -> None:
        link = await self._approvedLink(interaction)
        if not link:
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            destination = cfg.rescueDestination()
            output = await _rcon(buildSpawnCommand(link.minecraftName, destination))
            await asyncio.to_thread(
                self.diaryStore.record,
                "rescue",
                f"{link.minecraftName} returned to configured spawn.",
                interaction.user.id,
            )
            await interaction.followup.send(
                f"✅ `{link.minecraftName}`만 스폰으로 이동했습니다.\n`{output.strip() or 'done'}`",
                ephemeral=True,
            )
            _log.info("self rescue by %s -> %s", userTag(interaction.user), link.minecraftName)
        except (ValueError, RconError, OSError, RuntimeError) as error:
            await interaction.followup.send(f"❌ {error}", ephemeral=True)

    @rescueGroup.command(name="whereami", description="Show your linked player's current location.")
    async def rescueWhereAmI(self, interaction: discord.Interaction) -> None:
        link = await self._approvedLink(interaction)
        if not link:
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            positionOutput, dimensionOutput = await asyncio.gather(
                _rcon(f"data get entity {link.minecraftName} Pos"),
                _rcon(f"data get entity {link.minecraftName} Dimension"),
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
    @app_commands.command(
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


async def setup(bot: commands.Bot) -> None:
    """Register the isolated friend-facing command surface."""
    await bot.add_cog(Friend(bot))
