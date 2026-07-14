#!/usr/bin/env bash
# install_server.sh — install a PaperMC server on a Raspberry Pi 4B (64-bit).
#
# What it does:
#   1. Resolves the newest STABLE PaperMC release through Fill v3.
#   2. Checks the selected release's minimum Java version.
#   3. Downloads and verifies the selected PaperMC server jar.
#   4. Seeds server.properties from the template and accepts the EULA.
#   5. Leaves ops/whitelist for you to fill in (owner-only cheats).
#
# Re-runnable: it will re-download the jar and refresh only missing config.
#
# Usage:
#   ./scripts/install_server.sh                         # newest STABLE version
#   MC_VERSION=26.1.2 ./scripts/install_server.sh       # selected STABLE version
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Load the HDD-backed server directory selected during setup.
. "$REPO_DIR/scripts/lib.sh"
load_env_file "$REPO_DIR/.env"
SERVER_DIR="${MC_SERVER_DIR:-$REPO_DIR/server}"
MC_VERSION="${MC_VERSION:-}"
API="https://fill.papermc.io/v3/projects/paper"
USER_AGENT="raspi-mc-server/installer (github.com/pachir1su/raspi-mc-server)"
TEMP_JAR=""

# Keep the previous paper.jar unless a verified replacement is ready.
cleanup_temp_jar() {
  if [ -n "$TEMP_JAR" ] && [ -f "$TEMP_JAR" ]; then
    rm -f -- "$TEMP_JAR"
  fi
}
trap cleanup_temp_jar EXIT

# Fetch one Fill API resource with the required project identification.
api_get() {
  curl -fsSL -H "User-Agent: $USER_AGENT" "$1"
}

# Return the newest STABLE build object for one Minecraft version.
stable_build_for_version() {
  local version="$1" buildsJson stableBuild
  buildsJson="$(api_get "$API/versions/$version/builds")" || return 1
  stableBuild="$(
    jq -c '[.[] | select(.channel == "STABLE")] | sort_by(.id) | last // empty' \
      <<<"$buildsJson"
  )" || return 1
  [ -n "$stableBuild" ] || return 1
  printf '%s\n' "$stableBuild"
}

# Extract a modern Java major version from `java -version` output.
java_major_version() {
  local versionLine rawVersion
  versionLine="$(java -version 2>&1 | head -n1)"
  rawVersion="$(sed -n 's/.*version "\([0-9][0-9.]*\)".*/\1/p' <<<"$versionLine")"
  if [[ "$rawVersion" == 1.* ]]; then
    cut -d. -f2 <<<"$rawVersion"
  else
    cut -d. -f1 <<<"$rawVersion"
  fi
}

# Point operators to Paper's supported Java installation path.
print_java_install_help() {
  local requiredJava="$1"
  echo "   Paper Java guide: https://docs.papermc.io/misc/java-install/" >&2
  echo "   After adding its Corretto apt repository, install with:" >&2
  echo "   sudo apt-get install -y java-$requiredJava-amazon-corretto-jdk libxi6 libxtst6 libxrender1" >&2
}

if ! command -v jq >/dev/null 2>&1; then
  echo "!! jq is required to read the Paper Fill API." >&2
  echo "   Install it with: sudo apt install jq" >&2
  exit 1
fi

echo "==> raspi-mc-server installer"
echo "    server dir : $SERVER_DIR"

# --- 1. Paper version and STABLE build ----------------------------------
BUILD_JSON=""
if [ -n "$MC_VERSION" ]; then
  echo "==> Resolving the newest STABLE Paper build for $MC_VERSION..."
  if ! BUILD_JSON="$(stable_build_for_version "$MC_VERSION")"; then
    echo "!! Could not find a STABLE Paper build for $MC_VERSION." >&2
    exit 1
  fi
else
  echo "==> Resolving the newest Minecraft version with a STABLE Paper build..."
  if ! PROJECT_JSON="$(api_get "$API")"; then
    echo "!! Could not retrieve the Paper version list from Fill v3." >&2
    exit 1
  fi
  if ! VERSION_LIST="$(jq -er '.versions | to_entries | map(.value) | add | .[]' <<<"$PROJECT_JSON")"; then
    echo "!! Fill v3 returned no Paper versions." >&2
    exit 1
  fi
  while IFS= read -r candidateVersion; do
    if BUILD_JSON="$(stable_build_for_version "$candidateVersion")"; then
      MC_VERSION="$candidateVersion"
      break
    fi
  done < <(sort -Vr <<<"$VERSION_LIST")
  if [ -z "$MC_VERSION" ] || [ -z "$BUILD_JSON" ]; then
    echo "!! Could not find any STABLE Paper build in Fill v3." >&2
    exit 1
  fi
fi

if ! BUILD_ID="$(jq -er '.id' <<<"$BUILD_JSON")" ||
   ! DOWNLOAD_NAME="$(jq -er '.downloads["server:default"].name' <<<"$BUILD_JSON")" ||
   ! DOWNLOAD_URL="$(jq -er '.downloads["server:default"].url' <<<"$BUILD_JSON")" ||
   ! EXPECTED_SHA256="$(jq -er '.downloads["server:default"].checksums.sha256' <<<"$BUILD_JSON")"; then
  echo "!! Fill v3 returned an incomplete STABLE build response for $MC_VERSION." >&2
  exit 1
fi
echo "    mc version : $MC_VERSION"
echo "    Paper build: $BUILD_ID (STABLE)"

# --- 2. Java requirement ------------------------------------------------
REQUIRED_JAVA=""
if VERSION_JSON="$(api_get "$API/versions/$MC_VERSION" 2>/dev/null)" &&
   REQUIRED_JAVA="$(jq -er '.version.java.version.minimum' <<<"$VERSION_JSON" 2>/dev/null)"; then
  echo "    minimum Java: $REQUIRED_JAVA"
else
  REQUIRED_JAVA=""
  echo "!! Warning: could not read the minimum Java version; continuing." >&2
fi

if ! command -v java >/dev/null 2>&1; then
  if [ -n "$REQUIRED_JAVA" ] && [ "$REQUIRED_JAVA" -gt 21 ]; then
    echo "!! Paper $MC_VERSION requires Java $REQUIRED_JAVA, but Java is not installed." >&2
    print_java_install_help "$REQUIRED_JAVA"
    exit 1
  fi
  echo "==> Installing OpenJDK 21 (headless)..."
  sudo apt-get update
  sudo apt-get install -y openjdk-21-jre-headless
fi

CURRENT_JAVA="$(java_major_version)"
if ! [[ "$CURRENT_JAVA" =~ ^[0-9]+$ ]]; then
  echo "!! Could not determine the installed Java major version." >&2
  exit 1
fi
echo "==> Java present: $(java -version 2>&1 | head -n1)"
if [ -n "$REQUIRED_JAVA" ] && [ "$CURRENT_JAVA" -lt "$REQUIRED_JAVA" ]; then
  echo "!! Paper $MC_VERSION requires Java $REQUIRED_JAVA; Java $CURRENT_JAVA is active." >&2
  print_java_install_help "$REQUIRED_JAVA"
  exit 1
fi

# --- 3. Verified PaperMC jar --------------------------------------------
mkdir -p "$SERVER_DIR"
TEMP_JAR="$(mktemp "$SERVER_DIR/.paper.jar.XXXXXX")"
echo "==> Downloading $DOWNLOAD_NAME ..."
if ! curl -fL -H "User-Agent: $USER_AGENT" -o "$TEMP_JAR" "$DOWNLOAD_URL"; then
  echo "!! Paper download failed; existing paper.jar was not changed." >&2
  exit 1
fi
ACTUAL_SHA256="$(sha256sum "$TEMP_JAR" | awk '{print $1}')"
if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
  echo "!! Paper SHA-256 mismatch; existing paper.jar was not changed." >&2
  echo "   expected: $EXPECTED_SHA256" >&2
  echo "   actual:   $ACTUAL_SHA256" >&2
  exit 1
fi
mv -f -- "$TEMP_JAR" "$SERVER_DIR/paper.jar"
TEMP_JAR=""
echo "    verified SHA-256 and saved to $SERVER_DIR/paper.jar"

# --- 4. Config seeding ---------------------------------------------------
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
