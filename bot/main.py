"""Entry point for the Discord admin bot.

Run with:  python -m bot.main   (or via the systemd unit)

Registers the Admin cog and syncs slash commands. If DISCORD_GUILD_ID is
set, commands sync to that guild instantly (best for a private server);
otherwise they sync globally (can take up to ~1 hour to appear).
"""

import asyncio

import discord
from discord.ext import commands

from bot import log
from bot import userTag
from bot.config import cfg

_log = log.get("main")


class McBot(commands.Bot):
    def __init__(self):
        # This bot only needs slash commands — no privileged message intent.
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.load_extension("bot.cogs.admin")
        if cfg.guild_id:
            guild = discord.Object(id=int(cfg.guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            _log.info("synced commands to guild %s", cfg.guild_id)
        else:
            await self.tree.sync()
            _log.info("synced commands globally")

    async def on_ready(self):
        _log.info("logged in as %s", userTag(self.user))
        await self.change_presence(
            activity=discord.Game(name="Raspberry Pi Minecraft")
        )


def main():
    log.setup()
    cfg.validate()
    _log.info("starting bot (admins: %d)", len(cfg.admin_ids))
    McBot().run(cfg.token, log_handler=None)


if __name__ == "__main__":
    main()
