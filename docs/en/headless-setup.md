# Headless installation from SD card to Minecraft login

This guide sets up a Raspberry Pi 4B (4GB) with **no monitor, keyboard, or
mouse**. It starts with imaging a 32GB microSD on Windows, configures the Pi over
SSH, puts the Paper world on a 500GB USB HDD, and finishes with Java and mobile
Bedrock players joining the same world.

Always check the label above each command:

- **Windows PowerShell** runs on your Windows PC.
- **Pi SSH** runs after connecting to the Raspberry Pi with `ssh`.
- `/dev/sda` and `/dev/sda1` are examples. Identify your own HDD first.

The upstream references are the official
[Raspberry Pi getting-started guide](https://www.raspberrypi.com/documentation/computers/getting-started.html)
and [Raspberry Pi Imager](https://www.raspberrypi.com/software/).

## 1. Hardware and recommended wiring

- Raspberry Pi 4B 4GB with a cooled case
- A good 5V/3A USB-C power supply
- 32GB or larger microSD and a Windows SD reader
- 500GB USB 3.0 HDD
- Preferably a **self-powered HDD enclosure or powered USB hub**
- Router and, preferably, an Ethernet cable
- A Windows PC on the same router

Paper worlds, backups, and uploaded media live on the HDD at `/mnt/minecraft`.
Raspberry Pi OS, the repository, and the bot program stay on microSD. A
bus-powered HDD can cause undervoltage and disconnects, so externally powered
storage is the safer unattended setup.

## 2. Image the microSD on Windows

1. Install the [official Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2. Disconnect the HDD from the PC and insert **only the microSD**.
3. Select:
   - Device: `Raspberry Pi 4`
   - OS: `Raspberry Pi OS (other)` → `Raspberry Pi OS Lite (64-bit)`
   - Storage: the prepared microSD
4. Open **OS customisation**.

Recommended customisation:

| Item | Recommended value | Purpose |
|---|---|---|
| Hostname | `mc-pi` | SSH later through `mc-pi.local` |
| Username | `mcadmin` | A custom lowercase user instead of `pi` |
| Password | strong and unique | Different from Discord and RCON secrets |
| Time zone | `Asia/Seoul` or your location | Correct logs and schedules |
| Wi-Fi country | your country | Correct wireless regulation |
| Wi-Fi | home SSID and password | Useful as fallback even with Ethernet |
| Remote Access | **Enable SSH** | Required for headless operation |
| SSH authentication | public key preferred; password is acceptable initially | Can be hardened later |
| Raspberry Pi Connect | optional | Not needed when SSH is enough |

5. Select **Write** and verify the target is the microSD one last time.
6. Wait for write and verification to finish, then safely eject the card.

> Imaging erases the selected storage. Verify its name and capacity are not the
> HDD. On Raspberry Pi OS Bookworm and later, configure Wi-Fi in Imager; the old
> boot-partition `wpa_supplicant.conf` method is no longer the supported path.

## 3. First headless boot and SSH

1. Insert the microSD while Pi power is disconnected.
2. Connect Ethernet to the router when possible.
3. The HDD is not needed yet.
4. Connect USB-C power last and allow 3–5 minutes for first boot.

In Windows PowerShell:

```powershell
ping mc-pi.local
ssh mcadmin@mc-pi.local
```

At the first connection, verify the hostname and answer `yes` to the host-key
prompt. If `mc-pi.local` does not resolve, find `mc-pi` or the new Pi in the
router's connected-device list and use its IP:

```powershell
ssh mcadmin@192.168.0.42
```

If you reused the hostname for a newly imaged card and SSH reports a changed
host key, first confirm that this really is your new card, then remove the old
Windows entry:

```powershell
ssh-keygen -R mc-pi.local
```

## 4. Update and inspect Raspberry Pi OS

Unless marked otherwise, commands from here run in **Pi SSH**.

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

Wait 1–3 minutes after SSH disconnects, then reconnect from Windows:

```powershell
ssh mcadmin@mc-pi.local
```

Inspect the base system in Pi SSH:

```bash
uname -m
cat /etc/os-release
hostname -I
timedatectl
free -h
df -h /
```

- A 64-bit OS normally reports `aarch64` from `uname -m`.
- Correct localisation through `sudo raspi-config` if necessary.
- Reserve the Pi's IP in the router's DHCP settings so SSH and port forwarding
  stay stable.

## 5. Use an SSH key

Skip this if Imager already configured public-key authentication. Otherwise,
create and install a key from Windows PowerShell:

```powershell
ssh-keygen -t ed25519
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | ssh mcadmin@mc-pi.local "umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"
```

Test `ssh mcadmin@mc-pi.local` in a new PowerShell window. To disable password
login, keep the existing session open and create this file on the Pi:

```bash
sudo nano /etc/ssh/sshd_config.d/99-headless.conf
```

```text
PasswordAuthentication no
PermitRootLogin no
```

```bash
sudo sshd -t
sudo systemctl reload ssh
```

Close the old session only after a new key-based session succeeds.

## 6. Clone the repository

In Pi SSH:

```bash
sudo apt install -y git
cd ~
git clone https://github.com/pachir1su/raspi-mc-server.git
cd raspi-mc-server
git status --short --branch
```

Keep the repository on microSD and place only large Minecraft data on the HDD.

## 7. Prepare the 500GB HDD

If the reported `100 × 700 mm` means approximately `100 × 70 mm`, it is likely
a 2.5-inch disk. “7 versus 10” normally means 7mm versus 9.5mm height, not
inches. Read [HDD form factor, enclosure, and power](hdd-hardware.md) before
buying the enclosure or choosing bus power.

### 7.1 Power down and attach storage

```bash
sudo poweroff
```

Wait for SSH to disconnect and activity LEDs to stop, remove Pi power, connect
the HDD to a blue USB 3.0 port, power the HDD enclosure first when applicable,
and then power the Pi. Reconnect over SSH.

### 7.2 Identify the exact device

```bash
lsblk -o NAME,SIZE,FSTYPE,LABEL,MODEL,SERIAL,MOUNTPOINTS
sudo wipefs -n /dev/sda
```

A nominal 500GB disk can appear around 465GiB. microSD is usually `mmcblk0` and
USB HDD is often `sda`, but verify **size, MODEL, and SERIAL** instead of trusting
names.

Stop and back up any HDD that contains wanted data. The following partition and
format commands erase the selected HDD.

### 7.3 Partition and format only a new empty HDD

Use this example only if you verified `/dev/sda` as the HDD and `/dev/sda1` as
its partition:

```bash
sudo apt install -y parted
sudo parted /dev/sda --script mklabel gpt
sudo parted /dev/sda --script mkpart primary ext4 0% 100%
sudo partprobe /dev/sda
lsblk -f /dev/sda
sudo mkfs.ext4 -L minecraft-data /dev/sda1
```

### 7.4 Register the UUID mount

The repository script never formats disks. It registers the ext4 UUID in
`/etc/fstab` and creates the `/mnt/minecraft` data tree.

```bash
cd ~/raspi-mc-server
sudo ./scripts/setup_hdd.sh /dev/sda1
findmnt /mnt/minecraft
df -h /mnt/minecraft
ls -ld /mnt/minecraft /mnt/minecraft/live
```

Reboot and prove the mount and ownership work:

```bash
sudo reboot
```

After reconnecting:

```bash
findmnt /mnt/minecraft
touch /mnt/minecraft/.write-test
rm /mnt/minecraft/.write-test
```

Do not continue when `findmnt` fails. Writing into an unmounted
`/mnt/minecraft` can put world data on microSD by mistake.

## 8. Provision Paper and the Discord bot

```bash
cd ~/raspi-mc-server
./deploy/setup_raspberrypi.sh
```

The script installs Java 21, the Python environment, Paper, systemd units, and a
narrow sudoers rule limited to the Minecraft service. It is designed to be
re-runnable.

## 9. Configure RCON and Discord secrets

Generate an RCON password candidate:

```bash
openssl rand -hex 32
```

Keep it in a private secret store, not chat or GitHub. Edit Paper configuration:

```bash
nano /mnt/minecraft/live/server.properties
```

Confirm:

```properties
enable-rcon=true
rcon.port=25575
rcon.password=<generated password>
white-list=true
enforce-whitelist=true
```

Edit the repository `.env` and restrict its permissions:

```bash
cd ~/raspi-mc-server
nano .env
chmod 600 .env
```

Replace at least these values:

```dotenv
DISCORD_TOKEN=<Discord Developer Portal bot token>
DISCORD_GUILD_ID=<your Discord server ID>
ADMIN_USER_IDS=<your Discord user ID>
RCON_PASSWORD=<exactly the same value as server.properties>
MC_STORAGE_ROOT=/mnt/minecraft
MC_SERVER_DIR=/mnt/minecraft/live
MC_REQUIRE_STORAGE_MOUNT=true
MC_STATE_DIR=/mnt/minecraft/bot-state
MC_PUBLIC_ADDRESS=<public address or IP given to friends>
MC_PUBLIC_VERSION="Paper Java 1.21.x + Bedrock"
MC_PUBLIC_RULES="Respect builds and items; tell the operator when something breaks."
```

Initially place only the owner in `ADMIN_USER_IDS`. See
[discord-bot.md](discord-bot.md) for token and ID creation. Never commit `.env`,
real tokens, or RCON passwords. Old `BOT_LANGUAGE` values are ignored; the first
launch menu selects language.

Shell scripts also source `.env`, so quote values containing spaces as shown.
An unquoted value such as `MC_PUBLIC_VERSION=Paper Java ...` makes provisioning
or RCON helper commands fail while loading the file.

## 10. First launch through `main.py`

```bash
cd ~/raspi-mc-server
sudo systemctl enable minecraft.service mc-discord-bot.service
.venv/bin/python -m bot.main
```

Recommended mixed-device choices:

```text
1. 한국어
2. Java + mobile/Windows Bedrock (recommended)
Bedrock UDP port [19132]: Enter
```

This single launch verifies/configures missing Geyser and Floodgate plugins,
starts Paper, and starts the Discord bot. Wait for `logged in as ...`. Select
Java-only in the menu when Bedrock is not required.

After Paper starts, op only the owner's Java Minecraft account from another SSH
session:

```bash
cd ~/raspi-mc-server
set -a
. ./.env
set +a
mcrcon -H 127.0.0.1 -P 25575 -p "$RCON_PASSWORD" "op Owner_Java_Name"
```

Prefer a Java account for owner administration. Friends join through Discord
approval and never receive op.

## 11. Hand the foreground process to systemd

After verifying first setup and Discord login, press `Ctrl+C` to stop the
foreground bot. Paper remains running. Start the bot service:

```bash
sudo systemctl start mc-discord-bot.service
systemctl is-enabled minecraft.service mc-discord-bot.service
systemctl is-active minecraft.service mc-discord-bot.service
sudo journalctl -u mc-discord-bot.service -n 100 --no-pager
```

Test unattended reboot recovery:

```bash
sudo reboot
```

Reconnect after 2–5 minutes and run:

```bash
cd ~/raspi-mc-server
./scripts/health_check.sh
```

The HDD mount, both services, Paper TPS, and RCON should be healthy.

## 12. Router and Internet access

Reserve the Pi's DHCP address, then forward only these game ports to it:

| Use | External/internal port | Protocol |
|---|---:|---|
| Java Edition | 25565 | TCP |
| iPhone, Android, Minecraft for Windows | 19132 | UDP |

Never expose:

- RCON `25575`
- SSH `22`; prefer a VPN if remote SSH is required

Ordinary Cloudflare HTTP Tunnel does not carry the raw Minecraft TCP and
Bedrock UDP traffic. Under CGNAT where port forwarding is unavailable, consider
a VPN such as Tailscale or a tunnel designed for game traffic. See
[remote-access.md](remote-access.md).

Test from mobile data or another network, not from the same Wi-Fi.

## 13. What friends actually do

### Java PC

1. Minecraft Java Edition → Multiplayer → Add Server
2. Enter the owner-provided address (default port `25565`)
3. Save once and click the saved server later

### iPhone, Android, and Minecraft for Windows

1. Play → Servers → Add Server
2. Enter the same address and port `19132`
3. Join with the normal Microsoft/Xbox account
4. Tap the saved server on later visits

Friends install no Geyser, Floodgate, mod, or separate launcher.

In Discord, the friend runs:

```text
/link request minecraft_name:<exact name or Xbox gamertag> edition:<Java or Bedrock>
```

The owner runs:

```text
/link list
/link approve user:<friend Discord account>
```

Approval also adds the correct Java/Floodgate whitelist entry. Approved friends
can use `/rescue spawn` and `/rescue whereami` only for their linked account.

Floodgate documents that `fwhitelist` can resolve a gamertag only after that Xbox
account has joined some Geyser server before. If approval fails for a completely
new account, follow the first-Bedrock-login recovery in
[friend-tools.md](friend-tools.md); do not leave the whitelist disabled.

## 14. Daily headless operation

Normally use Discord `/panel`. If the bot is unavailable, connect from Windows:

```powershell
ssh mcadmin@mc-pi.local
```

Basic Pi SSH checks:

```bash
cd ~/raspi-mc-server
./scripts/health_check.sh
sudo journalctl -u minecraft.service -n 100 --no-pager
sudo journalctl -u mc-discord-bot.service -n 100 --no-pager
```

Before physically removing power:

```bash
sudo systemctl stop mc-discord-bot.service
sudo systemctl stop minecraft.service
sudo poweroff
```

Wait for SSH to close and activity LEDs to stop. Pulling power while the server
runs can corrupt the world or microSD.

## 15. Safe update

### Discord and GitHub Release updater (recommended)

Install this feature once with the manual procedure below and rerun
provisioning. For later versions, publishing a GitHub Release automatically
attaches `raspi-mc-server-vX.Y.Z.zip` plus its SHA-256 file.

Run `/update check` and press **Install update**. The Pi downloads the official
Release asset directly and verifies its manifest and every file's SHA-256. Only
the Discord bot restarts; Paper and the world keep running.

If the Release ZIP is already on your PC, `/update upload file:<ZIP>` is the
recovery path. Use the deployment ZIP attached by the workflow, not GitHub's
automatic `Source code (zip)` or a repacked archive; those lack the verification
manifest. Use `/update check` when Discord's attachment limit is too small.

The updater preserves `.env`, `/mnt/minecraft/live`, bot state (links, places,
journal), photos, and logs. It prepares a new Python environment first and
rolls code and dependencies back if the bot fails its startup check. Inspect
the result after restart with `/update status`.

### First installation or bot unavailable

```bash
cd ~/raspi-mc-server
git status --short
git fetch origin
git switch main
git pull --ff-only
.venv/bin/pip install -r requirements.txt
sudo ./deploy/setup_raspberrypi.sh
sudo systemctl restart mc-discord-bot.service
./scripts/health_check.sh
```

Back up unexpected local changes rather than overwriting them.
Normal application updates do not restart `minecraft.service`, reducing lag
and player disconnects because Minecraft data is outside the code release.

## 16. Troubleshooting without a screen

### `mc-pi.local` does not respond

1. Allow five minutes on first boot.
2. Verify PC and Pi are on the same normal LAN; guest Wi-Fi may isolate devices.
3. Find the IP in the router and try `ssh mcadmin@<IP>`.
4. Check Ethernet and power LEDs.

### SSH works but Minecraft does not

```bash
findmnt /mnt/minecraft
systemctl status minecraft.service mc-discord-bot.service --no-pager
sudo journalctl -u minecraft.service -n 200 --no-pager
sudo journalctl -u mc-discord-bot.service -n 200 --no-pager
```

If the HDD is not mounted, do not force-start services. Fix USB power, cable,
and UUID/mount problems first.

### Check undervoltage and temperature

```bash
vcgencmd get_throttled
vcgencmd measure_temp
```

Resolve active undervoltage at the PSU or HDD power source first. See
[operator-runbook.md](operator-runbook.md) for interpretation.

### Rebuild after microSD failure

1. Create a new card from section 2.
2. Clone the repository again.
3. Do **not format the existing HDD**; register its ext4 partition with
   `setup_hdd.sh`.
4. Restore privately stored `.env` and `server.properties` secrets.
5. Run `setup_raspberrypi.sh` again.

Backups on the same HDD do not protect against HDD failure. Keep important
world backups and secrets on a PC or separate storage too.

## 17. Completion checklist

- [ ] Imager configured Raspberry Pi OS Lite 64-bit, user, Wi-Fi, and SSH
- [ ] `ssh mcadmin@mc-pi.local` works
- [ ] SSH still works after OS update and reboot
- [ ] HDD was identified by size, MODEL, and SERIAL and prepared as ext4
- [ ] `findmnt /mnt/minecraft` succeeds after reboot
- [ ] RCON passwords match in `.env` and `server.properties`
- [ ] First `python -m bot.main` menu completed
- [ ] Only the owner account is op
- [ ] Both systemd services are enabled and active
- [ ] `health_check.sh` reports healthy HDD, RCON, and TPS
- [ ] Router forwards `25565/TCP` and, when needed, `19132/UDP` only
- [ ] Real external Java and Bedrock connections tested
- [ ] Discord link approval and self-rescue tested
- [ ] At least one recent world backup exists outside the Pi/HDD
