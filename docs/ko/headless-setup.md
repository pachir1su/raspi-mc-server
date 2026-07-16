# 모니터 없이 처음부터 설치: SD카드 → Minecraft 접속

이 문서는 Raspberry Pi 4B(4GB)를 **모니터·키보드·마우스 없이** 운영하는 전체
절차입니다. Windows PC에서 32GB microSD를 만들고, SSH로 Pi를 설정하고, 500GB USB
HDD에 Paper 월드를 설치한 뒤 Java·모바일 Bedrock 친구가 접속하는 데까지 이어집니다.

명령 블록 위의 실행 위치를 꼭 확인하세요.

- **Windows PowerShell**: 내 Windows PC에서 실행
- **Pi SSH**: `ssh`로 Raspberry Pi에 접속한 뒤 실행
- `/dev/sda`와 `/dev/sda1`은 예시입니다. HDD 장치명은 반드시 직접 확인합니다.

공식 기준은 [Raspberry Pi 시작 안내](https://www.raspberrypi.com/documentation/computers/getting-started.html)와
[Raspberry Pi Imager](https://www.raspberrypi.com/software/)입니다.

## 1. 준비물과 권장 연결

- Raspberry Pi 4B 4GB와 방열판·팬이 있는 케이스
- 품질 좋은 5V/3A USB-C 전원 어댑터
- 32GB 이상 microSD와 Windows용 SD카드 리더
- 500GB USB 3.0 HDD
- 가능하면 **별도 전원형 HDD 케이스/허브**
- 공유기와 Ethernet 케이블 권장
- 같은 공유기에 연결된 Windows PC

Paper 월드·백업·업로드 사진은 HDD의 `/mnt/minecraft`에 두고, Raspberry Pi OS와
저장소·봇 프로그램만 microSD에 둡니다. HDD가 Pi USB 전력을 많이 가져가면 저전압과
디스크 끊김이 생길 수 있으므로 별도 전원형 구성이 가장 안전합니다.

## 2. Windows에서 microSD 만들기

1. [공식 Raspberry Pi Imager](https://www.raspberrypi.com/software/)를 설치합니다.
2. **HDD는 PC에서 분리하고 microSD만** 카드 리더에 꽂습니다.
3. Imager에서 다음을 선택합니다.
   - 장치: `Raspberry Pi 4`
   - 운영체제: `Raspberry Pi OS (other)` → `Raspberry Pi OS Lite (64-bit, Debian 13 Trixie)`
   - 저장소: 준비한 microSD
4. **OS 사용자 지정**을 엽니다.

권장 사용자 지정 값:

| 항목 | 권장값 | 설명 |
|---|---|---|
| Hostname | `mc-pi` | 이후 `mc-pi.local`로 SSH 접속 |
| Username | `mcadmin` | `pi` 대신 직접 정한 소문자 사용자명 |
| Password | 강력하고 고유한 값 | Discord/RCON 비밀번호와 다르게 설정 |
| Time zone | `Asia/Seoul` | 로그와 예약 작업 시간 기준 |
| Wi-Fi country | `KR` | 무선 채널 규정 적용 |
| Wi-Fi | 집 SSID/비밀번호 | Ethernet을 써도 장애 대비용으로 설정 가능 |
| Remote Access | **Enable SSH** | 헤드리스 운영에 필수 |
| SSH authentication | 공개키 권장, 처음에는 비밀번호도 가능 | 아래에서 키 전환 가능 |
| Raspberry Pi Connect | 선택 | SSH만 쓸 경우 꺼도 됨 |

5. **쓰기**를 누르고 대상이 microSD인지 마지막으로 다시 확인합니다.
6. 쓰기와 검증이 끝나면 Imager를 종료하고 Windows에서 안전하게 꺼냅니다.

> microSD 쓰기는 선택한 저장소를 지웁니다. 용량과 드라이브 이름이 HDD가 아닌지
> 반드시 확인하세요. Raspberry Pi OS Bookworm 이후에는 예전
> `wpa_supplicant.conf` 복사 방식 대신 Imager의 Wi-Fi 메뉴를 사용합니다.

## 3. 디스플레이 없이 첫 부팅과 SSH 접속

1. Pi 전원이 빠진 상태에서 microSD를 넣습니다.
2. 가능하면 Ethernet 케이블을 공유기에 연결합니다.
3. 아직 HDD는 연결하지 않아도 됩니다.
4. 마지막으로 USB-C 전원을 연결하고 첫 부팅에 3~5분 기다립니다.

Windows PowerShell에서:

```powershell
ping mc-pi.local
ssh mcadmin@mc-pi.local
```

처음 접속할 때 호스트 지문 질문에는 호스트명이 맞는지 확인한 뒤 `yes`를 입력합니다.
`mc-pi.local`을 못 찾으면 공유기 관리 페이지의 연결 기기 목록에서 `mc-pi` 또는 새
Raspberry Pi의 IP를 찾아 다음처럼 접속합니다.

```powershell
ssh mcadmin@192.168.0.42
```

같은 호스트명으로 SD카드를 다시 만들었고 SSH 키 경고가 뜬다면, 새 SD카드임을 직접
확인한 뒤 Windows PowerShell에서 이전 기록만 제거합니다.

```powershell
ssh-keygen -R mc-pi.local
```

## 4. Raspberry Pi OS 첫 업데이트와 확인

이제부터 별도 표시가 없으면 **Pi SSH 안에서** 실행합니다.

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

SSH 연결이 끊기면 1~3분 기다린 뒤 Windows에서 다시 접속합니다.

```powershell
ssh mcadmin@mc-pi.local
```

Pi SSH에서 기본 상태를 확인합니다.

```bash
uname -m
cat /etc/os-release
hostname -I
timedatectl
free -h
df -h /
```

- `uname -m`은 64비트 OS에서 보통 `aarch64`입니다.
- 시간대가 다르면 `sudo raspi-config` → Localisation Options에서 수정합니다.
- 공유기에서 Pi IP에 **DHCP 예약**을 걸어 두면 포트포워딩과 SSH 주소가 안정적입니다.

## 5. SSH 키로 비밀번호 입력 줄이기

Imager에서 공개키 인증을 이미 설정했다면 건너뜁니다. 그렇지 않다면 Windows
PowerShell에서 키를 만들고 Pi에 등록합니다.

```powershell
ssh-keygen -t ed25519
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | ssh mcadmin@mc-pi.local "umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"
```

새 PowerShell 창에서 `ssh mcadmin@mc-pi.local`이 키로 접속되는지 확인합니다.
비밀번호 로그인을 끄려면 **기존 SSH 창을 닫지 않은 상태에서** Pi에 다음 파일을
만듭니다.

```bash
sudo nano /etc/ssh/sshd_config.d/99-headless.conf
```

```text
PasswordAuthentication no
PermitRootLogin no
```

```bash
sudo sshd -t
sudo systemctl reload ssh
```

새 창의 키 접속이 성공한 뒤에만 기존 창을 닫습니다.

## 6. 저장소 내려받기

Pi SSH에서:

```bash
sudo apt install -y git
cd ~
git clone https://github.com/pachir1su/raspi-mc-server.git
cd raspi-mc-server
git status --short --branch
```

저장소는 microSD의 홈 디렉터리에 두고 대용량 Minecraft 데이터만 HDD로 분리합니다.

## 7. 500GB HDD 준비

사용자가 잰 값이 `100 × 700 mm`가 아니라 약 `100 × 70 mm`라면 2.5인치 HDD일
가능성이 큽니다. 7과 10은 보통 인치가 아니라 두께 7mm와 9.5mm를 뜻합니다.
케이스 규격, 2.5/3.5인치 구별, 외부 전원 없이 사용할 때의 고장 증상은 먼저
[HDD 규격·케이스·전원](hdd-hardware.md)을 읽으세요.

### 7.1 전원을 끄고 HDD 연결

```bash
sudo poweroff
```

SSH가 끊기고 Pi 활동 LED가 멈춘 뒤 전원을 분리합니다. HDD를 USB 3.0 파란색 포트에
연결하고, 별도 전원형 케이스라면 HDD 전원을 먼저 켠 뒤 Pi 전원을 연결합니다. 다시
SSH로 접속합니다.

### 7.2 정확한 장치 확인

```bash
lsblk -o NAME,SIZE,FSTYPE,LABEL,MODEL,SERIAL,MOUNTPOINTS
sudo wipefs -n /dev/sda
```

500GB 제품은 Linux에서 약 465GiB로 보일 수 있습니다. microSD는 보통 `mmcblk0`,
USB HDD는 흔히 `sda`지만 절대 이름만 믿지 말고 **크기·MODEL·SERIAL**을 함께
확인합니다.

기존 데이터가 필요한 HDD라면 여기서 멈추고 먼저 다른 장치에 백업합니다. 아래
파티션 생성과 포맷은 선택한 HDD 데이터를 모두 삭제합니다.

### 7.3 새 빈 HDD만 파티션·포맷

아래 예시는 확인된 HDD가 `/dev/sda`, 파티션이 `/dev/sda1`일 때만 사용합니다.

```bash
sudo apt install -y parted
sudo parted /dev/sda --script mklabel gpt
sudo parted /dev/sda --script mkpart primary ext4 0% 100%
sudo partprobe /dev/sda
lsblk -f /dev/sda
sudo mkfs.ext4 -L minecraft-data /dev/sda1
```

### 7.4 UUID 자동 마운트 등록

저장소 스크립트는 포맷하지 않습니다. ext4 파티션의 UUID를 `/etc/fstab`에 등록하고
`/mnt/minecraft` 데이터 디렉터리를 만듭니다.

```bash
cd ~/raspi-mc-server
sudo ./scripts/setup_hdd.sh /dev/sda1
findmnt /mnt/minecraft
df -h /mnt/minecraft
ls -ld /mnt/minecraft /mnt/minecraft/live
```

재부팅 후에도 마운트되는지 반드시 확인합니다.

```bash
sudo reboot
```

재접속 후:

```bash
findmnt /mnt/minecraft
touch /mnt/minecraft/.write-test
rm /mnt/minecraft/.write-test
```

`findmnt`가 실패하면 서버 설치를 진행하지 마세요. 마운트되지 않은
`/mnt/minecraft`에 파일을 만들면 microSD에 데이터가 잘못 쌓일 수 있습니다.

## 8. Paper와 Discord 봇 프로비저닝

```bash
cd ~/raspi-mc-server
./deploy/setup_raspberrypi.sh
```

이 스크립트는 기본 Java 21 패키지, Python 가상환경, Paper, systemd 서비스,
Minecraft 서비스만 제어할 수 있는 좁은 sudoers 규칙을 설치합니다. 현재 Paper
26.1에는 Java 25가 필요하므로 [설치 문서](setup.md#paper-261용-java-25)에 따라 먼저
설치하세요. 스크립트는 여러 번 실행해도 되도록 설계되어 있습니다.

## 9. RCON과 Discord 비밀값 설정

RCON 비밀번호 후보를 만들 수 있습니다.

```bash
openssl rand -hex 32
```

출력은 비밀 저장소에 보관하고 채팅·GitHub에 붙이지 않습니다. Paper 설정을 엽니다.

```bash
nano /mnt/minecraft/live/server.properties
```

다음을 확인합니다.

```properties
enable-rcon=true
rcon.port=25575
rcon.password=<방금 만든 비밀번호>
white-list=true
enforce-whitelist=true
```

저장소의 `.env`를 엽니다.

```bash
cd ~/raspi-mc-server
nano .env
chmod 600 .env
```

최소한 다음 값을 실제 값으로 바꿉니다.

```dotenv
DISCORD_TOKEN=<Discord Developer Portal 봇 토큰>
DISCORD_GUILD_ID=<내 Discord 서버 ID>
ADMIN_USER_IDS=<내 Discord 사용자 ID>
RCON_PASSWORD=<server.properties와 완전히 같은 비밀번호>
MC_STORAGE_ROOT=/mnt/minecraft
MC_SERVER_DIR=/mnt/minecraft/live
MC_REQUIRE_STORAGE_MOUNT=true
MC_STATE_DIR=/mnt/minecraft/bot-state
MC_PUBLIC_ADDRESS=<친구에게 줄 주소 또는 공인 IP>
MC_PUBLIC_VERSION="Paper Java 26.1.x + Bedrock"
```

`ADMIN_USER_IDS`에는 우선 서버장 본인만 넣습니다. Discord 토큰 발급과 ID 복사는
[discord-bot.md](discord-bot.md)를 참고합니다. `.env`, RCON 비밀번호, 실제 토큰은
커밋하지 않습니다. 예전 `BOT_LANGUAGE` 값은 무시되며 언어는 최초 실행 메뉴에서
선택합니다.

`.env`는 셸에서도 읽으므로 공백이 들어간 값은 위 예시처럼 큰따옴표로 감쌉니다.
따옴표 없이 `MC_PUBLIC_VERSION=Paper Java ...`처럼 쓰면 프로비저닝이나 RCON 명령에서
`.env`를 불러올 때 실패합니다.

## 10. `main.py` 하나로 최초 실행

```bash
cd ~/raspi-mc-server
sudo systemctl enable minecraft.service mc-discord-bot.service
.venv/bin/python -m bot.main
```

최초 메뉴 권장 선택:

```text
1. 한국어
2. Java + 모바일/Windows 베드락 (권장)
Bedrock UDP port [19132]: Enter
```

이 실행 하나가 필요한 Geyser·Floodgate 플러그인을 검증·설정하고 Paper와 Discord
봇을 시작합니다. `logged in as ...`가 표시될 때까지 기다립니다. Java 전용 서버라면
메뉴에서 Java만 선택합니다.

Paper가 뜬 뒤 서버장 Minecraft 계정만 op로 지정합니다. 새 Pi SSH 창에서:

```bash
cd ~/raspi-mc-server
set -a
. ./.env
set +a
.venv/bin/python -m bot.rcon "op 내_Java_닉네임"
```

Bedrock 계정이 아니라 **서버장이 관리에 사용할 Java 계정만** op로 두는 것을
권장합니다. 친구 계정은 Discord 관리자 패널에서 등록하며 op를 주지 않습니다.

## 11. 포그라운드 실행을 systemd로 넘기기

최초 설정과 Discord 로그인을 확인한 뒤 `Ctrl+C`로 `main.py`를 종료합니다. Paper는
계속 실행됩니다. 이제 봇 서비스를 시작합니다.

```bash
sudo systemctl start mc-discord-bot.service
systemctl is-enabled minecraft.service mc-discord-bot.service
systemctl is-active minecraft.service mc-discord-bot.service
sudo journalctl -u mc-discord-bot.service -n 100 --no-pager
```

마지막으로 재부팅 자동 복구를 시험합니다.

```bash
sudo reboot
```

2~5분 뒤 SSH로 재접속해:

```bash
cd ~/raspi-mc-server
./scripts/health_check.sh
```

HDD 마운트, 두 서비스, Paper TPS/RCON이 정상이어야 합니다.

## 12. 공유기와 외부 접속

공유기에서 Pi에 DHCP 예약을 건 뒤 다음 포트만 Pi 내부 IP로 전달합니다.

| 용도 | 외부/내부 포트 | 프로토콜 |
|---|---:|---|
| Java Edition | 25565 | TCP |
| iPhone·Android·Minecraft for Windows | 19132 | UDP |

다음 포트는 외부에 열지 않습니다.

- RCON `25575`
- SSH `22` — 외부 SSH가 필요하면 VPN을 권장

일반 Cloudflare HTTP Tunnel은 Minecraft TCP/Bedrock UDP를 그대로 처리하지 않습니다.
공유기 포트포워딩이 불가능한 CGNAT 환경이면 Tailscale 같은 VPN이나 게임 트래픽을
지원하는 별도 터널을 검토합니다. 자세한 내용은 [remote-access.md](remote-access.md)를
참고합니다.

외부 접속 시험은 같은 Wi-Fi가 아니라 휴대전화 모바일 데이터나 다른 네트워크에서
해야 합니다.

## 13. 친구가 실제로 할 일

### Java PC

1. Minecraft Java Edition → 멀티플레이 → 서버 추가
2. 서버장이 준 주소 입력(기본 포트 `25565`)
3. 한 번 저장하고 이후 저장된 서버를 클릭

### iPhone·Android·Minecraft for Windows

1. 플레이 → 서버 → 서버 추가
2. 같은 서버 주소와 포트 `19132` 입력
3. Microsoft/Xbox 계정으로 접속
4. 이후 저장된 서버를 탭

친구 기기에 Geyser, Floodgate, 모드, 별도 런처를 설치하지 않습니다.

Discord에서 서버장은 `/관리자`의 **친구 계정**에서 Discord 사용자를 고르고 정확한
Java 닉네임 또는 Xbox 게이머태그를 등록합니다. 같은 친구가 PC와 모바일/콘솔에서
여러 계정을 쓰면 추가 버튼을 반복합니다. 친구의 요청이나 승인 대기 절차는 없습니다.

등록 시 적절한 Java/Floodgate 화이트리스트에도 자동 추가합니다. 친구는 `/도구`에서
자기 계정 하나를 고른 뒤 **선택 계정 스폰 귀환**, **선택 계정 위치**를 쓸 수 있습니다.

Floodgate 공식 안내상 `fwhitelist`는 해당 Xbox 계정이 이전에 어떤 Geyser 서버에든
접속한 기록이 있어야 이름을 바로 찾을 수 있습니다. 완전히 새 계정의 등록이 실패하면
[friend-tools.md](friend-tools.md)의 첫 Bedrock 접속 문제 해결 절차를 따르며,
화이트리스트를 계속 꺼 둔 채 운영하지 않습니다.

## 14. 디스플레이 없는 일상 운영

평소에는 Discord `/관리자`를 쓰고, 봇이 안 될 때 Windows에서 SSH로 접속합니다.

```powershell
ssh mcadmin@mc-pi.local
```

Pi SSH의 기본 점검:

```bash
cd ~/raspi-mc-server
./scripts/health_check.sh
sudo journalctl -u minecraft.service -n 100 --no-pager
sudo journalctl -u mc-discord-bot.service -n 100 --no-pager
```

물리적으로 전원을 빼야 할 때는 먼저:

```bash
sudo systemctl stop mc-discord-bot.service
sudo systemctl stop minecraft.service
sudo poweroff
```

SSH가 끊기고 활동 LED가 멈춘 뒤 전원을 분리합니다. 실행 중 전원을 뽑으면 월드와
microSD가 손상될 수 있습니다.

## 15. 안전한 업데이트

### Discord에서 Release 자동 업데이트(권장)

이 기능을 처음 설치하는 한 번은 아래 수동 절차로 최신 코드를 받고 프로비저닝을
다시 실행해야 합니다. 이후 GitHub에서 새 Release를 발행하면 Release 워크플로가
`raspi-mc-server-vX.Y.Z.zip`과 SHA-256 파일을 자동 첨부합니다.

관리자가 `/관리자` → **업데이트** → **새 버전 확인**을 실행하고 **업데이트 설치**
버튼을 누릅니다. Pi가 GitHub Release 파일을 직접 내려받아 manifest와 모든 파일의
SHA-256을 검증합니다. 봇만 잠깐 재시작하고 Paper/월드는 계속 실행됩니다.

Release ZIP을 PC에 이미 받았다면 `/업로드 업데이트 파일:<ZIP>`도 사용할 수 있습니다.
반드시 Release에 자동 첨부된 배포 ZIP을 쓰세요. GitHub의 `Source code (zip)`이나
임의로 다시 압축한 ZIP에는 검증 manifest가 없어 거부됩니다. Discord 서버의 첨부
한도를 넘으면 **새 버전 확인** 방식을 사용합니다.

설치 과정은 `.env`, `/mnt/minecraft/live`, 봇 상태(연동·좌표·일지), 사진, 로그를
교체하지 않습니다. 새 Python 환경을 먼저 만들고 봇 시작 확인에 실패하면 코드와
환경을 자동 복구합니다. 결과는 재시작 후 업데이트 패널의 **최근 결과**로 확인합니다.

### 최초 1회 또는 봇이 작동하지 않을 때

```bash
cd ~/raspi-mc-server
git status --short
git fetch origin
git switch main
git pull --ff-only
.venv/bin/pip install -r requirements.txt
sudo ./deploy/setup_raspberrypi.sh
sudo systemctl restart mc-discord-bot.service
./scripts/health_check.sh
```

`git status`에 예상하지 않은 변경이 보이면 덮어쓰지 말고 먼저 별도로 백업합니다.
프로그램 업데이트는 Minecraft 데이터에 손대지 않으므로 정상 업데이트 때
`minecraft.service`를 재시작하지 않아 렉과 접속 끊김을 줄입니다.

## 16. 화면 없이 장애 찾기

### `mc-pi.local`이 안 됨

1. 첫 부팅이면 5분 기다립니다.
2. PC와 Pi가 같은 일반 LAN인지 확인합니다(게스트 Wi-Fi 기기 격리 주의).
3. 공유기 연결 기기 목록에서 IP를 찾고 `ssh mcadmin@<IP>`를 시도합니다.
4. Ethernet 케이블과 전원 LED를 확인합니다.

### SSH는 되는데 서버가 안 됨

```bash
findmnt /mnt/minecraft
systemctl status minecraft.service mc-discord-bot.service --no-pager
sudo journalctl -u minecraft.service -n 200 --no-pager
sudo journalctl -u mc-discord-bot.service -n 200 --no-pager
```

HDD가 마운트되지 않았다면 서비스를 억지로 시작하지 말고 USB 전원·케이블·UUID부터
확인합니다.

### 저전압·발열 확인

```bash
vcgencmd get_throttled
vcgencmd measure_temp
```

현재 저전압이면 전원 어댑터와 HDD 전원을 먼저 해결합니다. 자세한 판독은
[operator-runbook.md](operator-runbook.md)를 참고합니다.

### SD카드가 손상되어 다시 설치해야 함

1. 이 문서 2절부터 새 SD카드를 만듭니다.
2. 같은 저장소를 다시 clone합니다.
3. 기존 HDD는 **포맷하지 않고** ext4 파티션을 `setup_hdd.sh`로 다시 등록합니다.
4. 별도 보관한 `.env`와 `server.properties` 비밀값을 복원합니다.
5. `setup_raspberrypi.sh`를 다시 실행합니다.

같은 HDD 안의 백업만으로는 HDD 자체 고장에 대비할 수 없습니다. 중요한 월드 백업과
비밀값은 PC나 다른 저장장치에도 보관합니다.

## 17. 최종 완료 체크리스트

- [ ] Imager에서 Raspberry Pi OS Lite(64-bit, Debian 13 Trixie), 사용자, Wi-Fi, SSH를 설정함
- [ ] `ssh mcadmin@mc-pi.local` 접속 성공
- [ ] OS 업데이트와 재부팅 후 다시 SSH 접속 성공
- [ ] HDD 장치를 크기·MODEL·SERIAL로 확인하고 ext4로 준비함
- [ ] 재부팅 뒤에도 `findmnt /mnt/minecraft` 성공
- [ ] `.env`와 `server.properties`의 RCON 비밀번호가 일치함
- [ ] `python -m bot.main` 최초 메뉴 완료
- [ ] 서버장 계정만 op로 지정함
- [ ] 두 systemd 서비스가 enabled/active 상태임
- [ ] `health_check.sh`가 HDD·RCON·TPS를 정상 표시함
- [ ] 공유기에 `25565/TCP`, 필요 시 `19132/UDP`만 포워딩함
- [ ] Java와 Bedrock 실제 외부 접속 확인
- [ ] Discord `/관리자` 친구 계정 등록과 `/도구` 계정 선택·스폰 귀환 확인
- [ ] 최근 월드 백업을 Pi/HDD 밖에도 한 개 이상 보관함
