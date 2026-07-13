# Discord admin bot

A small bot that lets **you** (and only allowlisted admins) manage the server
remotely: run any command via RCON, manage the whitelist, start/stop/restart
the service, back up the world, and pull logs — all from Discord.

## Why a bot?

- Manage the server from your phone without SSH.
- The `/mc` command is your **remote cheat console** (runs at op level 4).
- Slow actions (backup, restart) show a **loading animation** so you get
  feedback instead of a frozen "thinking…".
- `/logs` attaches the current log file for quick debugging.

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
MC_SPAWN_DIMENSION=overworld
MC_SPAWN_X=0.5
MC_SPAWN_Y=80
MC_SPAWN_Z=0.5
MC_MAP_URL_TEMPLATE=https://map.example.com/?world={dimension}&x={x}&y={y}&z={z}
MC_PUBLIC_ADDRESS=play.example.com
MC_PUBLIC_VERSION=Paper Java 1.21.x
MC_PUBLIC_RULES=Respect builds and items; tell the operator when something breaks.
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

`/portal` and `/online` are friend-safe read-only commands. Approved links also
unlock the narrow `/rescue`, `/place`, `/diary`, and `/server-score` surface.
All general management commands remain **admin-only** (checked against
`ADMIN_USER_IDS`). Reopen the stored language/server menu with
`.venv/bin/python -m bot.main --setup`.

| Command | What it does |
|---|---|
| `/status` | Is the server up? Who's online (via RCON `list`). |
| `/say <message>` | Broadcast a chat message. |
| `/mc <command>` | **Run ANY server command via RCON** — your cheat console. |
| `/whitelist add <name>` | Add a player to the whitelist. |
| `/whitelist remove <name>` | Remove a player from the whitelist. |
| `/start` | Start the minecraft service. |
| `/stop` | Save, then stop the service. |
| `/restart` | Restart the service. |
| `/backup create/list/download/verify` | Create, list, download, and verify HDD backups. |
| `/backup timeline/restore-preview` | Show a recent-backup timeline and verify before restoring. |
| `/backup restore/delete` | Restore or delete with explicit confirmation. |
| `/backup settings/configure/enabled/prune` | Inspect/change policy or prune immediately. |
| `/world upload/list/download` | Validate, store, list, and download map archives. |
| `/world activate/delete` | Snapshot and switch maps, or delete a stored map. |
| `/storage` | Show HDD mount and capacity status. |
| `/health` | Check RCON, HDD, backup freshness, and scheduler state. |
| `/audit [limit]` | Show recent privileged-operation audit records. |
| `/panel` | Open the button-first combined administration dashboard. |
| `/players` | Select a live player and inspect inventory, location, stats, or effects. |
| `/metrics` | Show Pi temperature, load, memory, HDD, TPS, and throttle flags. |
| `/tuning-report` | Explain current performance risks and Pi-friendly tuning advice. |
| `/incident day/clear-weather/peaceful/clear-drops` | Accident helpers for day, weather, peaceful mode, and dropped items. `clear-drops` requires `CLEAR` because it deletes every dropped item. |
| `/portal`, `/online` | Friend-facing server info and online players. |
| `/link request/status` | Request and inspect your Discord ↔ Minecraft link. |
| `/link approve/revoke/list` | Admin-only link approval and management. |
| `/rescue spawn/whereami` | Move only the approved linked player to fixed spawn, or read that player's location. |
| `/place add/list/show/delete` | Shared coordinate book with durable photos and optional external map links. |
| `/diary add/recent/show` | Bounded shared server journal with optional photos. |
| `/server-score` | On-demand 0–100 score from Paper and Pi health metrics. |
| `/logs` | Open bot and Minecraft log controls. |

`/start`, `/stop`, `/restart`, `/backup create`, restore, and activation show the loading animation while
they run and then edit the message with the result.

See [backup.md](backup.md) for the complete retention and file-safety model.
See [friend-tools.md](friend-tools.md) for exact Pi configuration, approval flow,
runtime files, command examples, and troubleshooting.

## Button-first dashboard

Run `/panel` once, then use buttons without typing command arguments for:

- refreshing server, player, HDD, and latest-backup status
- creating a safe backup immediately
- starting, or confirming stop/restart of, the Minecraft service
- toggling automatic backups
- storage and health diagnostics
- Pi temperature, memory, TPS, undervoltage, throttle metrics, and tuning report
- emergency buttons for day, weather, peaceful difficulty, and dropped-item cleanup. Dropped-item cleanup asks for confirmation because it can delete friends' items.
- the live-player selector
- bot and Minecraft log controls

The ephemeral panel is visible only to the administrator who opened it and
expires after ten minutes. Callback failures produce a visible error instead of
leaving an apparently dead button.

## Player inspection

`/players` or the dashboard **Players** button builds a dropdown from Paper's
current `list` output. After selecting a player, buttons show:

- **Inventory** — hotbar, normal slots, armour, offhand item, and counts
- **Position** — coordinates and dimension
- **Health/XP** — health, food, experience level, and game mode
- **Effects** — current active-effect data

Names are sourced from the live list and validated again as Java usernames, so
they cannot be turned into arbitrary RCON input.

## Log panel

`/logs` now opens buttons instead of immediately attaching one file. It reads a
bounded tail of the bot log or Paper `latest.log` and supports:

- bot or Minecraft previews
- warning/error-only filtering for each source
- original attachments within the guild's actual Discord limit
- an SSH/SFTP hint when a file is too large

The privileged audit JSONL rotates once at 5 MiB instead of growing forever on
the microSD.

## Security notes

- The bot never needs your Minecraft account — it talks to the server over
  local RCON only.
- Keep `ADMIN_USER_IDS` tight. Anyone in that list can cheat and stop the
  server.
- The systemd unit uses a **narrow sudoers rule** (see `deploy/`) so the bot
  can control only the minecraft service, not run arbitrary root commands.
- Keep RCON on localhost; the bot connects to `127.0.0.1`.

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
