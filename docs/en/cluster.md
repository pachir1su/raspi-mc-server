# Raspberry Pi cluster (optional)

One Pi 4B is enough for a 3–4 player vanilla-style survival world. A "cluster" of
Pis does **not** make a single Minecraft world run faster — a vanilla/Paper
server is largely single-threaded per world and cannot be split across machines.
So think of a cluster as a way to run **more separate things**, not to
scale one world.

## What a cluster is good for

- **Separate servers per Pi**: e.g. a survival world on Pi #1, a creative world
  on Pi #2, joined by a **proxy** so players pick a world from one address.
- **Offloading side services**: run the Discord bot, backups/rclone, dynmap or a
  web map, and monitoring on a second Pi so the game Pi does nothing but tick.
- **Blue/green or test**: keep a spare Pi to test a version upgrade before
  moving the world over.

## Proxy-based multi-server (Velocity)

[Velocity](https://papermc.io/software/velocity) is a modern proxy from the
PaperMC team. Players connect to the proxy; it routes them to backend Paper
servers (each can be its own Pi).

```
                 ┌──────────────┐
players ───────▶ │  Velocity     │  (Pi #0, lightweight)
                 │  proxy :25565 │
                 └──────┬───────┘
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
     survival        creative        minigames
     (Pi #1)         (Pi #2)         (Pi #3)
```

Key points:

- Put backends in **offline-mode behind the proxy** and enable Velocity's
  **modern forwarding** with a shared secret, so only the proxy can reach them
  (never expose backends publicly).
- Each backend keeps its own whitelist/ops; op only yourself on each.
- This is overkill for one friends world — reach for it only if you want
  multiple worlds under one address.

## Lightweight orchestration

For a couple of Pis, plain **systemd** on each (as this repo sets up) is simpler
than Kubernetes/Docker Swarm. If you already run k3s for other projects you can
containerise the server, but the SD/CPU overhead rarely pays off for a small
Minecraft setup.

## Recommendation

- **3–4 friends, one world** → a single Pi 4B. Skip the cluster.
- **Multiple worlds / heavy side services** → 2–3 Pis with Velocity and side
  services offloaded, all managed by systemd.
