#!/usr/bin/env bash
# stop_server.sh — gracefully stop the server via RCON (saves the world first).
#
# Prefers a clean RCON "stop" so chunks are saved. Falls back to systemd if
# RCON is unreachable. Never kills -9 unless you ask it to.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$REPO_DIR/.env" ] && set -a && . "$REPO_DIR/.env" && set +a

RCON_HOST="${RCON_HOST:-127.0.0.1}"
RCON_PORT="${RCON_PORT:-25575}"

if command -v mcrcon >/dev/null 2>&1 && [ -n "${RCON_PASSWORD:-}" ]; then
  echo "==> Saving world and stopping via RCON..."
  mcrcon -H "$RCON_HOST" -P "$RCON_PORT" -p "$RCON_PASSWORD" "save-all" "stop" || true
  exit 0
fi

if systemctl is-active --quiet "${MC_SERVICE_NAME:-minecraft.service}"; then
  echo "==> Stopping via systemd (${MC_SERVICE_NAME:-minecraft.service})..."
  sudo systemctl stop "${MC_SERVICE_NAME:-minecraft.service}"
  exit 0
fi

echo "!! Could not reach RCON and no active systemd unit found." >&2
echo "   Install mcrcon (apt install mcrcon) or use the systemd service." >&2
exit 1
