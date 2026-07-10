# HDD automatic backups, restore, and map management

The live world and large files reside on the 500 GB external HDD mounted at
`/mnt/minecraft`. The bot verifies that this is a real mount point, preventing
an unplugged HDD from silently filling the microSD.

## Storage layout

```text
/mnt/minecraft/
├── live/          # PaperMC and the live world
├── backups/       # .tar.gz backups and SHA-256 sidecars
├── worlds/        # validated uploaded maps
├── uploads/       # temporary download files
├── staging/       # safe extraction and restore workspace
└── quarantine/    # reserved isolation area
```

## Automatic policy

The bot checks the saved policy every minute and backs up every **30 minutes**
by default. A running server is flushed with `save-off`, `save-all flush`,
backup, and `save-on`.

- Keep every backup for the newest 48 hours.
- Then keep the newest backup per day for 30 days.
- Stop at 80% HDD usage or below 30 GB free.
- `/backup configure` persists to `data/backup-settings.json`.
- The shortest permitted interval is 10 minutes.

Inspect and change the policy from Discord:

```text
/backup settings
/backup configure interval_minutes:30 retention_hours:48 daily_retention_days:30
/backup configure max_usage_percent:80 min_free_gb:30
/backup enabled enabled:false
```

## Backup and restore commands

```text
/backup create
/backup list
/backup download name:<filename>
/backup restore name:<filename> confirm:RESTORE
/backup delete name:<filename> confirm:DELETE
```

A restore first creates an emergency snapshot, only replaces the world after
Minecraft stops successfully, rolls back a failed directory swap, and starts
the service again. Files above the guild's actual Discord attachment limit must
be downloaded from `/mnt/minecraft/backups` over SSH/SFTP.

## Map uploads and switching

```text
/world upload name:<stored-name> file:<zip/tar.gz/tgz>
/world list
/world activate name:<stored-name> confirm:ACTIVATE
/world download name:<stored-name>
/world delete name:<stored-name> confirm:DELETE
```

An upload must contain exactly one Java Edition world with `level.dat`. The bot
rejects traversal paths, links, device files, archives expanding beyond 100 GiB,
and excessive file counts. Activating a map also snapshots the live world first.

## Disk failure is different

Keeping the live world and backups on one HDD protects against mistakes and
world corruption, not failure of that HDD. Periodically copy important archives
to another PC, NAS, or cloud destination.
