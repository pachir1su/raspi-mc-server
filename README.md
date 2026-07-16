# raspi-mc-server

A complete, friends-only **Minecraft Java + optional Bedrock crossplay server for
the Raspberry Pi 4B (4GB)**,
built for **3–4 players**, with **owner-only cheats** and **remote administration**
from Discord, SSH, or the web.

> 🇰🇷 한국어 문서: **[README.ko.md](README.ko.md)**

---

## What you get

- **PaperMC** tuned for a Pi 4B 4GB with 32GB microSD + 500GB USB HDD (Aikar
  GC flags and Pi-friendly view/simulation distance).
- **Whitelist-only, no mods** — a small private world for you and a few friends.
- **One Paper world for Java and Bedrock** — optional Geyser + Floodgate lets
  Java PC, iPhone/iPad, Android, and Minecraft for Windows play together with
  no friend-side mod. Friends save the address once and tap it afterward.
- **Owner-only cheats.** On a multiplayer server, only *operators* can run
  commands. You op **only yourself**, so nobody else can cheat in-game — but you
  always can, remotely, through any admin channel.
- **Remote administration** three ways:
  - 🤖 **Discord bot** (primary) — admin-only slash commands, a loading
    animation for slow actions, and log-file attachments.
  - 💻 **SSH + RCON** (baseline) — a console from anywhere you can SSH in.
  - 🌐 **Cloudflare Tunnel** (optional) — reach the server/console with no port
    forwarding.
- **30-minute HDD backups**, SHA-256 verification, Discord restore/map
  upload/switching, administrator-assigned multi-profile Discord↔Minecraft links, self-rescue, a photo
  coordinate book, server diary, on-demand health score, friend portal commands,
  automatic performance alerts, tuning reports, a quick-command panel
  (time/weather/difficulty/gamerules/world-spawn placement),
  player quick actions (give items with Korean aliases, potion effects,
  enchants, gamemode, teleport, XP, heal, kick),
  backup timelines, a button-first dashboard,
  live-player inventory inspection, health checks, rotating audit logs, **systemd**
  auto-start, and a one-shot **provisioning script**.
- **Optional Raspberry Pi cluster** guidance for when one Pi isn't enough.
- **Full docs in English and Korean.**

---

## Quick start

For a Raspberry Pi with no display or keyboard, use the complete
**[headless SD-card-to-server guide](docs/en/headless-setup.md)**. It begins on
Windows with Raspberry Pi Imager and includes SSH, HDD safety, first launch,
router ports, friend admission, reboot testing, and recovery.

The setup script automatically installs Amazon Corretto Java 25 when needed.

On Raspberry Pi OS Lite (64-bit, Debian 13 Trixie), from the Pi:

```bash
git clone https://github.com/pachir1su/raspi-mc-server.git
cd raspi-mc-server

# 1. Identify and prepare the 500GB HDD (/dev/sda1 is an example; format destroys data)
lsblk -f
sudo mkfs.ext4 /dev/sda1
sudo ./scripts/setup_hdd.sh /dev/sda1

# 2. Provision everything (automatically installs Amazon Corretto Java 25)
./deploy/setup_raspberrypi.sh

# 3. Set your secrets
#    - /mnt/minecraft/live/server.properties -> rcon.password
#    - .env                     -> DISCORD_TOKEN, ADMIN_USER_IDS, RCON_PASSWORD

# 4. Enable reboot startup, then run the one entry point
sudo systemctl enable minecraft.service mc-discord-bot.service
.venv/bin/python -m bot.main
# Choose language and Java-only or Java+Bedrock on the first run.
```

Full walkthrough: **[docs/en/setup.md](docs/en/setup.md)**.

---

## Cheats: how "only I can cheat" works

Multiplayer Minecraft has no per-world "Allow Cheats" switch like singleplayer.
Instead, commands are gated by **operator (op) level**:

- **Normal players** cannot run cheat commands at all.
- **Operators** can. You op **only yourself** (`server/ops.json`).
- The **console, RCON, the Discord bot, and SSH** always run at op level 4 — so
  **you** can always cheat remotely, and **no one else** can in-game.

Details: **[docs/en/cheats-and-ops.md](docs/en/cheats-and-ops.md)**.

---

## Documentation

Third-party image sources and licenses are recorded in
[image attribution](docs/assets/ATTRIBUTION.md).

Gameplay guides use the server-side Java/Paper 26.1 rules, including for Bedrock
players connected through Geyser.

| Topic | English | 한국어 |
|---|---|---|
| Headless SD card → running server | [headless setup](docs/en/headless-setup.md) | [무화면 전체 설치](docs/ko/headless-setup.md) |
| HDD form factor, enclosure & power | [HDD hardware](docs/en/hdd-hardware.md) | [HDD 하드웨어](docs/ko/hdd-hardware.md) |
| Setup & first run | [setup](docs/en/setup.md) | [설치](docs/ko/setup.md) |
| Server configuration | [configuration](docs/en/configuration.md) | [설정](docs/ko/configuration.md) |
| Cheats & operators | [cheats-and-ops](docs/en/cheats-and-ops.md) | [치트와 관리자](docs/ko/cheats-and-ops.md) |
| Discord bot | [discord-bot](docs/en/discord-bot.md) | [디스코드 봇](docs/ko/discord-bot.md) |
| Friend links, rescue & journal | [friend-tools](docs/en/friend-tools.md) | [친구 도구](docs/ko/friend-tools.md) |
| Enchantments | [enchantments](docs/en/enchantments.md) | [인챈트](docs/ko/enchantments.md) |
| Status effects | [status effects](docs/en/status-effects.md) | [상태 효과](docs/ko/status-effects.md) |
| Brewing | [brewing](docs/en/brewing.md) | [양조법](docs/ko/brewing.md) |
| Villager trading | [villager trading](docs/en/villager-trading.md) | [주민 거래](docs/ko/villager-trading.md) |
| Ores & resources | [ores and resources](docs/en/ores-and-resources.md) | [광물과 자원](docs/ko/ores-and-resources.md) |
| Farming & breeding | [farming and breeding](docs/en/farming-and-breeding.md) | [농사와 사육](docs/ko/farming-and-breeding.md) |
| Food & hunger | [food](docs/en/food.md) | [음식과 허기](docs/ko/food.md) |
| Server-specific player features | [server features](docs/en/server-features.md) | [서버 전용 기능](docs/ko/server-features.md) |
| Death Box plugin | [death-box-design](docs/en/death-box-design.md) | [Death Box 설계](docs/ko/death-box-design.md) |
| Paper operations plugin | [paper-ops-plugin](docs/en/paper-ops-plugin.md) | [Paper 운영 플러그인](docs/ko/paper-ops-plugin.md) |
| Remote access (RCON / Cloudflare) | [remote-access](docs/en/remote-access.md) | [원격 접속](docs/ko/remote-access.md) |
| Backups | [backup](docs/en/backup.md) | [백업](docs/ko/backup.md) |
| Performance tuning | [performance](docs/en/performance.md) | [성능 튜닝](docs/ko/performance.md) |
| Raspberry Pi cluster | [cluster](docs/en/cluster.md) | [클러스터](docs/ko/cluster.md) |
| Java + Bedrock crossplay | [bedrock](docs/en/bedrock.md) | [자바+베드락](docs/ko/bedrock.md) |
| Troubleshooting | [troubleshooting](docs/en/troubleshooting.md) | [문제 해결](docs/ko/troubleshooting.md) |
| Server owner runbook | [operator runbook](docs/en/operator-runbook.md) | [운영 런북](docs/ko/operator-runbook.md) |
| Prompts for coding agents | [agent-prompts](docs/prompts/agent-prompts.md) | (same file, bilingual) |

Agent working rules live in [CLAUDE.md](CLAUDE.md) and [AGENTS.md](AGENTS.md).

---

## Repository layout

```
raspi-mc-server/
├── server/        # server.properties template, ops/whitelist examples
├── scripts/       # install / start / stop / backup / restore
├── deploy/        # systemd units + one-shot Pi provisioning
├── bot/           # Discord admin bot (Python, discord.py)
├── plugin/        # Paper plugins (DeathBox — protected chest on death)
├── docs/          # English + Korean docs, and agent prompts
├── .env           # tracked placeholders; replace locally on the Pi
└── README.md / README.ko.md
```

---

## Requirements

- Raspberry Pi 4B (4GB) with **Raspberry Pi OS Lite (64-bit)**. Bookworm
  (Legacy) is the tested baseline; on Trixie the `cloud-init` first boot may
  ignore Raspberry Pi Imager settings (SSH/user) — see
  [troubleshooting](docs/en/troubleshooting.md#trixie-imager-settings-ssh-user-are-not-applied).
- A 32GB microSD plus a 500GB USB 3.0 HDD for PaperMC, worlds, and backups.
  Some USB 3.0↔SATA adapters crash the Pi 4B xHCI controller under load; see
  the [troubleshooting notes](docs/en/troubleshooting.md#pi-4b-usb-30--sata-ssd-adapter-xhci-controller-dies).
- A Discord application/bot token (for the bot) — see
  [docs/en/discord-bot.md](docs/en/discord-bot.md).
- **Note:** `mcrcon` is **not** in the Debian repositories, so the setup script
  does not install it. Run one-off RCON commands with the built-in client:
  `.venv/bin/python -m bot.rcon "list"`.

## License

[MIT](LICENSE).
