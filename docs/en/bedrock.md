# Java and Bedrock in one world

This project can keep **Paper Java Edition as the one server and one world**
while Geyser translates Bedrock traffic and Floodgate authenticates Bedrock
players. Java PC, iPhone/iPad, Android, and Minecraft for Windows can therefore
play together. Friends install no client mod, plugin, or helper app.

## What the first-run choice does

Run the project entry point after Pi provisioning and `.env` secret setup:

```bash
cd ~/raspi-mc-server
.venv/bin/python -m bot.main
```

Choose a display language, then `Java + mobile/Windows Bedrock`. The launcher:

1. stores the non-secret choice in `MC_STATE_DIR/app-settings.json`;
2. downloads the latest official Geyser-Spigot and Floodgate-Spigot jars only
   when they are missing;
3. verifies each published SHA-256 before installing it;
4. configures Geyser for Floodgate and the chosen UDP port (default `19132`);
5. starts/restarts Paper only when setup requires it; and
6. starts the Discord bot and all of its cogs.

Normal launches do not poll for plugin updates or restart a healthy configured
server. This keeps Pi CPU, storage, and startup-network work low. To reopen the
menu later, run `.venv/bin/python -m bot.main --setup` in a terminal.

## Friend setup: save once, tap afterward

The owner must expose both game ports when players are outside the LAN:

- Java: `25565/TCP`
- Bedrock: `19132/UDP` (or the port selected in the menu)

Java friends open Multiplayer, add the server address once, and join normally.
On iPhone/iPad, Android, or Minecraft for Windows, the friend does this once:

1. Open **Play → Servers → Add Server**.
2. Enter the owner's address and Bedrock port `19132`.
3. Save it and join with the normal Microsoft/Xbox account.

After that, the saved server is a tap away. There is no Geyser/Floodgate setup
on the friend's device. Xbox, PlayStation, and Switch use Bedrock too, but their
custom-server UI is restricted and is not part of this one-tap support target.

## Discord link and admission

The friend runs `/link request`, enters the exact Java name or Xbox gamertag,
and selects the edition. The owner runs `/link approve`. Approval also runs the
correct Paper/Floodgate whitelist command, so no second whitelist step is
needed. Floodgate names use a `.` prefix internally to avoid colliding with a
Java account of the same name; the friend still types the ordinary gamertag.

## Network warning

Ordinary Cloudflare Tunnel/HTTP proxying does not carry the Bedrock UDP game
port. For the lowest friend setup, forward `25565/TCP` and `19132/UDP` on the
router. A VPN avoids public ports but requires each friend to install/join it.
Never expose RCON `25575`.

## Native Bedrock is a different design

Running a separate native Bedrock server would create a separate server/world
and would not use this Paper/RCON bot design. Geyser + Floodgate is the supported
mixed-device route here. Gameplay translation has occasional Java/Bedrock
differences, but all players remain in the same Paper world.

Official references: [Geyser setup](https://geysermc.org/wiki/geyser/setup/),
[Floodgate setup](https://geysermc.org/wiki/floodgate/setup/paper-spigot/), and
[current limitations](https://geysermc.org/wiki/geyser/current-limitations/).
