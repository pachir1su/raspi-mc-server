# Server owner operations runbook

Use this checklist for the Raspberry Pi 4B + 32GB microSD + 500GB USB HDD
deployment. Prefer Discord `/panel`; use SSH when Discord or the bot is down.

For initial imaging, Wi-Fi/SSH setup, and finding the Pi without a display, see
[headless-setup.md](headless-setup.md).

## Reach a headless Pi

From Windows PowerShell on the same LAN:

```powershell
ssh mcadmin@mc-pi.local
```

If mDNS does not resolve, use the router's connected-device list and connect to
the reserved IP. Guest Wi-Fi commonly blocks device-to-device traffic. Keep a
DHCP reservation for the Pi so port forwarding and emergency SSH do not move.

## Daily check

Open `/panel` and verify server status, HDD free space, backup freshness, and the
**Performance** card for TPS, CPU temperature, memory, and power flags.

| Metric | Healthy | Investigate |
|---|---|---|
| TPS | 19-20 | repeatedly below 18 |
| CPU temperature | below 70°C | 80°C or above |
| Memory | below 85% | sustained above 90% |
| HDD | at least 30GB free | below configured reserve |
| Power/throttle | `normal` | current undervoltage/throttling |

Get the same summary over SSH:

```bash
cd ~/raspi-mc-server
./scripts/health_check.sh
```

## Start, stop, and restart

- Normal path: `/panel` → **Server controls**.
- Stop and restart require a second confirmation click.
- If Discord is unavailable:

```bash
sudo systemctl status minecraft.service mc-discord-bot.service
sudo systemctl restart minecraft.service
sudo systemctl restart mc-discord-bot.service
```

The stop button attempts `save-all flush` first. After forced shutdown or power
loss, inspect logs and backup integrity before regular play resumes.

## Safe physical shutdown

Never remove Pi or HDD power while Paper is running. When the device must be
unplugged, use SSH:

```bash
sudo systemctl stop mc-discord-bot.service
sudo systemctl stop minecraft.service
sudo poweroff
```

Wait until SSH closes and activity LEDs stop before disconnecting power. Power
the HDD enclosure before the Pi at startup, and power the Pi down before
disconnecting the HDD.

## Player support

Use `/players` to select a connected player and inspect inventory,
position/dimension, health/food/XP, or effects. Inspection is read-only. RCON
cannot inspect an offline player's live entity data.

## Log triage order

1. `/logs` → **Minecraft errors**.
2. Use **Bot errors** for failed Discord commands.
3. Open the full preview for context.
4. Download the original when needed.
5. Use SSH when a file exceeds Discord's limit.

```bash
sudo journalctl -u minecraft.service -n 200 --no-pager
sudo journalctl -u mc-discord-bot.service -n 200 --no-pager
tail -n 200 /mnt/minecraft/live/logs/latest.log
```

## When the HDD disappears

Symptoms include `/storage` failure, systemd start failure, or a mount error in
`/health`.

```bash
lsblk -f
findmnt /mnt/minecraft
sudo journalctl -b -u mnt-minecraft.mount --no-pager
sudo mount /mnt/minecraft
```

Check USB power and cabling, confirm the expected UUID, and do not edit fstab
merely because `/dev/sdX` changed. Verify `/mnt/minecraft/live` before starting
services. Never create data under an unmounted `/mnt/minecraft`; that writes to
the empty mount directory on microSD.

## Undervoltage or throttling

Inspect `/metrics` or run:

```bash
vcgencmd get_throttled
vcgencmd measure_temp
```

- **Current undervoltage:** inspect PSU, cable, and HDD power immediately.
- **Historical undervoltage:** watch for recurrence; history bits can remain set.
- **Current thermal throttling:** inspect fan, heatsink, airflow, and room temperature.

## Backup and restore

Before restore, run `/backup verify`, copy an important archive off the HDD,
notify connected players, then run `/backup restore`. Restore makes another
emergency snapshot, but same-disk backups do not protect against HDD failure.

## Safe update procedure

Normally run `/update check`, press **Install update**, and inspect `/update
status` after the bot restarts. `/update upload` accepts an official deployment
ZIP already on your device; source-code ZIPs have no manifest and are rejected.
Paper keeps running, while `.env` and operational data remain untouched.

Use the manual procedure only for the first updater installation or when the
bot is unavailable.

```bash
cd ~/raspi-mc-server
git status --short
git fetch origin
git switch main
git pull --ff-only
.venv/bin/pip install -r requirements.txt
sudo ./deploy/setup_raspberrypi.sh
sudo systemctl restart mc-discord-bot.service
./scripts/health_check.sh
```

Back up unexpected local changes instead of overwriting them. After updating,
exercise `/panel`, `/metrics`, and `/logs`. Application updates do not modify
the world, so they avoid a routine world backup that would add HDD I/O and TPS
pressure.

## Keep these off-device

- several recent verified world backups
- real `.env` values in a private secret store
- `/mnt/minecraft/live/server.properties`
- Discord application recovery information

Never commit real tokens, RCON passwords, or world data.
