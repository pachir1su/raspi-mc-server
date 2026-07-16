# RaspiMcOps Paper plugin

Release archives include the Java 25 `RaspiMcOps` plugin. On bot startup, the
bundled JAR is validated, copied atomically to
`/mnt/minecraft/live/plugins/raspi-mc-ops.jar`, and Paper is restarted only when
the JAR changed. Source checkouts without a release-built JAR simply skip this
step.

The plugin configuration is generated at
`/mnt/minecraft/live/plugins/RaspiMcOps/config.yml`. These settings do not belong
in `.env`.

## Chat log

`chat-log.enabled: true` writes actual in-game player messages to
`plugins/RaspiMcOps/chat.log`. The listener is event-driven: it does not poll,
does not write when nobody chats, and creates the file only on the first message.
The Discord `/admin` → **Logs** panel can preview or download this file.

## Automatic rescue spawn

`MC_SPAWN_X/Y/Z` remain an optional operator override. When they are blank, the
Discord rescue button calls the plugin's narrow `raspiops rescue` command. The
plugin resolves one exact validated online player name and teleports only that
player to Paper's live primary-world spawn.

## Spawn safe zone

The default safe zone is enabled with a square radius of 16 blocks around the
primary world's current spawn. It blocks non-bypass players from breaking,
placing, interacting, using buckets, attacking entities, moving blocks with
pistons, or causing explosion block damage in the zone. Operators have the
`raspimcops.spawn.bypass` permission.

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

Death Box remains the separate [`plugin/deathbox`](../../plugin/deathbox)
implementation documented in [death-box-design.md](death-box-design.md). Do not
install a second death-container implementation alongside it.

## Build verification

The plugin targets Paper API `26.1.2.build.74-stable`, Java 25, and Gradle 9.1.
The Release workflow runs `clean test jar` before the JAR can enter the
manifest-verified deployment ZIP.
