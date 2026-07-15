# Troubleshooting

For a Pi with no display, start with the connection and recovery flow in
[headless-setup.md](headless-setup.md#16-troubleshooting-without-a-screen).

## Logs first

```bash
sudo journalctl -u minecraft.service -n 100 --no-pager       # server
sudo journalctl -u mc-discord-bot.service -n 100 --no-pager  # bot
tail -n 100 /mnt/minecraft/live/logs/latest.log              # Minecraft's own log
```

From Discord, `/admin` → **Logs** previews or attaches the current log file.

## Server won't start

| Symptom | Cause | Fix |
|---|---|---|
| `Unsupported class file major version` / Java errors | Java is older than Paper requires | Rerun `./deploy/setup_raspberrypi.sh` to install and verify Amazon Corretto Java 25. Paper 26.1+ requires Java 25; see [setup](setup.md#java-25-for-paper-261). |
| `Failed to bind to port` | Port 25565 in use | Another server running? `sudo ss -tlnp | grep 25565` |
| Exits immediately, EULA message | EULA not accepted | Confirm `/mnt/minecraft/live/eula.txt` contains `eula=true` (install script does this) |
| `Could not find a STABLE Paper build` | Bad `MC_VERSION`, or that version has only experimental builds | Use a version with a STABLE build, e.g. `MC_VERSION=26.1.2`, or leave `MC_VERSION` unset. |
| Installer v0.1.8 or earlier cannot download Paper | The retired `api.papermc.io/v2` endpoint is no longer supported | Update this repository and use the Fill v3 installer. |
| Out of memory / killed | Heap too big for 4GB | Lower `MC_MEMORY` (e.g. `2600M`) in `.env` |

## Players can't connect

1. **Discord link approved?** The owner opens `/admin` → **Account links**, selects the request, and presses **Approve**.
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
| **Advanced RCON** returns an RCON error | RCON off/mismatch | `enable-rcon=true`; `RCON_PASSWORD` must match `server.properties` |
| Server-control buttons fail | sudoers rule missing | Re-run `deploy/setup_raspberrypi.sh` |
| Bot crash-loops with `The "no new privileges" flag is set` | Old unit had `NoNewPrivileges=true`, which blocks `sudo` (setuid) | Reinstall `deploy/mc-discord-bot.service` (it no longer sets `NoNewPrivileges`; hardening is preserved with `ProtectSystem`/`ProtectHome`/`ReadWritePaths`). See [discord-bot.md](discord-bot.md#security-hardening-and-sudo). |
| Bot restarts every 10s right after install | First setup not completed | Run `.venv/bin/python -m bot.main` once in a terminal. The service now exits `EX_CONFIG` (78) and `RestartPreventExitStatus=78` stops the loop. |
| `raspi-mc-updater.service` shows `failed` at boot | No pending update request | Expected before this fix; update the repo so the updater treats "no request" as success (exit 0). |
| First setup fails with `PermissionError` writing `data/` | The root updater created `data/` first | Fixed: the updater now `chown`s `data/` to the service user; `setup_raspberrypi.sh` also runs `chown -R`. Manually: `sudo chown -R <user>:<user> data/`. |

## RCON connection refused

- `enable-rcon=true` in `server.properties` and the server restarted.
- `rcon.password` (server) == `RCON_PASSWORD` (.env).
- `RCON_HOST=127.0.0.1`, `RCON_PORT` matches `rcon.port` (25575).
- The server is fully started (RCON opens after `Done`).

The bot now distinguishes RCON failures instead of always reporting "offline":

- **🔴 Server offline** — the TCP connection was refused (server stopped/starting).
- **🟠 RCON authentication failed** — the port answered but the password is wrong;
  make `RCON_PASSWORD` (.env) match `rcon.password` (server.properties).
- **🟠 Slow response** — the connection opened but the server did not reply within
  the timeout (`RCON_TIMEOUT`, default 10s); usually mid-startup or overloaded.

Root causes are logged under the `mc.rcon` logger. You can test RCON without the
external `mcrcon` binary (which is not in the Debian repositories):

```bash
.venv/bin/python -m bot.rcon "list"
```

## Raspberry Pi OS / hardware gotchas

### Trixie: Imager settings (SSH, user) are not applied

On the newest Raspberry Pi OS (Trixie), the `cloud-init`-based first boot can
ignore the customisation you set in Raspberry Pi Imager (enable SSH, username,
Wi-Fi), leaving you locked out of a headless Pi.

- **Recommended:** flash **Raspberry Pi OS Bookworm (Legacy, 64-bit)** for this
  project. It is the tested baseline and applies Imager settings reliably.
- **If you must stay on Trixie:** after flashing, mount the boot partition and
  fix cloud-init by hand:
  - Ensure `ssh` (or `ssh.txt`) exists in the boot partition to force SSH on.
  - Edit `user-data` on the boot partition (cloud-init) to set the user,
    `ssh_pwauth`, and `chpasswd`, then reboot. Confirm with
    `sudo cloud-init status --long` on the device once you have console access.

### Pi 4B USB 3.0 + SATA SSD adapter: xHCI controller dies

Some USB 3.0 ↔ SATA adapters (notably certain JMicron/ASMedia bridges) crash the
Pi 4B's xHCI USB controller under load. Symptoms in `dmesg`/journal:

```
xhci_hcd ... WARNING: Host System Error
xhci_hcd ... HC died; cleaning up
```

The drive disappears and the world storage on `/mnt/minecraft` goes read-only or
vanishes. Work around it:

- **Move the SSD to a USB 2.0 port.** It is slower but the controller stays up;
  this alone fixes most cases.
- **Add a powered USB hub.** The adapter may be browning out the 5V rail;
  undervoltage also shows in `/admin` → **Performance** throttle flags.
- **Apply a usb-storage quirk** to disable UAS for the bridge. Find the
  `idVendor:idProduct` with `lsusb`, then add to `/boot/firmware/cmdline.txt`
  (one line): `usb-storage.quirks=VVVV:PPPP:u` and reboot. This forces the slower
  but far more stable BOT transport.

## Lag / low TPS

See [performance.md](performance.md). Quick wins: lower `simulation-distance`,
move the world to USB 3.0 HDD/SSD storage, ensure the Pi isn't thermally throttling
(`vcgencmd measure_temp`).

## "No space left on device"

- Confirm the HDD is mounted with `findmnt /mnt/minecraft` before deleting
  anything.
- Shorten retention with `/admin` → **Backups** → **Policy settings**, press **Prune**, remove
  unneeded restore archives, or move backups off-device.
- Inspect `/mnt/minecraft/live/logs/` and bot logs; use the configured retention
  rather than blindly deleting active files.
