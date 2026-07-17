# Discord admin bot

A small bot that lets **you** (and only allowlisted admins) manage the server
remotely: run any command via RCON, manage the whitelist, start/stop/restart
the service, back up the world, and pull logs — all from Discord.

## Why a bot?

- Manage the server from your phone without SSH.
- `/admin` → **Advanced tools** → **In-game command** is your remote cheat console (op level 4).
- Slow actions (backup, restart) show a **loading animation** so you get
  feedback instead of a frozen "thinking…".
- `/admin` → **Logs** previews or attaches the current log for quick debugging.

## 1. Create a Discord application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   → **New Application**.
2. **Bot** tab → **Add Bot** → copy the **token** (this is `DISCORD_TOKEN`).
3. Under **Privileged Gateway Intents**, you can leave all **off** — this bot
   uses only slash commands and the default intents.
4. **OAuth2 → URL Generator**: scopes `bot` + `applications.commands`; bot
   permissions `Send Messages`, `Embed Links`, `Attach Files`. Open the
   generated URL to invite the bot to your server.

## 2. Find the IDs you need

Enable **Developer Mode** (Discord Settings → Advanced), then right-click:

- **Your user** → *Copy User ID* → `ADMIN_USER_IDS` (put only yourself to be
  sole operator; comma-separate for multiple admins).
- **Your server** → *Copy Server ID* → `DISCORD_GUILD_ID` (optional; makes
  commands appear instantly instead of waiting for global sync).

## 3. Configure `.env`

```dotenv
DISCORD_TOKEN=your-bot-token
DISCORD_GUILD_ID=123456789012345678
ADMIN_USER_IDS=your-user-id
RCON_HOST=127.0.0.1
RCON_PORT=25575
RCON_PASSWORD=matches-server.properties
MC_SERVICE_NAME=minecraft.service
PUBLIC_COMMANDS_ENABLED=true
MC_STATE_DIR=/mnt/minecraft/bot-state
MC_MAP_URL_TEMPLATE=https://map.example.com/?world={dimension}&x={x}&y={y}&z={z}
MC_PUBLIC_ADDRESS=play.example.com
MC_PUBLIC_VERSION="Paper Java 26.1.x"
STATUS_CHANNEL_ID=123456789012345678
ALERT_TPS_THRESHOLD=18.0
ALERT_MEMORY_PERCENT=85
ALERT_TEMPERATURE_CELSIUS=80
ALERT_MIN_FREE_GB=20
```

## 4. Run

```bash
.venv/bin/python -m bot.main
```

The first terminal run asks for language and Java/Bedrock mode, prepares Paper,
and starts the bot. Stop it with Ctrl+C only when you are ready to hand over to
systemd:

```bash
sudo systemctl enable --now mc-discord-bot.service
sudo journalctl -u mc-discord-bot.service -f
```

## Commands

The bot publishes only five top-level commands. Legacy command callbacks remain
internal to the panels, so Discord's command picker stays short.

The first-run language controls bot responses and status text. Discord slash
command names follow each user's **Discord client language**. Korean clients see
`/서버`, `/관리자`, `/도구`, `/도움말`, and `/업로드`; English clients see the canonical
names below.

| Command | What it does |
|---|---|
| `/server` | Friend-safe access information, online players, and refresh buttons. |
| `/admin` | Private owner dashboard for service, player management (inspection plus give/effects/enchant/gamemode/teleport/XP/heal/kick), backups, worlds, updates, logs, storage, performance, quick commands (time/weather/difficulty/gamerules/set spawn), direct multi-account assignment, admin-only help, and advanced tools. |
| `/tools` | Private self-service panel for selecting an assigned account, rescue, location, score, coordinates, diary, and death boxes. |
| `/help` | Friend-safe explanation of the public commands without exposing owner controls. |
| `/upload world/update/place-photo/diary` | Attachment-only flows that Discord buttons cannot provide. World/update remain admin-only; friend media still checks link ownership. |

Destructive backup/world/service actions require a second confirmation button.
Text modals appear only where text is inherent: player name, coordinate name,
diary text, announcements, item names, the in-game command console, and
whitelist names.

See [backup.md](backup.md) for the complete retention and file-safety model.
See [friend-tools.md](friend-tools.md) for exact Pi configuration, approval flow,
runtime files, command examples, and troubleshooting.

## Stats, invincibility, and wiki (panel buttons)

Issue #79 briefly added eleven flat top-level commands (`/invincible`,
`/stats`, `/wiki`, and friends), but feedback (#85) was that they cluttered
the command picker, so they moved back behind panel buttons. The features are
unchanged — only the entry point differs.

| Feature | Entry point | What it does |
|---|---|---|
| Kill/death lookup (#68) | `/admin` → players → **킬·데스** | Show the selected player's death/kill totals. |
| My stats (#68) | `/tools` → **내 통계** | Show your own linked player's death/kill totals. |
| Invincibility (#75) | `/admin` → players → **무적** | Grant 30s/5m/30m invincibility or clear it: regeneration, resistance, fire resistance, and saturation with hidden particles. |
| Game wiki (#71) | `/tools` → **게임 위키** | Jump to a GitHub help doc — brewing, enchantments, farming, and more. |

Stats are tracked by scoreboards from the moment the bot first starts (no
retroactive history). The wiki base URL defaults to the repository docs and can
be changed with `MC_WIKI_BASE_URL` in `.env`.

## Button-first dashboard

Run `/admin` once, then use buttons without typing command arguments. The
first screen keeps only the everyday buttons (refresh, players, server
control, backups, quick commands, health, friend accounts, help); the
**More** button opens the second tier with performance, lag analysis, logs,
storage, worlds, updates, advanced tools, and the protection toggles.
Everything below stays reachable:

- refreshing server, player, HDD, and latest-backup status
- creating, selecting, checking, downloading, restoring, deleting, and pruning backups
- changing backup policy through dropdowns with the current values preselected
- starting, or confirming stop/restart of, the Minecraft service
- toggling automatic backups
- imported-world selection, update status, storage, and health diagnostics
- Pi temperature, memory, TPS, undervoltage, throttle metrics, and tuning report
- quick commands: time (day/night/freeze), weather (clear/rain/thunder/lock),
  four difficulty levels, gamerule toggles (keep inventory, mob griefing,
  immediate respawn, natural regeneration, days played), spawn placement
  (from a player's position or typed coordinates), and dropped-item cleanup.
  Dropped-item cleanup asks for confirmation because it can delete friends' items.
  Gamerule buttons the server version does not support are detected when the
  panel opens and disabled with a "(버전 미지원)" label.
- player quick actions: give items (Korean aliases supported), potion effects,
  enchants, gamemode, teleport (player/place/spawn), XP, heal, invincibility
  (30s/5m/30m/clear), kill/death lookup, and kick (with confirmation). Effect
  and enchant dropdowns include a free-input option.
- the live-player and account-link selectors
- bot, Minecraft, and event-driven player-chat log controls
- persistent Paper spawn-protection toggle

The ephemeral panel is visible only to the administrator who opened it and
expires after ten minutes. **On expiry the buttons grey out and the message
says how to reopen the panel** — no more dead buttons that only answer with
Discord's "interaction failed". Callback failures produce a visible error
instead of leaving an apparently dead button, and a global handler logs any
unexpected slash-command exception to the bot log while still answering the
user in Korean.

Sub-panels (players, service, backups, quick commands, More, health, …) and
even the player lookup results and the effect/enchant/gamemode/teleport/
invincibility/kick screens **swap the screen in place inside the same message
instead of posting a new one** (#58), so pressing buttons no longer piles up
chat. Every sub-screen carries both an **↩️ back** button (one level up:
players, More, logs, …) and a **🏠 home** button, so features can be chained
without retyping `/admin`. Slow lookups (performance, tuning) show a loading
frame first, then edit to the result.

## Player management (inspection + actions)

The `/admin` dashboard **Players** button builds a dropdown from Paper's
current `list` output. After selecting a player, inspection buttons show:

- **Inventory** — equipment (armour/offhand), hotbar, backpack, and ender
  chest, grouped into sections
- **Position** — coordinates and dimension
- **Health/XP** — health (with hearts), food, experience level, and game
  mode as a readable summary
- **Effects** — effect names (Korean), levels, and remaining time

Action buttons (all audited): give item (Korean alias or English ID with typo
suggestions), potion effects and enchants (common presets plus free input —
the effect modal also takes a duration, a strength level of 1–10, and hides
bubble particles by default; the dropdown redraws itself after every pick so
the same effect or enchant can be applied repeatedly without switching to a
different option first),
gamemode, teleport to another player / a saved place / spawn, XP +10/+30,
heal, and kick (with confirmation). Three atmosphere buttons also spawn
things near the selected player without any game-chat output: a creeper 5
blocks behind them, the creeper fuse sound 3 blocks behind them (sound only,
no mob), and lightning at their position — the lightning button only fires
while it is raining or thundering (checked through the plugin's weather
report) and otherwise says the sky is clear.

Names are sourced from the live list and validated again as Java or dot-prefixed Floodgate usernames, so
they cannot be turned into arbitrary RCON input.

## Log panel

The dashboard **Logs** button opens controls instead of immediately attaching one file. It reads a
bounded tail of the bot log, Paper `latest.log`, or `RaspiMcOps/chat.log` and supports:

- bot, Minecraft, or player-chat previews
- warning/error-only filtering for each source
- original attachments within the guild's actual Discord limit
- an SSH/SFTP hint when a file is too large

Every bot log line is timestamped (`YYYY-MM-DD HH:MM:SS`), and the bot rolls to a
fresh `bot_<timestamp>.log` file whenever the current one passes `LOG_MAX_BYTES`
(default 5 MiB, `0` disables) or the local date changes. `LOG_RETENTION_DAYS`
(default 14) prunes older files on startup.

The privileged audit JSONL rotates once at 5 MiB instead of growing forever on
the microSD.

## Security notes

- The bot never needs your Minecraft account — it talks to the server over
  local RCON only.
- Keep `ADMIN_USER_IDS` tight. Anyone in that list can cheat and stop the
  server.
- The systemd units use a **narrow sudoers rule** (see `deploy/`) so the bot
  can control only the named Minecraft service and queue the root-owned
  updater service, not run arbitrary root commands. Updates require a second
  admin button confirmation.
- Keep RCON on localhost; the bot connects to `127.0.0.1`.

## Security hardening and sudo

The bot restarts the Minecraft service through `sudo systemctl` (for crossplay
setup and the start/stop/restart controls). `sudo` relies on the kernel's
setuid mechanism, which **`NoNewPrivileges=true` blocks** — an earlier unit set
that flag, so every `sudo` call failed with `The "no new privileges" flag is
set` and the bot fell into a restart loop.

The fix keeps the elevation narrow while preserving hardening:

- `NoNewPrivileges` is **not** set on `mc-discord-bot.service` (it must allow
  `sudo`).
- Privilege escalation stays confined by the **narrow sudoers rule**
  (`/etc/sudoers.d/raspi-mc-server`): the bot may only start/stop/restart and
  query the named Minecraft service and queue the updater — nothing else.
- Compensating sandboxing is applied instead: `ProtectSystem=strict`,
  `ProtectHome=read-only` with an explicit `ReadWritePaths=` for the repo and
  `/mnt/minecraft`, `PrivateTmp=true`, `ProtectControlGroups=true`, and
  `ProtectKernelTunables=true`.

Trade-off: dropping `NoNewPrivileges` re-enables setuid within the unit, but the
sudoers allowlist means the only program the bot can run with elevated rights is
`systemctl` against two fixed services. The Minecraft and updater units still
keep `NoNewPrivileges=true` because they never call `sudo`.

If setup did not complete (no `data/app-settings.json`), the bot exits with
`EX_CONFIG` (78) and the unit's `RestartPreventExitStatus=78` stops systemd from
looping — run `.venv/bin/python -m bot.main` once in a terminal to finish setup.

## How the loading animation works

Discord forces its own "thinking…" text when a command `defer`s, and you can't
replace it. So for slow actions the bot sends its **own** embed first and edits
it on a timer with a progress bar that eases toward ~96% (never 100% until the
real result replaces it). Failed frame edits are ignored — the animation is
cosmetic and never blocks the actual work. See `bot/loading.py`.

## Automatic performance alerts and language

When `STATUS_CHANNEL_ID` is set, the bot checks TPS, memory, CPU temperature,
power/throttle flags, and HDD free space every five minutes. It posts only new
threshold warnings after the `ALERT_COOLDOWN_MINUTES` cooldown. The first-run
menu stores the portal, alert, report, and incident-response language outside
`.env`. Some older fixed operational strings can be migrated to the same i18n
helper over time.
