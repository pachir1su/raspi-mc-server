# Setup & first run

This walks you through a fresh Raspberry Pi 4B (4GB) to a running, whitelisted
PaperMC server with the Discord admin bot.

## 0. Prerequisites

- Raspberry Pi 4B (4GB), **64-bit Raspberry Pi OS** (Bookworm recommended).
- A 32GB microSD and 500GB external HDD. The OS and bot remain on microSD;
  PaperMC, live worlds, backups, and uploaded maps live on the HDD.
- Network: the Pi on your LAN, and (for friends outside your LAN) either port
  forwarding or a tunnel — see [remote-access.md](remote-access.md).

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

```bash
nano /mnt/minecraft/live/server.properties   # rcon.password=...
nano .env                        # RCON_PASSWORD / DISCORD_TOKEN / ADMIN_USER_IDS
chmod 600 .env
```

## 4. First start & op yourself

```bash
sudo systemctl enable --now minecraft.service
sudo journalctl -u minecraft.service -f   # watch it boot; Ctrl+C to stop watching
```

Once you see `Done (…)! For help, type "help"`, op **only yourself**. From the
console (or the Discord `/mc` command once the bot is up):

```
op YourMinecraftName
```

This is what makes you the only in-game cheater. See
[cheats-and-ops.md](cheats-and-ops.md).

## 5. Whitelist your friends

```
whitelist add Friend1
whitelist add Friend2
```

Whitelist is already **on** in the template, so only listed players can join.

## 6. Start the Discord bot

```bash
sudo systemctl enable --now mc-discord-bot.service
sudo journalctl -u mc-discord-bot.service -f
```

The bot registers slash commands. If you set `DISCORD_GUILD_ID`, they appear
instantly in that server; otherwise global sync can take up to ~1 hour.

## 7. Connect

Players use **Java Edition** and connect to your Pi's LAN IP (e.g.
`192.168.0.42`) on the default port `25565`. For friends outside your network,
set up [remote-access.md](remote-access.md).

## Next

- [configuration.md](configuration.md) — tune `server.properties`.
- [backup.md](backup.md) — schedule automatic backups.
- [performance.md](performance.md) — keep TPS high on the Pi.
- [troubleshooting.md](troubleshooting.md) — when something's off.
