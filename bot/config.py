"""Configuration loaded from environment / .env.

Reads once at import. Fails loudly for the few values the bot cannot run
without (token, RCON password) so misconfiguration is obvious at startup
rather than at first command.
"""

import os

from dotenv import load_dotenv

from bot import log
from bot.app_settings import AppSettingsStore

_log = log.get("config")

# Load .env from the repo root if present. On the Pi, systemd also injects
# these via EnvironmentFile — load_dotenv won't clobber existing vars.
load_dotenv()


def _storedLanguage(stateDir: str) -> str:
    """Read the menu-selected language, defaulting only before first setup."""
    store = AppSettingsStore(stateDir)
    if not store.exists():
        return "ko"
    return store.load().language


def _int_set(raw: str):
    """Parse a comma-separated list of IDs into a set of ints (ignores blanks)."""
    out = set()
    for part in (raw or "").split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def _guild_ids(raw: str):
    """Parse comma-separated guild IDs into a list of ints (이슈 G, #18).

    빈 값이면 전역 등록을 위해 빈 리스트를 반환합니다. 공백은 허용하고 빈 항목은
    무시하며, 숫자가 아닌 값은 크래시 대신 경고 로그 후 건너뜁니다.
    """
    out = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        if part.isdigit():
            out.append(int(part))
        else:
            _log.warning("ignoring invalid DISCORD_GUILD_ID entry: %r", part)
    return out


class Config:
    # Runtime data path is needed before loading menu-managed settings.
    state_dir = os.getenv("MC_STATE_DIR", "data")

    # Discord
    token = os.getenv("DISCORD_TOKEN", "")
    # 쉼표로 여러 길드를 지정할 수 있습니다(친구 서버 + 개인 서버). 빈 값이면 전역.
    guild_ids = _guild_ids(os.getenv("DISCORD_GUILD_ID", ""))
    admin_ids = _int_set(os.getenv("ADMIN_USER_IDS", ""))
    status_channel_id = os.getenv("STATUS_CHANNEL_ID", "").strip() or None
    language = _storedLanguage(state_dir)
    public_address = os.getenv("MC_PUBLIC_ADDRESS", "").strip()
    public_version = os.getenv("MC_PUBLIC_VERSION", "Paper / Java").strip()
    public_rules = os.getenv("MC_PUBLIC_RULES", "").strip()
    public_commands_enabled = os.getenv("PUBLIC_COMMANDS_ENABLED", "true").lower() in {
        "1", "true", "yes", "on",
    }
    map_url_template = os.getenv("MC_MAP_URL_TEMPLATE", "").strip()
    # MC_SPAWN_X/Y/Z/DIMENSION 오버라이드는 제거했습니다. 스폰 귀환은 항상
    # 월드 스폰(setworldspawn)을 사용하므로 죽었을 때 리스폰 위치와 항상
    # 일치합니다. 운영 .env에 남은 MC_SPAWN_* 값은 무시되며 지워도 됩니다.
    # 스폰 위치 변경: 관리 패널 → 빠른 명령 → 스폰 지정.
    alert_cooldown_minutes = int(os.getenv("ALERT_COOLDOWN_MINUTES", "30"))
    alert_tps_threshold = float(os.getenv("ALERT_TPS_THRESHOLD", "18.0"))
    alert_memory_percent = float(os.getenv("ALERT_MEMORY_PERCENT", "85"))
    alert_temperature_celsius = float(os.getenv("ALERT_TEMPERATURE_CELSIUS", "80"))
    alert_min_free_gb = float(os.getenv("ALERT_MIN_FREE_GB", "20"))

    # RCON
    rcon_host = os.getenv("RCON_HOST", "127.0.0.1")
    rcon_port = int(os.getenv("RCON_PORT", "25575"))
    rcon_password = os.getenv("RCON_PASSWORD", "")

    # systemd service the bot may start/stop.
    mc_service = os.getenv("MC_SERVICE_NAME", "minecraft.service")

    # Storage paths. Runtime worlds and archives live on the external HDD.
    storage_root = os.getenv("MC_STORAGE_ROOT", "/mnt/minecraft")
    server_dir = os.getenv("MC_SERVER_DIR", "/mnt/minecraft/live")
    require_storage_mount = os.getenv("MC_REQUIRE_STORAGE_MOUNT", "true").lower() in {
        "1", "true", "yes", "on",
    }

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
                "\nSet these in the tracked placeholder .env on the Pi."
            )


cfg = Config()
