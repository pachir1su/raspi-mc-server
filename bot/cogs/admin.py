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
from bot.i18n import t
from bot.backup_settings import SettingsStore
from bot.control_panel import AdminDashboardView, LogPanelView, PlayerPanelView
from bot.log_viewer import discordPreview, filterImportant, readTail
from bot.loading import animate_while
from bot.player_info import parseOnlinePlayers, summarizeInventory, validatePlayerName
from bot.performance_report import parseTps, shouldAlert
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
PUBLIC_COMMANDS = {"portal", "online"}


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
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settingsStore = SettingsStore(cfg.state_dir)
        self.auditLog = AuditLog(cfg.state_dir)
        self.storage = WorldStorage(
            cfg.storage_root, cfg.server_dir, cfg.require_storage_mount
        )
        self.updateStore = UpdateStore(cfg.state_dir, cfg.storage_root)
        self.operationLock = asyncio.Lock()
        self.lastAlertAt: dict[str, datetime] = {}

    async def cog_load(self):
        """Start the persistent in-bot scheduler after the cog is ready."""
        self.backupScheduler.start()
        self.performanceAlerts.start()

    def cog_unload(self):
        """Stop scheduler polling when the extension unloads."""
        self.backupScheduler.cancel()
        self.performanceAlerts.cancel()

    # A single guard applied to every command in this cog.
    async def cog_check(self, ctx):  # for prefix commands (unused)
        return True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        commandName = interaction.command.name if interaction.command else ""
        if commandName in PUBLIC_COMMANDS and cfg.public_commands_enabled:
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
                "Current undervoltage/throttle flag: " + ", ".join(throttleFlags)
            )
        tpsText = "RCON unavailable"
        tpsValue = None
        try:
            tpsText = stripMinecraftFormatting(await _rcon("tps"))
            tpsValue = parseTps(tpsText)
            if tpsValue is not None and tpsValue < cfg.alert_tps_threshold:
                warnings.append(f"TPS {tpsValue:.1f} < {cfg.alert_tps_threshold:.1f}")
        except RconError:
            warnings.append("RCON/TPS check failed")
        hddText = "HDD unavailable"
        try:
            total, used, free = await asyncio.to_thread(self.storage.storageUsage)
            hddText = (
                f"{self._formatBytes(used)} / {self._formatBytes(total)} "
                f"(free {self._formatBytes(free)})"
            )
            freeGb = free / 1024 ** 3
            if freeGb < cfg.alert_min_free_gb:
                warnings.append(f"HDD free {freeGb:.1f} GB < {cfg.alert_min_free_gb:.0f} GB")
        except StorageError:
            warnings.append("HDD check failed")
        recommendations = []
        if tpsValue is not None and tpsValue < 18:
            recommendations.append(
                "Lower view-distance/simulation-distance and check mob farms "
                "or chunk loaders."
            )
        if memoryPercent >= 85:
            recommendations.append(
                "Avoid raising MC_MEMORY; first reduce loaded chunks/entities "
                "or restart during off-hours."
            )
        if systemMetrics.temperatureCelsius is not None and systemMetrics.temperatureCelsius >= 75:
            recommendations.append(
                "Improve cooling, case airflow, or power supply before "
                "increasing player load."
            )
        if any("전압" in label or "undervoltage" in label.lower() for label in throttleFlags):
            recommendations.append(
                "Use a stronger USB-C power supply/cable; undervoltage "
                "causes lag spikes."
            )
        recommendations.append(
            "For a Pi 4B 4GB, keep 3-4 players, modest farms, and "
            "conservative render/simulation distance."
        )
        embed = discord.Embed(
            title=t("tuning_title"),
            description=t("tuning_summary"),
            color=ERR_RED if warnings else OK_GREEN,
        )
        embed.add_field(name="TPS", value=f"```{tpsText[:900]}```", inline=False)
        embed.add_field(name="CPU", value=f"Temp: {systemMetrics.temperatureCelsius if systemMetrics.temperatureCelsius is not None else 'n/a'}°C\nLoad: {systemMetrics.load1:.2f}/{systemMetrics.load5:.2f}/{systemMetrics.load15:.2f}", inline=True)
        embed.add_field(name="Memory", value=f"{self._formatBytes(usedMemory)} / {self._formatBytes(systemMetrics.memoryTotalBytes)} ({memoryPercent:.1f}%)", inline=True)
        embed.add_field(name="HDD", value=hddText, inline=False)
        embed.add_field(name="Power/throttle", value=", ".join(throttleFlags), inline=False)
        embed.add_field(name="Recommendations", value="\n".join(f"• {item}" for item in recommendations)[:1000], inline=False)
        return warnings, embed

    # --- player-facing portal ------------------------------------------
    @app_commands.command(name="portal", description="Show friend-safe server access info and live status.")
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
        embed.add_field(
            name=t("portal_rules"),
            value=cfg.public_rules or t("portal_rules_default"),
            inline=False,
        )
        embed.set_footer(text=statusText[:200])
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="online", description="Show who is online without exposing admin controls.")
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
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    # --- read-only ------------------------------------------------------
    @app_commands.command(description="Show whether the server is up and who is online.")
    async def status(self, interaction: discord.Interaction):
        try:
            out = await _rcon("list")
            e = discord.Embed(title="🟢 Server online", description=out, color=OK_GREEN)
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
                title="🔴 Server offline",
                description="RCON is unreachable — the server is stopped or starting.",
                color=ERR_RED,
            )
        await interaction.response.send_message(embed=e)
        _log.info("status by %s", userTag(interaction.user))

    # --- broadcast / commands ------------------------------------------
    @app_commands.command(description="Broadcast a message to everyone in-game.")
    @app_commands.describe(message="Text to say in chat")
    async def say(self, interaction: discord.Interaction, message: str):
        try:
            await _rcon(f"say {message}")
            await interaction.response.send_message(f"📢 Sent: {message}", ephemeral=True)
            _log.info("say by %s: %s", userTag(interaction.user), message)
            await self._audit(interaction, "server.say", "success")
        except RconError as e:
            await self._audit(interaction, "server.say", "failed", str(e))
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    @app_commands.command(name="mc", description="Run ANY server command via RCON (owner cheat channel).")
    @app_commands.describe(command="e.g. gamemode creative YourName, time set day, give ...")
    async def mc(self, interaction: discord.Interaction, command: str):
        # This is the "only I can cheat" channel: it runs at op level 4.
        try:
            out = await _rcon(command)
            body = out.strip() or "(no output)"
            e = discord.Embed(
                title="🎛️ Command executed",
                description=f"`/{command}`\n```\n{body[:1800]}\n```",
                color=BRAND_BLUE,
            )
            await interaction.response.send_message(embed=e)
            _log.info("mc by %s: %s", userTag(interaction.user), command)
            commandName = command.split(maxsplit=1)[0] if command.strip() else "empty"
            await self._audit(interaction, "server.command", "success", commandName)
        except RconError as e:
            await self._audit(interaction, "server.command", "failed", str(e))
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    # --- whitelist ------------------------------------------------------
    whitelist = app_commands.Group(name="whitelist", description="Manage the whitelist.")

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
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

    # --- lifecycle (systemd) -------------------------------------------
    @app_commands.command(description="Start the Minecraft service.")
    async def start(self, interaction: discord.Interaction):
        await self._lifecycle(interaction, "start", "Starting the server")

    @app_commands.command(description="Stop the Minecraft service (saves first).")
    async def stop(self, interaction: discord.Interaction):
        # Best-effort graceful save before systemd stops the JVM.
        try:
            await _rcon("save-all")
        except RconError:
            pass
        await self._lifecycle(interaction, "stop", "Stopping the server")

    @app_commands.command(description="Restart the Minecraft service.")
    async def restart(self, interaction: discord.Interaction):
        await self._lifecycle(interaction, "restart", "Restarting the server")

    async def _lifecycle(self, interaction, action, label):
        async def work():
            return await asyncio.to_thread(_systemctl, action)

        ok, out = await animate_while(interaction, work(), label)
        color = OK_GREEN if ok else ERR_RED
        mark = "✅" if ok else "❌"
        e = discord.Embed(
            title=f"{mark} {label}",
            description=f"```\n{(out or 'done')[:1500]}\n```",
            color=color,
        )
        await interaction.edit_original_response(embed=e)
        _log.info("%s by %s -> ok=%s", action, userTag(interaction.user), ok)
        await self._audit(
            interaction, f"service.{action}", "success" if ok else "failed", out
        )

    # --- HDD backups ----------------------------------------------------
    backupGroup = app_commands.Group(name="backup", description="Manage HDD world backups.")

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
            archivePath = await animate_while(interaction, work(), "Backing up the world")
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="✅ Backup complete",
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
                "\n".join(lines) or "No backups yet.", ephemeral=True
            )
        except StorageError as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @backupGroup.command(name="timeline", description="Show a compact backup timeline with ages and sizes.")
    async def backupTimeline(self, interaction: discord.Interaction):
        try:
            backups = await asyncio.to_thread(self.storage.listBackups)
            if not backups:
                await interaction.response.send_message("No backups yet.", ephemeral=True)
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
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @backupGroup.command(name="restore-preview", description="Verify and preview a backup before restoring it.")
    @app_commands.autocomplete(name=backupNameAutocomplete)
    async def backupRestorePreview(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        try:
            path = self.storage.resolveBackup(name)
            digest = await asyncio.to_thread(self.storage.verifyBackup, name)
            description = (
                f"{t('restore_preview_ok')}\n"
                f"File: `{path.name}`\n"
                f"Size: **{self._formatBytes(path.stat().st_size)}**\n"
                f"SHA-256: `{digest}`\n\n"
                "Run `/backup restore` with confirm `RESTORE` only when you are ready to stop and replace the live world."
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
            await interaction.followup.send(f"❌ {error}", ephemeral=True)

    @backupGroup.command(name="download", description="Download a backup if it fits Discord's limit.")
    @app_commands.autocomplete(name=backupNameAutocomplete)
    async def backupDownload(self, interaction: discord.Interaction, name: str):
        try:
            path = self.storage.resolveBackup(name)
            await self._sendFile(interaction, path, "World backup")
        except StorageError as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @backupGroup.command(name="delete", description="Delete one selected backup archive.")
    @app_commands.describe(confirm="Type DELETE to confirm permanent deletion")
    @app_commands.autocomplete(name=backupNameAutocomplete)
    async def backupDelete(self, interaction: discord.Interaction, name: str, confirm: str):
        if confirm != "DELETE":
            await interaction.response.send_message("❌ Type `DELETE` exactly to confirm.", ephemeral=True)
            return
        try:
            await asyncio.to_thread(self.storage.deleteBackup, name)
            await interaction.response.send_message(f"✅ Deleted `{name}`.", ephemeral=True)
            await self._audit(interaction, "backup.delete", "success", name)
            _log.warning("backup delete by %s: %s", userTag(interaction.user), name)
        except StorageError as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @backupGroup.command(name="restore", description="Restore a backup after an emergency snapshot.")
    @app_commands.describe(confirm="Type RESTORE to confirm stopping and replacing the live world")
    @app_commands.autocomplete(name=backupNameAutocomplete)
    async def backupRestore(self, interaction: discord.Interaction, name: str, confirm: str):
        if confirm != "RESTORE":
            await interaction.response.send_message("❌ Type `RESTORE` exactly to confirm.", ephemeral=True)
            return

        async def work():
            async with self.operationLock:
                self.storage.resolveBackup(name)
                await self._safeBackup("pre-restore")
                stopped, stopOutput = await asyncio.to_thread(_systemctl, "stop")
                if not stopped:
                    raise StorageError(f"Could not stop Minecraft: {stopOutput}")
                try:
                    await self.storage.restoreBackup(name)
                finally:
                    started, startOutput = await asyncio.to_thread(_systemctl, "start")
                    if not started:
                        raise StorageError(f"World changed but Minecraft failed to start: {startOutput}")

        try:
            await animate_while(interaction, work(), "Restoring the world")
            await interaction.edit_original_response(
                embed=discord.Embed(title="✅ World restored", description=f"`{name}`", color=OK_GREEN)
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
                f"✅ `{name}` is intact.\nSHA-256: `{digest}`", ephemeral=True
            )
        except StorageError as error:
            await interaction.followup.send(f"❌ {error}", ephemeral=True)

    @backupGroup.command(name="prune", description="Apply the saved retention policy immediately.")
    async def backupPrune(self, interaction: discord.Interaction):
        try:
            settings = self.settingsStore.load()
            deletedCount = await asyncio.to_thread(self.storage.pruneBackups, settings)
            await interaction.response.send_message(
                f"✅ Retention applied; deleted **{deletedCount}** expired backup(s).",
                ephemeral=True,
            )
            await self._audit(interaction, "backup.prune", "success", str(deletedCount))
        except (StorageError, RuntimeError, OSError) as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @backupGroup.command(name="settings", description="Show automatic backup and HDD settings.")
    async def backupSettings(self, interaction: discord.Interaction):
        try:
            settings = self.settingsStore.load()
            total, used, free = await asyncio.to_thread(self.storage.storageUsage)
            description = (
                f"Enabled: **{settings.enabled}**\n"
                f"Interval: **{settings.intervalMinutes} minutes**\n"
                f"Dense retention: **{settings.retentionHours} hours**\n"
                f"Daily retention: **{settings.dailyRetentionDays} days**\n"
                f"Usage ceiling: **{settings.maxUsagePercent}%**\n"
                f"Minimum free: **{settings.minFreeGb} GB**\n"
                f"HDD: **{self._formatBytes(used)} / {self._formatBytes(total)}**, "
                f"free **{self._formatBytes(free)}**"
            )
            backups = await asyncio.to_thread(self.storage.listBackups)
            if settings.enabled and backups:
                nextTimestamp = int(
                    backups[0].modifiedAt.timestamp() + settings.intervalMinutes * 60
                )
                description += f"\nNext due: <t:{nextTimestamp}:R>"
            elif settings.enabled:
                description += "\nNext due: **as soon as the scheduler starts**"
            else:
                description += "\nNext due: **paused**"
            await interaction.response.send_message(embed=discord.Embed(title="Backup settings", description=description, color=BRAND_BLUE), ephemeral=True)
        except (StorageError, RuntimeError) as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

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
            await interaction.response.send_message("✅ Backup settings saved. Use `/backup settings` to review them.", ephemeral=True)
            _log.warning("backup settings changed by %s", userTag(interaction.user))
            await self._audit(interaction, "backup.configure", "success", str(changes))
        except (ValueError, RuntimeError, OSError) as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @backupGroup.command(name="enabled", description="Enable or pause automatic backups.")
    async def backupEnabled(self, interaction: discord.Interaction, enabled: bool):
        try:
            settings = replace(self.settingsStore.load(), enabled=enabled)
            self.settingsStore.save(settings)
            await interaction.response.send_message(f"✅ Automatic backups: **{enabled}**", ephemeral=True)
            await self._audit(interaction, "backup.enabled", "success", str(enabled))
        except (ValueError, RuntimeError, OSError) as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    # --- uploaded maps --------------------------------------------------
    worldGroup = app_commands.Group(name="world", description="Upload and activate HDD maps.")

    @worldGroup.command(name="upload", description="Upload and validate a Java map archive.")
    async def worldUpload(self, interaction: discord.Interaction, name: str, file: discord.Attachment):
        await interaction.response.defer(ephemeral=True)
        uploadPath = self.storage.uploadsDir / f"{uuid.uuid4().hex}-{Path(file.filename).name}"
        try:
            self.storage.ensureReady()
            await file.save(uploadPath)
            async with self.operationLock:
                targetPath = await asyncio.to_thread(self.storage.importWorldArchive, uploadPath, name)
            await interaction.followup.send(f"✅ Map `{targetPath.name}` validated and stored on the HDD.", ephemeral=True)
            _log.info("world upload by %s: %s", userTag(interaction.user), targetPath.name)
            await self._audit(interaction, "world.upload", "success", targetPath.name)
        except (StorageError, OSError) as error:
            await self._audit(interaction, "world.upload", "failed", str(error))
            await interaction.followup.send(f"❌ {error}", ephemeral=True)
        finally:
            uploadPath.unlink(missing_ok=True)

    @worldGroup.command(name="list", description="List imported maps on the HDD.")
    async def worldList(self, interaction: discord.Interaction):
        try:
            worlds = await asyncio.to_thread(self.storage.listWorlds)
            lines = [f"`{item.name}` — {self._formatBytes(item.size)}" for item in worlds[:20]]
            await interaction.response.send_message("\n".join(lines) or "No imported maps.", ephemeral=True)
        except StorageError as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @worldGroup.command(name="activate", description="Back up the live world and switch to an imported map.")
    @app_commands.describe(confirm="Type ACTIVATE to confirm stopping and replacing the live world")
    @app_commands.autocomplete(name=worldNameAutocomplete)
    async def worldActivate(self, interaction: discord.Interaction, name: str, confirm: str):
        if confirm != "ACTIVATE":
            await interaction.response.send_message("❌ Type `ACTIVATE` exactly to confirm.", ephemeral=True)
            return

        async def work():
            async with self.operationLock:
                await self._safeBackup("pre-activate")
                stopped, stopOutput = await asyncio.to_thread(_systemctl, "stop")
                if not stopped:
                    raise StorageError(f"Could not stop Minecraft: {stopOutput}")
                try:
                    await self.storage.activateWorld(name)
                finally:
                    started, startOutput = await asyncio.to_thread(_systemctl, "start")
                    if not started:
                        raise StorageError(f"Map changed but Minecraft failed to start: {startOutput}")

        try:
            await animate_while(interaction, work(), "Activating the uploaded map")
            await interaction.edit_original_response(embed=discord.Embed(title="✅ Map activated", description=f"`{name}`", color=OK_GREEN))
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
            await self._sendFile(interaction, outputPath, "Stored map", deferred=True)
        except StorageError as error:
            await interaction.followup.send(f"❌ {error}", ephemeral=True)
        finally:
            if outputPath:
                outputPath.unlink(missing_ok=True)

    @worldGroup.command(name="delete", description="Delete one imported map from the HDD.")
    @app_commands.describe(confirm="Type DELETE to confirm permanent deletion")
    @app_commands.autocomplete(name=worldNameAutocomplete)
    async def worldDelete(self, interaction: discord.Interaction, name: str, confirm: str):
        if confirm != "DELETE":
            await interaction.response.send_message("❌ Type `DELETE` exactly to confirm.", ephemeral=True)
            return
        try:
            await asyncio.to_thread(self.storage.deleteWorld, name)
            await interaction.response.send_message(f"✅ Deleted imported map `{name}`.", ephemeral=True)
            _log.warning("world delete by %s: %s", userTag(interaction.user), name)
            await self._audit(interaction, "world.delete", "success", name)
        except StorageError as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @app_commands.command(name="storage", description="Show HDD mount and free-space status.")
    async def storageStatus(self, interaction: discord.Interaction):
        try:
            total, used, free = self.storage.storageUsage()
            await interaction.response.send_message(
                f"✅ HDD mounted at `{self.storage.storageRoot}`\n"
                f"Used: **{self._formatBytes(used)} / {self._formatBytes(total)}**\n"
                f"Free: **{self._formatBytes(free)}**",
                ephemeral=True,
            )
        except StorageError as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @app_commands.command(name="health", description="Check RCON, HDD, scheduler, and backup freshness.")
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
                f"✅ HDD: {self._formatBytes(free)} free of {self._formatBytes(total)}"
            )
            settings = self.settingsStore.load()
            backups = await asyncio.to_thread(self.storage.listBackups)
            if backups:
                ageMinutes = int(
                    (datetime.now(timezone.utc) - backups[0].modifiedAt).total_seconds() / 60
                )
                freshnessMark = "✅" if ageMinutes <= settings.intervalMinutes * 2 else "⚠️"
                results.append(f"{freshnessMark} Latest backup: {ageMinutes} minute(s) old")
            else:
                results.append("⚠️ Latest backup: none")
            results.append(
                f"{'✅' if settings.enabled else '⏸️'} Scheduler: "
                f"{'enabled' if settings.enabled else 'paused'} ({settings.intervalMinutes} min)"
            )
        except (StorageError, RuntimeError) as error:
            results.append(f"❌ Storage/scheduler: {error}")
        await interaction.response.send_message("\n".join(results), ephemeral=True)

    @app_commands.command(name="audit", description="Show recent privileged-operation audit records.")
    async def audit(self, interaction: discord.Interaction, limit: app_commands.Range[int, 1, 20] = 10):
        records = await asyncio.to_thread(self.auditLog.recent, limit)
        lines = [
            f"`{record.get('timestamp', '?')[:19]}` **{record.get('action', '?')}** "
            f"({record.get('outcome', '?')}) — user `{record.get('actorId', '?')}` "
            f"{record.get('detail', '')}"
            for record in records
        ]
        await interaction.response.send_message(
            "\n".join(lines)[:1900] or "No audit records yet.", ephemeral=True
        )

    # --- button-first control panel ------------------------------------
    @app_commands.command(name="panel", description="Open the button-first Minecraft admin dashboard.")
    async def panel(self, interaction: discord.Interaction):
        """Open routine administration without requiring command arguments."""
        embed = await self.panelOverviewEmbed()
        await interaction.response.send_message(
            embed=embed,
            view=AdminDashboardView(self, interaction.user.id),
            ephemeral=True,
        )

    @app_commands.command(name="players", description="Select an online player and inspect their state.")
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

    @app_commands.command(name="metrics", description="Show Raspberry Pi resources and Paper TPS.")
    async def metrics(self, interaction: discord.Interaction):
        """Keyboard shortcut for the same performance card used by the dashboard."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send(embed=await self.panelMetricsEmbed(), ephemeral=True)

    @app_commands.command(name="tuning-report", description="Explain current performance risks and tuning advice.")
    async def tuningReport(self, interaction: discord.Interaction):
        """Turn raw metrics into actionable Pi-friendly tuning advice."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            warnings, embed = await self._collectPerformanceWarnings()
            if warnings:
                embed.add_field(name="Warnings", value="\n".join(f"• {item}" for item in warnings)[:1000], inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except (OSError, RuntimeError, ValueError) as error:
            await interaction.followup.send(f"❌ {error}", ephemeral=True)

    # --- application updates -------------------------------------------
    updateGroup = app_commands.Group(
        name="update", description="Manage safe Raspberry Pi application updates."
    )

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
                raise UpdateError(output or "updater service did not start")
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

    incidentGroup = app_commands.Group(
        name="incident", description="One-click emergency helpers for common accidents."
    )

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
                await interaction.followup.send(f"❌ {error}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {error}", ephemeral=True)

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
        storageText = "HDD unavailable"
        try:
            total, used, free = await asyncio.to_thread(self.storage.storageUsage)
            storageText = f"{self._formatBytes(free)} free / {self._formatBytes(total)}"
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
            description="아래 버튼으로 자주 쓰는 작업을 실행하세요.",
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

    async def panelPlayerEmbed(self, player: str, detailType: str) -> discord.Embed:
        """Query a selected player's allowed read-only entity fields through RCON."""
        validatePlayerName(player)
        titleMap = {
            "inventory": "🎒 인벤토리",
            "position": "🧭 위치",
            "stats": "❤️ 체력·경험치",
            "effects": "✨ 상태 효과",
        }
        try:
            if detailType == "inventory":
                output = await _rcon(f"data get entity {player} Inventory")
                description = summarizeInventory(output)
            elif detailType == "position":
                position, dimension = await asyncio.gather(
                    _rcon(f"data get entity {player} Pos"),
                    _rcon(f"data get entity {player} Dimension"),
                )
                description = f"**좌표**\n`{position[:800]}`\n**차원**\n`{dimension[:500]}`"
            elif detailType == "stats":
                health, food, level, mode = await asyncio.gather(
                    _rcon(f"data get entity {player} Health"),
                    _rcon(f"data get entity {player} foodLevel"),
                    _rcon(f"data get entity {player} XpLevel"),
                    _rcon(f"data get entity {player} playerGameType"),
                )
                description = (
                    f"**체력** `{health[:300]}`\n**허기** `{food[:300]}`\n"
                    f"**경험치 레벨** `{level[:300]}`\n**게임 모드** `{mode[:300]}`"
                )
            elif detailType == "effects":
                description = discordPreview(
                    await _rcon(f"data get entity {player} active_effects"), 1500
                )
            else:
                raise ValueError("Unknown player detail type")
            return discord.Embed(
                title=f"{titleMap[detailType]} — {player}",
                description=description[:4000],
                color=BRAND_BLUE,
            )
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
        raise ValueError("Unknown log source")

    async def panelLogEmbed(self, source: str, errorsOnly: bool = False) -> discord.Embed:
        """Preview a bounded log tail or filtered warning/error lines."""
        try:
            path = self.panelLogPath(source)
            text = await asyncio.to_thread(readTail, path)
            if errorsOnly:
                text = filterImportant(text)
            preview = discordPreview(text)
            title = "⚠️ 최근 경고·오류" if errorsOnly else (
                "🤖 봇 로그" if source == "bot" else "⛏️ 마인크래프트 로그"
            )
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
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @tasks.loop(seconds=60)
    async def backupScheduler(self):
        """Poll the persisted interval and create a due backup without overlap."""
        try:
            settings = self.settingsStore.load()
            if not settings.enabled or self.operationLock.locked():
                return
            backups = await asyncio.to_thread(self.storage.listBackups)
            ageMinutes = float("inf")
            if backups:
                ageMinutes = (datetime.now(timezone.utc) - backups[0].modifiedAt).total_seconds() / 60
            if ageMinutes < settings.intervalMinutes:
                return
            async with self.operationLock:
                archivePath = await self._safeBackup("auto")
            _log.info("automatic backup complete: %s", archivePath.name)
        except (StorageError, RuntimeError, OSError, RconError):
            _log.exception("automatic backup failed")

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
        embed.add_field(name="New warnings", value="\n".join(f"• {item}" for item in fresh)[:1000], inline=False)
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
                f"❌ `{path.name}` is {self._formatBytes(path.stat().st_size)}, above this server's "
                f"Discord limit of {self._formatBytes(uploadLimit)}. Download it from the HDD over SSH/SFTP."
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
            embed=discord.Embed(title="❌ Operation failed", description=str(error)[:1800], color=ERR_RED)
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
    @app_commands.command(description="Open button controls for bot and Minecraft logs.")
    async def logs(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "확인할 로그를 선택하세요.",
            view=LogPanelView(self, interaction.user.id),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
