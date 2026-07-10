"""Admin-only slash commands.

Every command here is gated to the user IDs in ADMIN_USER_IDS. Put only
your own ID there to be the sole operator: then the raw ``/mc`` command
(which runs ANY server command through RCON) is effectively "only I can
cheat", while in-game everyone else is a non-op who cannot run commands.

Read-only status is also admin-gated by default to keep the bot quiet in a
small private server; loosen the check if you want players to see status.
"""

import asyncio
import os
import subprocess
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks

from bot import log
from bot import BRAND_BLUE, OK_GREEN, ERR_RED, userTag
from bot.config import cfg
from bot.backup_settings import SettingsStore
from bot.loading import animate_while
from bot.rcon import Rcon, RconError
from bot.world_storage import StorageError, WorldStorage

_log = log.get("cog.admin")


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


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settingsStore = SettingsStore(cfg.state_dir)
        self.storage = WorldStorage(
            cfg.storage_root, cfg.server_dir, cfg.require_storage_mount
        )
        self.operationLock = asyncio.Lock()

    async def cog_load(self):
        """Start the persistent in-bot scheduler after the cog is ready."""
        self.backupScheduler.start()

    def cog_unload(self):
        """Stop scheduler polling when the extension unloads."""
        self.backupScheduler.cancel()

    # A single guard applied to every command in this cog.
    async def cog_check(self, ctx):  # for prefix commands (unused)
        return True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if _is_admin(interaction):
            return True
        await interaction.response.send_message(
            "⛔ You are not authorised to use this bot.", ephemeral=True
        )
        _log.warning("denied command from %s", userTag(interaction.user))
        return False

    # --- read-only ------------------------------------------------------
    @app_commands.command(description="Show whether the server is up and who is online.")
    async def status(self, interaction: discord.Interaction):
        try:
            out = await _rcon("list")
            e = discord.Embed(title="🟢 Server online", description=out, color=OK_GREEN)
        except RconError:
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
        except RconError as e:
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
        except RconError as e:
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
        except RconError as e:
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
        except (StorageError, RuntimeError) as error:
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

    @backupGroup.command(name="download", description="Download a backup if it fits Discord's limit.")
    async def backupDownload(self, interaction: discord.Interaction, name: str):
        try:
            path = self.storage.resolveBackup(name)
            await self._sendFile(interaction, path, "World backup")
        except StorageError as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @backupGroup.command(name="delete", description="Delete one selected backup archive.")
    @app_commands.describe(confirm="Type DELETE to confirm permanent deletion")
    async def backupDelete(self, interaction: discord.Interaction, name: str, confirm: str):
        if confirm != "DELETE":
            await interaction.response.send_message("❌ Type `DELETE` exactly to confirm.", ephemeral=True)
            return
        try:
            await asyncio.to_thread(self.storage.deleteBackup, name)
            await interaction.response.send_message(f"✅ Deleted `{name}`.", ephemeral=True)
            _log.warning("backup delete by %s: %s", userTag(interaction.user), name)
        except StorageError as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @backupGroup.command(name="restore", description="Restore a backup after an emergency snapshot.")
    @app_commands.describe(confirm="Type RESTORE to confirm stopping and replacing the live world")
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
        except (StorageError, RuntimeError) as error:
            await self._editError(interaction, error)

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
        except (ValueError, RuntimeError, OSError) as error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)

    @backupGroup.command(name="enabled", description="Enable or pause automatic backups.")
    async def backupEnabled(self, interaction: discord.Interaction, enabled: bool):
        try:
            settings = replace(self.settingsStore.load(), enabled=enabled)
            self.settingsStore.save(settings)
            await interaction.response.send_message(f"✅ Automatic backups: **{enabled}**", ephemeral=True)
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
        except (StorageError, OSError) as error:
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
        except (StorageError, RuntimeError) as error:
            await self._editError(interaction, error)

    @worldGroup.command(name="download", description="Download an imported map if it fits Discord's limit.")
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
    async def worldDelete(self, interaction: discord.Interaction, name: str, confirm: str):
        if confirm != "DELETE":
            await interaction.response.send_message("❌ Type `DELETE` exactly to confirm.", ephemeral=True)
            return
        try:
            await asyncio.to_thread(self.storage.deleteWorld, name)
            await interaction.response.send_message(f"✅ Deleted imported map `{name}`.", ephemeral=True)
            _log.warning("world delete by %s: %s", userTag(interaction.user), name)
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
    @app_commands.command(description="Attach the bot's current log file.")
    async def logs(self, interaction: discord.Interaction):
        path = log.current_log_file()
        if not path or not os.path.exists(path):
            await interaction.response.send_message("No log file yet.", ephemeral=True)
            return
        size = os.path.getsize(path)
        # Discord's default upload cap is 8MB; send a tail preview if larger.
        if size <= 7 * 1024 * 1024:
            await interaction.response.send_message(
                content="📄 Current bot log:", file=discord.File(path), ephemeral=True
            )
        else:
            tail = log.recent_lines(40)
            await interaction.response.send_message(
                content=f"📄 Log too large to attach ({size // 1024}KB). Last 40 lines:\n"
                f"```\n{tail[-1800:]}\n```",
                ephemeral=True,
            )
        _log.info("logs by %s", userTag(interaction.user))


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
