# Friend tools: links, rescue, places, diary, and score

The Discord bot exposes a narrow self-service surface for approved friends. It
does not make friends Minecraft operators and it never accepts arbitrary RCON
text from them.

## 1. Configure the Pi

Edit the existing `.env` on the Raspberry Pi. Do not commit the real file.

```bash
cd ~/raspi-mc-server
nano .env
```

Add or update these values:

```dotenv
# Enables the friend-facing cog. Existing admin commands remain allowlisted.
PUBLIC_COMMANDS_ENABLED=true

# Put runtime JSON and uploaded photos on the mounted HDD.
MC_STATE_DIR=/mnt/minecraft/bot-state

# Optional external web-map URL. Leave empty until a web map is deployed.
MC_MAP_URL_TEMPLATE=https://map.example.com/?world={dimension}&x={x}&y={y}&z={z}
```

> Note: the old `MC_SPAWN_X/Y/Z/DIMENSION` coordinate override has been
> removed. Rescue always uses the **world spawn**, so it always matches the
> on-death respawn location. If the operational `.env` still contains those
> values, they can be deleted (they are ignored).

To choose the spawn location:

1. Have any online player (ideally the owner) stand on the desired block.
2. Open `/admin` → **Quick commands** → **Set spawn** and pick that player.
   Coordinates can also be typed manually.
3. Both the on-death respawn (without a bed) and the `/tools` rescue button now
   use that point. The scatter radius (`spawnRadius`) is set to 0 as well.

`MC_MAP_URL_TEMPLATE` must match the web map you actually deploy. It supports
`{dimension}`, `{x}`, `{y}`, and `{z}` placeholders. The bot only builds a link;
it does not render or poll a map. If your map has a different URL format, open a
location in the browser, copy its URL, and replace the coordinate values with the
matching placeholders. Leave the setting blank if no web map is installed; the
coordinate book still works without a link.

Restart and check the bot after saving `.env`:

```bash
sudo systemctl restart mc-discord-bot.service
sudo systemctl status mc-discord-bot.service --no-pager
sudo journalctl -u mc-discord-bot.service -n 100 --no-pager
```

## 2. Assign each friend's accounts

The owner runs `/admin`, opens **Friend accounts**, and selects a Discord user.
Press **Add Java (PC)** or **Add Bedrock (mobile)** and type only the exact
Minecraft name in the modal. There is no friend request or approval queue. The
owner may add multiple Java and Bedrock profiles to the same Discord user and
may remove one selected profile without affecting the others. The friend sees
all assigned profiles under **My accounts** in `/tools`.

Adding a profile runs `whitelist add` for Java or Floodgate's `fwhitelist add`
for Bedrock. Removing it runs the matching removal command. These server
mutations remain behind `ADMIN_USER_IDS`. Java names follow the normal 1–16
character format; Bedrock gamertags may also contain spaces. Unsafe command
characters are rejected in both cases.

## 3. Rescue only the linked account

- Select an account in `/tools`, then press **Selected account: spawn**. It teleports only a Minecraft profile assigned to the caller. The
  player must be online — if not, the bot replies that the player is not in
  the game and runs nothing. The destination is always the **world spawn**
  (changed via the admin panel's Set spawn), so it matches the on-death
  respawn location. The friend cannot enter a target, coordinates, or RCON command.
- **Selected account: location** reads only that linked online player's dimension and XYZ.

The administrator's account assignment is the delegated authorization for this one fixed
teleport. All general server mutation, the in-game command console, lifecycle, backup, whitelist,
quick commands, and world-management commands remain behind `ADMIN_USER_IDS`.

## 4. Coordinate book and photos

Approved friends and admins open **Coordinates** in `/tools`. Existing places
are selected from a dropdown. **Save current position** reads the linked online
player's XYZ automatically and asks only for a short name and optional note.
View and delete are buttons. To attach or replace an image, use
`/upload place-photo`; attachments are the one thing Discord buttons cannot send.

Images must be PNG, JPEG, WebP, or GIF and no larger than 5 MiB. The bot downloads
them once to `MC_STATE_DIR/friend-media`; it does not depend on expiring Discord
attachment URLs. A friend may delete only their own place. An admin may delete
any place. The book is capped at 250 names to keep reads and Discord output small.

## 5. Server diary

Approved friends and admins open **Server diary** in `/tools`, select a recent
entry from the dropdown, or press **New entry**. Free-form writing uses one modal
because text is the feature. Use `/upload diary` only when adding a photo.

Rescue and saved-place events are added automatically. The journal uses
append-only JSONL for cheap writes and compacts to the newest 1,000 entries after
it grows past 2 MiB. Optional photos use the same 5 MiB local image policy.

## 6. On-demand server score

**Server score** in `/tools` samples Paper TPS, RCON reachability, CPU temperature, five-minute
load, memory, HDD free space, and Raspberry Pi undervoltage/throttle flags. It
returns 0–100, a grade, and every deduction. It runs only when requested: there
is no new background loop, chunk scan, or extra server tick work.

## Runtime files and backup

With the recommended HDD setting, these files live under
`/mnt/minecraft/bot-state`:

- `player-links.json`
- `places.json`
- `server-diary.jsonl`
- `friend-media/`

They contain Discord user IDs, Minecraft names, coordinates, diary text, and
photos. Protect them like other private server data and include the directory in
your host-level HDD backup. They are ignored by Git.

## Troubleshooting

| Symptom | Check |
|---|---|
| Friend sees the feature-disabled message | Set `PUBLIC_COMMANDS_ENABLED=true`, then restart the bot. |
| No account appears in `/tools` | Owner opens `/admin` → **Friend accounts**, selects the Discord user, then adds a Java or Bedrock profile. |
| Rescue reports an unknown `raspiops` command | Install a Release build containing the bundled Paper operations plugin, then restart Paper and the bot. |
| Bedrock registration says the whitelist command is unknown | Re-run `python -m bot.main --setup`, select Java+Bedrock, and check both plugin configs were generated. |
| Rescue or whereami cannot find the player | The exact linked Java/Floodgate account must currently be online. |
| Photo upload fails | Use a supported image type below 5 MiB and check `MC_STATE_DIR` permissions/free space. |
| Map link is missing | Set `MC_MAP_URL_TEMPLATE`; no map plugin means no live map link. |
| Map link opens the wrong place | Match the template to the deployed map's actual URL format. |
| Score reports zero HDD free | Confirm `/mnt/minecraft` is mounted; the bot treats a missing required mount as unhealthy. |

### First login for a brand-new Bedrock account

Floodgate documents that `fwhitelist add <gamertag>` can resolve only accounts
that have previously joined a Geyser server. A completely new Xbox account can
therefore fail its first registration before it is known to Floodgate.

Prefer doing this on LAN before public Bedrock port forwarding is enabled. In a
short maintenance window, with the exact friend ready to connect:

```text
whitelist off
# Friend attempts one Bedrock login so Floodgate learns the account.
fwhitelist add ExactGamertag
whitelist on
whitelist reload
```

Run these through local RCON or `/admin` → **Advanced tools** → **In-game command**; never delegate them to the
friend. Re-enable the whitelist immediately even if another step fails, verify
it with `whitelist list`, and then add the Bedrock profile again. Do not operate the
server with the whitelist left off. See the official
[Geyser whitelist FAQ](https://geysermc.org/wiki/geyser/faq/).

## Death Box buttons

The `/tools` panel includes **Locate death box** and **List death boxes**
buttons. These call the DeathBox plugin via RCON (`deathbox locate <player>`,
`deathbox list <player>`), so friends never need to type in-game commands.

Death Box is deliberately separate — it is a Paper plugin, not part of the bot.
See [death-box-design.md](death-box-design.md) for how it works, how to build and
install it, and its verification checklist.
