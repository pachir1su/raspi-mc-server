# Setup & first run

This walks you through a fresh Raspberry Pi 4B (4GB) to a running, whitelisted
PaperMC server with the Discord admin bot.

> **No monitor or keyboard?** Start with the complete
> [headless SD-card installation guide](headless-setup.md). It includes every
> Raspberry Pi Imager field, first SSH login from Windows, HDD identification
> and formatting safeguards, router ports, reboot testing, and recovery. Return
> here only when you need the shorter server-software reference.

## 0. Prerequisites

- Raspberry Pi 4B (4GB), **Raspberry Pi OS Lite (64-bit, Debian 13 Trixie)**.
- A 32GB microSD and 500GB external HDD. The OS and bot remain on microSD;
  PaperMC, live worlds, backups, and uploaded maps live on the HDD.
- Network: the Pi on your LAN, and (for friends outside your LAN) either port
  forwarding or a tunnel — see [remote-access.md](remote-access.md).
- Headless operation: configure hostname, user, network, and SSH in Raspberry Pi
  Imager before first boot. Do not rely on the removed Bookworm-era
  `wpa_supplicant.conf` boot-partition workaround.

Update the OS first:

```bash
sudo apt update && sudo apt full-upgrade -y && sudo reboot
```

## 1. Clone and prepare the HDD

```bash
git clone https://github.com/pachir1su/raspi-mc-server.git
cd raspi-mc-server
lsblk -f
```

Identify the **500GB HDD partition exactly**, then format and register it once.
`/dev/sda1` below is only an example; choosing the wrong device destroys that
device's data.

```bash
sudo mkfs.ext4 /dev/sda1       # DESTROYS all existing data on this partition
sudo ./scripts/setup_hdd.sh /dev/sda1
findmnt /mnt/minecraft
```

The script registers its UUID in `/etc/fstab` with `nofail` and creates the data
tree. Do not format a disk containing data; back it up and plan migration first.

## 2. Provision

```bash
./deploy/setup_raspberrypi.sh
```

`setup_raspberrypi.sh` installs Java 21, downloads PaperMC, creates the Python
venv for the bot, installs the systemd units, and adds a **narrow sudoers rule**
so the bot may start/stop only the minecraft service (not general root access).

> To install just the server without the bot/systemd, run
> `MC_VERSION=1.21.4 ./scripts/install_server.sh` instead.

## 3. Set your secrets

Two files hold secrets and are **not** committed:

1. `/mnt/minecraft/live/server.properties` — set a strong `rcon.password`.
2. The tracked placeholder `.env` — replace its values on the Pi:
   - `RCON_PASSWORD` — must match `server.properties`.
   - `DISCORD_TOKEN` — your bot token ([discord-bot.md](discord-bot.md)).
   - `ADMIN_USER_IDS` — **your own Discord user ID** (comma-separated for more).
   - `MC_MEMORY` — leave at `2600M` for a 4GB Pi unless tuning.

Language and Java/Bedrock mode are no longer environment variables. The first
`main.py` run asks for them and stores them in `MC_STATE_DIR/app-settings.json`.
An old `BOT_LANGUAGE` line in `.env` is ignored and may be removed locally.

```bash
nano /mnt/minecraft/live/server.properties   # rcon.password=...
nano .env                        # RCON_PASSWORD / DISCORD_TOKEN / ADMIN_USER_IDS
chmod 600 .env
```

## 4. Enable reboot startup and run the single launcher

```bash
sudo systemctl enable minecraft.service mc-discord-bot.service
.venv/bin/python -m bot.main
```

On the first run, choose Korean or English and then choose Java-only or
Java+Bedrock. For mixed devices, accept Bedrock UDP port `19132` unless your
network requires another port. This one command installs/configures missing
crossplay plugins, starts Paper, and starts every Discord feature. Leave it
running while you use the server. Later boots use systemd and the saved choices.

If you stopped the foreground launcher with Ctrl+C, start its service with:

```bash
sudo systemctl start mc-discord-bot.service
sudo journalctl -u mc-discord-bot.service -f
```

Once Paper reports `Done (…)!`, op **only yourself** with local RCON:

```bash
mcrcon -H 127.0.0.1 -P 25575 -p '<your RCON password>' 'op YourMinecraftName'
```

This is what makes you the only in-game cheater. See
[cheats-and-ops.md](cheats-and-ops.md).

## 5. Let a friend request access

```text
Friend: /link request minecraft_name:<name> edition:<Java or Bedrock>
Owner:  /link approve user:<Discord member>
```

Approval adds the account to the appropriate Java or Floodgate whitelist. The
friend is not made op and can rescue only their own linked player.

## 6. Reopen setup later

```bash
.venv/bin/python -m bot.main --setup
```

Run this interactively, not through systemd. Normal `python -m bot.main` loads
the saved choices without asking again. If `DISCORD_GUILD_ID` is set, slash
commands appear immediately in that server; global sync can take up to ~1 hour.

## 7. Connect

Java uses the server address on `25565/TCP`. iPhone/iPad, Android, and Minecraft
for Windows use the same address on `19132/UDP`, save it once under
**Play → Servers → Add Server**, then tap it on later visits. No friend-side mod
or plugin is required. See [bedrock.md](bedrock.md) and
[remote-access.md](remote-access.md).

## Next

- [configuration.md](configuration.md) — tune `server.properties`.
- [backup.md](backup.md) — schedule automatic backups.
- [performance.md](performance.md) — keep TPS high on the Pi.
- [troubleshooting.md](troubleshooting.md) — when something's off.
