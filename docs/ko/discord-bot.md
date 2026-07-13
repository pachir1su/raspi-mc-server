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
BOT_LANGUAGE=ko
PUBLIC_COMMANDS_ENABLED=true
MC_STATE_DIR=/mnt/minecraft/bot-state
MC_SPAWN_DIMENSION=overworld
MC_SPAWN_X=0.5
MC_SPAWN_Y=80
MC_SPAWN_Z=0.5
MC_MAP_URL_TEMPLATE=https://map.example.com/?world={dimension}&x={x}&y={y}&z={z}
MC_PUBLIC_ADDRESS=play.example.com
MC_PUBLIC_VERSION=Paper Java 1.21.x
MC_PUBLIC_RULES=건축물과 아이템을 존중하고 문제는 서버장에게 알려주세요.
STATUS_CHANNEL_ID=123456789012345678
ALERT_TPS_THRESHOLD=18.0
ALERT_MEMORY_PERCENT=85
ALERT_TEMPERATURE_CELSIUS=80
ALERT_MIN_FREE_GB=20
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

`/portal`, `/online`은 친구도 볼 수 있는 읽기 전용 명령입니다. 승인된 계정 연동은
범위가 좁은 `/rescue`, `/place`, `/diary`, `/server-score` 기능도 허용합니다. 일반
관리 명령은 모두 계속 **관리자 전용**(`ADMIN_USER_IDS` 확인)입니다.
`BOT_LANGUAGE=ko` 또는 `BOT_LANGUAGE=en`으로 새 봇 UX의 언어를 바꿀 수 있습니다.

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
| `/backup timeline/restore-preview` | 최근 백업 타임라인과 복구 전 검증 미리보기. |
| `/backup restore/delete` | 확인 문자열을 요구하는 복구·삭제. |
| `/backup settings/configure/enabled/prune` | 30분 주기와 보관·용량 정책 조회/변경/즉시 정리. |
| `/world upload/list/download` | 맵 압축 파일 검증·보관·다운로드. |
| `/world activate/delete` | 비상 백업 후 맵 전환 또는 보관 맵 삭제. |
| `/storage` | HDD 마운트와 사용량 확인. |
| `/health` | RCON·HDD·백업 최신성·스케줄러 종합 점검. |
| `/audit [개수]` | 최근 관리자 변경 작업 감사 기록. |
| `/panel` | 버튼 중심 통합 관리 패널. |
| `/players` | 접속자를 선택해 인벤토리·위치·체력·효과 조회. |
| `/metrics` | Pi 온도·부하·메모리·HDD·TPS·스로틀 상태. |
| `/tuning-report` | 현재 성능 위험과 Pi 친화 튜닝 조언. |
| `/incident day/clear-weather/peaceful/clear-drops` | 낮·날씨·평화 난이도·드롭템 정리 사고 대응. `clear-drops`는 모든 드롭 아이템을 지우므로 `CLEAR` 확인이 필요합니다. |
| `/portal`, `/online` | 친구용 서버 정보와 접속자 보기. |
| `/link request/status` | Discord ↔ 마인크래프트 연결 요청과 내 상태 확인. |
| `/link approve/revoke/list` | 관리자 전용 연결 승인·해제·목록. |
| `/rescue spawn/whereami` | 승인된 본인 계정만 고정 스폰으로 이동하거나 그 계정 위치 조회. |
| `/place add/list/show/delete` | 로컬 사진과 선택적 외부 지도 링크가 있는 공유 좌표북. |
| `/diary add/recent/show` | 사진을 넣을 수 있는 용량 제한 서버 일지. |
| `/server-score` | Paper와 Pi 지표 기반 요청 시점 0~100점. |
| `/logs` | 봇·마인크래프트 로그 버튼 패널. |

`/start`, `/stop`, `/restart`, `/backup create`, 복구와 맵 전환은 실행 중 로딩 애니메이션을 보여주고
결과로 메시지를 갱신합니다.

전체 백업·복구 정책과 파일 안전 규칙은 [backup.md](backup.md)를 참고하세요.
정확한 Pi 설정, 승인 순서, 런타임 파일, 명령 예시, 문제 해결은
[friend-tools.md](friend-tools.md)를 참고하세요.

## 버튼형 관리 패널

`/panel`만 입력하면 다음 작업은 텍스트 인자 없이 버튼으로 실행할 수 있습니다.

- 서버·접속자·HDD·최근 백업 상태 새로고침
- 즉시 안전 백업
- 서버 시작, 확인 후 정지·재시작
- 자동 백업 켜기/끄기
- 저장공간과 상태 진단
- CPU 온도, 메모리, TPS, 저전압·스로틀링 성능 카드와 튜닝 리포트
- 낮/날씨/평화 난이도/드롭템 정리 사고 대응 버튼. 드롭템 정리는 친구 아이템 삭제 위험 때문에 한 번 더 확인합니다.
- 플레이어 선택 메뉴
- 봇·마인크래프트 로그 패널

패널은 실행한 관리자에게만 보이며 10분 뒤 만료됩니다. 버튼 콜백 오류도 조용히
멈추지 않고 화면에 원인을 표시합니다.

## 플레이어 조회

`/players` 또는 패널의 **플레이어** 버튼을 누르면 현재 접속자 이름이 드롭다운으로
표시됩니다. 선택 후 다음 버튼을 사용할 수 있습니다.

- **인벤토리** — 핫바, 일반 슬롯, 방어구, 보조 손 아이템과 개수
- **위치** — 좌표와 차원
- **체력·경험치** — 체력, 허기, 경험치 레벨, 게임 모드
- **효과** — 현재 상태 효과 원본 데이터

조회 대상 이름은 실제 `list` 출력에서 만들고 Java 사용자 이름 형식을 다시
검사하므로 임의 RCON 명령으로 변형되지 않습니다.

## 로그 패널

`/logs`는 파일을 즉시 올리는 대신 버튼 패널을 엽니다. 봇 로그와 Paper
`latest.log`의 최근 부분만 효율적으로 읽으며 다음을 지원합니다.

- 봇 로그 또는 마인크래프트 로그 미리보기
- 봇/마인크래프트 경고·오류만 필터링
- Discord 서버의 실제 파일 한도 안에서 원본 첨부
- 너무 큰 파일은 SSH/SFTP 경로 안내

관리 작업 감사 로그는 5MiB에서 한 번 회전해 microSD에서 무한히 커지지 않습니다.

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

## 자동 성능 알림과 언어

`STATUS_CHANNEL_ID`를 설정하면 봇이 5분마다 TPS, 메모리, CPU 온도, 전원/스로틀, HDD 여유 공간을 확인하고 임계값을 넘은 새 경고만 쿨다운(`ALERT_COOLDOWN_MINUTES`)을 두고 게시합니다. `BOT_LANGUAGE=ko` 또는 `BOT_LANGUAGE=en`은 새 포털·알림·리포트·사고 대응 메시지의 기본 언어를 바꿉니다. 기존 운영 명령 중 일부 고정 문구는 점진적으로 같은 i18n 헬퍼로 옮길 수 있습니다.
