#!/usr/bin/env bash
# install_server.sh — Raspberry Pi 4B(64비트)에 PaperMC 서버를 설치합니다.
#
# 수행 작업:
#   1. Fill v3에서 최신 STABLE PaperMC 릴리스를 선택합니다.
#   2. 선택한 릴리스의 최소 Java 버전을 확인합니다.
#   3. PaperMC 서버 jar를 다운로드하고 검증합니다.
#   4. server.properties를 템플릿에서 만들고 EULA에 동의합니다.
#   5. 소유자 전용 치트를 위해 ops/whitelist 설정은 운영자에게 맡깁니다.
#
# 재실행하면 jar를 다시 내려받되 없는 설정 파일만 생성합니다.
#
# 사용법:
#   ./scripts/install_server.sh                         # 최신 STABLE 버전
#   MC_VERSION=26.1.2 ./scripts/install_server.sh       # 지정한 STABLE 버전
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# HDD 기반 서버 경로 설정을 불러옵니다.
. "$REPO_DIR/scripts/lib.sh"
load_env_file "$REPO_DIR/.env"
SERVER_DIR="${MC_SERVER_DIR:-$REPO_DIR/server}"
MC_VERSION="${MC_VERSION:-}"
API="https://fill.papermc.io/v3/projects/paper"
USER_AGENT="raspi-mc-server/installer (github.com/pachir1su/raspi-mc-server)"
TEMP_JAR=""

# 검증된 교체 파일이 준비되지 않으면 기존 paper.jar를 보존합니다.
cleanup_temp_jar() {
  if [ -n "$TEMP_JAR" ] && [ -f "$TEMP_JAR" ]; then
    rm -f -- "$TEMP_JAR"
  fi
}
trap cleanup_temp_jar EXIT

# 프로젝트 식별 헤더를 포함해 Fill API 리소스 하나를 가져옵니다.
api_get() {
  curl -fsSL -H "User-Agent: $USER_AGENT" "$1"
}

# Minecraft 버전 하나에서 가장 최신 STABLE 빌드 객체를 반환합니다.
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

# java -version 출력에서 주 버전을 추출합니다.
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

if ! command -v jq >/dev/null 2>&1; then
  echo "!! jq is required to read the Paper Fill API." >&2
  echo "   Install it with: sudo apt install jq" >&2
  exit 1
fi

echo "==> raspi-mc-server installer"
echo "    server dir : $SERVER_DIR"

# --- Paper 버전과 STABLE 빌드 -------------------------------------------
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

# --- Java 요구 버전 ------------------------------------------------------
REQUIRED_JAVA=""
if VERSION_JSON="$(api_get "$API/versions/$MC_VERSION" 2>/dev/null)" &&
   REQUIRED_JAVA="$(jq -er '.version.java.version.minimum' <<<"$VERSION_JSON" 2>/dev/null)"; then
  echo "    minimum Java: $REQUIRED_JAVA"
else
  REQUIRED_JAVA=""
  echo "!! Warning: could not read the minimum Java version; continuing." >&2
fi

if ! command -v java >/dev/null 2>&1; then
  echo "!! Java가 설치되어 있지 않습니다." >&2
  if [ -n "$REQUIRED_JAVA" ]; then
    echo "   Paper $MC_VERSION의 최소 요구 버전은 Java $REQUIRED_JAVA입니다." >&2
  fi
  echo "   저장소 루트에서 ./deploy/setup_raspberrypi.sh를 다시 실행해 Corretto 25를 설치하세요." >&2
  exit 1
fi

CURRENT_JAVA="$(java_major_version)"
if ! [[ "$CURRENT_JAVA" =~ ^[0-9]+$ ]]; then
  echo "!! Could not determine the installed Java major version." >&2
  exit 1
fi
echo "==> Java present: $(java -version 2>&1 | head -n1)"
if [ -n "$REQUIRED_JAVA" ] && [ "$CURRENT_JAVA" -lt "$REQUIRED_JAVA" ]; then
  echo "!! Paper $MC_VERSION requires Java $REQUIRED_JAVA; Java $CURRENT_JAVA is active." >&2
  echo "   저장소 루트에서 ./deploy/setup_raspberrypi.sh를 다시 실행해 Corretto 25를 설치하세요." >&2
  echo "   Java 25보다 높은 버전이 필요하면 요구 버전에 맞는 JDK를 직접 설치하세요." >&2
  exit 1
fi

# --- 검증된 PaperMC jar --------------------------------------------------
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

# --- 설정 파일 생성 ------------------------------------------------------
if [ ! -f "$SERVER_DIR/server.properties" ]; then
  cp "$REPO_DIR/server/server.properties.template" "$SERVER_DIR/server.properties"
  echo "==> Seeded server.properties from template."
  echo "    !! Edit rcon.password in $SERVER_DIR/server.properties before starting."
fi

# 서버 실행은 Mojang EULA 동의를 전제로 합니다.
echo "eula=true" > "$SERVER_DIR/eula.txt"

echo
echo "==> Done. Next steps:"
echo "  1. Set a strong rcon.password in $SERVER_DIR/server.properties"
echo "  2. Start once to generate the world, then stop:"
echo "       ./scripts/start_server.sh   (Ctrl+C to stop the first run)"
echo "  3. Op ONLY yourself:  op <YourName>   (in the console)"
echo "  4. Whitelist friends: whitelist add <name>"
echo "  5. Install the systemd services in deploy/ for auto-start."
