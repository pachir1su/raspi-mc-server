# Server-specific features

<img src="../assets/player-guides/openmoji/server-features.svg" alt="Desktop computer icon" width="96">

This is a player-facing index of features unique to this server. Follow the
linked operator docs for configuration details. Discord may display commands as
`/server` or their Korean localized names based on each user's app language.

## First connection

1. The owner opens Discord `/admin` → **Friend accounts** and selects the friend.
2. The owner adds the exact Java name or Bedrock/Xbox gamertag. One Discord user
   can have multiple Minecraft profiles.
3. The bot updates the appropriate Java or Floodgate whitelist.
4. The friend opens `/server` for address, version, online players, and days
   played, then joins.

Account changes mutate server access and remain admin-only. Friends cannot enter
arbitrary Minecraft targets, coordinates, or RCON strings to move someone else.

## Public commands

| Command | Audience | Purpose |
|---|---|---|
| `/server` | Discord server members | Address, version, players, days played, refresh |
| `/tools` | Assigned friends and admins | Profiles, rescue/location, places, diary, Death Boxes, server score |
| `/help` | Discord server members | Friend-safe help with admin capabilities hidden |
| `/upload place-photo` | Assigned friends and admins | Attach or replace a place photo |
| `/upload diary` | Assigned friends and admins | Create a diary entry with a photo |

Panels containing account, coordinate, or administration data use ephemeral
responses visible only to the caller.

## My profiles and rescue

Choose a profile assigned by an administrator in `/tools` first.

- **Profile list:** shows assigned Java/Bedrock profiles and current selection.
- **Selected profile location:** while online, reads the current dimension and XYZ.
- **Selected profile spawn rescue:** while online, moves only that profile to the
  server's actual world spawn. No target or destination can be entered.

Rescue calls the narrow `raspiops rescue` plugin command. It does not grant
friends op or general teleport permission.

## Coordinate book

- Reads an assigned online profile's current position and stores it with a short
  name and optional note.
- Preserves Overworld/Nether/End and XYZ, plus a link when an external web map is configured.
- Accepts PNG/JPEG/WebP/GIF images up to 5 MiB. The bot stores one local HDD copy
  rather than relying on an expiring Discord URL.
- Friends delete only their own entries; administrators can manage all entries.
- The collection is capped at 250 places to bound Pi file reads and menu size.

Save mine entrances, Nether portals, villages, farms, and trial chambers before
an accident makes the route hard to recover.

## Server diary

- View recent entries and write from `/tools` → **Server diary**.
- Use the panel/modal for text-only posts and `/upload diary` for a photo.
- Rescue and coordinate saves also create event entries.
- The append-only JSONL trims to the newest 1,000 records after reaching 2 MiB.

Write only adventure notes suitable for the group. Discord IDs, profiles,
photos, and text stay on the operational HDD rather than public Git, but the
server owner can access them.

## Death Box

On an ordinary death with `keepInventory` off and nonempty drops, the Death Box
plugin stores item stacks in a protected container instead of ground entities.

- Only the dead player and administrators can open it by default.
- Explosion, piston, hopper, unauthorized break, and unauthorized open are blocked.
- If no physical placement is safe, items remain in a virtual box.
- **Locate/List Death Boxes** in `/tools` query boxes for the selected assigned profile.
- Emptying a physical box removes its record and container.

No box is created under `keepInventory=true`. See [Death Box design](death-box-design.md)
for operator settings and recovery commands.

## Spawn protection and chest locking

- **Spawn protection:** by default, blocks ordinary build/break/interact, buckets,
  entity attacks, pistons, and explosion block damage in a 16-block square radius
  around the main-world spawn. Operators bypass it.
- **Chest locking:** records the placer of chests, trapped chests, barrels, and
  Shulker Boxes and blocks other players from opening or breaking them. It is not
  land protection and does not block hopper movement; check automation carefully.
- A player's Death Box remains recoverable inside spawn through an explicit
  compatibility exception.

Admins can toggle both from Discord and their state survives restarts. See the
[Paper operations plugin](paper-ops-plugin.md).

## Server score and performance

`/tools` → **Server score** measures these only when pressed and reports a 0–100
score with every deduction:

- Paper TPS and RCON response
- Raspberry Pi CPU temperature and five-minute load
- Memory use
- HDD free space and required mount
- Undervoltage/throttling flags

It does not add a world scan or background polling loop. If the score drops,
check automation and loose item buildup first, then notify the owner.

## Administrator-only features

`/admin` is restricted to `ADMIN_USER_IDS` and provides an ephemeral button panel for:

- service start/stop/restart and status diagnostics;
- online inventory, location, health, and effect inspection;
- bounded item/effect/enchantment/gamemode/TP/XP/heal/kick actions;
- backup create, verify, download, restore, prune, and world switching;
- time, weather, difficulty, game rules, spawn, and dropped-item cleanup;
- friend profiles and Java/Bedrock whitelists;
- updates, logs, storage, performance, spawn protection, and chest locking.

Risky stop, restart, restore, delete, update, kick, and dropped-item cleanup
actions require a second confirmation and write an audit record. See the
[Discord bot guide](discord-bot.md) and [operator runbook](operator-runbook.md).

## Data and privacy

Profiles, coordinates, diary entries, and photos live under
`/mnt/minecraft/bot-state` by default. Treat them like the private world and
never commit them to Git. Do not put home addresses, phone numbers, tokens, or
other real-world secrets in shared places or diary text.

## Related docs

- [Friend-tool setup and troubleshooting](friend-tools.md)
- [Discord administration bot](discord-bot.md)
- [Backup and restore](backup.md)
- [Death Box design](death-box-design.md)
- [Paper operations plugin](paper-ops-plugin.md)
- [Java+Bedrock connection](bedrock.md)
