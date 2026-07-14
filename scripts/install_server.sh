#!/usr/bin/env bash
# install_server.sh — install a PaperMC server on a Raspberry Pi 4B (64-bit).
#
# What it does:
#   1. Installs a headless JDK (Temurin 21 via apt on 64-bit Raspberry Pi OS).
#   2. Downloads the latest PaperMC build for the chosen Minecraft version.
#   3. Seeds server.properties from the template and accepts the EULA.
#   4. Leaves ops/whitelist for you to fill in (owner-only cheats).
#
# Re-runnable: it will re-download the jar and refresh only missing config.
#
# Usage:
#   MC_VERSION=1.21.4 ./scripts/install_server.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Load the HDD-backed server directory selected during setup.
. "$REPO_DIR/scripts/lib.sh"
load_env_file "$REPO_DIR/.env"
SERVER_DIR="${MC_SERVER_DIR:-$REPO_DIR/server}"
MC_VERSION="${MC_VERSION:-1.21.4}"

echo "==> raspi-mc-server installer"
echo "    server dir : $SERVER_DIR"
echo "    mc version : $MC_VERSION"

# --- 1. Java -------------------------------------------------------------
if ! command -v java >/dev/null 2>&1; then
  echo "==> Installing OpenJDK 21 (headless)..."
  sudo apt-get update
  sudo apt-get install -y openjdk-21-jre-headless
else
  echo "==> Java already present: $(java -version 2>&1 | head -n1)"
fi

mkdir -p "$SERVER_DIR"

# --- 2. PaperMC jar ------------------------------------------------------
echo "==> Resolving latest PaperMC build for $MC_VERSION..."
API="https://api.papermc.io/v2/projects/paper"
BUILD="$(curl -fsSL "$API/versions/$MC_VERSION/builds" \
  | grep -o '"build":[0-9]*' | tail -n1 | grep -o '[0-9]*')"
if [ -z "${BUILD:-}" ]; then
  echo "!! Could not find a Paper build for $MC_VERSION. Check the version." >&2
  exit 1
fi
JAR="paper-$MC_VERSION-$BUILD.jar"
URL="$API/versions/$MC_VERSION/builds/$BUILD/downloads/$JAR"
echo "==> Downloading $JAR ..."
curl -fsSL -o "$SERVER_DIR/paper.jar" "$URL"
echo "    saved to $SERVER_DIR/paper.jar (build $BUILD)"

# --- 3. Config seeding ---------------------------------------------------
if [ ! -f "$SERVER_DIR/server.properties" ]; then
  cp "$REPO_DIR/server/server.properties.template" "$SERVER_DIR/server.properties"
  echo "==> Seeded server.properties from template."
  echo "    !! Edit rcon.password in $SERVER_DIR/server.properties before starting."
fi

# EULA — running the server implies you accept Mojang's EULA.
echo "eula=true" > "$SERVER_DIR/eula.txt"

echo
echo "==> Done. Next steps:"
echo "  1. Set a strong rcon.password in $SERVER_DIR/server.properties"
echo "  2. Start once to generate the world, then stop:"
echo "       ./scripts/start_server.sh   (Ctrl+C to stop the first run)"
echo "  3. Op ONLY yourself:  op <YourName>   (in the console)"
echo "  4. Whitelist friends: whitelist add <name>"
echo "  5. Install the systemd services in deploy/ for auto-start."
