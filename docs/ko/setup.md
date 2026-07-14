# 설치 & 첫 실행

새 라즈베리파이 4B(4GB)에서 화이트리스트가 걸린 PaperMC 서버와 디스코드 관리 봇을
돌리는 데까지 안내합니다.

> **모니터와 키보드 없이 설치하나요?** 먼저
> [SD카드부터 시작하는 완전 헤드리스 설치 문서](headless-setup.md)를 따라가세요.
> Raspberry Pi Imager의 각 입력값, Windows 첫 SSH, HDD 장치 확인·포맷 안전장치,
> 공유기 포트, 재부팅 시험, 장애 복구까지 모두 들어 있습니다. 이 문서는 서버
> 소프트웨어 부분만 빠르게 다시 볼 때 사용합니다.

## 0. 준비물

- 라즈베리파이 4B(4GB), **Raspberry Pi OS Lite(64-bit, Debian 13 Trixie)**.
- 32GB microSD와 500GB 외장 HDD. 이 구성에서는 OS·봇은 microSD, PaperMC·월드·
  백업·업로드 맵은 HDD에 둡니다.
- 네트워크: 파이는 LAN에 연결. LAN 밖 친구가 들어오려면 포트포워딩이나 터널이
  필요합니다 — [remote-access.md](remote-access.md) 참고.
- 헤드리스 운영: 최초 부팅 전에 Raspberry Pi Imager에서 호스트명·사용자·네트워크·
  SSH를 설정합니다. Bookworm 이후 없어진 boot 파티션 `wpa_supplicant.conf` 방식에
  의존하지 않습니다.

먼저 OS를 업데이트하세요:

```bash
sudo apt update && sudo apt full-upgrade -y && sudo reboot
```

## 1. 클론 및 HDD 준비

```bash
git clone https://github.com/pachir1su/raspi-mc-server.git
cd raspi-mc-server
lsblk -f
```

`lsblk -f`로 **500GB HDD 파티션을 정확히 확인**한 뒤 처음 한 번만 ext4로
포맷하고 등록합니다. 아래 `/dev/sda1`은 예시이며 잘못 고르면 다른 디스크 데이터가
삭제됩니다.

```bash
sudo mkfs.ext4 /dev/sda1       # 해당 파티션의 기존 데이터가 모두 삭제됨
sudo ./scripts/setup_hdd.sh /dev/sda1
findmnt /mnt/minecraft
```

스크립트는 UUID를 `/etc/fstab`에 `nofail`로 등록하고 필요한 디렉터리를 만듭니다.
기존 데이터가 있는 HDD라면 포맷하지 말고 먼저 별도 백업·파티션 계획을 세우세요.

## 2. 프로비저닝

```bash
./deploy/setup_raspberrypi.sh
```

`setup_raspberrypi.sh`는 Java 21 설치, PaperMC 다운로드, 봇용 파이썬 venv 생성,
systemd 유닛 설치, 그리고 봇이 **마인크래프트 서비스만** 시작/정지할 수 있도록
**좁은 sudoers 규칙**을 추가합니다(전체 root 권한이 아닙니다).

> 봇/systemd 없이 서버만 설치하려면
> `MC_VERSION=1.21.4 ./scripts/install_server.sh` 를 실행하세요.

## 3. 비밀값 설정

비밀값이 담기고 **커밋되지 않는** 파일 두 개:

1. `/mnt/minecraft/live/server.properties` — 강력한 `rcon.password` 설정.
2. 추적되는 예시 `.env` — Pi에서 다음 값을 교체:
   - `RCON_PASSWORD` — `server.properties`와 **일치**해야 함.
   - `DISCORD_TOKEN` — 봇 토큰([discord-bot.md](discord-bot.md)).
   - `ADMIN_USER_IDS` — **본인 디스코드 유저 ID**(여러 명은 쉼표 구분).
   - `MC_MEMORY` — 4GB 파이는 `2600M` 그대로 두세요.

언어와 Java/Bedrock 모드는 더 이상 환경 변수로 정하지 않습니다. 최초 `main.py`
실행 메뉴에서 고르면 `MC_STATE_DIR/app-settings.json`에 저장됩니다. `.env`에 예전
`BOT_LANGUAGE` 줄이 있더라도 무시되며 Pi에서 지워도 됩니다.

```bash
nano /mnt/minecraft/live/server.properties   # rcon.password=...
nano .env                        # RCON_PASSWORD / DISCORD_TOKEN / ADMIN_USER_IDS
chmod 600 .env
```

## 4. 재부팅 자동 시작 등록 후 단일 실행기 실행

```bash
sudo systemctl enable minecraft.service mc-discord-bot.service
.venv/bin/python -m bot.main
```

최초 실행에서 한국어/English를 고르고 Java 전용 또는 Java+Bedrock을 고릅니다.
혼합 기기를 지원하려면 네트워크상 특별한 이유가 없는 한 베드락 UDP 포트 `19132`를
그대로 쓰세요. 이 명령 하나가 빠진 크로스플레이 플러그인 설치·설정, Paper 시작,
Discord 전체 기능 시작까지 처리합니다. 서버를 쓰는 동안 그대로 실행해 두면 됩니다.
이후 재부팅 때는 systemd가 저장된 선택으로 자동 실행합니다.

Ctrl+C로 포그라운드 실행을 끝냈다면 서비스를 시작합니다.

```bash
sudo systemctl start mc-discord-bot.service
sudo journalctl -u mc-discord-bot.service -f
```

Paper에 `Done (…)!`이 표시되면 로컬 RCON으로 **나만** op로 지정합니다.

```bash
mcrcon -H 127.0.0.1 -P 25575 -p '<내 RCON 비밀번호>' 'op 내마크닉네임'
```

이것이 나를 게임 내 유일한 치터로 만드는 핵심입니다.
[cheats-and-ops.md](cheats-and-ops.md) 참고.

## 5. 친구의 접속 요청 승인

```text
친구:   /연동 요청 마크닉:<닉네임> 에디션:<Java 또는 Bedrock>
서버장: /연동 승인 사용자:<Discord 멤버>
```

승인하면 Java 또는 Floodgate 화이트리스트에도 자동으로 추가됩니다. 친구에게 op를
주지 않으며, 친구의 구조 명령은 연동된 본인 계정에만 적용됩니다.

## 6. 나중에 설정 메뉴 다시 열기

```bash
.venv/bin/python -m bot.main --setup
```

systemd가 아니라 직접 터미널에서 실행하세요. 평소 `python -m bot.main`은 질문 없이
저장된 선택을 불러옵니다. `DISCORD_GUILD_ID`를 설정하면 슬래시 명령이 해당 서버에서
즉시 보이고, 아니면 전역 동기화에 최대 1시간 정도 걸립니다.

## 7. 접속

Java는 서버 주소의 `25565/TCP`로 접속합니다. 아이폰·아이패드, 안드로이드,
Minecraft for Windows는 같은 주소의 `19132/UDP`를 **플레이 → 서버 → 서버 추가**에
한 번 저장한 뒤 다음부터 탭해서 접속합니다. 친구 기기에는 모드나 플러그인이
필요 없습니다. [bedrock.md](bedrock.md), [remote-access.md](remote-access.md) 참고.

## 다음 단계

- [configuration.md](configuration.md) — `server.properties` 튜닝.
- [backup.md](backup.md) — 자동 백업 예약.
- [performance.md](performance.md) — 파이에서 TPS 유지.
- [troubleshooting.md](troubleshooting.md) — 문제 발생 시.
