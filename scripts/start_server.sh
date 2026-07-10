#!/usr/bin/env bash
# start_server.sh — launch PaperMC with memory/GC flags tuned for a Pi 4B (4GB).
#
# Memory: the Pi 4B has 4GB shared with the OS. We give the JVM a fixed
# 2600M heap (Xms=Xmx avoids runtime resizing pauses) which leaves ~1.4GB
# for the OS, RCON, and the Discord bot. Override with MC_MEMORY in .env.
#
# GC: the "Aikar flags" (G1GC tuned for Minecraft) keep pause times low.
# They are widely used for small survival servers and matter more than raw
# heap size for a smooth Pi experience.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Load .env if present (for MC_SERVER_DIR / MC_MEMORY).
[ -f "$REPO_DIR/.env" ] && set -a && . "$REPO_DIR/.env" && set +a

SERVER_DIR="${MC_SERVER_DIR:-$REPO_DIR/server}"
MEMORY="${MC_MEMORY:-2600M}"
JAR="${MC_JAR:-paper.jar}"

cd "$SERVER_DIR"

if [ ! -f "$JAR" ]; then
  echo "!! $SERVER_DIR/$JAR not found. Run scripts/install_server.sh first." >&2
  exit 1
fi

exec java \
  -Xms"$MEMORY" -Xmx"$MEMORY" \
  -XX:+UseG1GC \
  -XX:+ParallelRefProcEnabled \
  -XX:MaxGCPauseMillis=200 \
  -XX:+UnlockExperimentalVMOptions \
  -XX:+DisableExplicitGC \
  -XX:+AlwaysPreTouch \
  -XX:G1NewSizePercent=30 \
  -XX:G1MaxNewSizePercent=40 \
  -XX:G1HeapRegionSize=8M \
  -XX:G1ReservePercent=20 \
  -XX:G1HeapWastePercent=5 \
  -XX:G1MixedGCCountTarget=4 \
  -XX:InitiatingHeapOccupancyPercent=15 \
  -XX:G1MixedGCLiveThresholdPercent=90 \
  -XX:G1RSetUpdatingPauseTimePercent=5 \
  -XX:SurvivorRatio=32 \
  -XX:+PerfDisableSharedMem \
  -XX:MaxTenuringThreshold=1 \
  -Dusing.aikars.flags=https://mcflags.emc.gs \
  -Daikars.new.flags=true \
  -jar "$JAR" --nogui
