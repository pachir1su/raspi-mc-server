# Death Box (Paper plugin)

Death Box stores a player's dropped items in a protected, owner-only chest on
death, instead of leaving them to burn, explode, or despawn. It is implemented
as a small **Paper plugin** under [`plugin/deathbox`](../../plugin/deathbox),
**not** through the Discord RCON bot: RCON can only react after death messages
reach the log, by which time dropped items may already be gone, and it cannot
safely reconstruct item metadata, nested containers, enchantments, or ownership.

## How it works

The plugin is event-driven and does work only on death, on container access, and
on a light hourly expiry sweep. It never polls RCON, parses logs, scans
entities, or keeps chunks loaded.

1. It listens to the player-death event at **normal** priority and ignores
   `keepInventory` or empty-drop deaths, so gravestone-style plugins at a higher
   priority win.
2. It copies the event's complete item stacks in memory (inventory, armor, and
   offhand are all part of the death drops).
3. It clears the captured drops so items never exist as vulnerable ground
   entities.
4. It runs a small **bounded** search around the death block (default radius 4,
   hard-capped at 8) for a safe spot — never a whole chunk or world.
5. It places a double chest (54 slots, enough for a completely full inventory)
   and writes the captured stacks. Placement is verified at runtime to confirm
   the two halves actually merged. If no safe block exists (void, lava, world
   border, or a full area), it keeps the items in a plugin-owned **virtual box**
   and tells the player instead of deleting them.
6. It tags the container's block(s) with the dead player's UUID and a unique box
   ID using Paper's persistent data API, and shows the coordinates to that
   player only.
7. It removes the record when the box becomes empty (detected on close). An
   optional expiry is owner-configurable and defaults to disabled.

Physical boxes carry their owner/id tag on the block itself (so access checks
survive restarts without any index), and a small atomically-written
`boxes.yml` index lets `/deathbox list|locate` answer queries and holds virtual
boxes — all without scanning the world. On startup only known records are
loaded; no chunk is force-loaded.

## Ownership and safety

- Default access: the dead player and operators (`deathbox.admin`) only. When
  `friends-can-open` is enabled, players with the `deathbox.friend` permission
  may also open boxes.
- Boxes are protected from unauthorized opening, hopper siphoning, explosions,
  piston moves, and manual breaking. To retrieve items, the owner opens the box
  and empties it; the box then removes itself.
- Item metadata is preserved exactly — stacks are stored as real `ItemStack`s
  (virtual boxes use Bukkit object serialization), never as command strings.
- Placement respects the world border, world height limits, existing blocks, and
  liquids. If another gravestone plugin is detected (Graves, GravesX, AngelChest,
  DeadChest, SavageDeathChest, and similar), DeathBox disables itself on startup
  rather than duplicating items.

> Region/claim plugins: DeathBox does not place inside occupied blocks, but it
> does not yet integrate with WorldGuard/GriefPrevention claim checks. If you run
> a claim plugin, verify placement behaviour before relying on it (see the
> checklist below), or keep `search-radius` small.

## Build

Requires JDK 21 and Maven. The PaperMC Maven repository must be reachable.

```bash
cd plugin/deathbox
mvn -B package
# → target/DeathBox-1.0.0.jar
```

Set `<paper.api.version>` in `plugin/deathbox/pom.xml` to match the Paper version
you run on the Pi. CI also builds the plugin on every change under
`plugin/deathbox/` via `.github/workflows/plugin-build.yml`.

## Install

Release ZIPs bundle the plugin as `bundled-plugins/DeathBox.jar`, and the bot
validates and installs it into the server's `plugins/` directory on startup,
exactly like `RaspiMcOps`. Manual installation is only needed for source
checkouts without a release build:

1. Copy `target/DeathBox-1.0.0.jar` into the server's `plugins/` directory.
2. Start (or restart) the server once to generate `plugins/DeathBox/config.yml`.
3. Edit the config if needed, then restart.

## Configuration

`plugins/DeathBox/config.yml` (these settings belong to the plugin, not the
bot's `.env` and not `server.properties`):

```yaml
enabled: true
container: double-chest          # double-chest | chest | barrel
search-radius: 4                 # bounded; clamped to 1..8
expire-hours: 72                 # 0 means never expire (default 72h)
max-physical-boxes-per-player: 3 # anti-grief cap; 0 disables
friends-can-open: false
fallback-virtual-box: true
messages:                        # player-facing text (Korean defaults)
  death.stored: "§6[데스박스] §f아이템을 §e{x}, {y}, {z} ..."
  # Omitted keys fall back to the built-in Korean default.
```

All player-facing text defaults to Korean (#60). Override any key under
`messages:` to reword or translate it; keep the `{brace}` placeholders and
`§` colour codes. Omitted keys use the built-in default.

### Anti-grief (#65)

To stop one player from repeatedly dying at someone else's door and stacking
unbreakable chests:

- `max-physical-boxes-per-player` caps active **physical (block)** boxes per
  player (default 3). Beyond the cap, deaths are stored in a **virtual** box
  (no block placed) that an admin recovers with `/deathbox recover`, so blocks
  never pile up without bound.
- `expire-hours` defaults to 72h so old boxes are swept hourly.
- Emptied boxes already auto-remove the moment they are opened and cleared.

## Commands

| Command | Access | Purpose |
|---|---|---|
| `/deathbox locate` | box owner | Show the player's newest box coordinates. |
| `/deathbox list` | box owner | List that player's active boxes. |
| `/deathbox locate <player>` | admin / console | Look up another player's newest box. |
| `/deathbox list <player>` | admin / console | List another player's active boxes. |
| `/deathbox recover <id>` | admin | Recover a virtual fallback box into your inventory. |
| `/deathbox purge <id> confirm` | admin | Delete a box after explicit confirmation. |

Permissions: `deathbox.use` (default: all), `deathbox.friend` (default: none),
`deathbox.admin` (default: op). The Discord `/tools` panel exposes
**Locate death box** and **List death boxes** buttons that call the console
form (`deathbox locate/list <player>`) via RCON.

## Verification checklist (run on a real server)

Static review and CI compilation do not exercise gameplay. Before trusting the
plugin on the live Pi, verify:

- Normal inventory, armor, offhand, enchanted items, bundles, and shulker boxes.
- Lava, void, explosion, cramped cave, water, world border, and protected regions.
- More than 27 occupied slots and completely full inventories.
- Restart immediately after death and restart while a box is open.
- Simultaneous deaths, repeated deaths, and two boxes at the same coordinates.
- `keepInventory=true`, another death plugin, hopper access, explosions, and
  unauthorized players.
- Paper timings/profile comparison confirming no idle tick or chunk-load overhead.
