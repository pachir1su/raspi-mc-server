# Cheats & operators — "only I can cheat"

## The key idea

Singleplayer Minecraft has an **Allow Cheats** toggle per world. Multiplayer
servers **do not**. On a server, the ability to run cheat commands
(`/gamemode`, `/give`, `/time set`, `/tp`, …) is controlled by whether you are
an **operator (op)**:

- **Not an op** → you cannot run cheat commands at all.
- **An op** → you can, up to `op-permission-level` (4 = everything).

So "cheats off for the map, only I can cheat" is achieved by a simple rule:

> **Op only yourself. Never op anyone else.**

Your friends play normal survival with no command access. You keep full control.

## How to op yourself (and only yourself)

From the server console or Discord `/admin` → **In-game command** (on the dashboard or under **Advanced tools**):

```
op YourMinecraftName
```

Verify no one else is an op — `server/ops.json` should have exactly one entry
(you). An example is in `server/ops.json.example`.

To remove an accidental op:

```
deop SomeoneElse
```

## Why you can still cheat remotely

The **console, RCON, the Discord bot, and SSH sessions** all execute commands
at **op level 4** regardless of the ops list. That's why:

- Discord **In-game command** runs any command through RCON.
- `.venv/bin/python -m bot.rcon` from SSH runs any command using `.env`.

Because those channels are gated to **you** (admin allowlist / SSH access /
being at the console), they are effectively *your* private cheat console — even
though in-game you could also just be op.

## Command block & function levels

- `enable-command-block=false` (template default) removes another way for
  non-ops to trigger commands and shaves a little load. Turn it on only if your
  builds need command blocks — command blocks run at `op-permission-level`.
- `function-permission-level=2` limits what datapack functions can do.

## A note on `/gamemode` for yourself

As an op you can `/gamemode creative` yourself any time — that's the intended
"owner cheat". Your friends (non-ops) cannot, which is the whole point.

## Common owner cheat commands (via console / In-game command)

```
gamemode creative YourName
gamemode survival YourName
time set day
weather clear
give YourName minecraft:elytra
tp YourName 0 100 0
difficulty peaceful
```
