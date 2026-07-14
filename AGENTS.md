# AGENTS.md

Working rules for Codex and other coding agents in this repository. Same
intent as [CLAUDE.md](CLAUDE.md) — kept here so agents that look for
`AGENTS.md` find them too.

## Project

- **raspi-mc-server**: a friends-only Minecraft (Java/PaperMC) server for a
  Raspberry Pi 4B (4GB), 3–4 players, owner-only cheats, remote admin (Discord
  bot / SSH+RCON / optional Cloudflare Tunnel).
- **Public repository.** Never commit secrets, tokens, RCON passwords, world
  data, or personal config. The tracked `.env` contains placeholders only;
  real values belong only in the Pi's operational copy. Do not create
  `.env.example`.
- Docs are bilingual: English in `docs/en` + `README.md`, Korean in `docs/ko` +
  `README.ko.md`. Keep both in sync.

## How to work

- Follow the existing structure and naming; avoid out-of-scope changes.
- Small, focused commits (config → script → bot → docs) with clear messages.
- Update docs in both languages when behaviour changes.
- Ask before implementing anything ambiguous.
- Do not schedule recurring self-checks / PR re-verification unless asked.

## Code & verification

- Bot: Python, discord.py 2.x app_commands. Keep server-mutating commands
  behind `ADMIN_USER_IDS`.
- Scripts: Bash with `set -euo pipefail`, re-runnable.
- Verify: `python3 -m py_compile` on changed modules, `bash -n` on changed
  scripts; check doc links/commands for docs changes.
