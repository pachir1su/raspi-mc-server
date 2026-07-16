# Enchantment guide

<img src="../assets/player-guides/openmoji/enchantments.svg" alt="Open book icon" width="96">

This guide covers survival enchantments for this server's baseline,
**Minecraft Java Edition 26.1 on Paper**. Levels are the highest obtainable in
normal play, not arbitrary command-created levels. Bedrock clients joining
through Geyser are still governed by the Java/Paper server mechanics.

## Basics

- An enchanting table uses lapis lazuli and up to 15 bookshelves. A displayed
  `30` is the required experience-level threshold; accepting it spends 3 levels.
- An anvil combines equipment and enchanted books. Its prior-work penalty grows
  with repeated work; a survival operation costing 40 or more levels is rejected
  as **Too Expensive!**.
- A grindstone removes non-curse enchantments and returns some experience.
- Experience orbs first repair damaged Mending equipment held or worn in an
  eligible slot.
- Treasure enchantments never appear in the enchanting table. They require
  their specific sources such as structure loot, fishing, trading, or bartering.

In the tables below, `L` means the enchantment level and one damage point is
half a heart. Armor enchantments add enchantment protection factor (`EPF`): the
game totals applicable EPF across all four armor pieces, caps it at 20, then
reduces that damage by `4% × EPF` (at most 80%).

## How an enchantment result is selected

### Bookshelves and the table

- Only bookshelves in the ring exactly two horizontal blocks from the table,
  at the table's height or one block above, count. At most 15 apply, and the
  intervening block must be empty; even small blocks such as torches or flowers
  can break the connection.
- With 15 shelves, the third option can require level 30. That number is an
  eligibility threshold: accepting it spends 3 experience levels and 3 lapis.
  The upper options spend 1/1 and 2/2 respectively.
- The tooltip reveals only one enchantment from the result. Compatible hidden
  enchantments may be added after the option is accepted.

### Offers and extra enchantments

- Removing the item or reopening the table does not reroll offers. Enchanting
  any item, or enchanting and then grinding an item, generates a new set.
- Shovels, pickaxes, axes, and hoes share a tool offer category. Changing iron
  to gold or diamond does not by itself change that category's current offers.
- At least one enchantment is guaranteed. The adjusted enchanting level then
  repeatedly rolls for extras after incompatible candidates are removed.
- Gold has high enchantability and is more likely to receive high or multiple
  results. Stone and diamond are lower; netherite is higher than diamond. The
  same displayed level-30 option therefore has different result distributions.

### Books, anvils, and grindstones

- Enchanting a book draws from non-treasure table candidates but produces one
  enchantment. Moving it to equipment adds an anvil experience cost.
- Combining equal levels raises the result by one within the normal maximum:
  Efficiency IV + IV becomes V, while IV + III remains IV.
- Prior-work penalties grow `0, 1, 3, 7, 15, 31...`. A final survival cost of
  40 or more is rejected as **Too Expensive!**.
- A grindstone removes non-curse enchantments, returns some experience, and
  clears prior-work penalty. Binding and Vanishing cannot be removed this way.

## Armor

| Enchantment | Max | Equipment | Effect |
|---|---:|---|---|
| Protection | IV | All armor | Adds `L` EPF against almost every damage source that does not bypass invulnerability: I–IV add 1–4 EPF per piece. |
| Fire Protection | IV | All armor | Adds `2L` EPF against fire damage and reduces burning duration by `15% × L` per equipped piece. |
| Blast Protection | IV | All armor | Adds `2L` EPF against explosions and `0.15L` explosion-knockback resistance per equipped piece. |
| Projectile Protection | IV | All armor | Adds `2L` EPF against projectile-tagged damage: II adds 4 EPF, IV adds 8 per piece. |
| Feather Falling | IV | Boots | Adds `3L` EPF against fall-tagged damage, including ender pearls. IV supplies 12 EPF and can coexist with one armor protection type. |
| Respiration | III | Helmet | Each tick that would consume air succeeds with probability `1/(L+1)`. Average full-air time is therefore about 30/45/60 seconds at I/II/III instead of 15 seconds. It delays drowning; it does not change the later 1-second damage interval. |
| Aqua Affinity | I | Helmet | Removes the underwater mining-speed penalty. The separate penalty for floating remains. |
| Depth Strider | III | Boots | Adds `L/3` water-movement efficiency: I removes one third of the slowdown, II two thirds, and III removes it. |
| Frost Walker | II | Boots | Freezes eligible water in radius `L+2`: 3 blocks at I, 4 at II. Every level also prevents damage tagged as burning from stepping, such as magma blocks. |
| Soul Speed | III | Boots | On soul-speed blocks, adds `0.03 + 0.0105L` movement-speed attribute (0.0405/0.051/0.0615) and removes terrain inefficiency. Each eligible step has `4% × L` chance to cost 1 durability. |
| Swift Sneak | III | Leggings | Adds `15% × L` of normal speed to sneaking: the base 30% becomes 45%/60%/75% at I/II/III. |
| Thorns | III | All armor | Each equipped level gives a `15% × L` trigger chance (15/30/45%). A trigger rolls floating-point damage from `1.0` up to but below `5.0` and costs the selected armor piece 2 durability. |
| Curse of Binding | I | Wearable equipment | Prevents removal in Survival until death or until the item breaks. |

## Melee weapons and spears

| Enchantment | Max | Equipment | Effect |
|---|---:|---|---|
| Sharpness | V | Swords, spears, and other sharp weapons | Adds `1 + 0.5(L−1)` damage: +1/+1.5/+2/+2.5/+3 at I–V against eligible targets. |
| Smite | V | Weapons | Adds `2.5L` damage against `sensitive_to_smite` undead: +2.5 to +12.5 at I–V. |
| Bane of Arthropods | V | Weapons | Adds `2.5L` damage to tagged arthropods and applies Slowness IV for a random 1.5 s to `1.5 + 0.5(L−1)` s (up to 3.5 s at V). |
| Knockback | II | Melee weapons | Adds `L` knockback strength. Actual distance still depends on resistance, sprint state, friction, and collisions. |
| Fire Aspect | II | Supported melee weapons | Ignites a directly hit target for `4L` seconds: 4 s at I, 8 s at II. |
| Looting | III | Melee weapons | Supplies loot-table level `L`. Typical common-drop pools add a random `0..L` items, while equipped-item drop chance gains `1` percentage point per level; individual loot tables may use different formulas. |
| Sweeping Edge | III | Sword | Sets sweep secondary-damage ratio to `L/(L+1)`: 50%, 66.7%, and 75% at I–III. Java only. |
| Lunge | III | Spear | After a valid Jab, applies horizontal impulse `0.458L`, exhaustion `4L`, and exactly 1 item durability damage at every level. Survival needs at least 7 food; it cannot activate while riding, gliding, or in water. |

## Maces, tridents, and ranged weapons

| Enchantment | Max | Equipment | Effect |
|---|---:|---|---|
| Density | V | Mace | Adds `0.5L` smash damage for every fallen block counted by the mace: +0.5 to +2.5 damage per block at I–V. |
| Breach | IV | Mace | Subtracts `15% × L` from the target's armor effectiveness: 15/30/45/60% at I–IV. It does not simply ignore that percentage of armor points. |
| Wind Burst | III | Mace | A smash after at least 1.5 blocks of fall creates a 3.5-radius wind burst with knockback multiplier 1.2/1.75/2.2 at I/II/III. Treasure from ominous vaults. |
| Impaling | V | Trident | Adds `2.5L` damage to mobs in the Java `sensitive_to_impaling` tag: +2.5 to +12.5. Merely being wet is not enough on this server. |
| Loyalty | III | Trident | Adds return acceleration `L` to a thrown trident. The value is 1/2/3 at I–III, so higher levels close distance faster. |
| Riptide | III | Trident | Sets spin-attack strength to `1.5 + 0.75(L−1)`: 1.5/2.25/3.0 at I–III. It requires water or rain and prevents normal throwing. |
| Channeling | I | Trident | During a thunderstorm, summons lightning on a sky-exposed target hit by the thrown trident. |
| Power | V | Bow | Adds `1 + 0.5(L−1)` arrow damage in 26.1: +1/+1.5/+2/+2.5/+3 at I–V. Final damage still depends on draw strength and critical randomness. |
| Punch | II | Bow | Adds `L` arrow knockback strength: 1 at I, 2 at II. |
| Flame | I | Bow | Ignites spawned arrows for 100 ticks (5 seconds); there is no higher survival level. |
| Infinity | I | Bow | With at least one normal arrow present, normal arrows are not consumed. Tipped/spectral arrows and bow durability are still consumed. |
| Multishot | I | Crossbow | Adds 2 projectiles and 10° spread to the normal shot: one projectile is consumed and three are fired. The side shots do not normally stack on one target. |
| Piercing | IV | Crossbow | Adds piercing value `L`, allowing an arrow to pass through `L` targets and potentially hit `L+1` total; it bypasses shields and does not affect fireworks. |
| Quick Charge | III | Crossbow | Subtracts `0.25L` seconds from the 1.25-second charge: 1.00/0.75/0.50 s at I–III. |

## Tools, fishing rods, and general enchantments

| Enchantment | Max | Equipment | Effect |
|---|---:|---|---|
| Efficiency | V | Pickaxe, axe, shovel, hoe, shears | When the tool is suitable and base speed exceeds 1, adds `L²+1` mining efficiency: +2/+5/+10/+17/+26 at I–V before Haste and other multipliers. |
| Fortune | III | Mining tools | Supplies loot-table level `L`; there is no single formula for every block. The common ore multiplier is `max(1, random integer 0..L+1)`, averaging 1.33×/1.75×/2.20× at I/II/III; redstone, lapis, crops, and other tables use their own caps. |
| Silk Touch | I | Mining tools | Drops supported blocks themselves instead of their transformed loot. |
| Luck of the Sea | III | Fishing rod | Adds exactly `L` to the fishing-luck parameter. Fishing loot tables use that value to favor treasure and disfavor junk; it is not a universal percentage applied to every entry. |
| Lure | III | Fishing rod | Reduces the generated wait time by `5L` seconds: 5/10/15 seconds at I–III, before weather and open-water checks. |
| Unbreaking | III | Durable equipment | Non-armor consumes durability with probability `1/(L+1)`, giving expected lifetime 2×/3×/4×. Armor consumes with probability `0.6 + 0.4/(L+1)`: 80%/73.3%/70%, only about 1.25×/1.36×/1.43× life. |
| Mending | I | Durable equipment | Each collected XP point repairs 2 durability on one randomly selected damaged eligible item; any XP left after repair enters the player's XP bar. |
| Curse of Vanishing | I | Most equipment | Deletes the item on player death instead of dropping it. It does not delete it when `keepInventory=true`. |

## Level-by-level performance and edge cases

### Protection families

| Enchantment | I | II | III | IV | Separate modifier |
|---|---:|---:|---:|---:|---|
| Protection | 1 EPF | 2 | 3 | 4 | Almost every eligible source |
| Fire Protection | 2 EPF | 4 | 6 | 8 | `15% × L` shorter burning per piece |
| Blast Protection | 2 EPF | 4 | 6 | 8 | `0.15L` explosion knockback resistance per piece |
| Projectile Protection | 2 EPF | 4 | 6 | 8 | Projectile-tagged damage only |
| Feather Falling | 3 EPF | 6 | 9 | 12 | Falls and ender-pearl damage |

- Applicable EPF across all pieces is capped at 20 and reduces damage by
  `EPF × 4%`. Four Protection IV pieces give 16 EPF, or 64%; a matching
  specialized protection reaches the cap sooner.
- Feather Falling is compatible with one boot protection family and both are
  counted. Enchantment protection runs as a separate stage after armor and
  armor-toughness calculations.

### Breathing, water, and movement armor

| Enchantment | I | II | III |
|---|---:|---:|---:|
| Respiration: air-consumption chance | 1/2 | 1/3 | 1/4 |
| Respiration: average full-air time | about 30 s | about 45 s | about 60 s |
| Depth Strider: water slowdown removed | 1/3 | 2/3 | all |
| Swift Sneak: final sneak speed | 45% | 60% | 75% |
| Soul Speed: speed attribute added | 0.0405 | 0.051 | 0.0615 |

- Aqua Affinity removes the underwater mining penalty but the separate airborne
  slowdown remains. Respiration delays drowning; it does not change the later
  damage interval.
- Frost Walker I/II freezes in a 3/4-block radius, conflicts with Depth Strider,
  and at every level prevents the supported stepping-on-burning damage.
- Soul Speed consumes one durability on eligible movement with 4/8/12% chance
  at I/II/III.

### Damage enchantments

| Enchantment | I | II | III | IV | V |
|---|---:|---:|---:|---:|---:|
| Sharpness added damage | 1 | 1.5 | 2 | 2.5 | 3 |
| Smite/Bane added damage | 2.5 | 5 | 7.5 | 10 | 12.5 |
| Density per fallen block | 0.5 | 1 | 1.5 | 2 | 2.5 |
| Breach armor-effectiveness reduction | 15% | 30% | 45% | 60% | — |
| Sweeping Edge primary-damage ratio | 50% | 66.7% | 75% | — | — |

- Bane applies Slowness IV for at least 1.5 seconds; its random upper bound rises
  by 0.5 seconds per level and reaches 3.5 seconds at V.
- Fire Aspect I/II ignites for 4/8 seconds. Fire tick damage, Fire Resistance,
  water, and rain are evaluated separately.
- Thorns I/II/III has 15/30/45% trigger chance per equipped level. The armor
  piece selected for an actual reflection loses 2 durability.

### Tridents, bows, crossbows, maces, and spears

- Impaling adds 2.5 damage per level only to Java entities in the
  `sensitive_to_impaling` tag, not simply every wet target.
- Riptide I/II/III uses spin strength 1.5/2.25/3.0 and requires water or rain.
  It conflicts with Loyalty and Channeling and disables normal throwing.
- Quick Charge I/II/III gives 1.00/0.75/0.50-second crossbow charge. Piercing IV
  can pass through four targets and hit five total, bypasses shields, and does
  not apply to fireworks.
- Wind Burst I/II/III uses knockback multipliers 1.2/1.75/2.2 after a successful
  mace smash from at least 1.5 blocks. It is treasure from ominous vaults.
- Lunge I/II/III applies horizontal impulse 0.458/0.916/1.374 and exhaustion
  4/8/12 after a valid spear Jab. It always costs exactly one durability and is
  disabled below 7 food, while mounted, gliding, or in water.

### Tools, durability, and loot

| Enchantment | I | II | III | IV | V |
|---|---:|---:|---:|---:|---:|
| Efficiency bonus `L²+1` | +2 | +5 | +10 | +17 | +26 |
| Non-armor durability-use chance | 50% | 33.3% | 25% | 20% | 16.7% |
| Armor durability-use chance | 80% | 73.3% | 70% | 68% | 66.7% |
| Lure wait reduction | 5 s | 10 s | 15 s | — | — |

- Efficiency adds its bonus only when the tool is suitable and base breaking
  speed exceeds 1. Haste, Mining Fatigue, and water penalties follow.
- Fortune reads each block's loot table, so no single formula covers all blocks.
  The common ore multiplier averages about 1.33/1.75/2.20 at I/II/III, while
  redstone, lapis, and crops use separate quantities and caps.
- Mending repairs 2 durability per XP point on one randomly selected damaged
  eligible held or worn item. Only XP left after a full repair reaches the bar.
- Multi-durability actions roll Unbreaking for every unit. Unbreaking III gives
  non-armor four times expected life, but armor only about 1.43 times.

## Mutually exclusive combinations

Normal anvils and enchanting tables reject combinations within each line:

- Protection / Fire Protection / Blast Protection / Projectile Protection
- Sharpness / Smite / Bane of Arthropods / Impaling / Density / Breach
- Depth Strider / Frost Walker
- Fortune / Silk Touch
- Multishot / Piercing
- Infinity / Mending
- Riptide / Loyalty and Riptide / Channeling (`Loyalty + Channeling` is valid)

## Treasure quick reference

| Enchantment | Representative sources |
|---|---|
| Mending, Frost Walker | Librarian trading, loot, fishing |
| Soul Speed | Piglin bartering, bastion remnants |
| Swift Sneak | Ancient-city chests |
| Wind Burst | Ominous trial-chamber vaults |
| Binding and Vanishing curses | Loot, fishing, librarian trading, and other sources |

See [villager trading](villager-trading.md) for trade mechanics and
[ores and resources](ores-and-resources.md) for Fortune/Silk Touch choices.

## Research baseline

- [Minecraft Java Edition 26.1 release notes](https://feedback.minecraft.net/hc/en-us/articles/44551668333837-Minecraft-Java-Edition-26-1)
- [Minecraft Java Edition 1.21.11 release notes](https://www.minecraft.net/en-us/article/minecraft-java-edition-1-21-11)
- [Minecraft 26.1 generated enchantment definitions](https://github.com/misode/mcmeta/tree/26.1-data-json/data/minecraft/enchantment)
- [Minecraft 26.1 generated enchantment tags](https://github.com/misode/mcmeta/tree/26.1-data-json/data/minecraft/tags/enchantment)
