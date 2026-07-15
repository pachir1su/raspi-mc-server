#!/usr/bin/env bash
# setup_raspberrypi.sh — 새 64비트 Raspberry Pi OS를 한 번에 구성합니다.
#
# 시스템 패키지, Minecraft 서버, Discord 봇용 Python 가상 환경, systemd 유닛과
# 봇이 Minecraft 서비스만 시작·중지할 수 있는 제한된 sudoers 규칙을 설치합니다.
#
# Pi의 저장소 루트에서 실행합니다.
#   ./deploy/setup_raspberrypi.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_USER="${SERVICE_USER:-$(id -un)}"

echo "==> Provisioning raspi-mc-server for user '$SERVICE_USER'"

# java -version 출력에서 주 버전을 추출합니다.
java_major_version() {
  local versionLine rawVersion
  command -v java >/dev/null 2>&1 || return 1
  versionLine="$(java -version 2>&1 | head -n1)"
  rawVersion="$(sed -n 's/.*version "\([0-9][0-9.]*\)".*/\1/p' <<<"$versionLine")"
  [ -n "$rawVersion" ] || return 1
  if [[ "$rawVersion" == 1.* ]]; then
    cut -d. -f2 <<<"$rawVersion"
  else
    cut -d. -f1 <<<"$rawVersion"
  fi
}

# Corretto 공개키와 apt 저장소를 재실행에 안전하게 등록합니다.
register_corretto_repository() {
  local keyringTemp
  keyringTemp="$(mktemp)"
  if ! wget -qO- https://apt.corretto.aws/corretto.key | gpg --dearmor >"$keyringTemp"; then
    rm -f -- "$keyringTemp"
    echo "!! Amazon Corretto 공개키를 가져오지 못했습니다." >&2
    return 1
  fi
  sudo install -m 0644 "$keyringTemp" /usr/share/keyrings/corretto-keyring.gpg
  rm -f -- "$keyringTemp"
  printf '%s\n' \
    'deb [signed-by=/usr/share/keyrings/corretto-keyring.gpg] https://apt.corretto.aws stable main' | \
    sudo tee /etc/apt/sources.list.d/corretto.list >/dev/null
}

# --- 시스템 패키지 -------------------------------------------------------
echo "==> Installing system packages..."
sudo apt-get update
# 참고: mcrcon는 Debian(Bookworm) 저장소에 없어 apt로 설치할 수 없습니다(이슈 J).
# RCON 한 줄 실행은 내장 클라이언트(.venv/bin/python -m bot.rcon "...")로 대체합니다.
sudo apt-get install -y \
  python3 python3-venv python3-pip \
  ca-certificates apt-transport-https gnupg wget \
  curl jq tar zip

# Java 25 이상이 없을 때만 Amazon Corretto 25를 설치합니다.
JAVA_MAJOR="$(java_major_version 2>/dev/null || true)"
if [[ "$JAVA_MAJOR" =~ ^[0-9]+$ ]] && [ "$JAVA_MAJOR" -ge 25 ]; then
  echo "==> Java $JAVA_MAJOR already satisfies the Java 25 requirement."
else
  echo "==> Installing Amazon Corretto 25..."
  register_corretto_repository
  sudo apt-get update
  sudo apt-get install -y \
    java-25-amazon-corretto-jdk \
    libxi6 libxtst6 libxrender1
fi

# 설치 또는 기존 Java가 실제로 요구 버전을 충족하는지 확인합니다.
JAVA_MAJOR="$(java_major_version 2>/dev/null || true)"
if ! [[ "$JAVA_MAJOR" =~ ^[0-9]+$ ]] || [ "$JAVA_MAJOR" -lt 25 ]; then
  echo "!! Java 25 이상을 사용할 수 없습니다. Corretto 설치 상태와 기본 java 대상을 확인하세요." >&2
  echo "   확인 명령: java -version" >&2
  exit 1
fi
echo "==> Java verified: $(java -version 2>&1 | head -n1)"

# --- 봇용 Python 가상 환경 ----------------------------------------------
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
# 설치 대상을 검사하기 전에 운영자가 선택한 경로를 불러옵니다.
set -a
. "$REPO_DIR/.env"
set +a

# --- 외장 HDD ------------------------------------------------------------
if ! mountpoint -q /mnt/minecraft; then
  echo "!! /mnt/minecraft is not mounted. Prepare the HDD first:" >&2
  echo "     sudo mkfs.ext4 /dev/sdXN       # DESTRUCTIVE: choose the correct partition" >&2
  echo "     sudo $REPO_DIR/scripts/setup_hdd.sh /dev/sdXN" >&2
  exit 1
fi

# --- Minecraft 서버 ------------------------------------------------------
if [ ! -f "${MC_SERVER_DIR:-/mnt/minecraft/live}/paper.jar" ]; then
  echo "==> Installing PaperMC on the HDD..."
  "$REPO_DIR/scripts/install_server.sh"
fi

# 업데이터 경로를 한 번만 계산하고 상대 상태 경로는 저장소를 기준으로 고정합니다.
STORAGE_ROOT="${MC_STORAGE_ROOT:-/mnt/minecraft}"
STATE_DIR="${MC_STATE_DIR:-data}"
if [[ "$STATE_DIR" != /* ]]; then
  STATE_DIR="$REPO_DIR/$STATE_DIR"
fi

# --- sudoers: 봇이 지정된 Minecraft/업데이터 서비스만 제어하게 합니다. ---
SUDOERS="/etc/sudoers.d/raspi-mc-server"
echo "==> Installing narrow sudoers rule at $SUDOERS"
sudo tee "$SUDOERS" >/dev/null <<EOF
# $SERVICE_USER가 비밀번호 없이 지정된 서비스만 관리하도록 허용합니다.
$SERVICE_USER ALL=(root) NOPASSWD: /bin/systemctl start minecraft.service, /bin/systemctl stop minecraft.service, /bin/systemctl restart minecraft.service, /bin/systemctl is-active minecraft.service
$SERVICE_USER ALL=(root) NOPASSWD: /bin/systemctl start --no-block raspi-mc-updater.service, /bin/systemctl is-active raspi-mc-updater.service
EOF
sudo chmod 440 "$SUDOERS"

# --- systemd 유닛 --------------------------------------------------------
echo "==> Installing systemd units..."
# 유닛 템플릿의 @USER@/@REPO_DIR@ 자리표시자를 실제 값으로 치환해 설치합니다(이슈 F).
install_unit() {
  sed -e "s|@USER@|$SERVICE_USER|g" -e "s|@REPO_DIR@|$REPO_DIR|g" "$1" | \
    sudo tee "$2" >/dev/null
}
install_unit "$REPO_DIR/deploy/minecraft.service" /etc/systemd/system/minecraft.service
install_unit "$REPO_DIR/deploy/mc-discord-bot.service" /etc/systemd/system/mc-discord-bot.service

# 봇이 수정하지 못하도록 권한 상승 도우미를 root 소유로 설치합니다.
sudo install -d -m 755 /usr/local/lib/raspi-mc-server
sudo install -o root -g root -m 755 \
  "$REPO_DIR/deploy/apply_update.py" \
  /usr/local/lib/raspi-mc-server/apply_update.py
sed -e "s|@REPO_DIR@|$REPO_DIR|g" \
    -e "s|@STATE_DIR@|$STATE_DIR|g" \
    -e "s|@STORAGE_ROOT@|$STORAGE_ROOT|g" \
    "$REPO_DIR/deploy/raspi-mc-updater.service" | \
    sudo tee /etc/systemd/system/raspi-mc-updater.service >/dev/null
sudo systemctl daemon-reload

# 봇 상태 디렉터리(data/)를 서비스 계정 소유로 보정합니다. root로 도는 업데이터가
# 먼저 만들어 소유권이 어긋난 경우 봇 first-setup의 PermissionError를 막습니다(이슈 E).
mkdir -p "$STATE_DIR"
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$STATE_DIR"

cat <<EOF

==> Provisioning done. Remaining manual steps:
  1. Edit ${MC_SERVER_DIR:-/mnt/minecraft/live}/server.properties -> set a strong rcon.password
  2. Edit $REPO_DIR/.env                       -> DISCORD_TOKEN, ADMIN_USER_IDS,
                                                  RCON_PASSWORD (match server.properties)
  3. Enable reboot start: sudo systemctl enable minecraft.service mc-discord-bot.service
  4. Run everything:     $REPO_DIR/.venv/bin/python -m bot.main
     The first run asks for language and Java-only or Java+Bedrock mode.
  5. Op yourself once:   $REPO_DIR/.venv/bin/python -m bot.rcon 'op <YourName>'
     (RCON_HOST/RCON_PORT/RCON_PASSWORD는 .env에서 읽습니다. 별도 mcrcon 불필요.)

See docs/en/setup.md (English) or docs/ko/setup.md (한국어) for details.
EOF
