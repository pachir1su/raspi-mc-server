# CLAUDE.md


Working rules for Claude Code (and compatible agents) in this repository.
These override default behaviour — follow them exactly.

## Project

- **raspi-mc-server**: a friends-only Minecraft (Java/PaperMC) server for a
  Raspberry Pi 4B (4GB), 3–4 players, with owner-only cheats and remote
  administration (Discord bot, SSH+RCON, optional Cloudflare Tunnel).
- This repository is **public**. Never commit secrets, real tokens, RCON
  passwords, world data, or personal config. `.env` holds real values and is
  git-ignored; `.env.example` holds placeholders only.
- Documentation is written in **both English and Korean**. `README.md` is
  English (default); `README.ko.md` is Korean. Docs live in `docs/en` and
  `docs/ko` and should stay in sync.

## How to work

- Prefer the existing structure and naming. Avoid unrelated refactors and
  out-of-scope changes.
- Keep commits **small and focused** (one logical change each: config → script
  → bot code → docs), with clear messages.
- When you change behaviour, update the matching docs in **both** languages.
- If a requirement is ambiguous, **ask before implementing** — don't guess.
- Do **not** schedule recurring self-checks or auto re-verification of PRs
  unless the user explicitly asks.

## Code

- Bot code is Python (discord.py 2.x, app_commands). Match the existing module
  style and keep the bot single-purpose (admin/cheat control via RCON).
- Shell scripts are Bash with `set -euo pipefail`. Keep them re-runnable.
- Anything that mutates the server must stay behind the admin allowlist
  (`ADMIN_USER_IDS`). Read-only helpers may be loosened deliberately.

## Secrets & runtime data

- Treat `.env`, `server/server.properties` (contains the RCON password on the
  Pi), `server/world*/`, `bot/logs/`, and `backups/` as operational data.
- If a new setting is needed, tell the user what to add to `.env` — don't
  invent real values or commit them.

## Verify

- For code changes, run `python3 -m py_compile` on touched modules and
  `bash -n` on touched scripts at minimum.
- For docs-only changes, check links and command examples by hand.
=======
Claude Code 작업 지침입니다. 이 저장소에서 작업할 때는 아래 규칙을 우선 적용합니다.


## 작업 방식

- 이슈를 지정하면 해당 이슈 번호를 먼저 확인합니다. 본문뿐 아니라 댓글까지 모두 읽고 근거로 삼습니다.
- 한 작업 안에서 커밋은 되도록 잘게, 많이 쪼갭니다(판별 함수 → 구현 → 테스트 → 문서 등 단위별로).
- QA·검증할 항목이 있으면 PR 본문에 정리해 넣습니다(무엇을 어떻게 확인했는지, 남은 확인 사항 포함).
- 사용자가 직접 해야 할 일(설정 변경, 실기기 확인, 토큰 발급 등)이 있으면 하나하나 구체적으로 알려줍니다.
- 궁금하거나 불확실한 점은 임의로 결정하지 말고 항상 먼저 물어봅니다.
- **PR을 주기적으로(예: 1시간마다) 자동 재검증하거나 셀프 체크인을 예약하지 않습니다.** 사용자가 명시적으로 요청할 때만 합니다.

## 이슈와 PR

- 닫힌 이슈는 사용자가 명시적으로 요청하지 않는 한 읽거나 근거로 삼지 않습니다.
- 이슈를 확인할 때는 본문뿐 아니라 댓글도 확인합니다.
- PR은 카테고리 단위로 나누고, 커밋은 이슈나 작업 단위로 작게 쪼갭니다.
- PR 본문에는 관련 이슈 번호를 명확히 연결합니다.
- 불확실한 요구사항은 구현 전에 사용자에게 질문합니다.

## 코드 변경

- 기존 구조와 네이밍 스타일을 우선 따릅니다.
- 불필요한 리팩터링과 범위 밖 변경은 피합니다.
- 비밀값, 실제 토큰, 개인 설정 파일을 출력하거나 커밋하지 않습니다.
- `.env`, `data/`, 로그 파일은 운영 데이터로 보고 주의해서 다룹니다.

## 환경 변수(.env)

- 새 설정값이 필요하거나 `.env`를 고쳐야 하면, 직접 바꾸지 말고 **사용자에게 무엇을 어떻게 수정할지 알려줍니다.**
- 저장소의 `.env`에는 실제 값이 아니라 **예시 값**이 들어 있습니다. 실제 토큰·계정으로 착각하지 않습니다.
- `.env.example` 같은 별도 샘플 파일을 새로 만들지 않습니다. 설정 안내는 기존 `.env`를 기준으로 수정하도록 요청합니다.

## 검증

- 코드 변경이 있으면 가능한 범위에서 테스트를 실행합니다.
- 문서만 변경한 경우에도 링크와 명령 예시를 직접 확인합니다.
- PowerShell에서 한글 문서를 읽을 때는 `Get-Content -Encoding UTF8`을 사용합니다.
