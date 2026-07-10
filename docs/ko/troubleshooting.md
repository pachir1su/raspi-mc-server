# 문제 해결

## 먼저 로그

```bash
sudo journalctl -u minecraft.service -n 100 --no-pager       # 서버
sudo journalctl -u mc-discord-bot.service -n 100 --no-pager  # 봇
tail -n 100 server/logs/latest.log                           # 마인크래프트 자체 로그
```

디스코드에서는 `/logs`가 봇의 현재 로그 파일을 첨부합니다.

## 서버가 안 켜져요

| 증상 | 원인 | 해결 |
|---|---|---|
| `Unsupported class file major version` / 자바 오류 | 잘못된 자바 | JDK 21 설치: `sudo apt install openjdk-21-jre-headless` |
| `Failed to bind to port` | 25565 사용 중 | 다른 서버 실행 중? `sudo ss -tlnp | grep 25565` |
| 즉시 종료, EULA 메시지 | EULA 미동의 | `echo eula=true > server/eula.txt`(설치 스크립트가 처리) |
| `Could not find a Paper build` | 잘못된 `MC_VERSION` | 유효한 버전 사용, 예: `MC_VERSION=1.21.4` |
| 메모리 부족/강제 종료 | 4GB엔 힙 과대 | `.env`에서 `MC_MEMORY` 낮추기(예: `2600M`) |

## 플레이어가 접속을 못 해요

1. **화이트리스트 됐나요?** `whitelist add <이름>`(이름 대소문자 구분; 정확한
   계정명 사용).
2. **올바른 에디션/버전?** 서버 버전과 맞는 **자바 에디션** 필요.
3. **같은 LAN?** 파이의 LAN IP `:25565`로 접속. LAN 밖은 포트포워딩이나 VPN/터널
   필요 — [remote-access.md](remote-access.md).
4. **방화벽?** ufw가 켜져 있으면 `sudo ufw allow 25565/tcp`.

## 디스코드 봇 문제

| 증상 | 원인 | 해결 |
|---|---|---|
| 명령이 안 보임 | 전역 동기화 지연 | `DISCORD_GUILD_ID` 설정으로 즉시 길드 동기화 |
| 시작 시 `Missing required config` | `.env` 불완전 | `DISCORD_TOKEN`, `RCON_PASSWORD`, `ADMIN_USER_IDS` 설정 |
| `⛔ not authorised` | 내 ID가 허용목록에 없음 | 내 디스코드 유저 ID를 `ADMIN_USER_IDS`에 추가 |
| `/mc`가 RCON 오류 | RCON 꺼짐/불일치 | `enable-rcon=true`; `RCON_PASSWORD`가 `server.properties`와 일치 |
| `/start` 등 실패 | sudoers 규칙 없음 | `deploy/setup_raspberrypi.sh` 재실행 |

## RCON 연결 거부

- `server.properties`에 `enable-rcon=true`이고 서버 재시작됨.
- `rcon.password`(서버) == `RCON_PASSWORD`(.env).
- `RCON_HOST=127.0.0.1`, `RCON_PORT`가 `rcon.port`(25575)와 일치.
- 서버가 완전히 시작됨(RCON은 `Done` 이후 열림).

## 렉 / 낮은 TPS

[performance.md](performance.md) 참고. 빠른 개선: `simulation-distance` 낮추기,
월드를 USB 3.0 HDD/SSD로 옮기고 파이가 열 스로틀링 아닌지 확인(`vcgencmd measure_temp`).

## "No space left on device"

- `/backup configure`로 보관 기간을 줄이고 오래된 백업을 정리하거나,
  `server/logs/`·`bot/logs/` 정리(회전이 시간이 지나며 처리), 또는 백업을 기기
  밖으로 이동.
