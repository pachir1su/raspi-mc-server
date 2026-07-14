#!/usr/bin/env bash
# Read-only Raspberry Pi, HDD, service, RCON, and resource health summary.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$REPO_DIR/scripts/lib.sh"
load_env_file "$REPO_DIR/.env"

STORAGE_ROOT="${MC_STORAGE_ROOT:-/mnt/minecraft}"
SERVICE="${MC_SERVICE_NAME:-minecraft.service}"
RCON_HOST="${RCON_HOST:-127.0.0.1}"
RCON_PORT="${RCON_PORT:-25575}"

# Report critical dependencies first without mutating any service or file.
echo "==> Services"
systemctl is-active "$SERVICE" || true
systemctl is-active mc-discord-bot.service || true

echo
echo "==> HDD"
if mountpoint -q "$STORAGE_ROOT"; then
  findmnt "$STORAGE_ROOT"
  df -h "$STORAGE_ROOT"
else
  echo "!! Not mounted: $STORAGE_ROOT"
fi

echo
echo "==> Raspberry Pi"
uptime
free -h
if command -v vcgencmd >/dev/null 2>&1; then
  vcgencmd measure_temp
  vcgencmd get_throttled
else
  echo "vcgencmd unavailable"
fi

echo
echo "==> Paper RCON"
if command -v mcrcon >/dev/null 2>&1 && [ -n "${RCON_PASSWORD:-}" ]; then
  mcrcon -H "$RCON_HOST" -P "$RCON_PORT" -p "$RCON_PASSWORD" "list" "tps" || true
else
  echo "mcrcon or RCON_PASSWORD unavailable"
fi
