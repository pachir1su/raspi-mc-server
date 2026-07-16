# Brewing guide

<img src="../assets/player-guides/openmoji/brewing.svg" alt="Alembic icon" width="96">

This is the vanilla brewing system for **Minecraft Java Edition 26.1 on
Paper**. For effects regardless of their source, see [status effects](status-effects.md).

## Set up a brewing stand

<img src="../assets/player-guides/brewing/brewing-stand-interface.png" alt="Empty Brewing Stand interface" width="350">

1. <img src="../assets/player-guides/brewing/blaze-powder.png" alt="Blaze Powder" width="28"> Put **Blaze Powder** in the fuel slot. One powder fuels 20 brewing operations;
   each operation can process all three bottle slots together.
2. Fill glass bottles with water and place them in the bottom slots.
3. <img src="../assets/player-guides/brewing/nether-wart.png" alt="Nether Wart" width="28"> For most recipes, brew **Nether Wart** into the water bottles to make Awkward
   Potions first.
4. Put the effect ingredient in the top slot, then brew any desired modifiers.

<img src="../assets/player-guides/brewing/water-bottle.png" alt="Water Bottle" width="36"> <img src="../assets/player-guides/brewing/splash-water-bottle.png" alt="Splash Water Bottle" width="36"> <img src="../assets/player-guides/brewing/lingering-water-bottle.png" alt="Lingering Water Bottle" width="36">

The item images in this guide are ordered **drinkable · splash · lingering**.

Craft a stand from one Blaze Rod and three blocks in the stone crafting tag. A
cauldron fills only three bottles in Java Edition, so an infinite water source is
usually easier outside automation.

## Potion table

![Bilingual potion brewing flow from water bottle to lingering potion](../assets/player-guides/diagrams/brewing-flow.svg)

`Base / extended / strong` durations below are for drinkable potions. `—` means
that variant does not exist.

| Result | Ingredient added to Awkward Potion | Base | Redstone extended | Glowstone strong |
|---|---|---:|---:|---:|
| <img src="../assets/player-guides/brewing/night-vision.png" alt="Potion of Night Vision" width="28"> <img src="../assets/player-guides/brewing/splash-night-vision.png" alt="Splash Potion of Night Vision" width="28"> <img src="../assets/player-guides/brewing/lingering-night-vision.png" alt="Lingering Potion of Night Vision" width="28"><br>Night Vision | <img src="../assets/player-guides/brewing/golden-carrot.png" alt="" width="28"> Golden Carrot | 3:00 | 8:00 | — |
| <img src="../assets/player-guides/brewing/invisibility.png" alt="Potion of Invisibility" width="28"> <img src="../assets/player-guides/brewing/splash-invisibility.png" alt="Splash Potion of Invisibility" width="28"> <img src="../assets/player-guides/brewing/lingering-invisibility.png" alt="Lingering Potion of Invisibility" width="28"><br>Invisibility | <img src="../assets/player-guides/brewing/fermented-spider-eye.png" alt="" width="28"> Night Vision + Fermented Spider Eye | 3:00 | 8:00 | — |
| <img src="../assets/player-guides/brewing/leaping.png" alt="Potion of Leaping" width="28"> <img src="../assets/player-guides/brewing/splash-leaping.png" alt="Splash Potion of Leaping" width="28"> <img src="../assets/player-guides/brewing/lingering-leaping.png" alt="Lingering Potion of Leaping" width="28"><br>Leaping | <img src="../assets/player-guides/brewing/rabbit-foot.png" alt="" width="28"> Rabbit's Foot | 3:00 | 8:00 | II 1:30 |
| <img src="../assets/player-guides/brewing/fire-resistance.png" alt="Potion of Fire Resistance" width="28"> <img src="../assets/player-guides/brewing/splash-fire-resistance.png" alt="Splash Potion of Fire Resistance" width="28"> <img src="../assets/player-guides/brewing/lingering-fire-resistance.png" alt="Lingering Potion of Fire Resistance" width="28"><br>Fire Resistance | <img src="../assets/player-guides/brewing/magma-cream.png" alt="" width="28"> Magma Cream | 3:00 | 8:00 | — |
| <img src="../assets/player-guides/brewing/swiftness.png" alt="Potion of Swiftness" width="28"> <img src="../assets/player-guides/brewing/splash-swiftness.png" alt="Splash Potion of Swiftness" width="28"> <img src="../assets/player-guides/brewing/lingering-swiftness.png" alt="Lingering Potion of Swiftness" width="28"><br>Swiftness | <img src="../assets/player-guides/brewing/sugar.png" alt="" width="28"> Sugar | 3:00 | 8:00 | II 1:30 |
| <img src="../assets/player-guides/brewing/slowness.png" alt="Potion of Slowness" width="28"> <img src="../assets/player-guides/brewing/splash-slowness.png" alt="Splash Potion of Slowness" width="28"> <img src="../assets/player-guides/brewing/lingering-slowness.png" alt="Lingering Potion of Slowness" width="28"><br>Slowness | <img src="../assets/player-guides/brewing/fermented-spider-eye.png" alt="" width="28"> Swiftness or Leaping + Fermented Spider Eye | 1:30 | 4:00 | IV 0:20 |
| <img src="../assets/player-guides/brewing/water-breathing.png" alt="Potion of Water Breathing" width="28"> <img src="../assets/player-guides/brewing/splash-water-breathing.png" alt="Splash Potion of Water Breathing" width="28"> <img src="../assets/player-guides/brewing/lingering-water-breathing.png" alt="Lingering Potion of Water Breathing" width="28"><br>Water Breathing | <img src="../assets/player-guides/brewing/pufferfish.png" alt="" width="28"> Pufferfish | 3:00 | 8:00 | — |
| <img src="../assets/player-guides/brewing/healing.png" alt="Potion of Healing" width="28"> <img src="../assets/player-guides/brewing/splash-healing.png" alt="Splash Potion of Healing" width="28"> <img src="../assets/player-guides/brewing/lingering-healing.png" alt="Lingering Potion of Healing" width="28"><br>Healing | <img src="../assets/player-guides/brewing/glistering-melon-slice.png" alt="" width="28"> Glistering Melon Slice | Instant: 4 health | — | II: instant 8 health |
| <img src="../assets/player-guides/brewing/harming.png" alt="Potion of Harming" width="28"> <img src="../assets/player-guides/brewing/splash-harming.png" alt="Splash Potion of Harming" width="28"> <img src="../assets/player-guides/brewing/lingering-harming.png" alt="Lingering Potion of Harming" width="28"><br>Harming | <img src="../assets/player-guides/brewing/fermented-spider-eye.png" alt="" width="28"> Healing or Poison + Fermented Spider Eye | Instant: 6 damage | — | II: instant 12 damage |
| <img src="../assets/player-guides/brewing/poison.png" alt="Potion of Poison" width="28"> <img src="../assets/player-guides/brewing/splash-poison.png" alt="Splash Potion of Poison" width="28"> <img src="../assets/player-guides/brewing/lingering-poison.png" alt="Lingering Potion of Poison" width="28"><br>Poison | <img src="../assets/player-guides/brewing/spider-eye.png" alt="" width="28"> Spider Eye | 0:45 | 1:30 | II 0:21 |
| <img src="../assets/player-guides/brewing/regeneration.png" alt="Potion of Regeneration" width="28"> <img src="../assets/player-guides/brewing/splash-regeneration.png" alt="Splash Potion of Regeneration" width="28"> <img src="../assets/player-guides/brewing/lingering-regeneration.png" alt="Lingering Potion of Regeneration" width="28"><br>Regeneration | <img src="../assets/player-guides/brewing/ghast-tear.png" alt="" width="28"> Ghast Tear | 0:45 | 2:00 | II 0:22 |
| <img src="../assets/player-guides/brewing/strength.png" alt="Potion of Strength" width="28"> <img src="../assets/player-guides/brewing/splash-strength.png" alt="Splash Potion of Strength" width="28"> <img src="../assets/player-guides/brewing/lingering-strength.png" alt="Lingering Potion of Strength" width="28"><br>Strength | <img src="../assets/player-guides/brewing/blaze-powder.png" alt="" width="28"> Blaze Powder | 3:00 | 8:00 | II 1:30 |
| <img src="../assets/player-guides/brewing/weakness.png" alt="Potion of Weakness" width="28"> <img src="../assets/player-guides/brewing/splash-weakness.png" alt="Splash Potion of Weakness" width="28"> <img src="../assets/player-guides/brewing/lingering-weakness.png" alt="Lingering Potion of Weakness" width="28"><br>Weakness | <img src="../assets/player-guides/brewing/fermented-spider-eye.png" alt="" width="28"> **Water Bottle** + Fermented Spider Eye | 1:30 | 4:00 | — |
| <img src="../assets/player-guides/brewing/turtle-master.png" alt="Potion of the Turtle Master" width="28"> <img src="../assets/player-guides/brewing/splash-turtle-master.png" alt="Splash Potion of the Turtle Master" width="28"> <img src="../assets/player-guides/brewing/lingering-turtle-master.png" alt="Lingering Potion of the Turtle Master" width="28"><br>Turtle Master | <img src="../assets/player-guides/brewing/turtle-shell.png" alt="" width="28"> Turtle Shell | 0:20 | 0:40 | II 0:20 |
| <img src="../assets/player-guides/brewing/slow-falling.png" alt="Potion of Slow Falling" width="28"> <img src="../assets/player-guides/brewing/splash-slow-falling.png" alt="Splash Potion of Slow Falling" width="28"> <img src="../assets/player-guides/brewing/lingering-slow-falling.png" alt="Lingering Potion of Slow Falling" width="28"><br>Slow Falling | <img src="../assets/player-guides/brewing/phantom-membrane.png" alt="" width="28"> Phantom Membrane | 1:30 | 4:00 | — |
| <img src="../assets/player-guides/brewing/infestation.png" alt="Potion of Infestation" width="28"> <img src="../assets/player-guides/brewing/splash-infestation.png" alt="Splash Potion of Infestation" width="28"> <img src="../assets/player-guides/brewing/lingering-infestation.png" alt="Lingering Potion of Infestation" width="28"><br>Infestation | <img src="../assets/player-guides/brewing/stone.png" alt="" width="28"> Stone | 3:00 | — | — |
| <img src="../assets/player-guides/brewing/oozing.png" alt="Potion of Oozing" width="28"> <img src="../assets/player-guides/brewing/splash-oozing.png" alt="Splash Potion of Oozing" width="28"> <img src="../assets/player-guides/brewing/lingering-oozing.png" alt="Lingering Potion of Oozing" width="28"><br>Oozing | <img src="../assets/player-guides/brewing/slime-block.png" alt="" width="28"> Slime Block | 3:00 | — | — |
| <img src="../assets/player-guides/brewing/weaving.png" alt="Potion of Weaving" width="28"> <img src="../assets/player-guides/brewing/splash-weaving.png" alt="Splash Potion of Weaving" width="28"> <img src="../assets/player-guides/brewing/lingering-weaving.png" alt="Lingering Potion of Weaving" width="28"><br>Weaving | <img src="../assets/player-guides/brewing/cobweb.png" alt="" width="28"> Cobweb | 3:00 | — | — |
| <img src="../assets/player-guides/brewing/wind-charging.png" alt="Potion of Wind Charging" width="28"> <img src="../assets/player-guides/brewing/splash-wind-charging.png" alt="Splash Potion of Wind Charging" width="28"> <img src="../assets/player-guides/brewing/lingering-wind-charging.png" alt="Lingering Potion of Wind Charging" width="28"><br>Wind Charging | <img src="../assets/player-guides/brewing/breeze-rod.png" alt="" width="28"> Breeze Rod | 3:00 | — | — |

Turtle Master applies `Slowness IV + Resistance III`; its strong form applies
`Slowness VI + Resistance IV`. Decide when immobility is acceptable before using
the powerful defense.

### Creative-only potion

<img src="../assets/player-guides/brewing/luck.png" alt="Potion of Luck" width="36"> <img src="../assets/player-guides/brewing/splash-luck.png" alt="Splash Potion of Luck" width="36"> <img src="../assets/player-guides/brewing/lingering-luck.png" alt="Lingering Potion of Luck" width="36">

Luck exists in Java Edition but has no brewing recipe or survival source. The
Bedrock-only Potion of Decay is outside this Java/Paper guide.

## Modifiers

| Ingredient | Conversion | Caveat |
|---|---|---|
| <img src="../assets/player-guides/brewing/redstone-dust.png" alt="" width="28"> Redstone Dust | Extends a supported potion | Cannot also be the strong variant. |
| <img src="../assets/player-guides/brewing/glowstone-dust.png" alt="" width="28"> Glowstone Dust | Raises a supported potion's amplifier | Shorter duration; cannot also be extended. |
| <img src="../assets/player-guides/brewing/fermented-spider-eye.png" alt="" width="28"> Fermented Spider Eye | Corrupts or reverses an effect | Night Vision→Invisibility; Swiftness/Leaping→Slowness; Healing/Poison→Harming; Water→Weakness |
| <img src="../assets/player-guides/brewing/gunpowder.png" alt="" width="28"> Gunpowder | Drinkable→Splash | Applies in an impact area; entities nearer the center receive more duration. |
| <img src="../assets/player-guides/brewing/dragons-breath.png" alt="" width="28"> Dragon's Breath | Splash→Lingering | Leaves an effect cloud; the initial effect duration on an entity is one quarter of the original potion. |

Finishing redstone, glowstone, and fermented-eye changes before adding gunpowder
and Dragon's Breath makes mistakes less likely.

## Dead-end bases

- Mundane Potion: created by putting some ingredients such as redstone into a
  Water Bottle first; no effect.
- Thick Potion: Water Bottle + Glowstone Dust; no effect.
- Awkward Potion: no effect itself, but it is the base for nearly every useful
  potion.

Mundane, Thick, and Awkward Potions use the same bottle image as a Water Bottle;
their names and brewing data, not a distinct item silhouette, identify them.

There is no normal recipe that recovers a useful potion from a mistaken Mundane
or Thick Potion.

## Practical loadouts

- Nether: Fire Resistance 8:00, kept on the hotbar before a lava accident.
- Ocean monument: Water Breathing 8:00 + Night Vision 8:00.
- End cities: Slow Falling 4:00 to survive the end of Shulker Levitation.
- Boss fights: Strength II, Regeneration II or extended Regeneration, and Healing II.
- Zombie-villager cure: hit with Splash Weakness, then use an ordinary Golden
  Apple—not an enchanted one.
- Mob farms: contain escape routes and server load before using Oozing, Infested,
  or Weaving, which create extra entities or blocks.

## Safety notes

- Drinking the same potion again replaces its remaining duration; durations do
  not add together.
- A stronger amplifier takes precedence. A weaker effect with remaining time can
  reappear when the strong effect ends.
- Instant Health and Harming work in reverse on undead.
- Splash effects can hit allies and the thrower. A direct hit gives the greatest
  duration; the farther from impact, the shorter it becomes.

## Research baseline

- [Official Minecraft splash-potion guide](https://www.minecraft.net/en-us/article/how-brew-and-use-splash-potions)
- [Minecraft 24w13a new potion ingredients](https://www.minecraft.net/en-us/article/minecraft-snapshot-24w13a)
- [Minecraft Java Edition 1.21 release notes](https://feedback.minecraft.net/hc/en-us/articles/27547857163917-Minecraft-Java-Edition-1-21-Tricky-Trials)
- [Minecraft 26.1 potion registry](https://github.com/misode/mcmeta/blob/26.1-summary/registries/data.json)
