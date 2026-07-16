# raspi-mc-server (한국어)

**라즈베리파이 4B(4GB)**에서 돌리는 **친구용 마인크래프트 Java + 선택형 Bedrock
크로스플레이 서버**입니다.
**3~4명** 규모, **소유자만 치트 사용**, 그리고 **디스코드·SSH·웹으로 원격 관리**를
목표로 합니다.

> 🇬🇧 English: **[README.md](README.md)**

---

## 무엇이 들어 있나

- **PaperMC** 서버 — Pi 4B(4GB)·32GB microSD + 500GB USB HDD에 맞춘 튜닝
  (Aikar GC 플래그, 파이 친화적인 렌더/시뮬레이션 거리).
- **화이트리스트 전용, 모드 없음** — 나와 친구 몇 명만 들어오는 작은 사설 월드.
- **Java와 Bedrock이 Paper 월드 하나에서 함께 접속** — 선택형 Geyser + Floodgate로
  자바 PC, 아이폰·아이패드, 안드로이드, Minecraft for Windows가 같이 플레이합니다.
  친구는 모드 없이 주소를 한 번 저장한 뒤 다음부터 탭하면 됩니다.
- **소유자만 치트.** 멀티플레이 서버에서는 *관리자(op)*만 명령어를 쓸 수 있습니다.
  **나만 op**로 지정하면 게임 안에서는 아무도 치트를 못 쓰고, 나는 어떤 관리
  경로로든 언제나 원격으로 치트를 쓸 수 있습니다.
- **원격 관리 3가지 방법:**
  - 🤖 **디스코드 봇**(주력) — 관리자 전용 슬래시 명령어, 느린 작업용 로딩
    애니메이션, 로그 파일 첨부.
  - 💻 **SSH + RCON**(기본) — SSH만 되면 어디서든 콘솔.
  - 🌐 **Cloudflare Tunnel**(선택) — 포트포워딩 없이 서버/콘솔 접근.
- **30분 기본 HDD 자동 백업**, SHA-256 검증, 디스코드 복구·맵 업로드/전환,
  관리자 직접 등록형 Discord↔마인크래프트 다중 계정, 본인 구조, 사진 좌표북, 서버 일지, 요청 시점
  건강 점수, 친구용 포털, 성능 자동 알림·튜닝 리포트, 빠른 명령 패널(시간·날씨·
  난이도·게임룰·스폰 지정), 접속자 빠른 조작(한글 별칭 아이템 지급·포션 효과·
  인챈트·게임모드·TP·경험치·회복·추방), 백업 타임라인,
  버튼형 관리 패널·접속자 인벤토리 조회·상태 진단·회전 감사 로그, 자동 시작용
  **systemd** 서비스, 한 번에 끝내는
  **프로비저닝 스크립트**.
- **필요할 때를 위한 라즈베리파이 클러스터** 안내.
- **영어·한국어 전체 문서.**

---

## 빠른 시작

디스플레이와 키보드 없이 설치한다면
**[SD카드부터 서버 가동까지의 완전 헤드리스 문서](docs/ko/headless-setup.md)**를
먼저 보세요. Windows Raspberry Pi Imager, SSH, HDD 안전 확인, 최초 실행, 공유기 포트,
친구 계정 등록, 재부팅 시험, 복구까지 순서대로 설명합니다.

설정 스크립트는 필요할 때 Amazon Corretto Java 25를 자동으로 설치합니다.

Raspberry Pi OS Lite(64-bit, Debian 13 Trixie)에서 파이에 접속해:

```bash
git clone https://github.com/pachir1su/raspi-mc-server.git
cd raspi-mc-server

# 1. 500GB HDD 파티션 확인 후 준비(/dev/sda1은 예시이며 포맷 시 데이터 삭제)
lsblk -f
sudo mkfs.ext4 /dev/sda1
sudo ./scripts/setup_hdd.sh /dev/sda1

# 2. 전부 프로비저닝(Amazon Corretto Java 25 자동 설치 포함)
./deploy/setup_raspberrypi.sh

# 3. 비밀값 설정
#    - /mnt/minecraft/live/server.properties -> rcon.password
#    - .env                     -> DISCORD_TOKEN, ADMIN_USER_IDS, RCON_PASSWORD

# 4. 재부팅 자동 시작 등록 후 단일 진입점 실행
sudo systemctl enable minecraft.service mc-discord-bot.service
.venv/bin/python -m bot.main
# 최초 실행에서 언어와 Java 전용 또는 Java+Bedrock 선택
```

자세한 과정: **[docs/ko/setup.md](docs/ko/setup.md)**.

---

## 치트: "나만 치트" 는 이렇게 동작합니다

멀티플레이 마인크래프트에는 싱글플레이 같은 월드별 "치트 허용" 스위치가 없습니다.
대신 명령어는 **관리자(op) 레벨**로 통제됩니다.

- **일반 플레이어**는 치트 명령어를 아예 쓸 수 없습니다.
- **관리자(op)**만 쓸 수 있습니다. **나만** op로 지정합니다(`server/ops.json`).
- **콘솔·RCON·디스코드 봇·SSH**는 항상 op 레벨 4로 실행됩니다. 그래서 **나**는
  언제나 원격으로 치트를 쓸 수 있고, 게임 안의 **다른 사람은** 쓸 수 없습니다.

자세히: **[docs/ko/cheats-and-ops.md](docs/ko/cheats-and-ops.md)**.

---

## 문서

외부 이미지의 출처와 라이선스는 [이미지 출처 문서](docs/assets/ATTRIBUTION.md)에
기록합니다.

게임플레이 안내는 Geyser로 접속한 Bedrock 플레이어도 포함해 서버 측 Java/Paper 26.1
규칙을 기준으로 합니다.

| 주제 | 한국어 | English |
|---|---|---|
| 무화면 SD카드 → 서버 가동 | [헤드리스 전체 설치](docs/ko/headless-setup.md) | [headless setup](docs/en/headless-setup.md) |
| HDD 규격·케이스·전원 | [HDD 하드웨어](docs/ko/hdd-hardware.md) | [HDD hardware](docs/en/hdd-hardware.md) |
| 설치 & 첫 실행 | [설치](docs/ko/setup.md) | [setup](docs/en/setup.md) |
| 서버 설정 | [설정](docs/ko/configuration.md) | [configuration](docs/en/configuration.md) |
| 치트와 관리자 | [치트와 관리자](docs/ko/cheats-and-ops.md) | [cheats-and-ops](docs/en/cheats-and-ops.md) |
| 디스코드 봇 | [디스코드 봇](docs/ko/discord-bot.md) | [discord-bot](docs/en/discord-bot.md) |
| 친구 연동·구조·일지 | [친구 도구](docs/ko/friend-tools.md) | [friend-tools](docs/en/friend-tools.md) |
| 인챈트 | [인챈트](docs/ko/enchantments.md) | [enchantments](docs/en/enchantments.md) |
| 상태 효과 | [상태 효과](docs/ko/status-effects.md) | [status effects](docs/en/status-effects.md) |
| 양조법 | [양조법](docs/ko/brewing.md) | [brewing](docs/en/brewing.md) |
| 주민 거래 | [주민 거래](docs/ko/villager-trading.md) | [villager trading](docs/en/villager-trading.md) |
| 광물과 자원 | [광물과 자원](docs/ko/ores-and-resources.md) | [ores and resources](docs/en/ores-and-resources.md) |
| 농사와 사육 | [농사와 사육](docs/ko/farming-and-breeding.md) | [farming and breeding](docs/en/farming-and-breeding.md) |
| 음식과 허기 | [음식과 허기](docs/ko/food.md) | [food](docs/en/food.md) |
| 서버 전용 기능 | [서버 전용 기능](docs/ko/server-features.md) | [server features](docs/en/server-features.md) |
| Death Box 플러그인 | [Death Box 설계](docs/ko/death-box-design.md) | [death-box-design](docs/en/death-box-design.md) |
| Paper 운영 플러그인 | [Paper 운영 플러그인](docs/ko/paper-ops-plugin.md) | [paper-ops-plugin](docs/en/paper-ops-plugin.md) |
| 추천 플러그인(선택) | [추천 플러그인](docs/ko/recommended-plugins.md) | [recommended-plugins](docs/en/recommended-plugins.md) |
| 원격 접속(RCON / Cloudflare) | [원격 접속](docs/ko/remote-access.md) | [remote-access](docs/en/remote-access.md) |
| 백업 | [백업](docs/ko/backup.md) | [backup](docs/en/backup.md) |
| 성능 튜닝 | [성능 튜닝](docs/ko/performance.md) | [performance](docs/en/performance.md) |
| 라즈베리파이 클러스터 | [클러스터](docs/ko/cluster.md) | [cluster](docs/en/cluster.md) |
| Java + Bedrock 크로스플레이 | [자바+베드락](docs/ko/bedrock.md) | [bedrock](docs/en/bedrock.md) |
| 문제 해결 | [문제 해결](docs/ko/troubleshooting.md) | [troubleshooting](docs/en/troubleshooting.md) |
| 서버장 운영 런북 | [운영 런북](docs/ko/operator-runbook.md) | [operator runbook](docs/en/operator-runbook.md) |
| 코딩 에이전트용 프롬프트 | [agent-prompts](docs/prompts/agent-prompts.md) | (같은 파일, 이중언어) |

에이전트 작업 규칙은 [CLAUDE.md](CLAUDE.md), [AGENTS.md](AGENTS.md)에 있습니다.

---

## 저장소 구조

```
raspi-mc-server/
├── server/        # server.properties 템플릿, ops/whitelist 예시
├── scripts/       # 설치 / 시작 / 정지 / 백업 / 복원
├── deploy/        # systemd 유닛 + 파이 원샷 프로비저닝
├── bot/           # 디스코드 관리 봇 (Python, discord.py)
├── plugin/        # Paper 플러그인 (DeathBox — 사망 시 보호 상자)
├── docs/          # 영어·한국어 문서, 에이전트 프롬프트
├── .env           # 추적되는 예시값; Pi에서 실제 값으로 교체
└── README.md / README.ko.md
```

---

## 준비물

- **Raspberry Pi OS Lite(64-bit)**를 올린 라즈베리파이 4B(4GB). 테스트 기준은
  Bookworm(Legacy)이며, Trixie에서는 `cloud-init` 첫 부팅이 Imager 설정(SSH·사용자)을
  무시할 수 있습니다 —
  [문제 해결](docs/ko/troubleshooting.md#trixie-imager-설정ssh사용자이-적용되지-않음) 참고.
- 32GB microSD와 PaperMC·월드·백업용 500GB USB 3.0 HDD. 일부 USB 3.0↔SATA 어댑터는
  부하 시 Pi 4B xHCI 컨트롤러를 죽입니다 —
  [문제 해결 노트](docs/ko/troubleshooting.md#pi-4b-usb-30--sata-ssd-어댑터-xhci-컨트롤러-다운) 참고.
- 디스코드 애플리케이션/봇 토큰(봇용) — [docs/ko/discord-bot.md](docs/ko/discord-bot.md) 참고.
- **참고:** `mcrcon`은 데비안 저장소에 없어 설치 스크립트가 설치하지 않습니다. 일회성
  RCON 명령은 내장 클라이언트로 실행하세요: `.venv/bin/python -m bot.rcon "list"`.

## 라이선스

[MIT](LICENSE).
