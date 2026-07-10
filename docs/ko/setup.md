# 설치 & 첫 실행

새 라즈베리파이 4B(4GB)에서 화이트리스트가 걸린 PaperMC 서버와 디스코드 관리 봇을
돌리는 데까지 안내합니다.

## 0. 준비물

- 라즈베리파이 4B(4GB), **64비트 라즈베리파이 OS**(Bookworm 권장).
- 32GB 이상 SD카드. **USB 3.0 SSD**를 강력 권장합니다 — 월드는 I/O 부하가 크고,
  잦은 쓰기가 SD카드 수명을 갉아먹습니다.
- 네트워크: 파이는 LAN에 연결. LAN 밖 친구가 들어오려면 포트포워딩이나 터널이
  필요합니다 — [remote-access.md](remote-access.md) 참고.

먼저 OS를 업데이트하세요:

```bash
sudo apt update && sudo apt full-upgrade -y && sudo reboot
```

## 1. 클론 & 프로비저닝

```bash
git clone https://github.com/pachir1su/raspi-mc-server.git
cd raspi-mc-server
./deploy/setup_raspberrypi.sh
```

`setup_raspberrypi.sh`는 Java 21 설치, PaperMC 다운로드, 봇용 파이썬 venv 생성,
systemd 유닛 설치, 그리고 봇이 **마인크래프트 서비스만** 시작/정지할 수 있도록
**좁은 sudoers 규칙**을 추가합니다(전체 root 권한이 아닙니다).

> 봇/systemd 없이 서버만 설치하려면
> `MC_VERSION=1.21.4 ./scripts/install_server.sh` 를 실행하세요.

## 2. 비밀값 설정

비밀값이 담기고 **커밋되지 않는** 파일 두 개:

1. `server/server.properties` — 강력한 `rcon.password` 설정.
2. `.env`(`.env.example`에서 생성) — 다음을 설정:
   - `RCON_PASSWORD` — `server.properties`와 **일치**해야 함.
   - `DISCORD_TOKEN` — 봇 토큰([discord-bot.md](discord-bot.md)).
   - `ADMIN_USER_IDS` — **본인 디스코드 유저 ID**(여러 명은 쉼표 구분).
   - `MC_MEMORY` — 4GB 파이는 `2600M` 그대로 두세요.

```bash
nano server/server.properties   # rcon.password=...
nano .env                        # RCON_PASSWORD / DISCORD_TOKEN / ADMIN_USER_IDS
chmod 600 .env
```

## 3. 첫 시작 & 나 op 지정

```bash
sudo systemctl enable --now minecraft.service
sudo journalctl -u minecraft.service -f   # 부팅 확인; Ctrl+C 로 로그 보기 종료
```

`Done (…)! For help, type "help"` 가 보이면 **나만** op로 지정합니다. 콘솔에서
(또는 봇이 뜬 뒤 디스코드 `/mc` 명령으로):

```
op 내마크닉네임
```

이것이 나를 게임 내 유일한 치터로 만드는 핵심입니다.
[cheats-and-ops.md](cheats-and-ops.md) 참고.

## 4. 친구 화이트리스트

```
whitelist add 친구1
whitelist add 친구2
```

템플릿에서 화이트리스트는 이미 **켜져** 있어, 등록된 사람만 들어올 수 있습니다.

## 5. 디스코드 봇 시작

```bash
sudo systemctl enable --now mc-discord-bot.service
sudo journalctl -u mc-discord-bot.service -f
```

봇이 슬래시 명령을 등록합니다. `DISCORD_GUILD_ID`를 설정하면 해당 서버에서 즉시
보이고, 아니면 전역 동기화에 최대 1시간 정도 걸립니다.

## 6. 접속

플레이어는 **자바 에디션**으로 파이의 LAN IP(예: `192.168.0.42`) 기본 포트
`25565`에 접속합니다. 네트워크 밖 친구는 [remote-access.md](remote-access.md)를
설정하세요.

## 다음 단계

- [configuration.md](configuration.md) — `server.properties` 튜닝.
- [backup.md](backup.md) — 자동 백업 예약.
- [performance.md](performance.md) — 파이에서 TPS 유지.
- [troubleshooting.md](troubleshooting.md) — 문제 발생 시.
