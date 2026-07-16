#!/usr/bin/env bash
# install_plugin.sh — 서드파티 Paper 플러그인 JAR을 안전하게 서버에 설치합니다.
#
# 이 저장소에 번들된 RaspiMcOps/DeathBox와 달리, Lootin·JustLootIt·AuraSkills·
# Chunky 같은 외부 플러그인은 각자 배포처(Modrinth/Hangar 등)에서 받아야 합니다.
# 다운로드 URL은 버전마다 바뀌므로 저장소에 박아두지 않고 인자로 받습니다.
#
# 수행 작업:
#   1. 주어진 URL에서 JAR을 임시 파일로 내려받습니다(원자적 교체 전까지 기존 파일 보존).
#   2. (선택) --sha256으로 체크섬을 검증합니다.
#   3. 유효한 ZIP이며 plugin.yml 또는 paper-plugin.yml을 포함하는지 확인합니다.
#   4. 검증을 통과하면 서버의 plugins/ 폴더로 원자적으로 이동합니다.
#
# 재실행하면 같은 파일명을 덮어씁니다(플러그인 업데이트에 안전).
#
# 사용법:
#   ./scripts/install_plugin.sh <다운로드-URL> [설치-파일명.jar]
#   ./scripts/install_plugin.sh <URL> Lootin.jar --sha256 <해시>
#
# 설치 후에는 서버를 재시작해야 플러그인이 로드됩니다.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$REPO_DIR/scripts/lib.sh"
load_env_file "$REPO_DIR/.env"
SERVER_DIR="${MC_SERVER_DIR:-$REPO_DIR/server}"
PLUGINS_DIR="$SERVER_DIR/plugins"
USER_AGENT="raspi-mc-server/plugin-installer (github.com/pachir1su/raspi-mc-server)"

URL=""
TARGET_NAME=""
EXPECTED_SHA=""
TEMP_JAR=""

usage() {
  echo "사용법: $0 <다운로드-URL> [파일명.jar] [--sha256 <해시>]" >&2
  exit 2
}

cleanup_temp_jar() {
  [ -n "$TEMP_JAR" ] && [ -f "$TEMP_JAR" ] && rm -f "$TEMP_JAR"
  return 0
}
trap cleanup_temp_jar EXIT

# 인자 파싱: 첫 위치 인자는 URL, 두 번째(선택)는 파일명, --sha256은 어디든.
while [ "$#" -gt 0 ]; do
  case "$1" in
    --sha256)
      shift
      [ "$#" -gt 0 ] || usage
      EXPECTED_SHA="$1"
      ;;
    -h|--help)
      usage
      ;;
    -*)
      echo "!! 알 수 없는 옵션: $1" >&2
      usage
      ;;
    *)
      if [ -z "$URL" ]; then
        URL="$1"
      elif [ -z "$TARGET_NAME" ]; then
        TARGET_NAME="$1"
      else
        echo "!! 인자가 너무 많습니다: $1" >&2
        usage
      fi
      ;;
  esac
  shift
done

[ -n "$URL" ] || usage

# URL은 http(s)만 허용합니다(로컬 file:// 등 예기치 않은 스킴 차단).
case "$URL" in
  http://*|https://*) : ;;
  *) echo "!! http:// 또는 https:// URL만 지원합니다." >&2; exit 1 ;;
esac

# 파일명이 없으면 URL 마지막 경로 조각에서 유추합니다.
if [ -z "$TARGET_NAME" ]; then
  TARGET_NAME="${URL##*/}"
  TARGET_NAME="${TARGET_NAME%%\?*}"   # 쿼리스트링 제거
fi
# 파일명은 안전한 문자만, 반드시 .jar로 끝나야 합니다.
case "$TARGET_NAME" in
  */*|"") echo "!! 잘못된 파일명입니다: $TARGET_NAME" >&2; exit 1 ;;
esac
if [ "${TARGET_NAME%.jar}" = "$TARGET_NAME" ]; then
  TARGET_NAME="$TARGET_NAME.jar"
fi

mkdir -p "$PLUGINS_DIR"
TEMP_JAR="$(mktemp "$PLUGINS_DIR/.${TARGET_NAME}.XXXXXX")"

echo ">> 다운로드: $URL"
curl -fsSL --proto '=https' --tlsv1.2 -A "$USER_AGENT" -o "$TEMP_JAR" "$URL" \
  || { echo "!! 다운로드 실패: $URL" >&2; exit 1; }

if [ -n "$EXPECTED_SHA" ]; then
  echo ">> SHA-256 검증"
  actual="$(sha256sum "$TEMP_JAR" | awk '{print $1}')"
  if [ "$actual" != "$EXPECTED_SHA" ]; then
    echo "!! 체크섬 불일치." >&2
    echo "   기대: $EXPECTED_SHA" >&2
    echo "   실제: $actual" >&2
    exit 1
  fi
fi

# 유효한 JAR(ZIP)이며 플러그인 매니페스트를 담고 있는지 확인합니다.
echo ">> JAR 구조 검증"
if ! unzip -l "$TEMP_JAR" >/dev/null 2>&1; then
  echo "!! 유효한 JAR(ZIP)이 아닙니다. HTML 오류 페이지를 받았을 수 있습니다." >&2
  exit 1
fi
if ! unzip -l "$TEMP_JAR" 2>/dev/null | grep -Eq '(^|/)(plugin|paper-plugin)\.yml$'; then
  echo "!! plugin.yml 또는 paper-plugin.yml이 없습니다 — Paper 플러그인이 아닙니다." >&2
  exit 1
fi

# 원자적 교체(기존 플러그인 업데이트에도 안전).
mv -f "$TEMP_JAR" "$PLUGINS_DIR/$TARGET_NAME"
TEMP_JAR=""
echo "✓ 설치 완료: $PLUGINS_DIR/$TARGET_NAME"
echo "  서버를 재시작하면 플러그인이 로드됩니다."
