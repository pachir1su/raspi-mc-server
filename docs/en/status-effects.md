# Status-effect guide

<img src="../assets/player-guides/openmoji/status-effects.svg" alt="Sparkles icon" width="96">

Status effects are timed or instant buffs and debuffs applied to players and
mobs. Potions are only one source: beacons, food, mobs, conduits, and ominous
bottles also apply effects. This guide targets **Minecraft Java Edition 26.1 on
Paper**.

## Display and removal

- The inventory shows each effect's name, amplifier, and remaining duration.
  A higher amplifier such as `II` normally means stronger, not longer.
- A milk bucket clears ordinary beneficial and harmful effects together. It can
  cancel Raid Omen before the raid begins.
- A honey bottle clears **Poison only**, preserving other effects.
- Instant Health and Instant Damage resolve immediately and have no duration.
- Undead are damaged by Instant Health and healed by Instant Damage. Many undead
  are immune to Poison and Regeneration.

## Exact level scaling

`L` below is the displayed level (`I = 1`, `II = 2`). One health point is half a
heart, and 20 game ticks are one second. Unless a row says otherwise, duration
and level are independent: raising the level does not extend the timer.

| Effect | Exact Java 26.1 behavior at level `L` |
|---|---|
| Speed | Movement-speed attribute is multiplied by `1 + 0.20L`: I `+20%`, II `+40%`. |
| Slowness | Movement-speed attribute is multiplied by `1 - 0.15L`: I `−15%`, IV `−60%`, VI `−90%`. Attribute limits prevent negative movement speed. |
| Haste | Block-breaking speed is multiplied by `1 + 0.20L`; attack speed gains `+10% × L`. Haste II is therefore `+40%` mining and `+20%` attack speed. |
| Mining Fatigue | Mining multipliers are I `30%`, II `9%`, III `0.27%`, and IV or higher `0.081%` of the pre-effect speed. Attack speed also loses `10% × L`. |
| Strength | Adds `3L` attack-damage points (`1.5L` hearts) to direct melee attacks. I adds 3 damage; II adds 6. |
| Weakness | Subtracts `4L` attack-damage points (`2L` hearts) from direct melee attacks; the final attack cannot become negative damage. |
| Health Boost | Adds `4L` maximum-health points (`2L` hearts). It does not fill the newly added health automatically. |
| Absorption | Grants up to `4L` absorption points (`2L` yellow hearts); reapplying a weaker amount does not erase a larger remaining absorption pool. |
| Instant Health | Heals living targets by `4 × 2^(L−1)` health points. It instead deals `6 × 2^(L−1)` magic damage to undead. Splash distance scales the resolved amount. |
| Instant Damage | Deals `6 × 2^(L−1)` magic damage to living targets and instead heals undead by `4 × 2^(L−1)` health points. |
| Jump Boost | Adds `0.1L` to upward jump velocity and `L` blocks of safe-fall distance. Higher levels therefore increase both jump height and fall tolerance. |
| Regeneration | Restores 1 health point every `max(1, floor(50 / 2^(L−1)))` ticks: I every 2.5 s, II every 1.25 s, III every 0.6 s. |
| Resistance | Multiplies affected incoming damage by `max(0, 1 − 0.20L)`: I blocks 20%, IV blocks 80%, V blocks 100%. Damage tagged to bypass effects, including the void, is not reduced. |
| Saturation | Instantly adds `L` food points and up to `2L` saturation points, capped by the current food level. This is an instant effect, not a per-second refill. |
| Hunger | Adds `0.005L` exhaustion every tick, or `0.1L` per second. Each accumulated 4 exhaustion removes 1 saturation point, then food when saturation is empty. |
| Poison | Deals 1 health point every `max(1, floor(25 / 2^(L−1)))` ticks: I every 1.25 s, II every 0.6 s. Ordinary Poison stops dealing damage at 1 health. |
| Wither | Deals 1 health point every `max(1, floor(40 / 2^(L−1)))` ticks: I every 2 s, II every 1 s. It can reduce health to zero. |
| Levitation | Each tick moves vertical velocity 20% toward `0.05L` blocks/tick: `vy += (0.05L − vy) × 0.2`. Higher levels rise faster; the effect continually resets fall distance. |
| Luck / Bad Luck | Adds or subtracts exactly `L` from the `luck` attribute. Only loot tables that read this attribute change their results. |

These effects do **not** gain a stronger mechanic from a higher displayed level:
Breath of the Nautilus, Conduit Power, Dolphin's Grace, Fire Resistance,
Glowing, Invisibility, Night Vision, Water Breathing, Blindness, Darkness,
Nausea, Slow Falling, Infested, Oozing, Weaving, and Wind Charged. Commands can
show higher numerals, but only duration changes their ordinary behavior.

Omen levels are metadata rather than a direct stat multiplier. Bad Omen I–V is
carried into Raid Omen and the raid's omen level; winning grants the matching
Hero of the Village level. Trial Omen lasts 15 minutes for each converted Bad
Omen level. Raid Omen itself always uses the same 30-second preparation timer.

## Per-effect mechanics

The values below are the numbers used by the game rather than a generic
"stronger" description. Different levels of the same effect do not stack; the
stronger active instance wins, and level is independent from duration.

### Speed / Slowness

- Speed adds 20% of base movement speed per level. Levels I-V are
  `+20/+40/+60/+80/+100%`.
- Slowness subtracts 15% per level. Levels I-VI are
  `-15/-30/-45/-60/-75/-90%`; level VII reaches the attribute floor and
  practically stops movement.
- If both are active, both attribute modifiers are evaluated. Speed II with
  Slowness I is `+40% - 15% = +25%` of base speed. Sprinting, friction, and
  Soul Speed remain separate rules.

### Haste / Mining Fatigue

- Haste raises block-breaking speed by 20% and attack speed by 10% per level.
  Haste I means 120% mining and +10% attack speed; II means 140% and +20%.
- Mining Fatigue leaves 30%/9%/0.27%/0.081% mining speed at I/II/III/IV+.
  This is exponential rather than a linear subtraction, so Haste cannot
  realistically cancel a high level.
- Tool speed, Efficiency, the underwater penalty without Aqua Affinity, and
  the airborne mining penalty are still calculated separately.

### Strength / Weakness

- Strength adds 3 direct melee damage per level. Levels I-III add `3/6/9`
  damage, or `1.5/3/4.5` hearts.
- Weakness subtracts 4 direct melee damage per level. Levels I-III subtract
  `4/8/12`; an attack at or below zero may have no normal damage event.
- Attack cooldown, critical hits, and target armor are evaluated after weapon
  and attribute damage. The modifier does not normally increase projectile or
  other indirect damage.

### Jump Boost / Slow Falling / Levitation

- Jump Boost adds `0.1` initial upward velocity and one safe-fall block per
  level. It is not a percentage reduction to fall damage.
- Slow Falling limits descent and prevents fall damage and melee critical hits
  while active. Fall distance starts accumulating again if it expires in air.
- Levitation moves vertical velocity 20% toward `0.05L` every tick:
  `vy += (0.05L - vy) × 0.2`. A safe landing is still needed after expiration.

### Resistance / Fire Resistance

- Resistance I-IV reduce affected damage by `20/40/60/80%`; V reaches a
  calculated 100%. Armor and protection enchantments run in their own stages.
- The void, `/kill`, and damage tagged to bypass effects ignore Resistance.
  Some special sources such as starvation are also excluded.
- Fire Resistance prevents supported fire, lava, magma, and fireball damage at
  every level, but does nothing against ordinary melee, falls, or explosions.

### Health Boost / Absorption

- Health Boost adds 4 maximum health, or two hearts, per level. The new capacity
  is not filled automatically, and health above the restored maximum is clipped
  when the effect ends.
- Absorption gives 4 yellow temporary health per level, spent before ordinary
  health. Food and Regeneration cannot refill spent absorption health.

### Regeneration / Poison / Wither

| Level | Regeneration: heal 1 | Poison: damage 1 | Wither: damage 1 |
|---:|---:|---:|---:|
| I | every 50 ticks (2.5 s) | every 25 ticks (1.25 s) | every 40 ticks (2 s) |
| II | every 25 ticks (1.25 s) | every 12 ticks (0.6 s) | every 20 ticks (1 s) |
| III | every 12 ticks (0.6 s) | every 6 ticks (0.3 s) | every 10 ticks (0.5 s) |
| IV | every 6 ticks (0.3 s) | every 3 ticks (0.15 s) | every 5 ticks (0.25 s) |

The intervals are `50 >> (L-1)`, `25 >> (L-1)`, and `40 >> (L-1)` ticks,
with a one-tick minimum. Ordinary Poison stops at 1 health; Wither can kill.
A honey bottle removes Poison only, while milk also clears other effects.

### Instant Health / Instant Damage

| Level | Living target | Undead target |
|---:|---:|---:|
| Instant Health I | heal 4 | damage 6 |
| Instant Health II | heal 8 | damage 12 |
| Instant Damage I | damage 6 | heal 4 |
| Instant Damage II | damage 12 | heal 8 |

Drinking applies the full amount. A splash potion loses strength with distance
from its impact center, and lingering clouds and tipped arrows have their own
delivery multipliers. Milk cannot undo an instant result that already resolved.

### Hunger / Saturation

- Hunger adds `0.005` exhaustion per tick per level. Level I adds 0.1 each
  second, spending one saturation point after 40 idle seconds.
- Saturation instantly adds `L` food and at most `2L` saturation. Saturation
  cannot exceed the current food value, so the effective result depends on the
  bar before application.

### Luck / Bad Luck

- Luck adds one `luck` attribute point per level and Bad Luck removes one. It is
  not a universal improvement or penalty to every chest roll.
- Only loot tables that read `quality` or `bonus_rolls` change. Vanilla survival
  uses this in a limited set of cases, most noticeably fishing treasure logic.

### Invisibility, Glowing, and vision

- Invisibility hides the body but may leave armor, held items, embedded arrows,
  and particles visible. Mob detection range falls sharply, then changes with
  worn armor and the target's behavior.
- Glowing renders an outline through blocks and uses team color when available.
  It still reveals the outline of an invisible target.
- Night Vision changes screen brightness, not block light or spawning rules.
  Blindness limits view, sprinting, and critical hits; Darkness applies a
  separate brightness pulse.

### Underwater effects

- Water Breathing prevents air loss and drowning. Conduit Power provides that
  ability with underwater visibility and mining support, but its Haste-like
  mining bonus does not stack with Haste.
- Breath of the Nautilus pauses air loss without refilling missing air.
  Dolphin's Grace increases swimming speed only and does not preserve oxygen.

### Death triggers and omens

- Infested has a 10% chance on damage to spawn 1-2 silverfish. Oozing creates
  two medium slimes on death, Weaving attempts 2-3 cobwebs, and Wind Charged
  creates a wind explosion with strength from 3 up to but below 5.
- Higher displayed levels do not increase those chances or counts. Oozing obeys
  entity-cramming limits, and non-player Weaving placement obeys `mobGriefing`.
- Bad Omen transfers its level when converted. Raid Omen always prepares for 30
  seconds; Trial Omen lasts 15 minutes per transferred level. Winning the raid
  grants the matching Hero of the Village level.

### Effects whose core behavior does not scale

Breath of the Nautilus, Conduit Power, Dolphin's Grace, Fire Resistance,
Glowing, Invisibility, Night Vision, Water Breathing, Blindness, Darkness,
Nausea, Slow Falling, Infested, Oozing, Weaving, and Wind Charged gain no
stronger core mechanic from a command-created level II or higher.

## Beneficial effects

| Effect | What it does | Representative source or caveat |
|---|---|---|
| <img src="../assets/player-guides/status-effects/absorption.png" alt="" width="32"> Absorption | Adds temporary yellow health separate from maximum health. | Golden apples, enchanted golden apples, Totem of Undying |
| <img src="../assets/player-guides/status-effects/breath-of-the-nautilus.png" alt="" width="32"> Breath of the Nautilus | Pauses oxygen consumption but does not refill missing air. | Riding a tamed nautilus |
| <img src="../assets/player-guides/status-effects/conduit-power.png" alt="" width="32"> Conduit Power | Provides underwater equivalents of Water Breathing, Night Vision, and Haste. | Touching water/rain within an active conduit's range |
| <img src="../assets/player-guides/status-effects/dolphins-grace.png" alt="" width="32"> Dolphin's Grace | Greatly increases swimming speed. | Swimming near a dolphin |
| <img src="../assets/player-guides/status-effects/fire-resistance.png" alt="" width="32"> Fire Resistance | Prevents fire, lava, magma, and fireball damage, not the void or every special source. | Potions, Totem of Undying, piglin-bartered potions |
| <img src="../assets/player-guides/status-effects/glowing.png" alt="" width="32"> Glowing | Shows the entity's outline through blocks. | Spectral arrows; raiders revealed by a bell |
| <img src="../assets/player-guides/status-effects/haste.png" alt="" width="32"> Haste | Increases mining and attack speed. | Beacon |
| <img src="../assets/player-guides/status-effects/health-boost.png" alt="" width="32"> Health Boost | Raises maximum health; the extra maximum disappears when the effect ends. | Mainly commands or custom content |
| <img src="../assets/player-guides/status-effects/hero-of-the-village.png" alt="" width="32"> Hero of the Village | Discounts villager prices and enables villager gifts. | Winning a raid |
| <img src="../assets/player-guides/status-effects/instant-health.png" alt="" width="32"> Instant Health | Restores health immediately and damages undead. | Healing potions and tipped arrows |
| <img src="../assets/player-guides/status-effects/invisibility.png" alt="" width="32"> Invisibility | Hides the body, but held/worn items and particles may remain visible; mob detection range is reduced. | Invisibility potions |
| <img src="../assets/player-guides/status-effects/jump-boost.png" alt="" width="32"> Jump Boost | Raises jump height and reduces fall damage. | Leaping potions, beacon |
| <img src="../assets/player-guides/status-effects/luck.png" alt="" width="32"> Luck | Raises quality calculations in loot tables that use `luck`; vanilla survival impact is limited. | Primarily commands in 26.1 |
| <img src="../assets/player-guides/status-effects/night-vision.png" alt="" width="32"> Night Vision | Makes dark areas and underwater scenes visible. | Night Vision potions |
| <img src="../assets/player-guides/status-effects/regeneration.png" alt="" width="32"> Regeneration | Restores health at intervals. | Potions, golden apples, Totem of Undying, beacon |
| <img src="../assets/player-guides/status-effects/resistance.png" alt="" width="32"> Resistance | Reduces most incoming damage per level, excluding sources such as void and starvation. | Beacon, Turtle Master potions, enchanted golden apples |
| <img src="../assets/player-guides/status-effects/saturation.png" alt="" width="32"> Saturation | Instantly restores food and saturation. | Certain suspicious stews, commands |
| <img src="../assets/player-guides/status-effects/slow-falling.png" alt="" width="32"> Slow Falling | Removes fall damage and slows descent; sprint-jumping is disabled. | Slow Falling potions |
| <img src="../assets/player-guides/status-effects/speed.png" alt="" width="32"> Speed | Raises walking/running speed and field of view. | Swiftness potions, beacon |
| <img src="../assets/player-guides/status-effects/strength.png" alt="" width="32"> Strength | Raises melee attack damage. | Strength potions, beacon |
| <img src="../assets/player-guides/status-effects/water-breathing.png" alt="" width="32"> Water Breathing | Stops air loss and drowning. | Potions; brief effect from wearing a turtle shell |

## Harmful effects

| Effect | What it does | Representative source or response |
|---|---|---|
| <img src="../assets/player-guides/status-effects/blindness.png" alt="" width="32"> Blindness | Severely limits view and prevents sprinting and critical attacks. | Suspicious stew and other sources; clear with milk |
| <img src="../assets/player-guides/status-effects/darkness.png" alt="" width="32"> Darkness | Pulses screen brightness down and interferes with vision even alongside Night Vision. | Sculk shriekers and Wardens |
| <img src="../assets/player-guides/status-effects/hunger.png" alt="" width="32"> Hunger | Accelerates food exhaustion from actions. | Rotten flesh, husk attacks, pufferfish |
| <img src="../assets/player-guides/status-effects/instant-damage.png" alt="" width="32"> Instant Damage | Deals immediate magic damage and heals undead. | Harming potions and tipped arrows |
| <img src="../assets/player-guides/status-effects/levitation.png" alt="" width="32"> Levitation | Raises an entity and creates a fall hazard when it ends. | Shulker bullets |
| <img src="../assets/player-guides/status-effects/mining-fatigue.png" alt="" width="32"> Mining Fatigue | Greatly reduces mining and attack speed. | Elder Guardian; clear with milk |
| <img src="../assets/player-guides/status-effects/nausea.png" alt="" width="32"> Nausea | Warps the screen; distortion strength can be reduced in Accessibility settings. | Pufferfish, remaining in a Nether portal |
| <img src="../assets/player-guides/status-effects/poison.png" alt="" width="32"> Poison | Deals periodic damage but ordinary Poison cannot reduce health below 1. | Potions, cave spiders, bees, pufferfish; honey or milk |
| <img src="../assets/player-guides/status-effects/slowness.png" alt="" width="32"> Slowness | Reduces movement speed and field of view. | Potions, stray arrows, Turtle Master potions |
| <img src="../assets/player-guides/status-effects/unluck.png" alt="" width="32"> Bad Luck | Lowers `luck`-based loot calculations; vanilla survival impact is limited. | Primarily commands |
| <img src="../assets/player-guides/status-effects/weakness.png" alt="" width="32"> Weakness | Reduces melee attack damage. | Potions/arrows; required for curing zombie villagers |
| <img src="../assets/player-guides/status-effects/wither.png" alt="" width="32"> Wither | Blackens hearts and deals periodic damage that, unlike Poison, can kill. | Wither, wither skeletons, wither roses, suspicious stew |

## Trial and death-triggered effects

| Effect | What it does | Source and use |
|---|---|---|
| <img src="../assets/player-guides/status-effects/infested.png" alt="" width="32"> Infested | Each damage event has a 10% chance to spawn 1–2 silverfish; level does not change the chance or count. | Awkward Potion + Stone; silverfish are immune |
| <img src="../assets/player-guides/status-effects/oozing.png" alt="" width="32"> Oozing | Spawns two size-2 slimes on death, limited by nearby-slime/entity-cramming checks; level does not change the count. | Awkward Potion + Slime Block; slimes are immune |
| <img src="../assets/player-guides/status-effects/weaving.png" alt="" width="32"> Weaving | Attempts to place 2–3 cobwebs within one block on death and reduces the movement penalty in cobwebs; level does not change it. | Awkward Potion + Cobweb; non-player placement obeys `mobGriefing` |
| <img src="../assets/player-guides/status-effects/wind-charged.png" alt="" width="32"> Wind Charged | Emits a wind explosion with random strength from `3.0` up to but below `5.0` on death; level does not change the burst. | Awkward Potion + Breeze Rod |

Ominous trial spawners can also deploy potions with these effects. Isolate farms
that use them so spawned slimes, silverfish, or cobwebs cannot damage operations.

## Omen effects

| Effect | Behavior |
|---|---|
| <img src="../assets/player-guides/status-effects/bad-omen.png" alt="" width="32"> Bad Omen | Drinking an ominous bottle applies level I–V for 1 hour 40 minutes. It converts to Raid Omen in a village or Trial Omen near an eligible trial spawner. |
| <img src="../assets/player-guides/status-effects/raid-omen.png" alt="" width="32"> Raid Omen | A 30-second preparation effect created in a village. A raid starts where it was acquired when the timer expires; milk can cancel it first. |
| <img src="../assets/player-guides/status-effects/trial-omen.png" alt="" width="32"> Trial Omen | Created in a trial chamber. It lasts 15 minutes per converted Bad Omen level and turns detecting trial spawners ominous. |

## Beacon tiers

Tier 1 offers Speed or Haste; tier 2 adds Resistance or Jump Boost; tier 3 adds
Strength. A complete tier-4 pyramid can upgrade the selected primary effect to
II or add Regeneration I as the secondary effect. Conduit Power is separate from
beacons.

See [brewing](brewing.md) for ingredients and transformations and
[food](food.md) for hunger and saturation values.

## Research baseline

- [Minecraft Java Edition 26.1 release notes](https://feedback.minecraft.net/hc/en-us/articles/44551668333837-Minecraft-Java-Edition-26-1)
- [Minecraft Java Edition 1.21.11: Breath of the Nautilus](https://www.minecraft.net/en-us/article/minecraft-java-edition-1-21-11)
- [Minecraft 24w13a: omens and new mob effects](https://www.minecraft.net/en-us/article/minecraft-snapshot-24w13a)
- [Minecraft 26.1 generated registries](https://github.com/misode/mcmeta/blob/26.1-summary/registries/data.json)
