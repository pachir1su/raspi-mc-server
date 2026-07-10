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

# --- Minecraft server ----------------------------------------------------
if [ ! -f "$REPO_DIR/server/paper.jar" ]; then
  echo "==> Installing PaperMC..."
  "$REPO_DIR/scripts/install_server.sh"
fi

# --- Python venv for the bot --------------------------------------------
if [ ! -d "$REPO_DIR/.venv" ]; then
  echo "==> Creating Python venv..."
  python3 -m venv "$REPO_DIR/.venv"
fi
"$REPO_DIR/.venv/bin/pip" install --upgrade pip
"$REPO_DIR/.venv/bin/pip" install -r "$REPO_DIR/requirements.txt"

# --- .env ----------------------------------------------------------------
if [ ! -f "$REPO_DIR/.env" ]; then
  cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
  chmod 600 "$REPO_DIR/.env"
  echo "==> Created .env from example (chmod 600). EDIT IT before starting the bot."
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
sudo cp "$REPO_DIR/deploy/minecraft.service" /etc/systemd/system/
sudo cp "$REPO_DIR/deploy/mc-discord-bot.service" /etc/systemd/system/
sudo systemctl daemon-reload

cat <<EOF

==> Provisioning done. Remaining manual steps:
  1. Edit $REPO_DIR/server/server.properties  -> set a strong rcon.password
  2. Edit $REPO_DIR/.env                       -> DISCORD_TOKEN, ADMIN_USER_IDS,
                                                  RCON_PASSWORD (match server.properties)
  3. Start the server:   sudo systemctl enable --now minecraft.service
  4. Op yourself once:   (console) op <YourName>
  5. Start the bot:      sudo systemctl enable --now mc-discord-bot.service

See docs/en/setup.md (English) or docs/ko/setup.md (한국어) for details.
EOF
