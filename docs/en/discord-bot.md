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
```

## 4. Run

```bash
sudo systemctl enable --now mc-discord-bot.service
sudo journalctl -u mc-discord-bot.service -f
```

Or manually for testing:

```bash
.venv/bin/python -m bot.main
```

## Commands

All commands are **admin-only** (checked against `ADMIN_USER_IDS`).

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
| `/backup` | Back up the world now (rotated). |
| `/logs` | Attach the bot's current log file. |

`/start`, `/stop`, `/restart`, and `/backup` show the loading animation while
they run and then edit the message with the result.

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
