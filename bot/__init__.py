"""Discord admin bot package for raspi-mc-server.

Small, single-purpose bot: it lets the OWNER run server admin and cheat
commands remotely (via RCON) and manage the systemd service, with a few
quality-of-life touches (a loading animation for slow actions, log-file
attachments). Everything player-facing stays read-only; only whitelisted
admin user IDs can mutate the server.
"""

# Brand accent used across embeds (a calm blue). Kept in one place so the
# bot has a consistent look.
BRAND_BLUE = 0x4C9EDA
OK_GREEN = 0x57F287
WARN_YELLOW = 0xFEE75C
ERR_RED = 0xED4245


def userTag(user) -> str:
    """Readable '@name (id)' tag for logs — never dumps tokens or secrets."""
    name = getattr(user, "display_name", None) or getattr(user, "name", "?")
    return f"@{name} ({getattr(user, 'id', '?')})"
