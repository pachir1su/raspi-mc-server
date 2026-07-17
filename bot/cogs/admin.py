"""Admin-only slash commands.

Every command here is gated to the user IDs in ADMIN_USER_IDS. Put only
your own ID there to be the sole operator: then the raw ``/mc`` command
(which runs ANY server command through RCON) is effectively "only I can
cheat", while in-game everyone else is a non-op who cannot run commands.

Read-only status is also admin-gated by default to keep the bot quiet in a
small private server; loosen the check if you want players to see status.
"""

import asyncio
import subprocess
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks

from bot import log
from bot import BRAND_BLUE, OK_GREEN, WARN_YELLOW, ERR_RED, userTag
from bot.audit import AuditLog
from bot.config import cfg
from bot.error_text import describeError
from bot.i18n import t
from bot.internal_actions import InternalActionGroup, internalAction
from bot.backup_settings import SettingsStore
from bot.control_panel import (
    AdminDashboardView,
    HomeButton,
    LogPanelView,
    PlayerPanelView,
    replaceScreen,
    sendScreen,
)
from bot.log_viewer import discordPreview, filterImportant, readTail
from bot.loading import animate_while
from bot.player_info import (
    parseOnlinePlayers,
    summarizeEffects,
    summarizeEnderChest,
    summarizeInventorySections,
    summarizePlayerStats,
)
from bot.player_names import buildPlayerSelector, validateServerPlayerName
from bot.performance_report import parseTps, shouldAlert
from bot.places import PlaceStore
from bot.public_panel import PublicServerView
from bot.quick_commands import (
    COMMON_EFFECTS,
    DEFAULT_ON_GAMERULES,
    DIFFICULTIES,
    GAMEMODES,
    GAMERULES,
    GAMERULE_UNSUPPORTED_MESSAGE,
    SCOREBOARD_STATS,
    SPAWN_RADIUS_ZERO_COMMAND,
    buildDifficultyCommand,
    buildEffectClearCommand,
    buildEffectCommand,
    buildEnchantCommand,
    buildForceEnchantCommand,
    buildGamemodeCommand,
    buildGameruleQueryCommand,
    buildGameruleSetCommand,
    buildGiveCommand,
    buildHealCommands,
    buildInvincibilityClearCommands,
    buildInvincibilityCommands,
    buildKickCommand,
    buildScoreboardGetCommand,
    buildScoreboardSetupCommands,
    buildTeleportToCoordsCommand,
    buildTeleportToPlayerCommand,
    buildWorldSpawnCommand,
    buildXpCommand,
    ensureGameruleAccepted,
    ensureServerAccepted,
    parseDaysPlayed,
    parseGameruleValue,
    parseScoreboardValue,
)
from bot.rescue import buildAutomaticSpawnCommand, ensureRescueSucceeded, parsePosition
from bot.rcon import (
    Rcon,
    RconAuthError,
    RconConnectionError,
    RconError,
    RconTimeout,
)
from bot.system_metrics import (
    formatDuration,
    readSystemMetrics,
    readThrottleFlags,
    stripMinecraftFormatting,
)
from bot.update_manager import (
    MAX_ARCHIVE_BYTES,
    ReleaseInfo,
    UpdateError,
    UpdateStore,
    fetchLatestRelease,
)
from bot.update_ui import UpdateConfirmView
from bot.world_storage import StorageError, WorldStorage

_log = log.get("cog.admin")
PUBLIC_COMMANDS = {"server", "portal", "online"}

# 접속자가 0명이면 자동 백업 주기를 이 배수만큼 늘려 부하를 줄입니다(이슈 I, #16).
IDLE_INTERVAL_MULTIPLIER = 4


def _autoBackupDecision(
    playersOnline: int | None,
    worldChanged: bool,
    ageMinutes: float,
    intervalMinutes: int,
) -> str:
    """Decide whether a due auto-backup should run, be skipped, or wait longer.

    playersOnline가 None이면 접속자 수를 확인하지 못한 것이므로(RCON 실패) 안전하게
    평소 주기대로 백업합니다. 반환값: "backup" | "skip_idle_unchanged" | "skip_not_due".
    """
    if playersOnline == 0 and not worldChanged:
        # 아무도 없고 마지막 백업 이후 변경도 없으면 백업할 게 없습니다.
        return "skip_idle_unchanged"
    threshold = intervalMinutes
    if playersOnline == 0:
        # 접속자가 없으면 주기를 넉넉하게 늘립니다.
        threshold = intervalMinutes * IDLE_INTERVAL_MULTIPLIER
    if ageMinutes < threshold:
        return "skip_not_due"
    return "backup"


def _is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.id in cfg.admin_ids


async def _rcon(cmd: str) -> str:
    """Run a single RCON command, opening and closing the connection."""
    async with Rcon(cfg.rcon_host, cfg.rcon_port, cfg.rcon_password) as r:
        return await r.command(cmd)


def _systemctl(action: str) -> tuple[bool, str]:
    """Run 'sudo systemctl <action> <service>' (narrow sudoers rule)."""
    try:
        res = subprocess.run(
            ["sudo", "systemctl", action, cfg.mc_service],
            capture_output=True, text=True, timeout=120,
        )
        ok = res.returncode == 0
        return ok, (res.stdout + res.stderr).strip()
    except (subprocess.SubprocessError, OSError) as e:
        return False, str(e)


def _startUpdater() -> tuple[bool, str]:
    """Queue only the fixed updater unit without waiting for bot restart."""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "start", "--no-block", "raspi-mc-updater.service"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, (result.stdout + result.stderr).strip()
    except (OSError, subprocess.SubprocessError) as error:
        return False, str(error)


class Admin(commands.Cog):
    uploadGroup = app_commands.Group(
        name="upload", description="Upload files that Discord buttons cannot attach."
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settingsStore = SettingsStore(cfg.state_dir)
        self.auditLog = AuditLog(cfg.state_dir)
        self.storage = WorldStorage(
            cfg.storage_root, cfg.server_dir, cfg.require_storage_mount
        )
        self.updateStore = UpdateStore(cfg.state_dir, cfg.storage_root)
        # 접속자 관리의 TP 버튼이 공유 좌표북을 읽습니다(쓰기는 친구 cog 담당).
        self.placeStore = PlaceStore(cfg.state_dir)
        self.operationLock = asyncio.Lock()
        self.lastAlertAt: dict[str, datetime] = {}
        # 게임룰 키 → 이 서버 버전 지원 여부. 빠른 명령 패널을 처음 열 때
        # 한 번 조회해 캐시하고, 미지원 버튼을 비활성화합니다(#59).
        self.supportedGamerules: dict[str, bool] = {}

    @app_commands.command(
        name="server", description="Check server status and online players with buttons."
    )
    async def serverPanel(self, interaction: discord.Interaction) -> None:
        """Open the read-only public panel without command arguments."""
        await sendScreen(
            interaction,
            embed=await self.publicServerEmbed(),
            view=PublicServerView(self, interaction.user.id),
        )

    @app_commands.command(
        name="admin", description="Manage the server, backups, worlds, and friend accounts."
    )
    async def adminPanel(self, interaction: discord.Interaction) -> None:
        """Open the single owner-only entry point for routine operations."""
        await sendScreen(
            interaction,
            embed=await self.panelOverviewEmbed(),
            view=AdminDashboardView(self, interaction.user.id),
        )

    @uploadGroup.command(name="world", description="Upload a Java world ZIP to use on this server.")
    async def uploadWorld(
        self, interaction: discord.Interaction, file: discord.Attachment
    ) -> None:
        """Derive the map name from the file so uploading requires no typing."""
        name = Path(file.filename).stem[:60]
        await self.worldUpload(interaction, name, file)

    @uploadGroup.command(
        name="update", description="Upload a trusted bot program update ZIP."
    )
    async def uploadUpdate(
        self, interaction: discord.Interaction, file: discord.Attachment
    ) -> None:
        """Forward a selected ZIP into the existing verified update flow."""
        await self.updateUpload(interaction, file)

    @uploadGroup.command(
        name="place-photo", description="Add a photo to a saved shared coordinate."
    )
    async def uploadPlacePhoto(
        self, interaction: discord.Interaction, name: str, file: discord.Attachment
    ) -> None:
        """Keep optional coordinate photos while the normal place flow stays button-only."""
        friend = self.bot.get_cog("Friend")
        if friend is None:
            await interaction.response.send_message("친구 도구가 준비되지 않았습니다.", ephemeral=True)
            return
        await friend.panelUploadPlacePhoto(interaction, name, file)

    @uploadGroup.command(
        name="diary", description="Write a server diary entry and attach a photo."
    )
    async def uploadDiaryPhoto(
        self, interaction: discord.Interaction, message: str, file: discord.Attachment
    ) -> None:
        """Preserve the attachment path for the inherently text-based diary feature."""
        friend = self.bot.get_cog("Friend")
        if friend is None:
            await interaction.response.send_message("친구 도구가 준비되지 않았습니다.", ephemeral=True)
            return
        await friend.panelUploadDiaryPhoto(interaction, message, file)

    async def cog_load(self):
        """Start the persistent in-bot scheduler after the cog is ready."""
        self.backupScheduler.start()
        self.performanceAlerts.start()
        # 운영자 기본값: 즉시 리스폰·자연 재생·플레이 일수 표시를 켠 채로
        # 시작합니다. 서버가 아직 안 떠 있을 수 있어 백그라운드에서 재시도.
        self._defaultGamerulesTask = asyncio.create_task(self._applyDefaultGamerules())

    def cog_unload(self):
        """Stop scheduler polling when the extension unloads."""
        self.backupScheduler.cancel()
        self.performanceAlerts.cancel()
        if getattr(self, "_defaultGamerulesTask", None):
            self._defaultGamerulesTask.cancel()

    async def _applyDefaultGamerules(self):
        """Turn the requested default-ON gamerules on once RCON is reachable.

        [유지보수 안내] 기본 ON 목록은 bot/quick_commands.py의
        DEFAULT_ON_GAMERULES 입니다. showDaysPlayed처럼 구버전 마인크래프트에
        없는 게임룰은 실패해도 봇을 막지 않고 경고 로그만 남깁니다.
        이미 켜져 있으면 다시 켜도 부작용이 없어(멱등) 매 시작마다 실행합니다.
        """
        for attempt in range(30):  # 서버 기동을 기다리며 최대 30분 재시도
            try:
                await _rcon("list")
                break
            except RconError:
                await asyncio.sleep(60)
        else:
            _log.warning("default gamerules skipped: RCON unreachable")
            return
        for gameruleKey in DEFAULT_ON_GAMERULES:
            try:
                ensureGameruleAccepted(
                    await _rcon(buildGameruleSetCommand(gameruleKey, True))
                )
                self.supportedGamerules[gameruleKey] = True
                _log.info("default gamerule applied: %s=true", gameruleKey)
            except ValueError as error:
                if str(error) == GAMERULE_UNSUPPORTED_MESSAGE:
                    self.supportedGamerules[gameruleKey] = False
                _log.warning("default gamerule %s failed: %s", gameruleKey, error)
            except RconError as error:
                _log.warning("default gamerule %s failed: %s", gameruleKey, error)
        # 통계 스코어보드 목표(#68)도 서버가 준비된 뒤 만들어 둡니다.
        # 이미 존재하면 서버가 오류 문구를 돌려주지만 무해하므로 넘어갑니다.
        for command in buildScoreboardSetupCommands():
            try:
                await _rcon(command)
            except RconError as error:
                _log.warning("scoreboard setup failed: %s", error)

    async def probeSupportedGamerules(self) -> dict[str, bool]:
        """Ask the server once which panel gamerules exist in this version.

        결과는 캐시되어 이후 패널 열기에서는 RCON을 다시 조회하지 않습니다.
        조회 자체가 실패(RCON 불통)하면 알 수 없는 키는 True로 두어 버튼을
        막지 않습니다 — 실제 토글 시점에 정확한 에러가 다시 안내됩니다.
        """
        for gameruleKey in GAMERULES:
            if gameruleKey in self.supportedGamerules:
                continue
            try:
                ensureGameruleAccepted(
                    await _rcon(buildGameruleQueryCommand(gameruleKey))
                )
                self.supportedGamerules[gameruleKey] = True
            except ValueError as error:
                self.supportedGamerules[gameruleKey] = (
                    str(error) != GAMERULE_UNSUPPORTED_MESSAGE
                )
            except RconError:
                break  # 서버가 꺼져 있으면 나머지 프로브도 의미 없음
        return dict(self.supportedGamerules)

    # A single guard applied to every command in this cog.
    async def cog_check(self, ctx):  # for prefix commands (unused)
        return True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        commandName = interaction.command.name if interaction.command else ""
        qualifiedName = (
            interaction.command.qualified_name if interaction.command else ""
        )
        if commandName in PUBLIC_COMMANDS and cfg.public_commands_enabled:
            return True
        if (
            qualifiedName in {"upload place-photo", "upload diary"}
            and cfg.public_commands_enabled
        ):
            return True
        if _is_admin(interaction):
            return True
        await interaction.response.send_message(
            t("not_authorized"), ephemeral=True
        )
        _log.warning("denied command from %s", userTag(interaction.user))
        return False

    @staticmethod
    def isAdmin(interaction: discord.Interaction) -> bool:
        """Expose the central ADMIN_USER_IDS check to owner-bound views."""
        return _is_admin(interaction)

    async def backupNameAutocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Suggest existing backup basenames and avoid error-prone manual typing."""
        try:
            names = [
                item.name
                for item in await asyncio.to_thread(self.storage.listBackups)
            ]
        except StorageError:
            return []
        currentLower = current.lower()
        return [
            app_commands.Choice(name=name[:100], value=name)
            for name in names if currentLower in name.lower()
        ][:25]

    async def worldNameAutocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Suggest validated map names stored on the HDD."""
        try:
            names = [
                item.name
                for item in await asyncio.to_thread(self.storage.listWorlds)
            ]
        except StorageError:
            return []
        currentLower = current.lower()
        return [
            app_commands.Choice(name=name[:100], value=name)
            for name in names if currentLower in name.lower()
        ][:25]

    async def _audit(
        self,
        interaction: discord.Interaction,
        action: str,
        outcome: str,
        detail: str = "",
    ):
        """Persist privileged actions outside the Discord message history."""
        await asyncio.to_thread(
            self.auditLog.record, action, interaction.user.id, outcome, detail
        )

    def _statusChannel(self):
        """Resolve the optional announcement channel for automatic alerts."""
        if not cfg.status_channel_id:
            return None
        try:
            return self.bot.get_channel(int(cfg.status_channel_id))
        except ValueError:
            return None

    async def _collectPerformanceWarnings(self) -> tuple[list[str], discord.Embed]:
        """Collect actionable Pi/Paper warnings and a detailed report embed."""
        systemMetrics, throttleFlags = await asyncio.gather(
            asyncio.to_thread(readSystemMetrics),
            asyncio.to_thread(readThrottleFlags),
        )
        usedMemory = systemMetrics.memoryTotalBytes - systemMetrics.memoryAvailableBytes
        memoryPercent = (
            usedMemory / systemMetrics.memoryTotalBytes * 100
            if systemMetrics.memoryTotalBytes else 100
        )
        warnings = []
        if (
            systemMetrics.temperatureCelsius is not None
            and systemMetrics.temperatureCelsius >= cfg.alert_temperature_celsius
        ):
            warnings.append(
                f"CPU temperature {systemMetrics.temperatureCelsius:.1f}°C >= "
                f"{cfg.alert_temperature_celsius:.0f}°C"
            )
        if memoryPercent >= cfg.alert_memory_percent:
            warnings.append(
                f"Memory usage {memoryPercent:.1f}% >= "
                f"{cfg.alert_memory_percent:.0f}%"
            )
        if any(
            label.startswith("현재") or label.startswith("Current")
            for label in throttleFlags
        ):
            warnings.append(
                "현재 저전압/스로틀 플래그: " + ", ".join(throttleFlags)
            )
        tpsText = "RCON 연결 불가"
        tpsValue = None
        try:
            tpsText = stripMinecraftFormatting(await _rcon("tps"))
            tpsValue = parseTps(tpsText)
            if tpsValue is not None and tpsValue < cfg.alert_tps_threshold:
                warnings.append(f"TPS {tpsValue:.1f} < {cfg.alert_tps_threshold:.1f}")
        except RconError:
            warnings.append("RCON/TPS 확인 실패")
        hddText = "HDD 확인 불가"
        try:
            total, used, free = await asyncio.to_thread(self.storage.storageUsage)
            hddText = (
                f"{self._formatBytes(used)} / {self._formatBytes(total)} "
                f"(여유 {self._formatBytes(free)})"
            )
            freeGb = free / 1024 ** 3
            if freeGb < cfg.alert_min_free_gb:
                warnings.append(f"HDD 여유 {freeGb:.1f} GB < {cfg.alert_min_free_gb:.0f} GB")
        except StorageError:
            warnings.append("HDD 확인 실패")
        recommendations = []
        if tpsValue is not None and tpsValue < 18:
            recommendations.append(
                "view-distance/simulation-distance를 낮추고 몹 농장이나 "
                "청크 로더를 점검하세요."
            )
        if memoryPercent >= 85:
            recommendations.append(
                "MC_MEMORY를 올리기보다, 먼저 로드된 청크/엔티티를 줄이거나 "
                "한가한 시간에 재시작하세요."
            )
        if systemMetrics.temperatureCelsius is not None and systemMetrics.temperatureCelsius >= 75:
            recommendations.append(
                "플레이어를 더 받기 전에 쿨링, 케이스 공기 흐름, 전원부터 "
                "개선하세요."
            )
        if any("전압" in label or "undervoltage" in label.lower() for label in throttleFlags):
            recommendations.append(
                "더 강한 USB-C 전원 어댑터/케이블을 사용하세요. 저전압은 "
                "렉 스파이크의 원인입니다."
            )
        recommendations.append(
            "Pi 4B 4GB에서는 플레이어 3-4명, 적당한 규모의 농장, 보수적인 "
            "렌더/시뮬레이션 거리를 유지하세요."
        )
        embed = discord.Embed(
            title=t("tuning_title"),
            description=t("tuning_summary"),
            color=ERR_RED if warnings else OK_GREEN,
        )
        embed.add_field(name="TPS", value=f"```{tpsText[:900]}```", inline=False)
        embed.add_field(name="CPU", value=f"온도: {systemMetrics.temperatureCelsius if systemMetrics.temperatureCelsius is not None else 'n/a'}°C\n부하: {systemMetrics.load1:.2f}/{systemMetrics.load5:.2f}/{systemMetrics.load15:.2f}", inline=True)
        embed.add_field(name="메모리", value=f"{self._formatBytes(usedMemory)} / {self._formatBytes(systemMetrics.memoryTotalBytes)} ({memoryPercent:.1f}%)", inline=True)
        embed.add_field(name="HDD", value=hddText, inline=False)
        embed.add_field(name="전원·스로틀", value=", ".join(throttleFlags), inline=False)
        embed.add_field(name="권장 조치", value="\n".join(f"• {item}" for item in recommendations)[:1000], inline=False)
        return warnings, embed

    # --- player-facing portal ------------------------------------------
    @internalAction(name="portal", description="Show friend-safe server access info and live status.")
    async def portal(self, interaction: discord.Interaction):
        players = []
        statusText = t("portal_offline")
        try:
            listOutput = await _rcon("list")
            players = parseOnlinePlayers(listOutput)
            statusText = listOutput
        except RconError:
            pass
        color = OK_GREEN if statusText != t("portal_offline") else WARN_YELLOW
        embed = discord.Embed(
            title=t("portal_title"),
            description=t("portal_description"),
            color=color,
        )
        embed.add_field(
            name=t("portal_address"),
            value=cfg.public_address or t("portal_address_missing"),
            inline=False,
        )
        embed.add_field(name=t("portal_version"), value=cfg.public_version, inline=True)
        embed.add_field(
            name=t("portal_online"),
            value=", ".join(players) if players else t("online_none"),
            inline=False,
        )
        embed.set_footer(text=statusText[:200])
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @internalAction(name="online", description="Show who is online without exposing admin controls.")
    async def online(self, interaction: discord.Interaction):
        try:
            players = parseOnlinePlayers(await _rcon("list"))
            body = "\n".join(f"• {player}" for player in players) or t("online_none")
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=t("online_title"), description=body, color=OK_GREEN
                ),
                ephemeral=True,
            )
        except RconError as error:
            await interaction.response.send_message(f"❌ {describeError(error)}", ephemeral=True)

    # --- read-only ------------------------------------------------------
    @internalAction(description="Show whether the server is up and who is online.")
    async def status(self, interaction: discord.Interaction):
        try:
            out = await _rcon("list")
            e = discord.Embed(title="🟢 서버 온라인", description=out, color=OK_GREEN)
        except RconAuthError as error:
            # 연결은 됐지만 비밀번호 불일치 — 설정 문제라 사용자에게 따로 안내.
            _log.warning("status RCON auth failed: %s", error)
            e = discord.Embed(
                title="🟠 RCON 인증 실패",
                description=(
                    "서버는 응답하지만 RCON 비밀번호가 일치하지 않습니다.\n"
                    "`.env`의 `RCON_PASSWORD`와 `server.properties`의 "
                    "`rcon.password`가 같은지 확인하세요."
                ),
                color=WARN_YELLOW,
            )
        except RconTimeout as error:
            # TCP는 열렸지만 응답이 늦음 — 대개 기동 중이거나 과부하.
            _log.warning("status RCON timed out: %s", error)
            e = discord.Embed(
                title="🟠 서버 응답 지연",
                description="RCON 연결은 됐지만 응답이 늦습니다 — 서버가 기동 중이거나 과부하일 수 있습니다.",
                color=WARN_YELLOW,
            )
        except RconError as error:
            _log.info("status RCON unreachable: %s", error)
            e = discord.Embed(
                title="🔴 서버 오프라인",
                description="RCON에 연결할 수 없습니다 — 서버가 꺼져 있거나 시작 중입니다.",
                color=ERR_RED,
            )
        await interaction.response.send_message(embed=e)
        _log.info("status by %s", userTag(interaction.user))

    # --- broadcast / commands ------------------------------------------
    @internalAction(description="Broadcast a message to everyone in-game.")
    @app_commands.describe(message="Text to say in chat")
    async def say(self, interaction: discord.Interaction, message: str):
        try:
            await _rcon(f"say {message}")
            await interaction.response.send_message(f"📢 공지 전송: {message}", ephemeral=True)
            _log.info("say by %s: %s", userTag(interaction.user), message)
            await self._audit(interaction, "server.say", "success")
        except RconError as e:
            await self._audit(interaction, "server.say", "failed", str(e))
            await interaction.response.send_message(f"❌ {describeError(e)}", ephemeral=True)

    @internalAction(name="mc", description="Run ANY server command via RCON (owner cheat channel).")
    @app_commands.describe(command="e.g. gamemode creative YourName, time set day, give ...")
    async def mc(self, interaction: discord.Interaction, command: str):
        # This is the "only I can cheat" channel: it runs at op level 4.
        try:
            out = await _rcon(command)
            body = out.strip() or "(출력 없음)"
            e = discord.Embed(
                title="🎛️ 명령 실행 완료",
                description=f"`/{command}`\n```\n{body[:1800]}\n```",
                color=BRAND_BLUE,
            )
            await interaction.response.send_message(embed=e)
            _log.info("mc by %s: %s", userTag(interaction.user), command)
            commandName = command.split(maxsplit=1)[0] if command.strip() else "empty"
            await self._audit(interaction, "server.command", "success", commandName)
        except RconError as e:
            await self._audit(interaction, "server.command", "failed", str(e))
            await interaction.response.send_message(f"❌ {describeError(e)}", ephemeral=True)

    # --- whitelist ------------------------------------------------------
    whitelist = InternalActionGroup()

    @whitelist.command(name="add", description="Whitelist a player by name.")
    async def wl_add(self, interaction: discord.Interaction, name: str):
        await self._wl(interaction, "add", name)

    @whitelist.command(name="remove", description="Remove a player from the whitelist.")
    async def wl_remove(self, interaction: discord.Interaction, name: str):
        await self._wl(interaction, "remove", name)

    async def _wl(self, interaction, action, name):
        try:
            out = await _rcon(f"whitelist {action} {name}")
            await interaction.response.send_message(f"✅ {out.strip() or f'whitelist {action} {name}'}")
            _log.info("whitelist %s %s by %s", action, name, userTag(interaction.user))
            await self._audit(interaction, f"whitelist.{action}", "success", name)
        except RconError as e:
            await self._audit(interaction, f"whitelist.{action}", "failed", str(e))
            await interaction.response.send_message(f"❌ {describeError(e)}", ephemeral=True)

    # --- lifecycle (systemd) -------------------------------------------
    @internalAction(description="Start the Minecraft service.")
    async def start(self, interaction: discord.Interaction):
        await self._lifecycle(interaction, "start", "서버 시작 중")

    @internalAction(description="Stop the Minecraft service (saves first).")
    async def stop(self, interaction: discord.Interaction):
        # Best-effort graceful save before systemd stops the JVM.
        try:
            await _rcon("save-all")
        except RconError:
            pass
        await self._lifecycle(interaction, "stop", "서버 정지 중")

    @internalAction(description="Restart the Minecraft service.")
    async def restart(self, interaction: discord.Interaction):
        await self._lifecycle(interaction, "restart", "서버 재시작 중")

    async def _lifecycle(self, interaction, action, label):
        async def work():
            return await asyncio.to_thread(_systemctl, action)

        ok, out = await animate_while(interaction, work(), label)
        color = OK_GREEN if ok else ERR_RED
        mark = "✅" if ok else "❌"
        e = discord.Embed(
            title=f"{mark} {label}",
            description=f"```\n{(out or '완료')[:1500]}\n```",
            color=color,
        )
        await interaction.edit_original_response(embed=e)
        _log.info("%s by %s -> ok=%s", action, userTag(interaction.user), ok)
        await self._audit(
            interaction, f"service.{action}", "success" if ok else "failed", out
        )

    # --- HDD backups ----------------------------------------------------
    backupGroup = InternalActionGroup()

    async def _safeBackup(self, label: str):
        """Flush Paper through RCON, archive the worlds, and always resume saving."""
        serverRunning = False
        try:
            await _rcon("save-off")
            serverRunning = True
            await _rcon("save-all flush")
            await asyncio.sleep(2)
        except RconError:
            _log.info("RCON unavailable; backing up a stopped server")
        try:
            return await self.storage.createBackup(self.settingsStore.load(), label)
        finally:
            if serverRunning:
                try:
                    await _rcon("save-on")
                except RconError:
                    _log.exception("failed to re-enable Paper saving")

    @backupGroup.command(name="create", description="Create a safe world backup now.")
    async def backupCreate(self, interaction: discord.Interaction):
        async def work():
            async with self.operationLock:
                return await self._safeBackup("manual")

        try:
            archivePath = await animate_while(interaction, work(), "월드 백업 중")
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="✅ 백업 완료",
                    description=f"`{archivePath.name}`",
                    color=OK_GREEN,
                )
            )
            _log.info("backup create by %s: %s", userTag(interaction.user), archivePath.name)
            await self._audit(interaction, "backup.create", "success", archivePath.name)
        except (StorageError, RuntimeError) as error:
            await self._audit(interaction, "backup.create", "failed", str(error))
            await self._editError(interaction, error)

    @backupGroup.command(name="list", description="List the newest HDD backups.")
    async def backupList(self, interaction: discord.Interaction):
        try:
            backups = await asyncio.to_thread(self.storage.listBackups)
            lines = [
                f"`{item.name}` — {self._formatBytes(item.size)} — <t:{int(item.modifiedAt.timestamp())}:R>"
                for item in backups[:20]
            ]
            await interaction.response.send_message(
                "\n".join(lines) or "아직 백업이 없습니다.", ephemeral=True
            )
        except StorageError as error:
            await interaction.response.send_message(f"❌ {describeError(error)}", ephemeral=True)

    @backupGroup.command(name="timeline", description="Show a compact backup timeline with ages and sizes.")
    async def backupTimeline(self, interaction: discord.Interaction):
        try:
            backups = await asyncio.to_thread(self.storage.listBackups)
            if not backups:
                await interaction.response.send_message("아직 백업이 없습니다.", ephemeral=True)
                return
            lines = []
            for index, item in enumerate(backups[:10], start=1):
                lines.append(
                    f"**{index}.** `{item.name}` — "
                    f"{self._formatBytes(item.size)} — "
                    f"<t:{int(item.modifiedAt.timestamp())}:R>"
                )
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=t("backup_timeline_title"),
                    description="\n".join(lines),
                    color=BRAND_BLUE,
                ),
                ephemeral=True,
            )
        except StorageError as error:
            await interaction.response.send_message(f"❌ {describeError(error)}", ephemeral=True)

    @backupGroup.command(name="restore-preview", description="Verify and preview a backup before restoring it.")
    @app_commands.autocomplete(name=backupNameAutocomplete)
    async def backupRestorePreview(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        try:
            path = self.storage.resolveBackup(name)
            digest = await asyncio.to_thread(self.storage.verifyBackup, name)
            description = (
                f"{t('restore_preview_ok')}\n"
                f"파일: `{path.name}`\n"
                f"크기: **{self._formatBytes(path.stat().st_size)}**\n"
                f"SHA-256: `{digest}`\n\n"
                "실제 복구는 서버를 정지하고 현재 월드를 교체합니다. 준비됐을 때만 `/backup restore`에서 확인문구에 `RESTORE`를 입력해 실행하세요."
            )
            await interaction.followup.send(
                embed=discord.Embed(
                    title=t("restore_preview_title"),
                    description=description[:4000],
                    color=OK_GREEN,
                ),
                ephemeral=True,
            )
        except StorageError as error:
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)

    @backupGroup.command(name="download", description="Download a backup if it fits Discord's limit.")
    @app_commands.autocomplete(name=backupNameAutocomplete)
    async def backupDownload(self, interaction: discord.Interaction, name: str):
        try:
            path = self.storage.resolveBackup(name)
            await self._sendFile(interaction, path, "월드 백업")
        except StorageError as error:
            await interaction.response.send_message(f"❌ {describeError(error)}", ephemeral=True)

    @backupGroup.command(name="delete", description="Delete one selected backup archive.")
    @app_commands.describe(confirm="Type DELETE to confirm permanent deletion")
    @app_commands.autocomplete(name=backupNameAutocomplete)
    async def backupDelete(self, interaction: discord.Interaction, name: str, confirm: str):
        if confirm != "DELETE":
            await interaction.response.send_message("❌ 확인문구에 `DELETE`를 정확히 입력해야 삭제됩니다.", ephemeral=True)
            return
        try:
            await asyncio.to_thread(self.storage.deleteBackup, name)
            await interaction.response.send_message(f"✅ `{name}` 백업을 삭제했습니다.", ephemeral=True)
            await self._audit(interaction, "backup.delete", "success", name)
            _log.warning("backup delete by %s: %s", userTag(interaction.user), name)
        except StorageError as error:
            await interaction.response.send_message(f"❌ {describeError(error)}", ephemeral=True)

    @backupGroup.command(name="restore", description="Restore a backup after an emergency snapshot.")
    @app_commands.describe(confirm="Type RESTORE to confirm stopping and replacing the live world")
    @app_commands.autocomplete(name=backupNameAutocomplete)
    async def backupRestore(self, interaction: discord.Interaction, name: str, confirm: str):
        if confirm != "RESTORE":
            await interaction.response.send_message("❌ 확인문구에 `RESTORE`를 정확히 입력해야 복구됩니다.", ephemeral=True)
            return

        async def work():
            async with self.operationLock:
                self.storage.resolveBackup(name)
                await self._safeBackup("pre-restore")
                stopped, stopOutput = await asyncio.to_thread(_systemctl, "stop")
                if not stopped:
                    raise StorageError(f"마인크래프트를 정지하지 못했습니다: {stopOutput}")
                try:
                    await self.storage.restoreBackup(name)
                finally:
                    started, startOutput = await asyncio.to_thread(_systemctl, "start")
                    if not started:
                        raise StorageError(f"월드는 교체됐지만 마인크래프트 시작에 실패했습니다: {startOutput}")

        try:
            await animate_while(interaction, work(), "월드 복구 중")
            await interaction.edit_original_response(
                embed=discord.Embed(title="✅ 월드 복구 완료", description=f"`{name}`", color=OK_GREEN)
            )
            _log.warning("backup restore by %s: %s", userTag(interaction.user), name)
            await self._audit(interaction, "backup.restore", "success", name)
        except (StorageError, RuntimeError) as error:
            await self._audit(interaction, "backup.restore", "failed", f"{name}: {error}")
            await self._editError(interaction, error)

    @backupGroup.command(name="verify", description="Verify a backup checksum and archive structure.")
    @app_commands.autocomplete(name=backupNameAutocomplete)
    async def backupVerify(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        try:
            digest = await asyncio.to_thread(self.storage.verifyBackup, name)
            await interaction.followup.send(
                f"✅ `{name}` 백업이 손상 없이 온전합니다.\nSHA-256: `{digest}`", ephemeral=True
            )
        except StorageError as error:
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)

    @backupGroup.command(name="prune", description="Apply the saved retention policy immediately.")
    async def backupPrune(self, interaction: discord.Interaction):
        try:
            settings = self.settingsStore.load()
            deletedCount = await asyncio.to_thread(self.storage.pruneBackups, settings)
            await interaction.response.send_message(
                f"✅ 보관 정책을 적용해 만료된 백업 **{deletedCount}개**를 삭제했습니다.",
                ephemeral=True,
            )
            await self._audit(interaction, "backup.prune", "success", str(deletedCount))
        except (StorageError, RuntimeError, OSError) as error:
            await interaction.response.send_message(f"❌ {describeError(error)}", ephemeral=True)

    @backupGroup.command(name="settings", description="Show automatic backup and HDD settings.")
    async def backupSettings(self, interaction: discord.Interaction):
        try:
            settings = self.settingsStore.load()
            total, used, free = await asyncio.to_thread(self.storage.storageUsage)
            description = (
                f"자동 백업: **{'켜짐' if settings.enabled else '꺼짐'}**\n"
                f"간격: **{settings.intervalMinutes}분**\n"
                f"단기 보관: **{settings.retentionHours}시간**\n"
                f"일일 보관: **{settings.dailyRetentionDays}일**\n"
                f"최대 사용률: **{settings.maxUsagePercent}%**\n"
                f"최소 여유 공간: **{settings.minFreeGb} GB**\n"
                f"HDD: **{self._formatBytes(used)} / {self._formatBytes(total)}**, "
                f"여유 **{self._formatBytes(free)}**"
            )
            backups = await asyncio.to_thread(self.storage.listBackups)
            if settings.enabled and backups:
                nextTimestamp = int(
                    backups[0].modifiedAt.timestamp() + settings.intervalMinutes * 60
                )
                description += f"\n다음 백업: <t:{nextTimestamp}:R>"
            elif settings.enabled:
                description += "\n다음 백업: **스케줄러가 시작되는 즉시**"
            else:
                description += "\n다음 백업: **일시 중지됨**"
            await interaction.response.send_message(embed=discord.Embed(title="백업 설정", description=description, color=BRAND_BLUE), ephemeral=True)
        except (StorageError, RuntimeError) as error:
            await interaction.response.send_message(f"❌ {describeError(error)}", ephemeral=True)

    @backupGroup.command(name="configure", description="Change the persistent automatic backup policy.")
    async def backupConfigure(
        self,
        interaction: discord.Interaction,
        interval_minutes: int | None = None,
        retention_hours: int | None = None,
        daily_retention_days: int | None = None,
        max_usage_percent: int | None = None,
        min_free_gb: int | None = None,
    ):
        try:
            settings = self.settingsStore.load()
            changes = {
                "intervalMinutes": interval_minutes,
                "retentionHours": retention_hours,
                "dailyRetentionDays": daily_retention_days,
                "maxUsagePercent": max_usage_percent,
                "minFreeGb": min_free_gb,
            }
            settings = replace(settings, **{key: value for key, value in changes.items() if value is not None})
            self.settingsStore.save(settings)
            await interaction.response.send_message("✅ 백업 설정을 저장했습니다. `/backup settings`로 확인하세요.", ephemeral=True)
            _log.warning("backup settings changed by %s", userTag(interaction.user))
            await self._audit(interaction, "backup.configure", "success", str(changes))
        except (ValueError, RuntimeError, OSError) as error:
            await interaction.response.send_message(f"❌ {describeError(error)}", ephemeral=True)

    @backupGroup.command(name="enabled", description="Enable or pause automatic backups.")
    async def backupEnabled(self, interaction: discord.Interaction, enabled: bool):
        try:
            settings = replace(self.settingsStore.load(), enabled=enabled)
            self.settingsStore.save(settings)
            await interaction.response.send_message(f"✅ 자동 백업: **{'켜짐' if enabled else '꺼짐'}**", ephemeral=True)
            await self._audit(interaction, "backup.enabled", "success", str(enabled))
        except (ValueError, RuntimeError, OSError) as error:
            await interaction.response.send_message(f"❌ {describeError(error)}", ephemeral=True)

    # --- uploaded maps --------------------------------------------------
    worldGroup = InternalActionGroup()

    @worldGroup.command(name="upload", description="Upload and validate a Java map archive.")
    async def worldUpload(self, interaction: discord.Interaction, name: str, file: discord.Attachment):
        await interaction.response.defer(ephemeral=True)
        uploadPath = self.storage.uploadsDir / f"{uuid.uuid4().hex}-{Path(file.filename).name}"
        try:
            self.storage.ensureReady()
            await file.save(uploadPath)
            async with self.operationLock:
                targetPath = await asyncio.to_thread(self.storage.importWorldArchive, uploadPath, name)
            await interaction.followup.send(f"✅ 맵 `{targetPath.name}`을(를) 검증해 HDD에 저장했습니다.", ephemeral=True)
            _log.info("world upload by %s: %s", userTag(interaction.user), targetPath.name)
            await self._audit(interaction, "world.upload", "success", targetPath.name)
        except (StorageError, OSError) as error:
            await self._audit(interaction, "world.upload", "failed", str(error))
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)
        finally:
            uploadPath.unlink(missing_ok=True)

    @worldGroup.command(name="list", description="List imported maps on the HDD.")
    async def worldList(self, interaction: discord.Interaction):
        try:
            worlds = await asyncio.to_thread(self.storage.listWorlds)
            lines = [f"`{item.name}` — {self._formatBytes(item.size)}" for item in worlds[:20]]
            await interaction.response.send_message("\n".join(lines) or "업로드된 맵이 없습니다.", ephemeral=True)
        except StorageError as error:
            await interaction.response.send_message(f"❌ {describeError(error)}", ephemeral=True)

    @worldGroup.command(name="activate", description="Back up the live world and switch to an imported map.")
    @app_commands.describe(confirm="Type ACTIVATE to confirm stopping and replacing the live world")
    @app_commands.autocomplete(name=worldNameAutocomplete)
    async def worldActivate(self, interaction: discord.Interaction, name: str, confirm: str):
        if confirm != "ACTIVATE":
            await interaction.response.send_message("❌ 확인문구에 `ACTIVATE`를 정확히 입력해야 적용됩니다.", ephemeral=True)
            return

        async def work():
            async with self.operationLock:
                await self._safeBackup("pre-activate")
                stopped, stopOutput = await asyncio.to_thread(_systemctl, "stop")
                if not stopped:
                    raise StorageError(f"마인크래프트를 정지하지 못했습니다: {stopOutput}")
                try:
                    await self.storage.activateWorld(name)
                finally:
                    started, startOutput = await asyncio.to_thread(_systemctl, "start")
                    if not started:
                        raise StorageError(f"맵은 교체됐지만 마인크래프트 시작에 실패했습니다: {startOutput}")

        try:
            await animate_while(interaction, work(), "업로드한 맵 적용 중")
            await interaction.edit_original_response(embed=discord.Embed(title="✅ 맵 적용 완료", description=f"`{name}`", color=OK_GREEN))
            _log.warning("world activate by %s: %s", userTag(interaction.user), name)
            await self._audit(interaction, "world.activate", "success", name)
        except (StorageError, RuntimeError) as error:
            await self._audit(interaction, "world.activate", "failed", f"{name}: {error}")
            await self._editError(interaction, error)

    @worldGroup.command(name="download", description="Download an imported map if it fits Discord's limit.")
    @app_commands.autocomplete(name=worldNameAutocomplete)
    async def worldDownload(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        outputPath = None
        try:
            outputPath = await self.storage.exportWorld(name)
            await self._sendFile(interaction, outputPath, "저장된 맵", deferred=True)
        except StorageError as error:
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)
        finally:
            if outputPath:
                outputPath.unlink(missing_ok=True)

    @worldGroup.command(name="delete", description="Delete one imported map from the HDD.")
    @app_commands.describe(confirm="Type DELETE to confirm permanent deletion")
    @app_commands.autocomplete(name=worldNameAutocomplete)
    async def worldDelete(self, interaction: discord.Interaction, name: str, confirm: str):
        if confirm != "DELETE":
            await interaction.response.send_message("❌ 확인문구에 `DELETE`를 정확히 입력해야 삭제됩니다.", ephemeral=True)
            return
        try:
            await asyncio.to_thread(self.storage.deleteWorld, name)
            await interaction.response.send_message(f"✅ 업로드된 맵 `{name}`을(를) 삭제했습니다.", ephemeral=True)
            _log.warning("world delete by %s: %s", userTag(interaction.user), name)
            await self._audit(interaction, "world.delete", "success", name)
        except StorageError as error:
            await interaction.response.send_message(f"❌ {describeError(error)}", ephemeral=True)

    @internalAction(name="storage", description="Show HDD mount and free-space status.")
    async def storageStatus(self, interaction: discord.Interaction):
        try:
            total, used, free = self.storage.storageUsage()
            await interaction.response.send_message(
                f"✅ HDD 마운트 위치: `{self.storage.storageRoot}`\n"
                f"사용량: **{self._formatBytes(used)} / {self._formatBytes(total)}**\n"
                f"여유: **{self._formatBytes(free)}**",
                ephemeral=True,
            )
        except StorageError as error:
            await interaction.response.send_message(f"❌ {describeError(error)}", ephemeral=True)

    @internalAction(name="health", description="Check RCON, HDD, scheduler, and backup freshness.")
    async def health(self, interaction: discord.Interaction):
        results = []
        try:
            output = await _rcon("list")
            results.append(f"✅ RCON: `{output[:300]}`")
        except RconError as error:
            results.append(f"❌ RCON: {error}")
        try:
            total, used, free = await asyncio.to_thread(self.storage.storageUsage)
            results.append(
                f"✅ HDD: 전체 {self._formatBytes(total)} 중 {self._formatBytes(free)} 여유"
            )
            settings = self.settingsStore.load()
            backups = await asyncio.to_thread(self.storage.listBackups)
            if backups:
                ageMinutes = int(
                    (datetime.now(timezone.utc) - backups[0].modifiedAt).total_seconds() / 60
                )
                freshnessMark = "✅" if ageMinutes <= settings.intervalMinutes * 2 else "⚠️"
                results.append(f"{freshnessMark} 최근 백업: {ageMinutes}분 전")
            else:
                results.append("⚠️ 최근 백업: 없음")
            results.append(
                f"{'✅' if settings.enabled else '⏸️'} 스케줄러: "
                f"{'켜짐' if settings.enabled else '일시 중지'} ({settings.intervalMinutes}분 간격)"
            )
        except (StorageError, RuntimeError) as error:
            results.append(f"❌ 저장소/스케줄러: {error}")
        await interaction.response.send_message("\n".join(results), ephemeral=True)

    @internalAction(name="audit", description="Show recent privileged-operation audit records.")
    async def audit(self, interaction: discord.Interaction, limit: app_commands.Range[int, 1, 20] = 10):
        records = await asyncio.to_thread(self.auditLog.recent, limit)
        lines = [
            f"`{record.get('timestamp', '?')[:19]}` **{record.get('action', '?')}** "
            f"({record.get('outcome', '?')}) — user `{record.get('actorId', '?')}` "
            f"{record.get('detail', '')}"
            for record in records
        ]
        await interaction.response.send_message(
            "\n".join(lines)[:1900] or "아직 감사 기록이 없습니다.", ephemeral=True
        )

    # --- button-first control panel ------------------------------------
    @internalAction(name="panel", description="Open the button-first Minecraft admin dashboard.")
    async def panel(self, interaction: discord.Interaction):
        """Open routine administration without requiring command arguments."""
        embed = await self.panelOverviewEmbed()
        await interaction.response.send_message(
            embed=embed,
            view=AdminDashboardView(self, interaction.user.id),
            ephemeral=True,
        )

    @internalAction(name="players", description="Select an online player and inspect their state.")
    async def players(self, interaction: discord.Interaction):
        """Open the live player dropdown directly as a keyboard-friendly shortcut."""
        players = await self.panelOnlinePlayers()
        if not players:
            await interaction.response.send_message("현재 접속 중인 플레이어가 없습니다.", ephemeral=True)
            return
        await interaction.response.send_message(
            "조회할 플레이어를 선택하세요.",
            view=PlayerPanelView(self, interaction.user.id, players),
            ephemeral=True,
        )

    @internalAction(name="metrics", description="Show Raspberry Pi resources and Paper TPS.")
    async def metrics(self, interaction: discord.Interaction):
        """Keyboard shortcut for the same performance card used by the dashboard."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send(embed=await self.panelMetricsEmbed(), ephemeral=True)

    @internalAction(name="tuning-report", description="Explain current performance risks and tuning advice.")
    async def tuningReport(self, interaction: discord.Interaction):
        """Turn raw metrics into actionable Pi-friendly tuning advice."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            warnings, embed = await self._collectPerformanceWarnings()
            if warnings:
                embed.add_field(name="경고", value="\n".join(f"• {item}" for item in warnings)[:1000], inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except (OSError, RuntimeError, ValueError) as error:
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)

    # --- application updates -------------------------------------------
    updateGroup = InternalActionGroup()

    @updateGroup.command(
        name="check",
        description="Check the newest GitHub Release without installing it.",
    )
    async def updateCheck(self, interaction: discord.Interaction) -> None:
        """Show the official release and require a second button confirmation."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            release = await asyncio.to_thread(fetchLatestRelease)
            status = await asyncio.to_thread(self.updateStore.readStatus)
            currentTag = status.get("tag", "설치 기록 없음")
            embed = discord.Embed(
                title="⬆️ 프로그램 업데이트 확인",
                description=(
                    f"**현재 기록:** `{currentTag}`\n"
                    f"**최신 Release:** [`{release.tag}`]({release.pageUrl})\n"
                    f"**파일:** `{release.assetName}` ({self._formatBytes(release.size)})\n\n"
                    "설치를 누르면 ZIP을 라즈베리파이가 GitHub에서 직접 받아 검증합니다. "
                    "마인크래프트 월드는 정지하지 않고 봇만 잠시 재시작합니다."
                ),
                color=BRAND_BLUE,
            )
            await interaction.followup.send(
                embed=embed,
                view=UpdateConfirmView(self, interaction.user.id, release, release.tag),
                ephemeral=True,
            )
        except UpdateError as error:
            await interaction.followup.send(f"❌ 업데이트 확인 실패: {error}", ephemeral=True)

    @updateGroup.command(
        name="upload",
        description="Upload a trusted release ZIP and open a confirmation panel.",
    )
    async def updateUpload(
        self, interaction: discord.Interaction, file: discord.Attachment
    ) -> None:
        """Stage one bounded Discord ZIP on the HDD after full manifest checks."""
        if not file.filename.lower().endswith(".zip"):
            await interaction.response.send_message("❌ ZIP 파일만 업로드할 수 있습니다.", ephemeral=True)
            return
        if file.size <= 0 or file.size > MAX_ARCHIVE_BYTES:
            await interaction.response.send_message("❌ 업데이트 ZIP은 50 MiB 이하여야 합니다.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        temporaryPath = None
        try:
            self.updateStore.stagingDir.mkdir(parents=True, exist_ok=True)
            temporaryPath = self.updateStore.stagingDir / f".discord-{uuid.uuid4().hex}.zip"
            await file.save(temporaryPath)
            stagedPayload = await asyncio.to_thread(
                self.updateStore.stageUploadedArchive, temporaryPath
            )
            temporaryPath = None
            await interaction.followup.send(
                content=(
                    f"✅ `{stagedPayload['tag']}` ZIP 검증을 통과했습니다. "
                    "아래 버튼을 눌러야 실제 설치됩니다."
                ),
                view=UpdateConfirmView(
                    self, interaction.user.id, stagedPayload, stagedPayload["tag"]
                ),
                ephemeral=True,
            )
        except (UpdateError, OSError, discord.HTTPException) as error:
            await interaction.followup.send(f"❌ ZIP 준비 실패: {error}", ephemeral=True)
        finally:
            if temporaryPath is not None:
                temporaryPath.unlink(missing_ok=True)

    @updateGroup.command(
        name="status", description="Show the most recent updater result."
    )
    async def updateStatus(self, interaction: discord.Interaction) -> None:
        """Read the updater result written outside the restarted bot process."""
        status = await asyncio.to_thread(self.updateStore.readStatus)
        if not status:
            await interaction.response.send_message("아직 업데이트 실행 기록이 없습니다.", ephemeral=True)
            return
        stateLabels = {
            "preparing": "준비 중",
            "success": "성공",
            "rolled_back": "실패 후 자동 복구됨",
            "failed": "실패",
        }
        state = str(status.get("state", "unknown"))
        lines = [
            f"**상태:** {stateLabels.get(state, state)}",
            f"**버전:** `{status.get('tag', '알 수 없음')}`",
        ]
        if status.get("finishedAt"):
            lines.append(f"**완료:** `{status['finishedAt']}`")
        if status.get("error"):
            lines.append(f"**오류:** `{str(status['error'])[:1200]}`")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    async def startPreparedUpdate(
        self, interaction: discord.Interaction, payload: ReleaseInfo | dict
    ) -> None:
        """Persist one validated request and launch the fixed privileged service."""
        try:
            if isinstance(payload, ReleaseInfo):
                await asyncio.to_thread(self.updateStore.requestRelease, payload)
                tag = payload.tag
                source = "github"
            else:
                await asyncio.to_thread(self.updateStore.requestUpload, payload)
                tag = str(payload.get("tag", "unknown"))
                source = "upload"
            ok, output = await asyncio.to_thread(_startUpdater)
            if not ok:
                raise UpdateError(output or "업데이트 서비스가 시작되지 않았습니다")
            await self._audit(interaction, "app.update", "queued", f"{tag} via {source}")
            _log.info(
                "application update queued by %s: %s via %s",
                userTag(interaction.user),
                tag,
                source,
            )
        except (OSError, UpdateError) as error:
            await self._audit(interaction, "app.update", "failed", str(error))
            try:
                await interaction.followup.send(f"❌ 업데이트 시작 실패: {error}", ephemeral=True)
            except discord.HTTPException:
                _log.exception("could not report updater start failure")

    incidentGroup = InternalActionGroup()

    async def _incidentCommand(
        self, interaction: discord.Interaction, command: str, successKey: str
    ):
        try:
            out = await _rcon(command)
            await self._audit(
                interaction, f"incident.{command.split()[0]}", "success", command
            )
            message = f"{t(successKey)}\n`{out.strip() or command}`"
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except RconError as error:
            await self._audit(
                interaction, f"incident.{command.split()[0]}", "failed", str(error)
            )
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {describeError(error)}", ephemeral=True)

    @incidentGroup.command(name="day", description="Set the overworld time to day.")
    async def incidentDay(self, interaction: discord.Interaction):
        await self._incidentCommand(interaction, "time set day", "incident_day")

    @incidentGroup.command(name="clear-weather", description="Clear storm/rain after an accident.")
    async def incidentClearWeather(self, interaction: discord.Interaction):
        await self._incidentCommand(interaction, "weather clear", "incident_clear")

    @incidentGroup.command(name="peaceful", description="Temporarily switch difficulty to peaceful.")
    async def incidentPeaceful(self, interaction: discord.Interaction):
        await self._incidentCommand(interaction, "difficulty peaceful", "incident_peaceful")

    @incidentGroup.command(
        name="clear-drops",
        description="Remove dropped item entities to recover from lag.",
    )
    @app_commands.describe(
        confirm="Type CLEAR to confirm deleting every dropped item entity"
    )
    async def incidentClearDrops(self, interaction: discord.Interaction, confirm: str):
        if confirm != "CLEAR":
            await interaction.response.send_message(
                t("incident_confirm_clear_drops"), ephemeral=True
            )
            return
        await self._incidentCommand(interaction, "kill @e[type=item]", "incident_kill_items")

    async def publicServerEmbed(self) -> discord.Embed:
        """Build the friend-safe server card shared by `/서버` panel refreshes.

        이슈 #44/#45 개편: 규칙 문구 대신 친구가 실제로 궁금해하는
        접속 주소·상태·접속자 이름·버전·플레이 일수를 보여줍니다.
        """
        players = []
        daysPlayed = None
        statusText = t("portal_offline")
        try:
            statusText = await _rcon("list")
            players = parseOnlinePlayers(statusText)
            # 월드가 시작된 뒤 지난 게임 일수 — 서버 자랑 겸 근황 표시용.
            daysPlayed = parseDaysPlayed(await _rcon("time query day"))
        except RconError:
            pass
        online = statusText != t("portal_offline")
        embed = discord.Embed(
            title=t("portal_title"),
            description=t("portal_description"),
            color=OK_GREEN if online else WARN_YELLOW,
        )
        embed.add_field(
            name="상태", value="🟢 온라인" if online else "🔴 오프라인", inline=True
        )
        embed.add_field(
            name=t("portal_online"),
            value=", ".join(players) if players else t("online_none"),
            inline=True,
        )
        embed.add_field(
            name=t("portal_address"),
            value=cfg.public_address or t("portal_address_missing"),
            inline=False,
        )
        embed.add_field(name=t("portal_version"), value=cfg.public_version, inline=True)
        if daysPlayed is not None:
            embed.add_field(
                name=t("portal_days"), value=f"{daysPlayed:,}일차", inline=True
            )
        return embed

    async def panelLegacyCommand(
        self, commandName: str, interaction: discord.Interaction, *args
    ) -> None:
        """Invoke a preserved command callback from a button without duplicating logic."""
        callback = getattr(self, commandName, None)
        if callback is None or not callable(callback):
            raise RuntimeError(f"panel action is unavailable: {commandName}")
        await callback(interaction, *args)

    async def panelBackups(self):
        """Return newest backup metadata for the panel dropdown."""
        try:
            return await asyncio.to_thread(self.storage.listBackups)
        except StorageError:
            return []

    async def panelWorlds(self):
        """Return imported world metadata for the panel dropdown."""
        try:
            return await asyncio.to_thread(self.storage.listWorlds)
        except StorageError:
            return []

    async def panelBackupEmbed(self) -> discord.Embed:
        """Summarize the persistent backup policy and most recent archive."""
        settings = await asyncio.to_thread(self.settingsStore.load)
        backups = await self.panelBackups()
        latest = backups[0].modifiedAt.strftime("%Y-%m-%d %H:%M UTC") if backups else "없음"
        embed = discord.Embed(title="💾 월드 백업", color=BRAND_BLUE)
        embed.description = (
            f"**자동 백업:** {'켜짐' if settings.enabled else '꺼짐'}\n"
            f"**주기:** {settings.intervalMinutes}분\n"
            f"**최근 백업:** {latest}\n"
            f"**보관:** {settings.retentionHours}시간 + 일일 {settings.dailyRetentionDays}일"
        )
        return embed

    async def panelBackupSettings(self):
        """Return the current backup settings for stateful button labels."""
        return await asyncio.to_thread(self.settingsStore.load)

    async def panelUpdateBackupSetting(self, fieldName: str, value: int):
        """Persist one allowlisted backup setting selected from a dropdown."""
        allowed = {
            "intervalMinutes",
            "retentionHours",
            "dailyRetentionDays",
            "maxUsagePercent",
            "minFreeGb",
        }
        if fieldName not in allowed:
            raise ValueError("unsupported backup setting")
        settings = await asyncio.to_thread(self.settingsStore.load)
        updated = replace(settings, **{fieldName: value})
        await asyncio.to_thread(self.settingsStore.save, updated)
        return updated

    async def panelTextAction(
        self, interaction: discord.Interaction, action: str, value: str
    ) -> None:
        """Route the few unavoidable text modals through existing audited actions."""
        mapping = {
            "say": "say",
            "mc": "mc",
            "wl_add": "wl_add",
            "wl_remove": "wl_remove",
        }
        commandName = mapping.get(action)
        if commandName is None:
            raise ValueError("unsupported text action")
        await self.panelLegacyCommand(commandName, interaction, value)

    # --- 접속자 관리 조작 버튼 (빠른 명령) ------------------------------
    # 버튼 → 명령 대응은 bot/quick_commands.py의 빌더가 담당하고, 여기서는
    # 실행 + 응답 검증 + 감사 기록 + 한글 안내만 합니다.
    async def _quickPlayerAction(
        self,
        interaction: discord.Interaction,
        commands: list[str],
        auditAction: str,
        successMessage: str,
    ) -> None:
        """Run one quick action (already deferred), verify, audit, and reply."""
        try:
            for command in commands:
                ensureServerAccepted(await _rcon(command))
            await self._audit(interaction, auditAction, "success", commands[-1][:200])
            await interaction.followup.send(f"✅ {successMessage}", ephemeral=True)
            _log.info("%s by %s", auditAction, userTag(interaction.user))
        except (ValueError, RconError) as error:
            await self._audit(interaction, auditAction, "failed", str(error)[:200])
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)

    async def panelGiveItem(
        self, interaction: discord.Interaction, playerName: str, rawItem: str, rawCount: str
    ) -> None:
        try:
            command = buildGiveCommand(playerName, rawItem, rawCount)
        except ValueError as error:
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)
            return
        itemId, count = command.split()[-2:]
        await self._quickPlayerAction(
            interaction,
            [command],
            "player.give",
            f"`{playerName}` 에게 `{itemId.removeprefix('minecraft:')}` {count}개를 지급했습니다.",
        )

    async def panelApplyEffect(
        self,
        interaction: discord.Interaction,
        playerName: str,
        effectId: str,
        seconds: int,
        amplifier: int,
        hideParticles: bool = True,
    ) -> None:
        try:
            command = buildEffectCommand(
                playerName, effectId, seconds, amplifier, hideParticles
            )
        except ValueError as error:
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)
            return
        label = next(
            (label for eid, label, _s, _a in COMMON_EFFECTS if eid == effectId.strip().lower()),
            effectId.strip().lower(),
        )
        levelText = f" {amplifier + 1}단계" if amplifier else ""
        await self._quickPlayerAction(
            interaction,
            [command],
            "player.effect",
            f"`{playerName}` 에게 **{label}**{levelText} 효과를 {seconds // 60}분 적용했습니다.",
        )

    async def panelClearEffects(
        self, interaction: discord.Interaction, playerName: str
    ) -> None:
        await self._quickPlayerAction(
            interaction,
            [buildEffectClearCommand(playerName)],
            "player.effect_clear",
            f"`{playerName}` 의 모든 포션 효과를 해제했습니다.",
        )

    async def panelEnchant(
        self, interaction: discord.Interaction, playerName: str, enchantId: str, level: int
    ) -> None:
        try:
            command = buildEnchantCommand(playerName, enchantId, level)
        except ValueError as error:
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)
            return
        await self._quickPlayerAction(
            interaction,
            [command],
            "player.enchant",
            f"`{playerName}` 가 들고 있는 아이템에 `{enchantId.strip().lower()}` {level}레벨을 부여했습니다.",
        )

    async def panelForceEnchant(
        self, interaction: discord.Interaction, playerName: str, enchantId: str, level: int
    ) -> None:
        """RaspiMcOps 플러그인으로 제한 없이 인챈트 (곡괭이에 날카로움 등, #62)."""
        try:
            command = buildForceEnchantCommand(playerName, enchantId, level)
        except ValueError as error:
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)
            return
        await self._quickPlayerAction(
            interaction,
            [command],
            "player.enchant_force",
            f"`{playerName}` 가 들고 있는 아이템에 `{enchantId.strip().lower()}` "
            f"{level}레벨을 **제한 없이** 부여했습니다.",
        )

    async def panelGamemode(
        self, interaction: discord.Interaction, playerName: str, mode: str
    ) -> None:
        await self._quickPlayerAction(
            interaction,
            [buildGamemodeCommand(playerName, mode)],
            "player.gamemode",
            f"`{playerName}` 의 게임모드를 **{GAMEMODES[mode]}** 로 바꿨습니다.",
        )

    async def panelTeleportToPlayer(
        self, interaction: discord.Interaction, playerName: str, targetName: str
    ) -> None:
        try:
            command = buildTeleportToPlayerCommand(playerName, targetName)
        except ValueError as error:
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)
            return
        await self._quickPlayerAction(
            interaction,
            [command],
            "player.tp",
            f"`{playerName}` 를 `{targetName}` 에게 이동시켰습니다.",
        )

    async def panelTeleportToPlace(
        self, interaction: discord.Interaction, playerName: str, placeName: str
    ) -> None:
        place = await asyncio.to_thread(self.placeStore.get, placeName)
        if place is None:
            await interaction.followup.send("❌ 저장된 좌표를 찾지 못했습니다.", ephemeral=True)
            return
        try:
            command = buildTeleportToCoordsCommand(
                playerName, place.dimension, place.x, place.y, place.z
            )
        except ValueError as error:
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)
            return
        await self._quickPlayerAction(
            interaction,
            [command],
            "player.tp_place",
            f"`{playerName}` 를 좌표 **{place.name}** 으로 이동시켰습니다.",
        )

    async def panelTeleportToSpawn(
        self, interaction: discord.Interaction, playerName: str
    ) -> None:
        # 스폰 귀환과 같은 플러그인 경로를 쓰므로 월드 스폰과 항상 일치합니다.
        try:
            output = await _rcon(buildAutomaticSpawnCommand(playerName))
            ensureRescueSucceeded(output)
            await self._audit(interaction, "player.tp_spawn", "success", playerName)
            await interaction.followup.send(
                f"✅ `{playerName}` 를 스폰으로 이동시켰습니다.", ephemeral=True
            )
        except (ValueError, RconError) as error:
            await self._audit(interaction, "player.tp_spawn", "failed", str(error)[:200])
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)

    async def panelXp(
        self, interaction: discord.Interaction, playerName: str, levels: int
    ) -> None:
        await self._quickPlayerAction(
            interaction,
            [buildXpCommand(playerName, levels)],
            "player.xp",
            f"`{playerName}` 에게 경험치 {levels}레벨을 지급했습니다.",
        )

    async def panelHeal(
        self, interaction: discord.Interaction, playerName: str
    ) -> None:
        await self._quickPlayerAction(
            interaction,
            buildHealCommands(playerName),
            "player.heal",
            f"`{playerName}` 의 체력과 배고픔을 회복시켰습니다.",
        )

    async def panelKick(
        self, interaction: discord.Interaction, playerName: str
    ) -> None:
        await self._quickPlayerAction(
            interaction,
            [buildKickCommand(playerName)],
            "player.kick",
            f"`{playerName}` 를 서버에서 추방했습니다.",
        )

    async def panelInvincible(
        self, interaction: discord.Interaction, playerName: str, seconds: int
    ) -> None:
        """무적 세트(#75)를 접속자 관리 패널 버튼으로 부여합니다."""
        await self._quickPlayerAction(
            interaction,
            buildInvincibilityCommands(playerName, seconds),
            "player.invincible",
            f"`{playerName}` 를 **{seconds}초** 동안 무적으로 만들었습니다. "
            "(재생·저항·화염 저항·포화, 파티클 숨김)",
        )

    async def panelMortal(
        self, interaction: discord.Interaction, playerName: str
    ) -> None:
        """무적을 즉시 해제합니다 — 무적 세트로 건 효과만 골라 지웁니다."""
        try:
            for command in buildInvincibilityClearCommands(playerName):
                await _rcon(command)
            await self._audit(interaction, "player.mortal", "success", playerName)
            await interaction.followup.send(
                f"⚔️ `{playerName}` 의 무적을 해제했습니다.", ephemeral=True
            )
        except (ValueError, RconError) as error:
            await self._audit(interaction, "player.mortal", "failed", str(error)[:200])
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)

    async def panelSharedPlaces(self):
        """Return the shared coordinate book for the teleport dropdown."""
        return await asyncio.to_thread(self.placeStore.list)

    # --- 빠른 명령: 월드(시간·날씨·난이도·게임룰·스폰) --------------------
    async def panelWorldCommand(
        self,
        interaction: discord.Interaction,
        command: str,
        successMessage: str,
        auditAction: str,
    ) -> None:
        """Run one world-level quick command (already deferred) with audit."""
        try:
            ensureServerAccepted(await _rcon(command))
            await self._audit(interaction, auditAction, "success", command[:200])
            await interaction.followup.send(f"✅ {successMessage}", ephemeral=True)
        except (ValueError, RconError) as error:
            await self._audit(interaction, auditAction, "failed", str(error)[:200])
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)

    async def panelToggleGamerule(
        self, interaction: discord.Interaction, gameruleKey: str
    ) -> None:
        """Query the current gamerule value and flip it in one button press."""
        gameruleName, koreanLabel = GAMERULES[gameruleKey]
        try:
            current = parseGameruleValue(
                ensureGameruleAccepted(await _rcon(buildGameruleQueryCommand(gameruleKey)))
            )
            ensureGameruleAccepted(
                await _rcon(buildGameruleSetCommand(gameruleKey, not current))
            )
            self.supportedGamerules[gameruleKey] = True
            await self._audit(
                interaction, "world.gamerule", "success", f"{gameruleName}={not current}"
            )
            stateText = "켜짐 🟢" if not current else "꺼짐 🔴"
            await interaction.followup.send(
                f"✅ **{koreanLabel}**: {stateText}", ephemeral=True
            )
        except (ValueError, RconError) as error:
            if str(error) == GAMERULE_UNSUPPORTED_MESSAGE:
                self.supportedGamerules[gameruleKey] = False
            await self._audit(interaction, "world.gamerule", "failed", str(error)[:200])
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)

    async def panelSetDifficulty(
        self, interaction: discord.Interaction, difficulty: str
    ) -> None:
        await self.panelWorldCommand(
            interaction,
            buildDifficultyCommand(difficulty),
            f"난이도를 **{DIFFICULTIES[difficulty]}** 로 바꿨습니다.",
            "world.difficulty",
        )

    async def _applySpawn(
        self, interaction: discord.Interaction, x: int, y: int, z: int
    ) -> None:
        """Set the overworld spawn and pin the respawn point exactly there."""
        ensureServerAccepted(await _rcon(buildWorldSpawnCommand(x, y, z)))
        # 분산 반경을 0으로 맞춰 정확히 그 지점에 리스폰되게 합니다.
        ensureServerAccepted(await _rcon(SPAWN_RADIUS_ZERO_COMMAND))
        await self._audit(interaction, "world.setspawn", "success", f"{x} {y} {z}")
        await interaction.followup.send(
            f"✅ 월드 스폰을 **({x}, {y}, {z})** 로 지정했습니다.\n"
            "이제 죽었을 때 리스폰(침대가 없을 때)과 `/도구`의 스폰 귀환이 "
            "모두 이 지점입니다. 침대에서 잔 플레이어는 여전히 침대에서 "
            "리스폰합니다.",
            ephemeral=True,
        )

    async def panelSetSpawnFromPlayer(
        self, interaction: discord.Interaction, playerName: str
    ) -> None:
        """선택한 접속자가 서 있는 자리를 월드 스폰으로 지정."""
        try:
            selector = buildPlayerSelector(playerName)
            positionOutput, dimensionOutput = await asyncio.gather(
                _rcon(f"data get entity {selector} Pos"),
                _rcon(f"data get entity {selector} Dimension"),
            )
            dimension, x, y, z = parsePosition(positionOutput, dimensionOutput)
            if dimension != "overworld":
                raise ValueError(
                    "오버월드에 있는 플레이어의 위치만 스폰으로 지정할 수 있습니다 "
                    f"(현재: {dimension})."
                )
            await self._applySpawn(interaction, round(x), round(y), round(z))
        except (ValueError, RconError) as error:
            await self._audit(interaction, "world.setspawn", "failed", str(error)[:200])
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)

    async def panelSetSpawnCoords(
        self, interaction: discord.Interaction, rawX: str, rawY: str, rawZ: str
    ) -> None:
        """모달에 입력한 좌표를 검증해 월드 스폰으로 지정."""
        try:
            try:
                x, y, z = (int(value.strip()) for value in (rawX, rawY, rawZ))
            except ValueError:
                raise ValueError("좌표는 정수로 입력하세요 (예: 120 64 -35).") from None
            await self._applySpawn(interaction, x, y, z)
        except (ValueError, RconError) as error:
            await self._audit(interaction, "world.setspawn", "failed", str(error)[:200])
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)

    async def panelOpenLinkAdmin(self, interaction: discord.Interaction) -> None:
        """Open direct multi-profile account management for one Discord user."""
        friend = self.bot.get_cog("Friend")
        if friend is None:
            await interaction.response.send_message("친구 도구가 준비되지 않았습니다.", ephemeral=True)
            return
        from bot.friend_panel import ManagedAccountView

        # 대시보드에서 여는 화면이므로 같은 메시지에서 전환하고, 관리
        # 대시보드로 돌아가는 홈 버튼을 함께 둡니다(#58 규칙과 통일).
        # 사용자를 선택해 화면이 다시 그려져도 팩토리가 홈 버튼을 되살립니다.
        ownerId = interaction.user.id
        view = ManagedAccountView(
            friend,
            ownerId,
            extraNavFactory=lambda: [HomeButton(self, ownerId, row=3)],
        )
        await replaceScreen(
            interaction,
            content=(
                "**1. Discord 사용자 선택 → 2. Java/Bedrock 계정 추가**\n"
                "연동 요청이나 승인은 없습니다. 한 사용자에게 계정을 여러 개 등록할 수 있습니다."
            ),
            embed=None,
            view=view,
        )

    @staticmethod
    def panelHelpEmbed() -> discord.Embed:
        """Explain administrator-only controls in plain Korean."""
        embed = discord.Embed(
            title="❓ 관리자 전용 도움말",
            description=(
                "이 도움말과 관리 버튼은 관리자에게만 보입니다. "
                "평소에는 **상태 확인 → 필요한 버튼 한 번**이면 됩니다."
            ),
            color=BRAND_BLUE,
        )
        embed.add_field(
            name="매일 쓰는 버튼 (첫 화면)",
            value=(
                "**접속자 관리**: 접속자를 고른 뒤 조회(인벤토리·위치·체력·효과)와 "
                "조작(아이템 주기·포션 효과·인챈트·게임모드·TP·경험치·회복·추방)\n"
                "**서버 제어**: 서버 시작·정지·재시작\n"
                "**백업**: 즉시 백업, 자동 백업 주기·보관 설정, 복구\n"
                "**빠른 명령**: 시간·날씨·난이도·게임룰 토글·드롭템 정리·스폰 지정\n"
                "**상태 진단**: 서버가 이상할 때 첫 확인"
            ),
            inline=False,
        )
        embed.add_field(
            name="스폰 지정",
            value=(
                "**빠른 명령 → 스폰 지정**으로 월드 스폰을 옮기면 죽었을 때 "
                "리스폰(침대 없을 때)과 `/도구`의 스폰 귀환이 모두 그 지점으로 "
                "바뀝니다. 접속자가 서 있는 자리로 지정하는 것이 가장 쉽습니다."
            ),
            inline=False,
        )
        embed.add_field(
            name="더보기 안의 도구",
            value=(
                "**성능 상세 / 렉 원인**: 라즈베리파이 지표와 튜닝 조언\n"
                "**월드**: 업로드한 월드 선택·적용\n"
                "**업데이트**: 새 프로그램 확인·설치 결과 확인\n"
                "**로그 / 저장공간**: 오류 기록과 HDD 여유 확인\n"
                "**스폰 보호 / 상자 잠금**: 월드 보호 켜기/끄기"
            ),
            inline=False,
        )
        embed.add_field(
            name="친구 계정",
            value=(
                "Discord 사용자를 고른 뒤 **Java(PC)** 또는 "
                "**Bedrock(모바일/콘솔)** 닉네임을 등록합니다.\n"
                "한 Discord 사용자에게 여러 계정을 추가할 수 있고, "
                "삭제할 때도 선택한 계정 하나만 삭제됩니다."
            ),
            inline=False,
        )
        embed.add_field(
            name="파일 업로드가 필요할 때",
            value=(
                "Discord 명령 입력창에서 `/업로드`를 고른 뒤 "
                "**월드 / 업데이트 / 좌표사진 / 일지** 중 목적을 선택하세요."
            ),
            inline=False,
        )
        embed.add_field(
            name="주의가 필요한 버튼",
            value=(
                "**빠른 명령**은 서버 상태를 즉시 바꿉니다. **고급 도구**의 "
                "**인게임 명령어**는 마인크래프트 콘솔 명령을 입력한 그대로 "
                "실행합니다(자주 쓰는 명령은 접속자 관리·빠른 명령 버튼 우선). "
                "정지·재시작·삭제·복구 작업은 확인 화면을 읽고 실행하세요."
            ),
            inline=False,
        )
        embed.set_footer(
            text="일반 친구에게는 /서버와 /도구만 안내하면 됩니다."
        )
        return embed

    async def panelOnlinePlayers(self) -> list[str]:
        """Return validated live player names from Paper's list command."""
        try:
            return parseOnlinePlayers(await _rcon("list"))
        except RconError:
            return []

    async def panelOverviewEmbed(self) -> discord.Embed:
        """Build a compact dashboard summary resilient to individual subsystem failures."""
        players = []
        online = False
        try:
            players = parseOnlinePlayers(await _rcon("list"))
            online = True
        except RconError:
            pass
        settings = self.settingsStore.load()
        storageText = "HDD 확인 불가"
        try:
            total, used, free = await asyncio.to_thread(self.storage.storageUsage)
            storageText = f"여유 {self._formatBytes(free)} / 전체 {self._formatBytes(total)}"
        except StorageError:
            pass
        backups = []
        try:
            backups = await asyncio.to_thread(self.storage.listBackups)
        except StorageError:
            pass
        latestText = (
            f"<t:{int(backups[0].modifiedAt.timestamp())}:R>" if backups else "없음"
        )
        embed = discord.Embed(
            title="🎛️ Minecraft 관리 패널",
            description=(
                "서버 제어, 백업, 월드, 친구 계정을 버튼으로 관리합니다.\n"
                "처음이면 **관리 도움말**부터 누르세요."
            ),
            color=OK_GREEN if online else ERR_RED,
        )
        embed.add_field(name="서버", value="🟢 온라인" if online else "🔴 오프라인", inline=True)
        embed.add_field(
            name=f"접속자 {len(players)}명",
            value=", ".join(players)[:1000] if players else "없음",
            inline=True,
        )
        embed.add_field(name="HDD", value=storageText, inline=False)
        embed.add_field(name="최근 백업", value=latestText, inline=True)
        embed.add_field(
            name="자동 백업",
            value=f"{'켜짐' if settings.enabled else '꺼짐'} / {settings.intervalMinutes}분",
            inline=True,
        )
        return embed

    async def panelStorageEmbed(self) -> discord.Embed:
        """Build an HDD capacity card for the dashboard."""
        try:
            total, used, free = await asyncio.to_thread(self.storage.storageUsage)
            percent = (used / total * 100) if total else 100
            description = (
                f"마운트: `{self.storage.storageRoot}`\n"
                f"사용: **{self._formatBytes(used)} ({percent:.1f}%)**\n"
                f"여유: **{self._formatBytes(free)}**\n"
                f"전체: **{self._formatBytes(total)}**"
            )
            return discord.Embed(title="💽 HDD 저장공간", description=description, color=OK_GREEN)
        except StorageError as error:
            return discord.Embed(title="❌ HDD 오류", description=str(error), color=ERR_RED)

    async def panelHealthEmbed(self) -> discord.Embed:
        """Build a no-typing health summary for RCON, storage, and backups."""
        lines = []
        try:
            await _rcon("list")
            lines.append("✅ RCON 연결")
        except RconError as error:
            lines.append(f"❌ RCON: {error}")
        try:
            total, used, free = await asyncio.to_thread(self.storage.storageUsage)
            lines.append(f"✅ HDD 여유 {self._formatBytes(free)}")
            settings = self.settingsStore.load()
            backups = await asyncio.to_thread(self.storage.listBackups)
            if backups:
                ageMinutes = int(
                    (datetime.now(timezone.utc) - backups[0].modifiedAt).total_seconds() / 60
                )
                mark = "✅" if ageMinutes <= settings.intervalMinutes * 2 else "⚠️"
                lines.append(f"{mark} 최근 백업 {ageMinutes}분 전")
            else:
                lines.append("⚠️ 생성된 백업 없음")
            lines.append(f"{'✅' if settings.enabled else '⏸️'} 자동 백업 {settings.intervalMinutes}분")
        except (StorageError, RuntimeError) as error:
            lines.append(f"❌ 저장소: {error}")
        color = ERR_RED if any(line.startswith("❌") for line in lines) else OK_GREEN
        return discord.Embed(title="🩺 서버 상태 진단", description="\n".join(lines), color=color)

    async def panelMetricsEmbed(self) -> discord.Embed:
        """Combine procfs, Pi firmware, HDD, and Paper TPS in one card."""
        try:
            systemMetrics, throttleFlags = await asyncio.gather(
                asyncio.to_thread(readSystemMetrics),
                asyncio.to_thread(readThrottleFlags),
            )
        except (OSError, RuntimeError, ValueError) as error:
            return discord.Embed(
                title="❌ 시스템 지표 조회 실패", description=str(error), color=ERR_RED
            )
        usedMemory = systemMetrics.memoryTotalBytes - systemMetrics.memoryAvailableBytes
        memoryPercent = (
            usedMemory / systemMetrics.memoryTotalBytes * 100
            if systemMetrics.memoryTotalBytes else 100
        )
        temperatureText = (
            f"{systemMetrics.temperatureCelsius:.1f}°C"
            if systemMetrics.temperatureCelsius is not None else "확인 불가"
        )
        tpsText = "RCON 조회 실패"
        try:
            tpsText = stripMinecraftFormatting(await _rcon("tps"))[:1000]
        except RconError:
            pass
        hddText = "마운트 확인 실패"
        try:
            total, used, free = await asyncio.to_thread(self.storage.storageUsage)
            hddText = f"{self._formatBytes(used)} / {self._formatBytes(total)} (여유 {self._formatBytes(free)})"
        except StorageError:
            pass
        hasCurrentWarning = any(label.startswith("현재") for label in throttleFlags)
        isHot = (
            systemMetrics.temperatureCelsius is not None
            and systemMetrics.temperatureCelsius >= 80
        )
        color = ERR_RED if hasCurrentWarning or isHot else (
            WARN_YELLOW if memoryPercent >= 85 else OK_GREEN
        )
        embed = discord.Embed(
            title="📊 Raspberry Pi · Paper 성능",
            description=f"**TPS**\n```\n{tpsText}\n```",
            color=color,
        )
        embed.add_field(name="CPU 온도", value=temperatureText, inline=True)
        embed.add_field(
            name=f"Load ({systemMetrics.cpuCount} cores)",
            value=f"{systemMetrics.load1:.2f} / {systemMetrics.load5:.2f} / {systemMetrics.load15:.2f}",
            inline=True,
        )
        embed.add_field(
            name="메모리",
            value=f"{self._formatBytes(usedMemory)} / {self._formatBytes(systemMetrics.memoryTotalBytes)} ({memoryPercent:.1f}%)",
            inline=False,
        )
        embed.add_field(name="HDD", value=hddText, inline=False)
        embed.add_field(name="업타임", value=formatDuration(systemMetrics.uptimeSeconds), inline=True)
        embed.add_field(name="전원·스로틀", value=", ".join(throttleFlags), inline=False)
        return embed

    async def panelCreateBackup(self, interaction: discord.Interaction):
        """Create a safe manual backup and report through a deferred button response."""
        try:
            async with self.operationLock:
                archivePath = await self._safeBackup("panel")
            await self._audit(interaction, "backup.create", "success", archivePath.name)
            await interaction.followup.send(f"✅ 백업 완료: `{archivePath.name}`", ephemeral=True)
        except (StorageError, RuntimeError) as error:
            await self._audit(interaction, "backup.create", "failed", str(error))
            await interaction.followup.send(f"❌ 백업 실패: {error}", ephemeral=True)

    async def panelToggleBackup(self, interaction: discord.Interaction) -> bool:
        """Toggle and persist automatic backups from one dashboard button."""
        settings = self.settingsStore.load()
        settings = replace(settings, enabled=not settings.enabled)
        self.settingsStore.save(settings)
        await self._audit(interaction, "backup.enabled", "success", str(settings.enabled))
        return settings.enabled

    async def panelServiceAction(self, interaction: discord.Interaction, action: str):
        """Run a validated lifecycle action from a button with graceful stop saving."""
        if action not in {"start", "stop", "restart"}:
            await interaction.followup.send("❌ 잘못된 서버 작업입니다.", ephemeral=True)
            return
        if action == "stop":
            try:
                await _rcon("save-all flush")
            except RconError:
                pass
        ok, output = await asyncio.to_thread(_systemctl, action)
        await self._audit(
            interaction, f"service.{action}", "success" if ok else "failed", output
        )
        mark = "✅" if ok else "❌"
        await interaction.followup.send(
            f"{mark} 서버 {action}: `{(output or 'done')[:1400]}`", ephemeral=True
        )

    async def panelToggleSpawnProtection(self, interaction: discord.Interaction) -> None:
        """Toggle the bundled plugin's persistent safe-zone setting through RCON."""
        try:
            output = await _rcon("spawnprotection toggle")
            await self._audit(interaction, "spawn-protection.toggle", "success", output)
            await interaction.followup.send(
                f"🛡️ `{output.strip() or 'spawn protection toggled'}`", ephemeral=True
            )
        except RconError as error:
            await self._audit(interaction, "spawn-protection.toggle", "failed", str(error))
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)

    async def panelToggleChestLock(self, interaction: discord.Interaction) -> None:
        """Toggle the bundled plugin's persistent container-lock setting through RCON."""
        try:
            output = await _rcon("chestlock toggle")
            await self._audit(interaction, "chest-lock.toggle", "success", output)
            await interaction.followup.send(
                f"🔒 `{output.strip() or 'chest lock toggled'}`", ephemeral=True
            )
        except RconError as error:
            await self._audit(interaction, "chest-lock.toggle", "failed", str(error))
            await interaction.followup.send(f"❌ {describeError(error)}", ephemeral=True)

    async def panelPlayerEmbed(self, player: str, detailType: str) -> discord.Embed:
        """Query a selected player's allowed read-only entity fields through RCON."""
        safePlayer = validateServerPlayerName(player)
        playerTarget = buildPlayerSelector(safePlayer)
        titleMap = {
            "inventory": "🎒 인벤토리",
            "position": "🧭 위치",
            "stats": "❤️ 체력·경험치",
            "effects": "✨ 상태 효과",
            "records": "📊 킬·데스",
        }
        try:
            fields: list[tuple[str, str]] = []
            if detailType == "inventory":
                inventoryOutput, enderOutput = await asyncio.gather(
                    _rcon(f"data get entity {playerTarget} Inventory"),
                    _rcon(f"data get entity {playerTarget} EnderItems"),
                )
                fields = summarizeInventorySections(inventoryOutput)
                enderBody = summarizeEnderChest(enderOutput)
                if enderBody:
                    fields.append(("🟣 엔더상자", enderBody))
                description = "모든 칸이 비어 있습니다." if not fields else ""
            elif detailType == "position":
                position, dimension = await asyncio.gather(
                    _rcon(f"data get entity {playerTarget} Pos"),
                    _rcon(f"data get entity {playerTarget} Dimension"),
                )
                description = f"**좌표**\n`{position[:800]}`\n**차원**\n`{dimension[:500]}`"
            elif detailType == "stats":
                health, food, level, mode = await asyncio.gather(
                    _rcon(f"data get entity {playerTarget} Health"),
                    _rcon(f"data get entity {playerTarget} foodLevel"),
                    _rcon(f"data get entity {playerTarget} XpLevel"),
                    _rcon(f"data get entity {playerTarget} playerGameType"),
                )
                description = summarizePlayerStats(health, food, level, mode)
            elif detailType == "effects":
                description = summarizeEffects(
                    await _rcon(f"data get entity {playerTarget} active_effects")
                )
            elif detailType == "records":
                outputs = await asyncio.gather(
                    *(
                        _rcon(buildScoreboardGetCommand(safePlayer, objective))
                        for _, objective, _, _ in SCOREBOARD_STATS
                    )
                )
                lines = [
                    f"• {label}: **{parseScoreboardValue(output)}**"
                    for (_, _, _, label), output in zip(SCOREBOARD_STATS, outputs)
                ]
                lines.append("\n통계는 봇이 처음 실행된 시점부터 집계됩니다.")
                description = "\n".join(lines)
            else:
                raise ValueError("Unknown player detail type")
            embed = discord.Embed(
                title=f"{titleMap[detailType]} — {player}",
                description=description[:4000],
                color=BRAND_BLUE,
            )
            for fieldTitle, fieldBody in fields[:24]:
                embed.add_field(name=fieldTitle, value=fieldBody[:1024], inline=False)
            return embed
        except (RconError, ValueError) as error:
            return discord.Embed(
                title=f"❌ {player} 조회 실패", description=str(error), color=ERR_RED
            )

    def panelLogPath(self, source: str) -> Path:
        """Resolve only the two supported operational log files."""
        if source == "bot":
            currentPath = log.current_log_file()
            if not currentPath:
                raise FileNotFoundError("Bot log file is not ready")
            return Path(currentPath)
        if source == "server":
            return Path(cfg.server_dir) / "logs" / "latest.log"
        if source == "chat":
            return Path(cfg.server_dir) / "plugins" / "RaspiMcOps" / "chat.log"
        raise ValueError("Unknown log source")

    async def panelLogEmbed(self, source: str, errorsOnly: bool = False) -> discord.Embed:
        """Preview a bounded log tail or filtered warning/error lines."""
        try:
            path = self.panelLogPath(source)
            text = await asyncio.to_thread(readTail, path)
            if errorsOnly:
                text = filterImportant(text)
            preview = discordPreview(text)
            title = "⚠️ 최근 경고·오류" if errorsOnly else {
                "bot": "🤖 봇 로그",
                "server": "⛏️ 마인크래프트 로그",
                "chat": "💬 게임 채팅 로그",
            }[source]
            return discord.Embed(
                title=title,
                description=f"`{path}`\n```\n{preview}\n```",
                color=WARN_YELLOW if errorsOnly else BRAND_BLUE,
            )
        except (FileNotFoundError, OSError, ValueError) as error:
            return discord.Embed(title="❌ 로그 조회 실패", description=str(error), color=ERR_RED)

    async def panelLogDownload(self, interaction: discord.Interaction, source: str):
        """Attach a selected log while respecting the guild's upload limit."""
        try:
            await self._sendFile(interaction, self.panelLogPath(source), "Operational log")
        except (FileNotFoundError, OSError, ValueError) as error:
            await interaction.response.send_message(f"❌ {describeError(error)}", ephemeral=True)

    @tasks.loop(seconds=60)
    async def backupScheduler(self):
        """Poll the persisted interval and create a due backup without overlap."""
        try:
            settings = self.settingsStore.load()
            if not settings.enabled or self.operationLock.locked():
                return
            backups = await asyncio.to_thread(self.storage.listBackups)
            lastBackupAt = backups[0].modifiedAt if backups else None
            ageMinutes = float("inf")
            if lastBackupAt is not None:
                ageMinutes = (datetime.now(timezone.utc) - lastBackupAt).total_seconds() / 60
            if ageMinutes < settings.intervalMinutes:
                return
            # 접속자 0명 + 월드 변경 없음이면 백업을 건너뛰거나 주기를 늘립니다(이슈 I).
            playersOnline = await self._onlinePlayerCount()
            worldChanged = await asyncio.to_thread(self._worldChangedSince, lastBackupAt)
            decision = _autoBackupDecision(
                playersOnline, worldChanged, ageMinutes, settings.intervalMinutes
            )
            if decision != "backup":
                _log.info(
                    "자동 백업 건너뜀 (%s): 접속자=%s, 변경=%s, 경과=%.0f분",
                    decision, playersOnline, worldChanged, ageMinutes,
                )
                return
            async with self.operationLock:
                archivePath = await self._safeBackup("auto")
            _log.info("automatic backup complete: %s", archivePath.name)
        except (StorageError, RuntimeError, OSError, RconError):
            _log.exception("automatic backup failed")

    async def _onlinePlayerCount(self) -> int | None:
        """Return the online player count, or None when RCON is unreachable."""
        try:
            return len(parseOnlinePlayers(await _rcon("list")))
        except RconError:
            return None

    def _worldChangedSince(self, lastBackupAt) -> bool:
        """Return whether the live world looks newer than the last backup."""
        newest = self.storage.newestWorldMtime()
        if lastBackupAt is None or newest is None:
            return True
        return newest > lastBackupAt.timestamp()

    @tasks.loop(seconds=300)
    async def performanceAlerts(self):
        """Post cooldown-protected performance/storage warnings to STATUS_CHANNEL_ID."""
        channel = self._statusChannel()
        if not channel:
            return
        try:
            warnings, embed = await self._collectPerformanceWarnings()
        except (OSError, RuntimeError, ValueError):
            _log.exception("performance alert collection failed")
            return
        if not warnings:
            return
        now = datetime.now(timezone.utc)
        fresh = []
        cooldown = timedelta(minutes=cfg.alert_cooldown_minutes)
        for warning in warnings:
            previous = self.lastAlertAt.get(warning)
            if not shouldAlert(previous, now, cooldown):
                continue
            self.lastAlertAt[warning] = now
            fresh.append(warning)
        if not fresh:
            return
        embed.title = t("alerts_title")
        embed.add_field(name="새 경고", value="\n".join(f"• {item}" for item in fresh)[:1000], inline=False)
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            _log.exception("failed to send performance alert")

    @performanceAlerts.before_loop
    async def beforePerformanceAlerts(self):
        """Wait until Discord is ready before resolving channels."""
        await self.bot.wait_until_ready()

    @backupScheduler.before_loop
    async def beforeBackupScheduler(self):
        """Do not touch storage before Discord startup has completed."""
        await self.bot.wait_until_ready()

    async def _sendFile(self, interaction, path: Path, label: str, deferred: bool = False):
        """Respect the guild's actual Discord upload limit before reading the file."""
        uploadLimit = interaction.guild.filesize_limit if interaction.guild else 10 * 1024 * 1024
        if path.stat().st_size > uploadLimit:
            message = (
                f"❌ `{path.name}`은(는) {self._formatBytes(path.stat().st_size)}로, 이 서버의 Discord 업로드 한도 "
                f"{self._formatBytes(uploadLimit)}를 넘습니다. SSH/SFTP로 HDD에서 직접 내려받으세요."
            )
            if deferred:
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
            return
        if deferred:
            await interaction.followup.send(content=f"📦 {label}:", file=discord.File(path), ephemeral=True)
        else:
            await interaction.response.send_message(content=f"📦 {label}:", file=discord.File(path), ephemeral=True)

    async def _editError(self, interaction, error: Exception):
        """Replace a loading embed with a concise failure result."""
        await interaction.edit_original_response(
            embed=discord.Embed(title="❌ 작업 실패", description=str(error)[:1800], color=ERR_RED)
        )

    @staticmethod
    def _formatBytes(size: int) -> str:
        """Format byte counts for compact Discord messages."""
        value = float(size)
        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if value < 1024 or unit == "TiB":
                return f"{value:.1f} {unit}"
            value /= 1024

    # --- logs -----------------------------------------------------------
    @internalAction(description="Open button controls for bot and Minecraft logs.")
    async def logs(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "확인할 로그를 선택하세요.",
            view=LogPanelView(self, interaction.user.id),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
