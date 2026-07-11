#!/usr/bin/env bash
# Register an existing ext4 partition as the Minecraft HDD mount.
# This intentionally never formats a disk; formatting destroys data and remains manual.
set -euo pipefail

# Validate the one explicit block-device argument before changing fstab.
if [ "$#" -ne 1 ] || [ ! -b "$1" ]; then
  echo "Usage: sudo $0 /dev/sdXN" >&2
  echo "The partition must already be formatted as ext4." >&2
  exit 2
fi

DEVICE="$1"
MOUNT_POINT="/mnt/minecraft"
SERVICE_USER="${SUDO_USER:-$(id -un)}"
UUID="$(blkid -s UUID -o value "$DEVICE")"
TYPE="$(blkid -s TYPE -o value "$DEVICE")"

# Refuse unknown or unsuitable filesystems instead of guessing.
if [ -z "$UUID" ] || [ "$TYPE" != "ext4" ]; then
  echo "!! $DEVICE must have an ext4 filesystem and UUID." >&2
  exit 1
fi

# Mount by UUID so USB enumeration changes do not redirect the server.
mkdir -p "$MOUNT_POINT"
FSTAB_LINE="UUID=$UUID $MOUNT_POINT ext4 defaults,nofail,x-systemd.device-timeout=10s 0 2"
if ! grep -q "UUID=$UUID" /etc/fstab; then
  printf '%s\n' "$FSTAB_LINE" >> /etc/fstab
fi
mount "$MOUNT_POINT"

# Create the only writable data tree used by Minecraft and the bot.
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0750 \
  "$MOUNT_POINT/live" \
  "$MOUNT_POINT/backups" \
  "$MOUNT_POINT/worlds" \
  "$MOUNT_POINT/uploads" \
  "$MOUNT_POINT/staging" \
  "$MOUNT_POINT/quarantine"

echo "==> HDD ready at $MOUNT_POINT (UUID=$UUID, owner=$SERVICE_USER)"
