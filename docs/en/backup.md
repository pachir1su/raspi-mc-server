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
- Changes from `/admin` → **Backups** → **Policy settings** persist to `data/backup-settings.json`.
- The shortest permitted interval is 10 minutes.

Open `/admin` → **Backups**. The card shows the current policy; **Automatic
backup** toggles it, and **Policy settings** provides preselected dropdowns for
interval, retention, maximum usage, and minimum free space.

## Backup and restore commands

Open `/admin` → **Backups**, choose an archive from the dropdown, then use
**Back up now**, **Verify**, **Download**, **Prune**, **Restore**, or **Delete**.
Restore and delete require a second confirmation button rather than typed words.

Every backup has a SHA-256 sidecar. **Verify** checks the digest, archive
structure, and `world/level.dat`. Restore requires that verification to pass;
corrupt backups and archives without a checksum are blocked. **Prune**
applies the saved retention policy immediately.

A restore first creates an emergency snapshot, only replaces the world after
Minecraft stops successfully, rolls back a failed directory swap, and starts
the service again. Files above the guild's actual Discord attachment limit must
be downloaded from `/mnt/minecraft/backups` over SSH/SFTP.

## Map uploads and switching

Upload with `/upload world file:<zip>`; the filename becomes the stored name.
Then open `/admin` → **Worlds**, select it, and use **Activate**, **Download**, or
**Delete**. Activation and deletion require a second confirmation button.

An upload must contain exactly one Java Edition world with `level.dat`. The bot
rejects traversal paths, links, device files, archives expanding beyond 100 GiB,
and excessive file counts. Activating a map also snapshots the live world first.

Backup and map dropdowns list actual HDD entries. `/admin` → **Health** checks
RCON, HDD capacity, backup freshness, and scheduler state. **Advanced tools** → **Audit log** displays
privileged creation, deletion, restore, activation, and settings changes stored
in `data/audit.jsonl`.

## Disk failure is different

Keeping the live world and backups on one HDD protects against mistakes and
world corruption, not failure of that HDD. Periodically copy important archives
to another PC, NAS, or cloud destination.
