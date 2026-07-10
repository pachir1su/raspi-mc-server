# Prompts for coding agents / 코딩 에이전트용 프롬프트

Ready-to-use prompts for driving a coding agent (Claude Code, Codex, etc.) to
build, extend, or maintain this repository. Copy a block, adjust the bracketed
parts, and paste it to your agent.

바로 쓸 수 있는 프롬프트 모음입니다(Claude Code, Codex 등). 블록을 복사해
`[대괄호]` 부분만 바꿔 에이전트에게 붙여넣으세요.

> Agents should read [CLAUDE.md](../../CLAUDE.md) / [AGENTS.md](../../AGENTS.md)
> first. This repo is **public** — never commit secrets.
> 에이전트는 먼저 CLAUDE.md / AGENTS.md 를 읽으세요. 이 저장소는 **공개**이니
> 비밀값을 커밋하지 마세요.

---

## 1. Bootstrap from scratch / 처음부터 구축

**EN**
```
Build a friends-only Minecraft Java (PaperMC) server for a Raspberry Pi 4B (4GB),
3–4 players, no mods. Requirements:
- Whitelist-only; owner-only cheats via the op model (op only me).
- server.properties tuned for a Pi 4B; RCON enabled on localhost.
- Scripts: install (download Paper, JDK 21), start (Aikar flags, ~2600M heap),
  stop (graceful via RCON), backup (save-off/flush + tar + rotation), restore.
- systemd units for the server and a Discord admin bot; a one-shot Pi
  provisioning script with a narrow sudoers rule for the bot.
- A Discord bot (discord.py) with admin-only slash commands over RCON: status,
  say, run-any-command, whitelist add/remove, start/stop/restart, backup, logs.
  Add a loading animation for slow actions and per-run rotating log files.
- Docs in English and Korean (README + docs/en + docs/ko), covering setup,
  configuration, cheats/ops, the bot, remote access, backups, performance,
  cluster, Bedrock alternative, troubleshooting.
Keep commits small and focused. Verify with py_compile and bash -n.
```

**KO**
```
라즈베리파이 4B(4GB)용 친구 전용 마인크래프트 자바(PaperMC) 서버를 만들어줘.
3~4명, 모드 없음. 요구사항:
- 화이트리스트 전용, op 모델로 소유자만 치트(나만 op).
- Pi 4B에 맞춘 server.properties, RCON은 localhost에서만.
- 스크립트: 설치(Paper 다운로드, JDK 21), 시작(Aikar 플래그, 힙 ~2600M),
  정지(RCON로 정상 종료), 백업(save-off/flush + tar + 회전), 복원.
- 서버와 디스코드 관리 봇용 systemd 유닛, 봇 전용 좁은 sudoers 규칙을 포함한
  파이 원샷 프로비저닝 스크립트.
- discord.py 봇: RCON 경유 관리자 전용 슬래시 명령(status, say, 임의 명령 실행,
  whitelist add/remove, start/stop/restart, backup, logs). 느린 작업용 로딩
  애니메이션과 실행별 회전 로그 파일 추가.
- 영어·한국어 문서(README + docs/en + docs/ko): 설치, 설정, 치트/op, 봇,
  원격 접속, 백업, 성능, 클러스터, 베드락 대안, 문제 해결.
커밋은 작게 쪼개고, py_compile 과 bash -n 으로 검증해줘.
```

---

## 2. Add a Discord slash command / 슬래시 명령 추가

**EN**
```
Add an admin-only slash command `/[name]` to bot/cogs/admin.py that [does X via
RCON]. Keep it behind the ADMIN_USER_IDS check, log the action with userTag,
and if it's slow wrap the work with bot.loading.animate_while. Update
docs/en/discord-bot.md and docs/ko/discord-bot.md. Verify with py_compile.
```

**KO**
```
bot/cogs/admin.py 에 관리자 전용 슬래시 명령 `/[이름]` 을 추가해줘. 기능은
[RCON으로 X 수행]. ADMIN_USER_IDS 체크 뒤에 두고, userTag 로 로그를 남기고,
느리면 bot.loading.animate_while 로 감싸줘. docs/en/discord-bot.md 와
docs/ko/discord-bot.md 를 갱신하고 py_compile 로 검증해줘.
```

---

## 3. Support Bedrock / 베드락 지원

**EN**
```
Add optional Bedrock support without breaking the Java path. Introduce a
transport abstraction so bot/cogs/admin.py can talk to either RCON (Java) or a
stdin/plugin bridge (Bedrock/PocketMine). Document the differences in
docs/en/bedrock.md and docs/ko/bedrock.md (ops via permissions.json, no RCON).
Do not remove the existing RCON path.
```

**KO**
```
자바 경로를 깨지 않고 베드락 지원을 선택적으로 추가해줘. bot/cogs/admin.py 가
RCON(자바) 또는 stdin/플러그인 브리지(베드락/PocketMine) 중 하나와 통신하도록
전송 계층을 추상화하고, 차이점을 docs/en/bedrock.md·docs/ko/bedrock.md 에
정리해줘(permissions.json 기반 op, RCON 없음). 기존 RCON 경로는 지우지 마.
```

---

## 4. Add a Velocity proxy for a cluster / 클러스터용 Velocity 프록시

**EN**
```
Add a Velocity proxy config and a systemd unit so multiple Pi backends sit
behind one address, following docs/en/cluster.md. Use modern forwarding with a
shared secret; keep backends private. Add setup docs in both languages.
```

**KO**
```
docs/en/cluster.md 를 따라 여러 파이 백엔드를 하나의 주소 뒤에 두는 Velocity
프록시 설정과 systemd 유닛을 추가해줘. 공유 시크릿으로 modern forwarding 을
쓰고 백엔드는 비공개로 유지해줘. 설치 문서를 영어·한국어로 추가해.
```

---

## 5. Maintenance / 유지보수

**EN**
```
Bump the default PaperMC/Minecraft version to [X] in scripts/install_server.sh
and the docs, verify the download URL resolves, and note any breaking config
changes in docs/en/troubleshooting.md and docs/ko/troubleshooting.md.
```

**KO**
```
scripts/install_server.sh 와 문서의 기본 PaperMC/마인크래프트 버전을 [X] 로
올리고, 다운로드 URL 이 유효한지 확인하고, 호환성에 영향 있는 설정 변경을
docs/en/troubleshooting.md·docs/ko/troubleshooting.md 에 적어줘.
```

---

## Guardrails for any prompt / 모든 프롬프트 공통 원칙

- Never commit `.env`, real tokens, RCON passwords, or world data.
  `.env`·실제 토큰·RCON 비밀번호·월드 데이터는 절대 커밋 금지.
- Keep server-mutating actions behind `ADMIN_USER_IDS`.
  서버를 바꾸는 동작은 `ADMIN_USER_IDS` 뒤에.
- Update English **and** Korean docs together.
  영어·한국어 문서를 함께 갱신.
- Small, focused commits; verify (`py_compile`, `bash -n`) before pushing.
  작은 단위 커밋, 푸시 전 검증.
