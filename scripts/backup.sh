#!/usr/bin/env bash
# backup.sh — snapshot the world folders with rotation.
#
# Safe-by-default: if the server is running and RCON is available, it
# disables auto-save and flushes to disk before copying, then re-enables
# it — so backups are never taken mid-write. Old backups beyond
# BACKUP_KEEP (default 96) are pruned so a manual fallback cannot fill the HDD.
#
# Usage:  ./scripts/backup.sh
# Automatic scheduling is handled by the Discord bot's persistent policy.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$REPO_DIR/scripts/lib.sh"
load_env_file "$REPO_DIR/.env"

STORAGE_ROOT="${MC_STORAGE_ROOT:-/mnt/minecraft}"
SERVER_DIR="${MC_SERVER_DIR:-$STORAGE_ROOT/live}"
BACKUP_DIR="${MC_BACKUP_DIR:-$STORAGE_ROOT/backups}"
KEEP="${BACKUP_KEEP:-96}"
RCON_HOST="${RCON_HOST:-127.0.0.1}"
RCON_PORT="${RCON_PORT:-25575}"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/world_$STAMP.tar.gz"

# Never fall through to the microSD when the configured external HDD is absent.
if [ "${MC_REQUIRE_STORAGE_MOUNT:-true}" = "true" ] && ! mountpoint -q "$STORAGE_ROOT"; then
  echo "!! HDD is not mounted at $STORAGE_ROOT" >&2
  exit 1
fi
mkdir -p "$BACKUP_DIR"

# Serialize bot-scheduled and manual backups at the filesystem boundary.
if ! command -v flock >/dev/null 2>&1; then
  echo "!! flock is required for safe backups (install util-linux)." >&2
  exit 1
fi
exec 9>"$BACKUP_DIR/.backup.lock"
if ! flock -n 9; then
  echo "==> Another backup is already running; skipping."
  exit 0
fi

rcon() {
  command -v mcrcon >/dev/null 2>&1 && [ -n "${RCON_PASSWORD:-}" ] || return 1
  mcrcon -H "$RCON_HOST" -P "$RCON_PORT" -p "$RCON_PASSWORD" "$@" >/dev/null 2>&1
}

RUNNING=0
if rcon "list"; then RUNNING=1; fi

if [ "$RUNNING" -eq 1 ]; then
  echo "==> Server up: flushing world before backup..."
  rcon "say §7Backing up the world..." || true
  # Always restore auto-save if any later backup step exits unexpectedly.
  trap 'rcon "save-on" || true' EXIT
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
