# Performance tuning for a Pi 4B (4GB)

A Pi 4B can host a smooth 3–4 player survival world if you keep the working set
small. The goal is a steady **20 TPS** (ticks per second).

## The big levers (in order of impact)

1. **`view-distance` / `simulation-distance`** (`server.properties`). Lower =
   fewer chunks loaded/ticked. Start at `view-distance=8`, `simulation-distance=6`;
   drop to `6`/`4` if you see lag with everyone online. Simulation distance
   matters most for TPS.
2. **Storage.** Use **USB 3.0 storage**, not microSD, for the world. SSD is best,
   but a 500GB HDD is workable for a 3-4 player server. SD-card
   random writes are the most common Pi bottleneck and cause tick stalls.
3. **Memory.** `MC_MEMORY=2600M` (fixed Xms=Xmx) leaves room for the OS + bot.
   Don't over-allocate — the Pi has only 4GB shared with the GPU/OS.
4. **Player count.** Keep `max-players` small (6). Each player loads chunks.

## JVM / GC

`scripts/start_server.sh` uses the **Aikar flags** (G1GC tuned for Minecraft)
with `AlwaysPreTouch` and a fixed heap. These minimise GC pauses, which on a Pi
are felt as stutters. Don't raise the heap past what leaves ~1–1.5GB for the OS.

## PaperMC world tuning

Paper exposes knobs in `config/paper-world-defaults.yml`. Pi-friendly changes:

- **Reduce mob caps / spawn ranges** if farms cause lag:
  `entities.spawning.per-player-mob-spawns: true` (default true) helps.
- **`ticks-per.hopper-transfer`** / hopper checks — increase slightly to cut
  hopper load on big farms.
- **`chunks.max-auto-save-chunks-per-tick`** — lower to smooth save spikes.
- **Merge/limit items**: `entities.spawning.tick-inactive-villagers` and item
  merge radius reduce entity counts.

Apply changes and restart. Change one thing at a time and watch TPS.

## Monitoring

Discord `/metrics` or the dashboard **Performance** button combines Paper TPS,
Pi CPU temperature, 1/5/15-minute load averages, memory, HDD, uptime, and current
or historical undervoltage/throttle flags.

Over SSH, summarize services, HDD, resources, and RCON together:

```bash
./scripts/health_check.sh
```

- In-game / RCON: `tps` (Paper) shows recent TPS; `mspt` shows ms per tick.
- OS: `htop`, `vcgencmd measure_temp` (thermals), `iostat` (disk).
- Keep the Pi **cool** — a hot Pi throttles and TPS drops. Use a heatsink + fan,
  especially in a case.

## Symptoms → fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| Periodic freezes | Storage write stalls | Check USB 3.0, pregenerate, or consider SSD |
| Low TPS with mobs | Too much simulation | Lower `simulation-distance`, mob caps |
| Lag on join/explore | Chunk gen on SD | SSD; pre-generate with a plugin |
| Rising lag over hours | Thermal throttling | Cooling; check `vcgencmd measure_temp` |
| GC stutters | Heap too big/small | Keep `MC_MEMORY` ~2600M, Aikar flags on |
