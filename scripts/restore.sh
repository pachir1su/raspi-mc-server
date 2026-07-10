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
[ -f "$REPO_DIR/.env" ] && set -a && . "$REPO_DIR/.env" && set +a

SERVER_DIR="${MC_SERVER_DIR:-$REPO_DIR/server}"
BACKUP_DIR="${MC_BACKUP_DIR:-$REPO_DIR/backups}"
SERVICE="${MC_SERVICE_NAME:-minecraft.service}"

ARCHIVE="${1:-$(ls -1t "$BACKUP_DIR"/world_*.tar.gz 2>/dev/null | head -n1 || true)}"
if [ -z "${ARCHIVE:-}" ] || [ ! -f "$ARCHIVE" ]; then
  echo "!! No backup archive found. Pass one explicitly: ./scripts/restore.sh <file>" >&2
  exit 1
fi

if systemctl is-active --quiet "$SERVICE"; then
  echo "!! $SERVICE is running. Stop it first:  sudo systemctl stop $SERVICE" >&2
  exit 1
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
echo "==> Restoring $ARCHIVE into $SERVER_DIR"
for w in world world_nether world_the_end; do
  if [ -d "$SERVER_DIR/$w" ]; then
    mv "$SERVER_DIR/$w" "$SERVER_DIR/${w}.bak_$STAMP"
    echo "    moved current $w -> ${w}.bak_$STAMP"
  fi
done

tar -xzf "$ARCHIVE" -C "$SERVER_DIR"
echo "==> Restore complete. Start the server when ready:"
echo "     sudo systemctl start $SERVICE"
