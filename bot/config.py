"""Configuration loaded from environment / .env.

Reads once at import. Fails loudly for the few values the bot cannot run
without (token, RCON password) so misconfiguration is obvious at startup
rather than at first command.
"""

import os

from dotenv import load_dotenv

# Load .env from the repo root if present. On the Pi, systemd also injects
# these via EnvironmentFile — load_dotenv won't clobber existing vars.
load_dotenv()


def _int_set(raw: str):
    """Parse a comma-separated list of IDs into a set of ints (ignores blanks)."""
    out = set()
    for part in (raw or "").split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


class Config:
    # Discord
    token = os.getenv("DISCORD_TOKEN", "")
    guild_id = os.getenv("DISCORD_GUILD_ID", "").strip() or None
    admin_ids = _int_set(os.getenv("ADMIN_USER_IDS", ""))
    status_channel_id = os.getenv("STATUS_CHANNEL_ID", "").strip() or None

    # RCON
    rcon_host = os.getenv("RCON_HOST", "127.0.0.1")
    rcon_port = int(os.getenv("RCON_PORT", "25575"))
    rcon_password = os.getenv("RCON_PASSWORD", "")

    # systemd service the bot may start/stop.
    mc_service = os.getenv("MC_SERVICE_NAME", "minecraft.service")

    def validate(self):
        """Raise if a must-have value is missing — called at startup."""
        missing = []
        if not self.token:
            missing.append("DISCORD_TOKEN")
        if not self.rcon_password:
            missing.append("RCON_PASSWORD")
        if not self.admin_ids:
            missing.append("ADMIN_USER_IDS (at least your own ID)")
        if missing:
            raise SystemExit(
                "Missing required config: " + ", ".join(missing) +
                "\nSet these in .env (see .env.example)."
            )


cfg = Config()
