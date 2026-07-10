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
