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

# Fixed destination used by /rescue spawn. No default coordinates are used.
MC_SPAWN_DIMENSION=overworld
MC_SPAWN_X=0.5
MC_SPAWN_Y=80
MC_SPAWN_Z=0.5

# Optional external web-map URL. Leave empty until a web map is deployed.
MC_MAP_URL_TEMPLATE=https://map.example.com/?world={dimension}&x={x}&y={y}&z={z}
```

Valid spawn dimensions are `overworld`, `nether`, and `the_end`. Coordinates
must be numbers. X and Z must stay within ±30,000,000 and Y within -2048…2048.

To choose the spawn location:

1. Join the server with the owner's Minecraft account.
2. Stand on the exact safe block where rescued players should arrive.
3. Press **F3** and note XYZ, or use the admin `/players` position view.
4. Put those values in `MC_SPAWN_X/Y/Z`. Adding `.5` to block-centre X/Z avoids
   spawning on an edge.
5. Make sure the destination is lit, not obstructed, and inside the world border.

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

## 2. Link each friend

The friend runs:

```text
/link request minecraft_name:<exact Java name>
```

The owner reviews pending requests:

```text
/link list
```

The owner selects that Discord user and approves:

```text
/link approve user:<Discord member>
```

The friend verifies the result with `/link status`. Use `/link revoke` if the
Discord account or Minecraft name changes. A Minecraft name can belong to only
one Discord account, comparison is case-insensitive, and only valid 1–16
character Java names are accepted.

Approval does **not** add the player to the Minecraft whitelist. Continue to use
the admin `/whitelist add` command for server admission.

## 3. Rescue only the linked account

- `/rescue spawn` teleports only the Minecraft name approved for the caller. The
  player must be online. The destination is the fixed `MC_SPAWN_*` configuration;
  the friend cannot enter a target, coordinates, or RCON command.
- `/rescue whereami` reads only that linked online player's dimension and XYZ.

The account-link approval is the delegated authorization for this one fixed
teleport. All general server mutation, raw `/mc`, lifecycle, backup, whitelist,
incident, and world-management commands remain behind `ADMIN_USER_IDS`.

## 4. Coordinate book and photos

Approved friends and admins can use:

```text
/place add name:<name> dimension:<choice> x:<x> y:<y> z:<z> description:<optional> photo:<optional>
/place list
/place show name:<name>
/place delete name:<name>
```

Images must be PNG, JPEG, WebP, or GIF and no larger than 5 MiB. The bot downloads
them once to `MC_STATE_DIR/friend-media`; it does not depend on expiring Discord
attachment URLs. A friend may delete only their own place. An admin may delete
any place. The book is capped at 250 names to keep reads and Discord output small.

## 5. Server diary

Approved friends and admins can use:

```text
/diary add message:<text> photo:<optional>
/diary recent limit:<1-20>
/diary show entry_id:<ID shown by recent>
```

Rescue and saved-place events are added automatically. The journal uses
append-only JSONL for cheap writes and compacts to the newest 1,000 entries after
it grows past 2 MiB. Optional photos use the same 5 MiB local image policy.

## 6. On-demand server score

`/server-score` samples Paper TPS, RCON reachability, CPU temperature, five-minute
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
| Link remains pending | Owner runs `/link list`, then `/link approve`. |
| Rescue says spawn is not configured | Set all four `MC_SPAWN_DIMENSION/X/Y/Z` values and restart. |
| Rescue or whereami cannot find the player | The exact linked Java name must currently be online. |
| Photo upload fails | Use a supported image type below 5 MiB and check `MC_STATE_DIR` permissions/free space. |
| Map link is missing | Set `MC_MAP_URL_TEMPLATE`; no map plugin means no live map link. |
| Map link opens the wrong place | Match the template to the deployed map's actual URL format. |
| Score reports zero HDD free | Confirm `/mnt/minecraft` is mounted; the bot treats a missing required mount as unhealthy. |

Death Box is deliberately separate. See [death-box-design.md](death-box-design.md)
for the Paper plugin design and its test plan.
