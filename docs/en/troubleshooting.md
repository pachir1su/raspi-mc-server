# Troubleshooting

## Logs first

```bash
sudo journalctl -u minecraft.service -n 100 --no-pager       # server
sudo journalctl -u mc-discord-bot.service -n 100 --no-pager  # bot
tail -n 100 server/logs/latest.log                           # Minecraft's own log
```

From Discord, `/logs` attaches the bot's current log file.

## Server won't start

| Symptom | Cause | Fix |
|---|---|---|
| `Unsupported class file major version` / Java errors | Wrong Java | Install JDK 21: `sudo apt install openjdk-21-jre-headless` |
| `Failed to bind to port` | Port 25565 in use | Another server running? `sudo ss -tlnp | grep 25565` |
| Exits immediately, EULA message | EULA not accepted | `echo eula=true > server/eula.txt` (install script does this) |
| `Could not find a Paper build` | Bad `MC_VERSION` | Use a valid version, e.g. `MC_VERSION=1.21.4` |
| Out of memory / killed | Heap too big for 4GB | Lower `MC_MEMORY` (e.g. `2600M`) in `.env` |

## Players can't connect

1. **Whitelisted?** `whitelist add <name>` (names are case-sensitive; use the
   exact account name).
2. **Right edition/version?** They need **Java Edition** matching the server
   version.
3. **On your LAN?** Connect to the Pi's LAN IP `:25565`. Outside the LAN needs
   port forwarding or a VPN/tunnel — see [remote-access.md](remote-access.md).
4. **Firewall?** `sudo ufw allow 25565/tcp` if ufw is on.

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

- Shorten retention with `/backup configure`, prune old backups, or
  restores, clear `server/logs/` and `bot/logs/` (retention handles this over
  time), or move backups off-device.
