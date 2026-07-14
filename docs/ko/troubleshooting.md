# 문제 해결

디스플레이 없는 Pi라면 먼저
[headless-setup.md](headless-setup.md)의 화면 없는 접속·복구 순서를 확인합니다.

## 먼저 로그

```bash
sudo journalctl -u minecraft.service -n 100 --no-pager       # 서버
sudo journalctl -u mc-discord-bot.service -n 100 --no-pager  # 봇
tail -n 100 /mnt/minecraft/live/logs/latest.log              # 마인크래프트 자체 로그
```

디스코드에서는 `/로그`가 봇의 현재 로그 파일을 첨부합니다.

## 서버가 안 켜져요

| 증상 | 원인 | 해결 |
|---|---|---|
| `Unsupported class file major version` / 자바 오류 | 잘못된 자바 | JDK 21 설치: `sudo apt install openjdk-21-jre-headless` |
| `Failed to bind to port` | 25565 사용 중 | 다른 서버 실행 중? `sudo ss -tlnp | grep 25565` |
| 즉시 종료, EULA 메시지 | EULA 미동의 | `/mnt/minecraft/live/eula.txt`에 `eula=true`인지 확인(설치 스크립트가 처리) |
| `Could not find a Paper build` | 잘못된 `MC_VERSION` | 유효한 버전 사용, 예: `MC_VERSION=1.21.4` |
| 메모리 부족/강제 종료 | 4GB엔 힙 과대 | `.env`에서 `MC_MEMORY` 낮추기(예: `2600M`) |

## 플레이어가 접속을 못 해요

1. **Discord 연동이 승인됐나요?** 서버장이 `/연동 목록` 후 `/연동 승인` 실행.
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
| `/마크명령`이 RCON 오류 | RCON 꺼짐/불일치 | `enable-rcon=true`; `RCON_PASSWORD`가 `server.properties`와 일치 |
| `/시작` 등 실패 | sudoers 규칙 없음 | `deploy/setup_raspberrypi.sh` 재실행 |

## RCON 연결 거부

- `server.properties`에 `enable-rcon=true`이고 서버 재시작됨.
- `rcon.password`(서버) == `RCON_PASSWORD`(.env).
- `RCON_HOST=127.0.0.1`, `RCON_PORT`가 `rcon.port`(25575)와 일치.
- 서버가 완전히 시작됨(RCON은 `Done` 이후 열림).

## 렉 / 낮은 TPS

[performance.md](performance.md) 참고. 빠른 개선: `simulation-distance` 낮추기,
월드를 USB 3.0 HDD/SSD로 옮기고 파이가 열 스로틀링 아닌지 확인(`vcgencmd measure_temp`).

## "No space left on device"

- 먼저 `findmnt /mnt/minecraft`로 HDD가 마운트됐는지 확인하고 무작정 삭제하지 않기.
- `/백업 구성`으로 보관 기간을 줄이고 오래된 백업·불필요한 복구 아카이브를
  정리하거나 백업을 기기 밖으로 이동.
- `/mnt/minecraft/live/logs/`와 봇 로그를 확인하고 활성 파일을 직접 지우기보다 설정된
  보관 정책 사용.
