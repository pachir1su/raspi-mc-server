# Ores and resources

<img src="../assets/player-guides/openmoji/ores-and-resources.svg" alt="Mining pick icon" width="96">

This guide uses default **Minecraft Java Edition 26.1 on Paper** world
generation. `Y` is the height coordinate shown on the F3 debug screen. In an
upgraded world, already-generated chunks retain old terrain; new generation
starts only in newly explored chunks.

## Overworld ore heights

![Bilingual chart of Overworld ore generation ranges and recommended heights](../assets/player-guides/diagrams/ore-distribution.svg)

`Recommended Y` balances the distribution peak with mining safety. Generation
approaches zero near some range edges. Coal, diamond, and some other ores reduce
air-exposed attempts, so branch mining can outperform looking only at huge cave
walls.

| Resource | Main range and distribution | Recommended Y/place | Minimum pickaxe | Fortune result |
|---|---|---|---|---|
| Coal | Y 0–192 centered on 96, plus abundant generation above 136 | Y 96 or high mountains | Wooden | More coal |
| Iron | Y -24–56 centered on 16; increasing high-altitude generation above 80 | Y 16, or mountains near 232 | Stone | More raw iron |
| Copper | Y -16–112 centered on 48 | Y 48; larger in dripstone caves | Stone | More raw copper |
| Gold | Y -64–32 centered on -16, plus extra below -48 | Y -16; abundant in Badlands Y 32–256 | Iron | More raw gold |
| Redstone | Below Y 15, increasing strongly below -32 | Y -59 above bedrock | Iron | More dust |
| Lapis | Y -32–32 centered on 0, plus buried ore Y -64–64 | Y 0; search enclosed blocks too | Stone | More lapis |
| Diamond | Below Y 16, increasing toward the bottom; reduced air exposure | Y -59 above lava/bedrock | Iron | More diamonds |
| Emerald | Mountain biomes above Y -16, centered near 232 | High mountains near Y 232 | Iron | More emeralds |

The practical Overworld build limit is Y 320, so the higher ends of iron and
emerald placement definitions are clipped by terrain. For branch mining, Y -59
means the player's feet; alternate the two blocks ahead to avoid opening lava
directly below yourself.

## Large veins and biome exceptions

- Large **iron veins** appear deep underground with tuff. Raw Iron Blocks are a
  strong sign; follow the surrounding tuff.
- Large **copper veins** occur with granite above Y 0. Dripstone caves also use
  larger normal copper blobs.
- **Badlands** add large amounts of gold from Y 32 to 256.
- Only **mountain biomes** naturally generate emerald ore. Trading is more
  efficient for bulk emeralds.
- Coal does not generate below Y 0, so bring torch fuel before descending.

## Nether resources

| Resource | Location | Minimum tool and tip |
|---|---|---|
| Nether Quartz | Uniform through Nether Y 10–118 | Wooden pickaxe; Fortune raises quartz and it is good experience |
| Nether Gold Ore | Y 10–118, more common in Nether Wastes | Wooden pickaxe; Fortune raises nuggets, while Silk Touch + smelting yields one ingot |
| Ancient Debris | Sparse everywhere, concentrated Y 8–24 around 16 | **Diamond or better**; blast-resistant, enabling bed/TNT mining near Y 15 |
| Glowstone | Ceiling clusters | Check for lava below; Fortune raises dust but caps at four per block |
| Nether Wart | Fortress stair gardens and some bastions | No tool; farm on Soul Sand |
| Blaze Rod | Blazes in Nether Fortresses | Needed for brewing fuel and Eyes of Ender; bring Fire Resistance |

Smelting Ancient Debris gives Netherite Scrap. Four scrap plus four gold ingots
make one Netherite Ingot. Upgrading equipment also needs a Netherite Upgrade
Smithing Template from a bastion remnant.

## Fortune versus Silk Touch

- Fortune III can raise output from coal, diamond, emerald, lapis, redstone,
  quartz, and raw iron/copper/gold.
- Silk Touch stores the ore block itself, useful for inventory packing or mining
  it later with Fortune III.
- Fortune and Silk Touch cannot normally coexist on one tool.
- Smelting an ore block generally yields only one item, wasting a Fortune-capable
  resource. Fortune raw iron/copper/gold first, then smelt the raw items.
- Ancient Debris ignores Fortune and always drops itself once.

## Mining safely

1. Bring a water bucket, food, shield, spare pick, blocks, and torches.
2. Save coordinates and a return path in the [coordinate book](server-features.md).
3. Never dig straight above or below yourself.
4. Deep underground, listen for lava and expose the area around diamond before
   mining it.
5. Caves are fast for iron, copper, and coal. Pair them with Y -59 branch mining
   because exposed diamond generation is reduced.
6. Do not leave large piles of drops and experience orbs. Entity buildup costs
   tick time on a Raspberry Pi server.

## Other renewable resources

- Iron is renewable through iron golems, gold through zombified piglins, and
  copper through drowned.
- Emeralds are renewable through trading; clerics renewably sell redstone,
  lapis, and glowstone.
- Diamonds themselves are nonrenewable, but villagers can repeatedly sell
  diamond equipment.
- Budding Amethyst cannot be moved in Survival. Leave growth faces open and
  build the farm around the geode.

## Research baseline

- [Minecraft 26.1 generated ore placement definitions](https://github.com/misode/mcmeta/tree/26.1-data-json/data/minecraft/worldgen/placed_feature)
- [Minecraft 21w40a ore-distribution changes](https://www.minecraft.net/en-us/article/minecraft-snapshot-21w40a)
- [Official Minecraft mining guide](https://www.minecraft.net/en-us/article/the-best-way-to-mine)
- [Caves & Cliffs Part I: raw ore and Fortune](https://www.minecraft.net/en-us/article/caves---cliffs--part-i-out-today-java)
