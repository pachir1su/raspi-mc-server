# Bedrock alternative

This repo implements a **Java Edition (PaperMC)** server, which is the best fit
for RCON-based remote admin, whitelisting, and the op-based "owner-only cheats"
model. If your players are on phones/consoles/Windows 10+, you may prefer
**Bedrock**. Here's how the pieces map — and what changes.

## When to choose Bedrock

- Your friends play on **mobile / console / Windows (Bedrock) editions**.
- You want the lightest possible load on the Pi (Bedrock's server is leaner).

## Trade-offs vs the Java setup here

| Aspect | Java (this repo) | Bedrock |
|---|---|---|
| Performance on Pi | Good with tuning | Generally lighter |
| **RCON** | ✅ built in | ❌ not supported |
| Remote commands | RCON (bot/CLI) | Need `stdin`/wrapper or an add-on |
| Cheats/ops model | op level (clean) | `permissions.json` + `allow-cheats` in `server.properties` |
| Plugins | Paper plugins | Behaviour packs / limited server addons |
| Cross-play | Java only (or Geyser) | Bedrock devices natively |

## Getting Bedrock on a Pi

The official Bedrock Dedicated Server (BDS) is **x86-only**, so on ARM you use
one of:

- **[PocketMine-MP](https://pmmp.io/)** (PHP) — runs natively on ARM, supports
  plugins, and has a console you can drive.
- **BDS via `box64`** (x86 emulation) — works but adds overhead; not ideal on a
  Pi.

PocketMine is the usual ARM choice.

## Owner-only cheats on Bedrock

Bedrock's model differs from Java:

- `server.properties` has `allow-cheats` and `default-player-permission-level`.
- Set `default-player-permission-level=member` so normal players can't use
  commands, and grant yourself **operator** in `permissions.json` (by XUID).
- The server console (and PocketMine's console/plugins) can always run commands
  — that's your remote cheat channel.

## Remote administration without RCON

Since Bedrock has no RCON, adapt the remote-admin approach:

- **PocketMine**: use a console-bridge plugin or its command API; a Discord bot
  can talk to a plugin's local socket/HTTP instead of RCON.
- **BDS**: wrap the server so you can write to its **stdin** (e.g. a `tmux`/
  `screen` session or a small supervisor), and have the bot send commands there.

The Discord bot in this repo is RCON-based; to support Bedrock you'd swap
`bot/rcon.py` for a stdin/plugin transport and keep the rest (admin gating,
loading animation, logs) the same.

## Cross-play option (keep Java + let Bedrock join)

If you like the Java setup but have Bedrock friends, add
**[Geyser](https://geysermc.org/)** (+ Floodgate) as a Paper plugin. Bedrock
clients then connect to your Java server. This keeps RCON, ops, and everything
in this repo — usually the best of both worlds for a mixed friend group.
