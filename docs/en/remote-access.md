# Remote access — RCON, SSH, and Cloudflare Tunnel

Three ways to reach and administer the server, from most local to most remote.
For **players** to join from outside your LAN you also need one of the exposure
options below (or port forwarding).

## 1. SSH + RCON (baseline)

The simplest remote console: SSH into the Pi, then use the bundled Python RCON client.

```bash
ssh pi@your-pi-lan-ip
cd raspi-mc-server
# The client loads RCON_HOST/RCON_PORT/RCON_PASSWORD from .env.
.venv/bin/python -m bot.rcon "list"
.venv/bin/python -m bot.rcon "gamemode creative YourName"
```

RCON runs at op level 4, so this is a full admin/cheat console. Keep RCON bound
to localhost — **never forward port 25575 to the internet**.

## 2. Discord bot (primary)

The most convenient for day-to-day use, including from your phone. See
[discord-bot.md](discord-bot.md). The bot connects to RCON on localhost, so no
ports are exposed.

## 3. Cloudflare Tunnel (optional, no port forwarding)

A [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
(`cloudflared`) gives you outbound-only connectivity — no router port forwarding
and no exposed home IP. Two common uses:

### a) Admin web/SSH over the tunnel

Expose SSH or a small admin web page (if you add one) through the tunnel and
protect it with **Cloudflare Access** (email/SSO) so only you can reach it.

```bash
# On the Pi
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -o cloudflared
sudo install cloudflared /usr/local/bin/
cloudflared tunnel login
cloudflared tunnel create raspi-mc
# Route a hostname to a local service (example: SSH on 22)
cloudflared tunnel route dns raspi-mc mc-admin.example.com
```

Put the tunnel config in `~/.cloudflared/config.yml` and run it as a service:

```yaml
tunnel: raspi-mc
credentials-file: /home/pi/.cloudflared/<TUNNEL_ID>.json
ingress:
  - hostname: mc-admin.example.com
    service: ssh://localhost:22
  - service: http_status:404
```

```bash
sudo cloudflared service install
```

Then connect with `cloudflared access ssh --hostname mc-admin.example.com`.

### b) Player traffic

Minecraft's Java protocol is raw TCP, not HTTP, so the free Cloudflare HTTP
proxy does **not** carry the game port. Geyser Bedrock traffic is UDP and is not
carried by ordinary Cloudflare Tunnel either. Options for players:

- **Cloudflare Tunnel TCP** via `cloudflared access tcp` on each player's side
  (works but requires every player to run cloudflared — clunky for friends).
- **Port forwarding** `25565/TCP` and, for Bedrock, `19132/UDP` on your router
  to the Pi (simplest for friends; exposes only game ports).
- A **VPN** like Tailscale/WireGuard: add friends to your tailnet and they
  connect to the Pi's VPN IP — no public exposure at all. This is often the
  nicest option for a 3–4 player friends server.

> Recommendation: for near-zero friend setup, forward `25565/TCP` and
> `19132/UDP`; use **Tailscale** when installing a VPN on each friend device is
> acceptable. Use **Cloudflare Access + the Discord bot** for administration.

## Security summary

- Expose only game ports (`25565/TCP`, optionally `19132/UDP`) to players, or
  keep them private via VPN.
- Never expose RCON (25575) or SSH directly; tunnel/VPN them and gate with
  Access or keys.
- Use strong, unique passwords for RCON and never commit them.
