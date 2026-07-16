# Villager trading guide

<img src="../assets/player-guides/openmoji/villager-trading.svg" alt="Handshake icon" width="96">

This guide covers default **Minecraft Java Edition 26.1 on Paper** trading.
Version 26.1 made trade definitions data-driven, but this server uses the vanilla
26.1 pools unless a separate data pack is installed. Do not confuse them with
the old experimental Villager Trade Rebalance pools.

## Assigning and locking a profession

1. An unemployed adult that can reach a workstation takes its profession. A
   green-robed Nitwit can never work or trade.
2. Completing **any trade once** permanently locks that villager's profession
   and generated offers.
3. Before the first trade, breaking and replacing the workstation can reroll
   offers. Do not trade until the desired offer is visible.
4. An exhausted offer locks. A villager that can physically reach its linked
   workstation can restock up to twice per day. Access to that workstation—not
   merely a nearby bed—is the key requirement.

Levels are Novice, Apprentice, Journeyman, Expert, and Master. Trading fills the
villager's experience bar and unlocks the next tier; unlocked offers remain for
the villager's lifetime.

## Useful trades by profession

Prices and selected offers vary by villager and change with demand and
reputation. This is a practical summary of the 26.1 default pools, not a fixed
price list.

| Profession | Workstation | Useful items to sell | Notable purchases |
|---|---|---|---|
| Armorer | Blast Furnace | Coal, iron, lava buckets, diamonds | Iron/chain armor, shields, enchanted diamond armor |
| Butcher | Smoker | Raw meat, coal, dried-kelp blocks, sweet berries | Cooked meat, rabbit stew |
| Cartographer | Cartography Table | Paper, glass panes, compasses | Empty maps; village, swamp, jungle, ocean, trial-chamber, and woodland-mansion maps; banners |
| Cleric | Brewing Stand | Rotten flesh, gold, rabbit feet, turtle scutes, bottles, Nether Wart | Redstone, lapis, glowstone, Ender Pearls, experience bottles |
| Farmer | Composter | Wheat, potatoes, carrots, beetroot, pumpkins, melons | Bread, apples, pies, cookies, cake, suspicious stew, golden carrots |
| Fisherman | Barrel | String, coal, fish, pufferfish, boats | Cooked fish, campfires, enchanted fishing rods |
| Fletcher | Fletching Table | Sticks, flint, string, feathers, tripwire hooks | Arrows, bows, crossbows, enchanted ranged weapons, tipped arrows |
| Leatherworker | Cauldron | Leather, flint, rabbit hide, turtle scutes | Dyed leather gear, leather horse armor, saddles |
| Librarian | Lectern | Paper, books, ink sacs, writable books | Enchanted books, bookshelves, glass, lanterns, clocks, compasses, candles |
| Mason | Stonecutter | Clay, stone, granite, andesite, diorite, quartz | Bricks, chiseled bricks, dripstone blocks, polished stone, terracotta, quartz blocks |
| Shepherd | Loom | Wool and assorted dyes | Shears, wool, carpet, beds, banners, paintings |
| Toolsmith | Smithing Table | Coal, iron, flint, diamonds | Stone, iron, and diamond tools, including enchanted tools |
| Weaponsmith | Grindstone | Coal, iron, flint, diamonds | Iron axes/swords and enchanted diamond axes/swords |

Default 26.1 librarians can roll enchanted-book offers from Novice through
Expert. Tradeable treasure such as Mending can appear, but Soul Speed, Swift
Sneak, and Wind Burst are not librarian trades. See [enchantments](enchantments.md).

## Why prices change

- **Demand:** exhausting one offer can raise its price after restocking. Leaving
  it unused or using alternatives can ease demand over time.
- **Reputation:** attacking villagers worsens nearby prices. Trading and curing
  improve reputation.
- **Hero of the Village:** winning a raid grants temporary discounts.
- **Curing:** the first zombie-villager cure grants a permanent discount. Since
  Java 1.20.2, repeatedly infecting and curing the same villager does not stack
  more permanent discounts.

Displayed cost cannot fall below one item and high demand can push it above the
base cost.

## Curing a zombie villager

1. Contain it away from sunlight and other mobs.
2. Hit it with a **Splash Potion of Weakness**.
3. Use an ordinary **Golden Apple** on the weakened zombie villager.
4. Keep it safe for roughly 3–5 minutes while it shakes and emits red particles.
   Nearby iron bars and beds can shorten the conversion somewhat.

When a zombie kills a villager, conversion chance is 0% on Easy, 50% on Normal,
and 100% on Hard. Deliberate infection can simply kill the villager on Easy or
Normal. Check this server's difficulty first.

## Safe trading-hall design

- Give each villager one workstation and verify green work particles at it.
- Move workstations one at a time and identify the linked villager; the closest
  visible villager is not guaranteed to claim it.
- Protect against lightning with a roof and lightning rod; lightning converts
  villagers into witches.
- Separate curing from the main hall and test difficulty, containment, and
  sunlight protection first.
- Concentrating many villagers, hoppers, and redstone in one chunk raises tick
  cost on a Raspberry Pi. Keep only useful offers and simplify pathfinding.

## Suggested progression

1. Sell sticks to a Fletcher for early emeralds.
2. Sell farm output to Farmers and establish renewable Golden Carrots.
3. Secure Mending, Unbreaking, Efficiency, and protection books from Librarians.
4. Level armorers, toolsmiths, and weaponsmiths to make diamond equipment renewable.
5. Sell rotten flesh to Clerics and buy Ender Pearls and experience bottles.

## Research baseline

- [Minecraft Java Edition 26.1: data-driven villager trades](https://feedback.minecraft.net/hc/en-us/articles/44551668333837-Minecraft-Java-Edition-26-1)
- [Minecraft 26.1 generated profession trades](https://github.com/misode/mcmeta/tree/26.1-data-json/data/minecraft/villager_trade)
- [Minecraft 26.1 generated level pools](https://github.com/misode/mcmeta/tree/26.1-data-json/data/minecraft/tags/villager_trade)
- [Minecraft 19w11a: workstations, demand, and two daily restocks](https://feedback.minecraft.net/hc/en-us/articles/360024978852-Minecraft-Java-Edition-Snapshot-19W11A)
