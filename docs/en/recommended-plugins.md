# Recommended plugins (optional)

This page lists **third-party** Paper plugins that add fun to the friends-only
survival server (Raspberry Pi 4B, 3–4 players). Unlike the bundled `RaspiMcOps`
and `DeathBox`, these are downloaded from their own distributors and installed
manually.

> ⚠️ **Version compatibility**: this server runs Paper 26.1.x. The published
> compatibility lists for these plugins do not always name the latest Minecraft
> version, so **verify on a staging server (or after a backup) first** before
> putting them on the live server. Lootin in particular has been seen to list
> confirmed compatibility only up to older builds, so 26.1.x must be checked
> beforehand.

## How to install

Download URLs change with every plugin release, so they are not stored in the
repo. Copy the **direct download URL of the latest Paper 26.1.x JAR** from the
distributor (Modrinth, Hangar, SpigotMC, …), then use the safe install helper
to drop it into the server's `plugins/` directory:

```bash
# URL only — the filename is inferred.
./scripts/install_plugin.sh "<download-url>"

# You can also pin the filename and a checksum (recommended).
./scripts/install_plugin.sh "<download-url>" Lootin.jar --sha256 <hash-from-distributor>
```

The script downloads, optionally verifies the checksum, confirms the file is a
valid JAR containing a plugin.yml, then atomically moves it into `plugins/`.
Re-running overwrites the same file (safe for updates). **Restart the server**
after installing so the plugin loads.

Manual install works too: copy the JAR into `server/plugins/` (the HDD
`plugins/` on the live server) and restart.

## Priority

| Rank | Plugin | Purpose | Pi load |
|---|---|---|---|
| 1 | **Lootin** or **JustLootIt** | Per-player structure-chest loot | Low |
| 2 | **AuraSkills** | Vanilla-based skill progression (RPG feel) | Low |
| 3 | **Chunky** | Pre-generate chunks to reduce exploration lag | High while running |

## 1. Lootin / JustLootIt — per-player loot (priority)

When you find a structure with a friend, a normal server gives everything to
whoever opens the chest first. This family of plugins lets **each player open a
dungeon chest once**, so:

- Your loot remains even if a friend raided the fortress first.
- Great for desert temples, mineshafts, ancient cities, and end cities.
- Fewer fights over chests.

Lootin separates structure-chest loot per player UUID. JustLootIt is an
equivalent alternative. **Strongly recommended** for its low load-to-fun ratio,
but verify on a staging server for 26.1.x per the compatibility note above.

## 2. AuraSkills — an easygoing progression system

Adds skill progression to your existing survival world: mining, foraging,
farming, fishing, fighting, archery, agility, defence, magic-family stats, and
health/strength/luck stats. It does **not** add lots of new blocks or mobs —
XP comes from **vanilla actions**, and Bedrock (crossplay) players can take part
too. Installing it midway into an existing world is low-impact.

**Recommended Pi 4B settings** (defaults can feel a bit fast):

- Overall XP multiplier: **0.6 – 0.8**
- Max level: default or **50**
- Combat skill bonus damage: light
- Health increase: **50%** of default
- Skill message / action-bar update frequency: **low** (less Pi load and chat spam)

## 3. Chunky — reduce exploration lag (later)

Pre-generates chunks in a given area so real-time generation does not stutter
during exploration. Especially useful if you add random teleport or world
generation features.

**Recommended Pi 4B ranges and operation**:

- Overworld radius: **3,000 blocks**
- Nether radius: **1,000 blocks**
- End: leave at default
- Run **when no players are online**
- Run **one world at a time**
- **Do not** run a full squaremap render at the same time (both hammer the disk)

Chunky does almost nothing while idle, but generation is CPU- and disk-heavy, so
follow the operating rules above.

## Post-install checklist (on the live server)

- [ ] Plugins load without errors in the startup log (`/plugins` or console).
- [ ] Lootin/JustLootIt: two accounts each open the same structure chest and get
      separate loot.
- [ ] AuraSkills: mining/foraging raise XP and the multiplier is not excessive.
- [ ] AuraSkills: Bedrock (crossplay) friends also gain skills.
- [ ] Chunky: generation runs one world at a time while empty and never overlaps
      a squaremap render.
- [ ] Monitor TPS, CPU temperature, and HDD free space via the `/admin`
      performance card during generation.

## References

- Related issue: [#47](https://github.com/pachir1su/raspi-mc-server/issues/47)
- Bundled plugins (auto-installed): [paper-ops-plugin.md](paper-ops-plugin.md),
  [death-box-design.md](death-box-design.md)
- Performance and tuning: [performance.md](performance.md)
