#!/usr/bin/env bash
# backup.sh — snapshot the world folders with rotation.
#
# Safe-by-default: if the server is running and RCON is available, it
# disables auto-save and flushes to disk before copying, then re-enables
# it — so backups are never taken mid-write. Old backups beyond
# BACKUP_KEEP (default 10) are pruned so the 32GB SD card doesn't fill up.
#
# Usage:  ./scripts/backup.sh
# Cron:   0 5 * * *  /home/pi/raspi-mc-server/scripts/backup.sh >> ~/mc-backup.log 2>&1
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$REPO_DIR/.env" ] && set -a && . "$REPO_DIR/.env" && set +a

SERVER_DIR="${MC_SERVER_DIR:-$REPO_DIR/server}"
BACKUP_DIR="${MC_BACKUP_DIR:-$REPO_DIR/backups}"
KEEP="${BACKUP_KEEP:-10}"
RCON_HOST="${RCON_HOST:-127.0.0.1}"
RCON_PORT="${RCON_PORT:-25575}"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/world_$STAMP.tar.gz"
mkdir -p "$BACKUP_DIR"

rcon() {
  command -v mcrcon >/dev/null 2>&1 && [ -n "${RCON_PASSWORD:-}" ] || return 1
  mcrcon -H "$RCON_HOST" -P "$RCON_PORT" -p "$RCON_PASSWORD" "$@" >/dev/null 2>&1
}

RUNNING=0
if rcon "list"; then RUNNING=1; fi

if [ "$RUNNING" -eq 1 ]; then
  echo "==> Server up: flushing world before backup..."
  rcon "say §7Backing up the world..." || true
  rcon "save-off" || true
  rcon "save-all flush" || true
  sleep 3
fi

# Only back up world dirs (not the jar/logs) to keep archives small.
WORLDS=()
for w in world world_nether world_the_end; do
  [ -d "$SERVER_DIR/$w" ] && WORLDS+=("$w")
done

if [ "${#WORLDS[@]}" -eq 0 ]; then
  echo "!! No world folders found in $SERVER_DIR — nothing to back up." >&2
  [ "$RUNNING" -eq 1 ] && rcon "save-on" || true
  exit 1
fi

echo "==> Archiving: ${WORLDS[*]}"
tar -czf "$OUT" -C "$SERVER_DIR" "${WORLDS[@]}"

if [ "$RUNNING" -eq 1 ]; then
  rcon "save-on" || true
  rcon "say §aBackup complete." || true
fi

echo "==> Wrote $OUT ($(du -h "$OUT" | cut -f1))"

# Rotation: keep only the newest $KEEP archives.
echo "==> Pruning old backups (keep $KEEP)..."
ls -1t "$BACKUP_DIR"/world_*.tar.gz 2>/dev/null | tail -n +"$((KEEP + 1))" | while read -r old; do
  echo "    rm $old"
  rm -f "$old"
done

echo "==> Backup done."
