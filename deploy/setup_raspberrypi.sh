#!/usr/bin/env bash
# setup_raspberrypi.sh — one-shot provisioning for a fresh 64-bit Raspberry Pi OS.
#
# Installs system packages, the Minecraft server, the Python venv for the
# Discord bot, the systemd units, and a narrow sudoers rule so the bot can
# start/stop ONLY the minecraft service (no broad root access).
#
# Run from the repo root on the Pi:
#   ./deploy/setup_raspberrypi.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_USER="${SERVICE_USER:-$(id -un)}"

echo "==> Provisioning raspi-mc-server for user '$SERVICE_USER'"

# --- System packages -----------------------------------------------------
echo "==> Installing system packages..."
sudo apt-get update
sudo apt-get install -y \
  openjdk-21-jre-headless \
  python3 python3-venv python3-pip \
  mcrcon \
  curl tar

# --- Python venv for the bot --------------------------------------------
if [ ! -d "$REPO_DIR/.venv" ]; then
  echo "==> Creating Python venv..."
  python3 -m venv "$REPO_DIR/.venv"
fi
"$REPO_DIR/.venv/bin/pip" install --upgrade pip
"$REPO_DIR/.venv/bin/pip" install -r "$REPO_DIR/requirements.txt"

# --- .env ----------------------------------------------------------------
if [ ! -f "$REPO_DIR/.env" ]; then
  echo "!! Tracked placeholder .env is missing; restore it from git before setup." >&2
  exit 1
fi
chmod 600 "$REPO_DIR/.env"
# Load paths selected by the operator before checking the installation target.
set -a
. "$REPO_DIR/.env"
set +a

# --- External HDD --------------------------------------------------------
if ! mountpoint -q /mnt/minecraft; then
  echo "!! /mnt/minecraft is not mounted. Prepare the HDD first:" >&2
  echo "     sudo mkfs.ext4 /dev/sdXN       # DESTRUCTIVE: choose the correct partition" >&2
  echo "     sudo $REPO_DIR/scripts/setup_hdd.sh /dev/sdXN" >&2
  exit 1
fi

# --- Minecraft server ----------------------------------------------------
if [ ! -f "${MC_SERVER_DIR:-/mnt/minecraft/live}/paper.jar" ]; then
  echo "==> Installing PaperMC on the HDD..."
  "$REPO_DIR/scripts/install_server.sh"
fi

# --- sudoers: let the bot control ONLY the minecraft service -------------
SUDOERS="/etc/sudoers.d/raspi-mc-server"
echo "==> Installing narrow sudoers rule at $SUDOERS"
sudo tee "$SUDOERS" >/dev/null <<EOF
# Allow $SERVICE_USER to manage only the minecraft service without a password.
$SERVICE_USER ALL=(root) NOPASSWD: /bin/systemctl start minecraft.service, /bin/systemctl stop minecraft.service, /bin/systemctl restart minecraft.service, /bin/systemctl is-active minecraft.service
EOF
sudo chmod 440 "$SUDOERS"

# --- systemd units -------------------------------------------------------
echo "==> Installing systemd units..."
# Render the repository path and service account instead of assuming /home/pi.
sed -e "s|^User=.*|User=$SERVICE_USER|" \
    -e "s|/home/pi/raspi-mc-server|$REPO_DIR|g" \
    "$REPO_DIR/deploy/minecraft.service" | sudo tee /etc/systemd/system/minecraft.service >/dev/null
sed -e "s|^User=.*|User=$SERVICE_USER|" \
    -e "s|/home/pi/raspi-mc-server|$REPO_DIR|g" \
    "$REPO_DIR/deploy/mc-discord-bot.service" | sudo tee /etc/systemd/system/mc-discord-bot.service >/dev/null
sudo systemctl daemon-reload

cat <<EOF

==> Provisioning done. Remaining manual steps:
  1. Edit ${MC_SERVER_DIR:-/mnt/minecraft/live}/server.properties -> set a strong rcon.password
  2. Edit $REPO_DIR/.env                       -> DISCORD_TOKEN, ADMIN_USER_IDS,
                                                  RCON_PASSWORD (match server.properties)
  3. Start the server:   sudo systemctl enable --now minecraft.service
  4. Op yourself once:   (console) op <YourName>
  5. Start the bot:      sudo systemctl enable --now mc-discord-bot.service

See docs/en/setup.md (English) or docs/ko/setup.md (한국어) for details.
EOF
