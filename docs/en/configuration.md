# Server configuration

The server reads `server/server.properties`. This repo ships
`server/server.properties.template` with Pi-friendly, friends-only defaults.
Below are the settings that matter most; the template comments explain each.

## Access control

| Key | Default | Why |
|---|---|---|
| `white-list` | `true` | Only listed players can join. |
| `enforce-whitelist` | `true` | Kicks non-whitelisted players even if added while running. |
| `online-mode` | `true` | Verifies accounts with Mojang (keep on). |
| `max-players` | `6` | Headroom over your 3–4; keep small on a Pi. |
| `op-permission-level` | `4` | Ops get full command access. |
| `enable-command-block` | `false` | Fewer non-op command paths + a little less load. |

## Performance keys (Pi-critical)

| Key | Default | Notes |
|---|---|---|
| `view-distance` | `8` | Biggest single lever. Try `6` if laggy, `10` if smooth. |
| `simulation-distance` | `6` | How far entities/redstone tick. Keep ≤ view-distance. |
| `network-compression-threshold` | `256` | Fine on LAN; lower it only for slow WAN links. |
| `sync-chunk-writes` | `false` | Better throughput on the Pi's storage. |

More in [performance.md](performance.md).

## RCON

RCON lets the Discord bot and CLI send commands to the running server.

```properties
enable-rcon=true
rcon.port=25575
rcon.password=<strong secret — set on the Pi, never commit>
broadcast-rcon-to-ops=false
```

Keep `rcon.port` bound to localhost (the default host the bot uses is
`127.0.0.1`). Do **not** forward `25575` to the internet. See
[remote-access.md](remote-access.md).

## Difficulty & gameplay

`gamemode`, `difficulty`, `pvp`, `hardcore`, `allow-nether` are set to sensible
survival defaults. Change them to taste; restart the server (or use `/restart`)
to apply.

## Applying changes

Most `server.properties` changes require a restart:

```bash
sudo systemctl restart minecraft.service   # or /restart from the Discord bot
```

## Paper-specific tuning

PaperMC adds `config/paper-global.yml`, `config/paper-world-defaults.yml`, and
`spigot.yml` / `bukkit.yml`. The defaults are good; for entity/mob tuning on a
Pi see [performance.md](performance.md).
