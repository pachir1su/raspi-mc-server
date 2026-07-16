# RaspiMcOps Paper plugin

Release archives include the Java 25 `RaspiMcOps` plugin (and the `DeathBox`
plugin — see [death-box-design.md](death-box-design.md)). On bot startup, each
bundled JAR is validated, copied atomically to
`/mnt/minecraft/live/plugins/`, and Paper is restarted only when a JAR
changed. Source checkouts without release-built JARs simply skip this step.

The plugin configuration is generated at
`/mnt/minecraft/live/plugins/RaspiMcOps/config.yml`. These settings do not belong
in `.env`.

## Chat log

`chat-log.enabled: true` writes actual in-game player messages to
`plugins/RaspiMcOps/chat.log`. The listener is event-driven: it does not poll,
does not write when nobody chats, and creates the file only on the first message.
The Discord `/admin` → **Logs** panel can preview or download this file.

## Automatic rescue spawn

The Discord rescue button always calls the plugin's narrow `raspiops rescue`
command. The plugin resolves one exact validated online player name and
teleports only that player to Paper's live primary-world spawn. The spawn point
itself is moved via `/admin` → **Quick commands** → **Set spawn**, and always
matches the on-death respawn location. (The old `MC_SPAWN_X/Y/Z` coordinate
override was removed because it let the two locations drift apart.)

## Spawn safe zone

The default safe zone is enabled with a square radius of 16 blocks around the
primary world's current spawn. It blocks non-bypass players from breaking,
placing, interacting, using buckets, attacking entities, moving blocks with
pistons, or causing explosion block damage in the zone. Operators have the
`raspimcops.spawn.bypass` permission.

Death boxes placed by the DeathBox plugin are the one exception: opening them
stays allowed inside the zone, so a player who dies at spawn can still retrieve
their items. DeathBox itself keeps the box owner-only.

Use the private `/admin` → **Spawn protection** button or the console command:

```text
spawnprotection status
spawnprotection on
spawnprotection off
spawnprotection toggle
```

The toggle is persisted in the plugin configuration. Change
`spawn-protection.radius` or `spawn-protection.world` in `config.yml` while the
server is stopped, then start Paper again.

## Container locks

`chest-lock.enabled: true` records who places each chest, trapped chest,
barrel, or shulker box, and blocks everyone else from opening or breaking it.
Placing a chest directly against someone else's locked chest is also refused so
a double chest cannot expose foreign items. Operators bypass locks with the
`raspimcops.chestlock.bypass` permission. Hopper item transfer is not blocked;
keep valuables in barrels or shulker boxes if that matters.

Use the private `/admin` → **Chest lock** button or the console command:

```text
chestlock status
chestlock on
chestlock off
chestlock toggle
```

The toggle is persisted in the plugin configuration. Turning the feature off
keeps recorded owners, so locks resume when it is turned back on.

## Force enchant (#62)

Vanilla `/enchant` refuses e.g. Sharpness on a pickaxe and caps levels, but
`enchantheld` applies an enchantment to the held item **ignoring compatibility
and the max level** (`ItemStack.addUnsafeEnchantment`). It is an owner cheat, so
it needs the `raspimcops.enchant` permission (default op).

```text
enchantheld <exact-player-name> <enchant-id> <level>
e.g. enchantheld QUI203 sharpness 20
```

Levels are clamped to 1..255. In Discord the `/admin` → **Players** →
**Enchant** dropdown's **강제 인챈트 (제한 없음)…** entry calls this command.

Death Box remains the separate [`plugin/deathbox`](../../plugin/deathbox)
implementation documented in [death-box-design.md](death-box-design.md). Do not
install a second death-container implementation alongside it.

## Build verification

The plugin targets Paper API `26.1.2.build.74-stable`, Java 25, and Gradle 9.1.
The Release workflow runs `clean test jar` before the JAR can enter the
manifest-verified deployment ZIP.
