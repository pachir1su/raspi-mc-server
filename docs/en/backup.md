# Backups

`scripts/backup.sh` snapshots the world folders (`world`, `world_nether`,
`world_the_end`) into `backups/` as timestamped `.tar.gz` archives, with
rotation so the SD card doesn't fill.

## Safe backups of a running server

If the server is up and RCON is reachable, the script:

1. `save-off` — pauses auto-save so no chunk is written mid-copy.
2. `save-all flush` — flushes everything to disk.
3. Archives the world folders.
4. `save-on` — re-enables auto-save.

If the server is down it just archives the folders directly.

## Run a backup

```bash
./scripts/backup.sh
```

Or from Discord: `/backup` (shows a loading animation, then the result).

## Rotation

Only the newest `BACKUP_KEEP` archives (default **10**) are kept; older ones are
deleted. Override in `.env`:

```dotenv
MC_BACKUP_DIR=/home/pi/raspi-mc-server/backups
BACKUP_KEEP=10
```

On a 32GB SD card, keep an eye on total size — a mature world can be hundreds of
MB per snapshot. Consider backing up to a USB SSD or copying archives off-device
(see below).

## Schedule with cron

Daily at 05:00:

```bash
crontab -e
```

```cron
0 5 * * *  /home/pi/raspi-mc-server/scripts/backup.sh >> /home/pi/mc-backup.log 2>&1
```

## Off-device copies (recommended)

SD cards fail. Copy archives elsewhere periodically, e.g. with `rclone` to cloud
storage or `rsync` to another machine:

```cron
30 5 * * *  rsync -a /home/pi/raspi-mc-server/backups/ backupuser@nas:/backups/mc/
```

## Restore

```bash
sudo systemctl stop minecraft.service
./scripts/restore.sh                       # newest backup
# or: ./scripts/restore.sh backups/world_20260709_050000.tar.gz
sudo systemctl start minecraft.service
```

`restore.sh` refuses to run while the server is up and moves the current world
aside as `world.bak_<timestamp>` before extracting, so a restore is reversible.
