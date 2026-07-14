#!/usr/bin/env bash
# restore.sh — restore a world backup created by backup.sh.
#
# Stops the server first (you never restore over a live world), moves the
# current world aside as world.bak_<stamp>, then extracts the chosen
# archive. Refuses to run unless the server is stopped.
#
# Usage:
#   ./scripts/restore.sh                       # restore the newest backup
#   ./scripts/restore.sh backups/world_XXX.tar.gz
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$REPO_DIR/scripts/lib.sh"
load_env_file "$REPO_DIR/.env"

STORAGE_ROOT="${MC_STORAGE_ROOT:-/mnt/minecraft}"
SERVER_DIR="${MC_SERVER_DIR:-$STORAGE_ROOT/live}"
BACKUP_DIR="${MC_BACKUP_DIR:-$STORAGE_ROOT/backups}"
SERVICE="${MC_SERVICE_NAME:-minecraft.service}"

# Never restore into a microSD directory when the expected HDD is absent.
if [ "${MC_REQUIRE_STORAGE_MOUNT:-true}" = "true" ] && ! mountpoint -q "$STORAGE_ROOT"; then
  echo "!! HDD is not mounted at $STORAGE_ROOT" >&2
  exit 1
fi

ARCHIVE="${1:-$(ls -1t "$BACKUP_DIR"/world_*.tar.gz 2>/dev/null | head -n1 || true)}"
if [ -z "${ARCHIVE:-}" ] || [ ! -f "$ARCHIVE" ]; then
  echo "!! No backup archive found. Pass one explicitly: ./scripts/restore.sh <file>" >&2
  exit 1
fi

# Reject corrupt or truncated archives before moving any current world.
echo "==> Verifying $ARCHIVE"
tar -tzf "$ARCHIVE" >/dev/null

if systemctl is-active --quiet "$SERVICE"; then
  echo "!! $SERVICE is running. Stop it first:  sudo systemctl stop $SERVICE" >&2
  exit 1
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
MOVED_WORLDS=()

# Restore every moved world if extraction or another later step fails.
rollback_worlds() {
  local status=$?
  trap - EXIT
  [ "$status" -ne 0 ] || return 0

  echo "!! Restore failed; rolling back previous worlds." >&2
  local worldName backupPath
  for worldName in "${MOVED_WORLDS[@]}"; do
    backupPath="$SERVER_DIR/${worldName}.bak_$STAMP"
    if [ -e "$backupPath" ]; then
      rm -rf -- "$SERVER_DIR/$worldName"
      mv -- "$backupPath" "$SERVER_DIR/$worldName"
      echo "    restored $worldName" >&2
    fi
  done
  exit "$status"
}
trap rollback_worlds EXIT

echo "==> Restoring $ARCHIVE into $SERVER_DIR"
for w in world world_nether world_the_end; do
  if [ -d "$SERVER_DIR/$w" ]; then
    mv "$SERVER_DIR/$w" "$SERVER_DIR/${w}.bak_$STAMP"
    MOVED_WORLDS+=("$w")
    echo "    moved current $w -> ${w}.bak_$STAMP"
  fi
done

tar -xzf "$ARCHIVE" -C "$SERVER_DIR"
trap - EXIT
echo "==> Restore complete. Start the server when ready:"
echo "     sudo systemctl start $SERVICE"
