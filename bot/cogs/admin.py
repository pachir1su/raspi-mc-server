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

import discord
from discord import app_commands
from discord.ext import commands

from bot import log
from bot import BRAND_BLUE, OK_GREEN, ERR_RED, userTag
from bot.config import cfg
from bot.loading import animate_while
from bot.rcon import Rcon, RconError

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

    # --- backup ---------------------------------------------------------
    @app_commands.command(description="Back up the world now (with rotation).")
    async def backup(self, interaction: discord.Interaction):
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        script = os.path.join(repo, "scripts", "backup.sh")

        async def work():
            return await asyncio.to_thread(
                lambda: subprocess.run(
                    ["bash", script], capture_output=True, text=True, timeout=600
                )
            )

        res = await animate_while(interaction, work(), "Backing up the world")
        ok = res.returncode == 0
        tail = (res.stdout + res.stderr).strip().splitlines()[-6:]
        e = discord.Embed(
            title="✅ Backup complete" if ok else "❌ Backup failed",
            description="```\n" + "\n".join(tail)[:1500] + "\n```",
            color=OK_GREEN if ok else ERR_RED,
        )
        await interaction.edit_original_response(embed=e)
        _log.info("backup by %s -> ok=%s", userTag(interaction.user), ok)

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
