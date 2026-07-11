# 디스코드 관리 봇

**나**(그리고 허용된 관리자)만 서버를 원격 관리할 수 있게 하는 작은 봇입니다:
RCON으로 임의 명령 실행, 화이트리스트 관리, 서비스 시작/정지/재시작, 월드 백업,
로그 가져오기 — 전부 디스코드에서.

## 왜 봇인가

- SSH 없이 폰에서도 서버 관리.
- `/mc` 명령이 **원격 치트 콘솔**(op 레벨 4로 실행).
- 느린 작업(백업, 재시작)은 **로딩 애니메이션**으로 피드백을 주어 멈춘 것처럼
  보이지 않게 합니다.
- `/logs`가 현재 로그 파일을 첨부해 빠른 디버깅.

## 1. 디스코드 애플리케이션 만들기

1. [Discord Developer Portal](https://discord.com/developers/applications)
   → **New Application**.
2. **Bot** 탭 → **Add Bot** → **토큰** 복사(이게 `DISCORD_TOKEN`).
3. **Privileged Gateway Intents**는 전부 **꺼도** 됩니다 — 이 봇은 슬래시 명령과
   기본 인텐트만 씁니다.
4. **OAuth2 → URL Generator**: 스코프 `bot` + `applications.commands`, 봇 권한은
   `Send Messages`, `Embed Links`, `Attach Files`. 생성된 URL로 봇을 서버에 초대.

## 2. 필요한 ID 찾기

**개발자 모드**를 켠 뒤(디스코드 설정 → 고급), 우클릭:

- **내 유저** → *사용자 ID 복사* → `ADMIN_USER_IDS`(단독 운영자면 나만; 여러 명은
  쉼표 구분).
- **내 서버** → *서버 ID 복사* → `DISCORD_GUILD_ID`(선택; 전역 동기화를 기다리지
  않고 명령이 즉시 보임).

## 3. `.env` 설정

```dotenv
DISCORD_TOKEN=봇토큰
DISCORD_GUILD_ID=123456789012345678
ADMIN_USER_IDS=내유저ID
RCON_HOST=127.0.0.1
RCON_PORT=25575
RCON_PASSWORD=server.properties와-일치
MC_SERVICE_NAME=minecraft.service
```

## 4. 실행

```bash
sudo systemctl enable --now mc-discord-bot.service
sudo journalctl -u mc-discord-bot.service -f
```

테스트용 수동 실행:

```bash
.venv/bin/python -m bot.main
```

## 명령어

모든 명령은 **관리자 전용**(`ADMIN_USER_IDS` 확인)입니다.

| 명령 | 기능 |
|---|---|
| `/status` | 서버 가동 여부와 접속자(RCON `list`). |
| `/say <메시지>` | 채팅 브로드캐스트. |
| `/mc <명령>` | **RCON으로 임의 서버 명령 실행** — 치트 콘솔. |
| `/whitelist add <이름>` | 화이트리스트 추가. |
| `/whitelist remove <이름>` | 화이트리스트 제거. |
| `/start` | 마인크래프트 서비스 시작. |
| `/stop` | 저장 후 서비스 정지. |
| `/restart` | 서비스 재시작. |
| `/backup create/list/download/verify` | HDD 백업 생성·목록·다운로드·무결성 검사. |
| `/backup restore/delete` | 확인 문자열을 요구하는 복구·삭제. |
| `/backup settings/configure/enabled/prune` | 30분 주기와 보관·용량 정책 조회/변경/즉시 정리. |
| `/world upload/list/download` | 맵 압축 파일 검증·보관·다운로드. |
| `/world activate/delete` | 비상 백업 후 맵 전환 또는 보관 맵 삭제. |
| `/storage` | HDD 마운트와 사용량 확인. |
| `/health` | RCON·HDD·백업 최신성·스케줄러 종합 점검. |
| `/audit [개수]` | 최근 관리자 변경 작업 감사 기록. |
| `/logs` | 봇의 현재 로그 파일 첨부. |

`/start`, `/stop`, `/restart`, `/backup create`, 복구와 맵 전환은 실행 중 로딩 애니메이션을 보여주고
결과로 메시지를 갱신합니다.

전체 백업·복구 정책과 파일 안전 규칙은 [backup.md](backup.md)를 참고하세요.

## 보안 메모

- 봇은 내 마인크래프트 계정이 필요 없습니다 — 로컬 RCON으로만 서버와 통신합니다.
- `ADMIN_USER_IDS`는 최소로 유지하세요. 목록에 있으면 치트·서버 정지가 가능합니다.
- systemd 유닛은 **좁은 sudoers 규칙**(`deploy/` 참고)을 써서 봇이 마인크래프트
  서비스만 제어하고 임의 root 명령은 못 하게 합니다.
- RCON은 localhost에 두세요; 봇은 `127.0.0.1`로 접속합니다.

## 로딩 애니메이션 원리

디스코드는 명령이 `defer`하면 자체 "생각 중…" 문구를 강제하며 교체할 수 없습니다.
그래서 느린 작업에서는 봇이 **자체 임베드**를 먼저 보내고, 진행 바가 ~96%로
수렴(작업이 끝나 실제 결과가 대체하기 전까지 100%가 되지 않음)하도록 타이머로
편집합니다. 프레임 편집이 실패해도 무시합니다 — 애니메이션은 장식일 뿐 실제 작업을
막지 않습니다. `bot/loading.py` 참고.
