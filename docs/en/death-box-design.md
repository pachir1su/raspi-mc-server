# Death Box design (Paper plugin follow-up)

Death Box is intentionally **not implemented through the Discord RCON bot**.
RCON can react only after death messages reach the log, by which time dropped
items may already have burned, exploded, or despawned. It also cannot safely
reconstruct item metadata, nested containers, enchantments, or ownership.

## Recommended implementation

Build a small Paper plugin as a separate follow-up change. A datapack is possible
for a simpler server, but a plugin is the reliable choice for exact inventories,
ownership, protected access, recovery after restart, and version-aware tests.

The plugin should be event-driven:

1. Listen to Paper's player-death event at normal priority and ignore cancelled or
   `keepInventory` deaths.
2. Copy the event's complete item stacks in memory, including armor and offhand.
3. Clear only the captured event drops so items never exist as vulnerable ground
   entities.
4. Find a safe container position using a small bounded search around the death
   block. Never scan a whole chunk or world.
5. Create a double chest or another 54-slot container and write the captured
   stacks. If no safe block exists (void, lava, protected region, or full area),
   retain a plugin-owned virtual inventory and notify the player instead of
   deleting items.
6. Tag the container with the dead player's UUID and a unique box ID using Paper's
   persistent data APIs. Display the coordinates to that player only.
7. Remove the metadata record when the box becomes empty. Optional expiry should
   be owner-configurable and default to disabled.

This performs work only on death, container access, and bounded cleanup. It does
not poll RCON, parse logs, scan entities, or keep chunks loaded.

## Ownership and safety rules

- Default access: the dead player and `ADMIN_USER_IDS`-equivalent Minecraft
  operators only. An optional `friends-can-open` setting may loosen this.
- Never run arbitrary commands supplied by Discord users.
- Preserve exact `ItemStack` metadata; do not serialize items as command strings.
- Detect an existing block, protected region, world border, and unloaded/unsafe
  destination before placing a container.
- Define compatibility with `keepInventory`, gravestone plugins, claim plugins,
  and death-drop modifiers. If another gravestone plugin is active, disable this
  plugin rather than duplicating items.
- Write metadata atomically. On startup, reconcile only known box records; never
  scan every loaded chunk.

## Suggested configuration

```yaml
enabled: true
container: double-chest
search-radius: 4
expire-hours: 0        # 0 means never expire
friends-can-open: false
fallback-virtual-box: true
```

These settings belong to the Paper plugin's own configuration, not `.env` and not
the Discord bot.

## Suggested commands

| Command | Access | Purpose |
|---|---|---|
| `/deathbox locate` | box owner | Show the player's newest box coordinates. |
| `/deathbox list` | box owner | List that player's active boxes. |
| `/deathbox recover <id>` | admin | Recover a virtual fallback box after inspection. |
| `/deathbox purge <id>` | admin | Delete a box only after explicit confirmation. |

Discord may later expose **read-only** box locations returned by a narrow plugin
API. Creation, inventory capture, recovery, and deletion must remain inside Paper.

## Verification required for the follow-up

- Normal inventory, armor, offhand, enchanted items, bundles, and shulker boxes.
- Lava, void, explosion, cramped cave, water, world border, and protected regions.
- More than 27 occupied slots and completely full inventories.
- Restart immediately after death and restart while a box is open.
- Simultaneous deaths, repeated deaths, and two boxes at the same coordinates.
- `keepInventory=true`, another death plugin, hopper access, explosions, and
  unauthorized players.
- Paper timings/profile comparison confirming no idle tick or chunk-load overhead.

Implement and release this as its own plugin-focused PR after selecting the exact
Paper version and region-protection compatibility requirements.
