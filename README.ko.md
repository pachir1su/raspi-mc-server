# raspi-mc-server (한국어)

**라즈베리파이 4B(4GB)**에서 돌리는 **친구용 마인크래프트(자바) 서버**입니다.
**3~4명** 규모, **소유자만 치트 사용**, 그리고 **디스코드·SSH·웹으로 원격 관리**를
목표로 합니다.

> 🇬🇧 English: **[README.md](README.md)**

---

## 무엇이 들어 있나

- **PaperMC** 서버 — Pi 4B(4GB)·32GB microSD + 500GB USB HDD에 맞춘 튜닝
  (Aikar GC 플래그, 파이 친화적인 렌더/시뮬레이션 거리).
- **화이트리스트 전용, 모드 없음** — 나와 친구 몇 명만 들어오는 작은 사설 월드.
- **소유자만 치트.** 멀티플레이 서버에서는 *관리자(op)*만 명령어를 쓸 수 있습니다.
  **나만 op**로 지정하면 게임 안에서는 아무도 치트를 못 쓰고, 나는 어떤 관리
  경로로든 언제나 원격으로 치트를 쓸 수 있습니다.
- **원격 관리 3가지 방법:**
  - 🤖 **디스코드 봇**(주력) — 관리자 전용 슬래시 명령어, 느린 작업용 로딩
    애니메이션, 로그 파일 첨부.
  - 💻 **SSH + RCON**(기본) — SSH만 되면 어디서든 콘솔.
  - 🌐 **Cloudflare Tunnel**(선택) — 포트포워딩 없이 서버/콘솔 접근.
- **30분 기본 HDD 자동 백업**, 디스코드 복구·맵 업로드/전환, 자동 시작용 **systemd** 서비스, 한 번에 끝내는
  **프로비저닝 스크립트**.
- **필요할 때를 위한 라즈베리파이 클러스터** 안내.
- **영어·한국어 전체 문서.**

---

## 빠른 시작

64비트 라즈베리파이 OS에서, 파이에 접속해:

```bash
git clone https://github.com/pachir1su/raspi-mc-server.git
cd raspi-mc-server

# 1. 500GB HDD 파티션 확인 후 준비(/dev/sda1은 예시이며 포맷 시 데이터 삭제)
lsblk -f
sudo mkfs.ext4 /dev/sda1
sudo ./scripts/setup_hdd.sh /dev/sda1

# 2. 전부 프로비저닝(자바, PaperMC, 파이썬 venv, systemd, sudoers)
./deploy/setup_raspberrypi.sh

# 3. 비밀값 설정
#    - /mnt/minecraft/live/server.properties -> rcon.password
#    - .env                     -> DISCORD_TOKEN, ADMIN_USER_IDS, RCON_PASSWORD

# 4. 서버 시작, 나 op 지정, 봇 시작
sudo systemctl enable --now minecraft.service
sudo systemctl enable --now mc-discord-bot.service
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

| 주제 | 한국어 | English |
|---|---|---|
| 설치 & 첫 실행 | [설치](docs/ko/setup.md) | [setup](docs/en/setup.md) |
| 서버 설정 | [설정](docs/ko/configuration.md) | [configuration](docs/en/configuration.md) |
| 치트와 관리자 | [치트와 관리자](docs/ko/cheats-and-ops.md) | [cheats-and-ops](docs/en/cheats-and-ops.md) |
| 디스코드 봇 | [디스코드 봇](docs/ko/discord-bot.md) | [discord-bot](docs/en/discord-bot.md) |
| 원격 접속(RCON / Cloudflare) | [원격 접속](docs/ko/remote-access.md) | [remote-access](docs/en/remote-access.md) |
| 백업 | [백업](docs/ko/backup.md) | [backup](docs/en/backup.md) |
| 성능 튜닝 | [성능 튜닝](docs/ko/performance.md) | [performance](docs/en/performance.md) |
| 라즈베리파이 클러스터 | [클러스터](docs/ko/cluster.md) | [cluster](docs/en/cluster.md) |
| 베드락 대안 | [베드락 대안](docs/ko/bedrock.md) | [bedrock](docs/en/bedrock.md) |
| 문제 해결 | [문제 해결](docs/ko/troubleshooting.md) | [troubleshooting](docs/en/troubleshooting.md) |
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
├── docs/          # 영어·한국어 문서, 에이전트 프롬프트
├── .env.example   # .env 로 복사해서 채우기
└── README.md / README.ko.md
```

---

## 준비물

- **64비트** 라즈베리파이 OS(Bookworm 권장)를 올린 라즈베리파이 4B(4GB).
- 32GB microSD와 PaperMC·월드·백업용 500GB USB 3.0 HDD.
- 디스코드 애플리케이션/봇 토큰(봇용) — [docs/ko/discord-bot.md](docs/ko/discord-bot.md) 참고.

## 라이선스

[MIT](LICENSE).
