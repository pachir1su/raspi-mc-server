# 문제 해결

디스플레이 없는 Pi라면 먼저
[headless-setup.md](headless-setup.md)의 화면 없는 접속·복구 순서를 확인합니다.

## 먼저 로그

```bash
sudo journalctl -u minecraft.service -n 100 --no-pager       # 서버
sudo journalctl -u mc-discord-bot.service -n 100 --no-pager  # 봇
tail -n 100 /mnt/minecraft/live/logs/latest.log              # 마인크래프트 자체 로그
```

디스코드에서는 `/관리자` → **로그**가 봇의 현재 로그를 미리 보거나 첨부합니다.

## 서버가 안 켜져요

| 증상 | 원인 | 해결 |
|---|---|---|
| `Unsupported class file major version` / 자바 오류 | Paper 요구 버전보다 낮은 Java | `./deploy/setup_raspberrypi.sh`를 다시 실행해 Amazon Corretto Java 25를 설치·검증하세요. Paper 26.1+는 Java 25가 필요하며 [설치 문서](setup.md#paper-261용-java-25)를 참고하세요. |
| `Failed to bind to port` | 25565 사용 중 | 다른 서버 실행 중? `sudo ss -tlnp | grep 25565` |
| 즉시 종료, EULA 메시지 | EULA 미동의 | `/mnt/minecraft/live/eula.txt`에 `eula=true`인지 확인(설치 스크립트가 처리) |
| `Could not find a STABLE Paper build` | 잘못된 `MC_VERSION` 또는 experimental 빌드만 존재 | STABLE 빌드가 있는 버전(예: `MC_VERSION=26.1.2`)을 쓰거나 `MC_VERSION`을 비워 두세요. |
| v0.1.8 이하 설치 스크립트가 Paper를 다운로드하지 못함 | 폐기된 `api.papermc.io/v2` 사용 | 저장소를 최신화하고 Fill v3 설치 스크립트를 사용하세요. |
| 메모리 부족/강제 종료 | 4GB엔 힙 과대 | `.env`에서 `MC_MEMORY` 낮추기(예: `2600M`) |

## 플레이어가 접속을 못 해요

1. **Minecraft 계정이 등록됐나요?** 서버장이 `/관리자` → **친구 계정**에서 Discord 사용자를 고르고 정확한 Java 또는 Bedrock 계정을 추가.
2. **접속 포트가 맞나요?** Java는 `25565/TCP`, 아이폰·Android·Minecraft for
   Windows는 Geyser `19132/UDP` 사용.
3. **버전·계정이 맞나요?** Java는 Paper 지원 프로토콜과 맞아야 하고 Bedrock은
   Microsoft/Xbox 계정으로 로그인해야 함.
4. **LAN 밖인가요?** 올바른 TCP/UDP 게임 포트를 포워딩하거나 적절한 VPN/터널 사용 —
   [remote-access.md](remote-access.md).
5. **방화벽?** ufw 사용 시 `25565/tcp`, Bedrock은 `19132/udp`도 허용.
6. **완전히 새 Bedrock 계정?** [friend-tools.md](friend-tools.md)의 최초 접속 절차 확인.

## 디스코드 봇 문제

| 증상 | 원인 | 해결 |
|---|---|---|
| 명령이 안 보임 | 전역 동기화 지연 | `DISCORD_GUILD_ID` 설정으로 즉시 길드 동기화 |
| 시작 시 `Missing required config` | `.env` 불완전 | `DISCORD_TOKEN`, `RCON_PASSWORD`, `ADMIN_USER_IDS` 설정 |
| `⛔ not authorised` | 내 ID가 허용목록에 없음 | 내 디스코드 유저 ID를 `ADMIN_USER_IDS`에 추가 |
| **고급 RCON**이 RCON 오류 | RCON 꺼짐/불일치 | `enable-rcon=true`; `RCON_PASSWORD`가 `server.properties`와 일치 |
| 서버 제어 버튼 실패 | sudoers 규칙 없음 | `deploy/setup_raspberrypi.sh` 재실행 |
| 봇이 `The "no new privileges" flag is set`로 crash loop | 옛 유닛의 `NoNewPrivileges=true`가 `sudo`(setuid)를 차단 | `deploy/mc-discord-bot.service`를 다시 설치하세요(이제 `NoNewPrivileges`를 두지 않고 `ProtectSystem`/`ProtectHome`/`ReadWritePaths`로 하드닝). [discord-bot.md](discord-bot.md#보안-하드닝과-sudo) 참고. |
| 설치 직후 봇이 10초마다 재시작 | first setup 미완료 | 터미널에서 `.venv/bin/python -m bot.main`을 한 번 실행하세요. 이제 서비스가 `EX_CONFIG`(78)로 종료하고 `RestartPreventExitStatus=78`이 재시작을 멈춥니다. |
| 부팅 시 `raspi-mc-updater.service`가 `failed` | 대기 중인 업데이트 요청 없음 | 이 수정 이전의 증상입니다. 저장소를 최신화하면 "요청 없음"을 성공(exit 0)으로 처리합니다. |
| first setup이 `data/` 쓰기 중 `PermissionError` | root 업데이터가 `data/`를 먼저 생성 | 수정됨: 업데이터가 `data/`를 서비스 계정으로 `chown`하고 `setup_raspberrypi.sh`도 `chown -R`을 실행합니다. 수동: `sudo chown -R <user>:<user> data/`. |

## RCON 연결 거부

- `server.properties`에 `enable-rcon=true`이고 서버 재시작됨.
- `rcon.password`(서버) == `RCON_PASSWORD`(.env).
- `RCON_HOST=127.0.0.1`, `RCON_PORT`가 `rcon.port`(25575)와 일치.
- 서버가 완전히 시작됨(RCON은 `Done` 이후 열림).

이제 봇은 RCON 실패를 항상 "오프라인"으로 뭉뚱그리지 않고 구분합니다:

- **🔴 Server offline** — TCP 연결이 거부됨(서버 정지/기동 중).
- **🟠 RCON 인증 실패** — 포트는 응답하지만 비밀번호가 틀림. `RCON_PASSWORD`(.env)와
  `rcon.password`(server.properties)를 일치시키세요.
- **🟠 서버 응답 지연** — 연결은 됐지만 제한 시간(`RCON_TIMEOUT`, 기본 10초) 안에
  응답이 없음. 대개 기동 중이거나 과부하.

원인은 `mc.rcon` 로거에 기록됩니다. 외부 `mcrcon` 바이너리(데비안 저장소에 없음)
없이도 RCON을 테스트할 수 있습니다:

```bash
.venv/bin/python -m bot.rcon "list"
```

## 라즈베리파이 OS / 하드웨어 함정

### Trixie: Imager 설정(SSH·사용자)이 적용되지 않음

최신 Raspberry Pi OS(Trixie)에서는 `cloud-init` 기반 첫 부팅이 Raspberry Pi
Imager에서 지정한 커스터마이즈(SSH 활성화, 사용자명, Wi‑Fi)를 무시할 수 있어,
화면 없는 Pi에 접속하지 못하는 경우가 있습니다.

- **권장:** 이 프로젝트에서는 **Raspberry Pi OS Bookworm(Legacy, 64-bit)**을
  구우세요. 테스트된 기준이며 Imager 설정이 안정적으로 적용됩니다.
- **꼭 Trixie를 써야 한다면:** 구운 뒤 boot 파티션을 마운트해 cloud-init을 손봅니다.
  - boot 파티션에 `ssh`(또는 `ssh.txt`) 파일을 만들어 SSH를 강제로 켭니다.
  - boot 파티션의 `user-data`(cloud-init)에서 사용자, `ssh_pwauth`, `chpasswd`를
    설정하고 재부팅합니다. 콘솔 접근이 되면 기기에서
    `sudo cloud-init status --long`으로 확인합니다.

### Pi 4B USB 3.0 + SATA SSD 어댑터: xHCI 컨트롤러 다운

일부 USB 3.0 ↔ SATA 어댑터(특정 JMicron/ASMedia 브리지 등)는 부하가 걸리면 Pi 4B의
xHCI USB 컨트롤러를 죽입니다. `dmesg`/저널 증상:

```
xhci_hcd ... WARNING: Host System Error
xhci_hcd ... HC died; cleaning up
```

드라이브가 사라지고 `/mnt/minecraft`의 월드 저장소가 읽기 전용이 되거나 없어집니다.
우회 방법:

- **SSD를 USB 2.0 포트로 옮기기.** 느리지만 컨트롤러가 죽지 않아 대부분 해결됩니다.
- **전원 공급형 USB 허브 사용.** 어댑터가 5V를 끌어내려 브라운아웃일 수 있습니다.
  전압 부족은 `/관리자` → **성능**의 스로틀 플래그에도 나타납니다.
- **usb-storage quirk로 UAS 비활성화.** `lsusb`로 `idVendor:idProduct`를 찾아
  `/boot/firmware/cmdline.txt`(한 줄)에 `usb-storage.quirks=VVVV:PPPP:u`를 추가하고
  재부팅합니다. 느리지만 훨씬 안정적인 BOT 전송으로 강제합니다.

## 렉 / 낮은 TPS

[performance.md](performance.md) 참고. 빠른 개선: `simulation-distance` 낮추기,
월드를 USB 3.0 HDD/SSD로 옮기고 파이가 열 스로틀링 아닌지 확인(`vcgencmd measure_temp`).

## "No space left on device"

- 먼저 `findmnt /mnt/minecraft`로 HDD가 마운트됐는지 확인하고 무작정 삭제하지 않기.
- `/관리자` → **백업** → **정책 설정**으로 보관 기간을 줄이고 **정리**를 누른 뒤 오래된 백업·불필요한 복구 아카이브를
  정리하거나 백업을 기기 밖으로 이동.
- `/mnt/minecraft/live/logs/`와 봇 로그를 확인하고 활성 파일을 직접 지우기보다 설정된
  보관 정책 사용.
