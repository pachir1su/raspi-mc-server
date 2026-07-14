# Troubleshooting

For a Pi with no display, start with the connection and recovery flow in
[headless-setup.md](headless-setup.md#16-troubleshooting-without-a-screen).

## Logs first

```bash
sudo journalctl -u minecraft.service -n 100 --no-pager       # server
sudo journalctl -u mc-discord-bot.service -n 100 --no-pager  # bot
tail -n 100 /mnt/minecraft/live/logs/latest.log              # Minecraft's own log
```

From Discord, `/logs` attaches the bot's current log file.

## Server won't start

| Symptom | Cause | Fix |
|---|---|---|
| `Unsupported class file major version` / Java errors | Wrong Java | Rerun `./deploy/setup_raspberrypi.sh` to install and verify Amazon Corretto Java 25 |
| `Failed to bind to port` | Port 25565 in use | Another server running? `sudo ss -tlnp | grep 25565` |
| Exits immediately, EULA message | EULA not accepted | Confirm `/mnt/minecraft/live/eula.txt` contains `eula=true` (install script does this) |
| `Could not find a Paper build` | Bad `MC_VERSION` | Use a valid version, e.g. `MC_VERSION=1.21.4` |
| Out of memory / killed | Heap too big for 4GB | Lower `MC_MEMORY` (e.g. `2600M`) in `.env` |

## Players can't connect

1. **Discord link approved?** The owner runs `/link list`, then `/link approve`.
2. **Correct endpoint?** Java uses `25565/TCP`; iPhone, Android, and Minecraft
   for Windows use Geyser on `19132/UDP`.
3. **Correct version/account?** Java must match the Paper-supported protocol;
   Bedrock joins through a signed-in Microsoft/Xbox account.
4. **Outside the LAN?** Forward the correct TCP/UDP game port or use a suitable
   VPN/tunnel — see [remote-access.md](remote-access.md).
5. **Firewall?** When ufw is enabled, allow `25565/tcp` and, for Bedrock,
   `19132/udp`.
6. **New Bedrock account?** Follow the first-login procedure in
   [friend-tools.md](friend-tools.md#first-login-for-a-brand-new-bedrock-account).

## Discord bot issues

| Symptom | Cause | Fix |
|---|---|---|
| Commands don't appear | Global sync delay | Set `DISCORD_GUILD_ID` for instant guild sync |
| `Missing required config` at start | `.env` incomplete | Set `DISCORD_TOKEN`, `RCON_PASSWORD`, `ADMIN_USER_IDS` |
| `⛔ not authorised` | Your ID not in allowlist | Add your Discord user ID to `ADMIN_USER_IDS` |
| `/mc` returns RCON error | RCON off/mismatch | `enable-rcon=true`; `RCON_PASSWORD` must match `server.properties` |
| `/start` etc. fail | sudoers rule missing | Re-run `deploy/setup_raspberrypi.sh` |

## RCON connection refused

- `enable-rcon=true` in `server.properties` and the server restarted.
- `rcon.password` (server) == `RCON_PASSWORD` (.env).
- `RCON_HOST=127.0.0.1`, `RCON_PORT` matches `rcon.port` (25575).
- The server is fully started (RCON opens after `Done`).

## Lag / low TPS

See [performance.md](performance.md). Quick wins: lower `simulation-distance`,
move the world to USB 3.0 HDD/SSD storage, ensure the Pi isn't thermally throttling
(`vcgencmd measure_temp`).

## "No space left on device"

- Confirm the HDD is mounted with `findmnt /mnt/minecraft` before deleting
  anything.
- Shorten retention with `/backup configure`, prune old backups, remove
  unneeded restore archives, or move backups off-device.
- Inspect `/mnt/minecraft/live/logs/` and bot logs; use the configured retention
  rather than blindly deleting active files.
