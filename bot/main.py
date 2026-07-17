"""Single entry point for first setup, crossplay, and the Discord bot.

Run with:  python -m bot.main   (or via the systemd unit)

Registers the Admin cog and syncs slash commands. If DISCORD_GUILD_ID is
set, commands sync to that guild instantly (best for a private server);
otherwise they sync globally (can take up to ~1 hour to appear).
"""

import argparse
import os
import sys

import discord
from discord.ext import commands
from dotenv import load_dotenv

from bot import log
from bot import userTag
from bot.app_settings import ensureFirstRunSetup
from bot.bundled_plugins import BundledPluginManager
from bot.crossplay import CrossplayManager
from bot.command_i18n import CommandTranslator

_log = log.get("main")
cfg = None
t = None


async def syncCommandTree(tree, guildIds: list[int]) -> None:
    """Publish the bounded command surface and remove stale guild globals."""
    if guildIds:
        for guildId in guildIds:
            guild = discord.Object(id=guildId)
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
        # Guild-only mode must also delete global commands from older
        # deployments, otherwise Discord shows both sets in one server.
        tree.clear_commands(guild=None)
        await tree.sync()
        return
    await tree.sync()


class McBot(commands.Bot):
    def __init__(self):
        # This bot only needs slash commands — no privileged message intent.
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Discord chooses these localizations from each user's client language.
        await self.tree.set_translator(CommandTranslator())
        await self.load_extension("bot.cogs.admin")
        await self.load_extension("bot.cogs.friend")
        await syncCommandTree(self.tree, cfg.guild_ids)
        if cfg.guild_ids:
            _log.info("synced commands to guilds %s", cfg.guild_ids)
        else:
            _log.info("synced commands globally")

    async def on_ready(self):
        _log.info("logged in as %s", userTag(self.user))
        await self.change_presence(
            activity=discord.Game(name=t("presence"))
        )


def main():
    """Complete setup if needed, prepare crossplay, and run every bot cog."""
    parser = argparse.ArgumentParser(description="raspi-mc-server launcher")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="reopen the language and server-mode setup menu",
    )
    args = parser.parse_args()

    # Secrets and machine-specific paths stay in .env; user choices do not.
    load_dotenv()
    stateDir = os.getenv("MC_STATE_DIR", "data")
    settings = ensureFirstRunSetup(
        stateDir,
        force=args.setup,
        interactive=sys.stdin.isatty(),
    )

    # Download and configure crossplay only when it is selected or incomplete.
    serverDir = os.getenv("MC_SERVER_DIR", "/mnt/minecraft/live")
    serviceName = os.getenv("MC_SERVICE_NAME", "minecraft.service")
    try:
        repoDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pluginManager = BundledPluginManager(repoDir, serverDir, serviceName)
        pluginChanged = pluginManager.ensure()
        crossplayManager = CrossplayManager(serverDir, serviceName)
        crossplayChanged = crossplayManager.ensure(settings)
        if pluginChanged and not crossplayChanged:
            pluginManager.restartMinecraft()
        crossplayManager.ensureMinecraftRunning()
    except RuntimeError as error:
        raise SystemExit(f"Crossplay setup failed: {error}") from error

    # Import config after the menu writes app-settings.json.
    global cfg, t
    from bot.config import cfg as loadedConfig
    from bot.i18n import t as translate

    cfg = loadedConfig
    t = translate
    log.setup()
    cfg.validate()
    _log.info("starting bot (admins: %d)", len(cfg.admin_ids))
    McBot().run(cfg.token, log_handler=None)


if __name__ == "__main__":
    main()
