# Farming and breeding

<img src="../assets/player-guides/openmoji/farming-and-breeding.svg" alt="Sheaf of rice icon" width="96">

This guide targets **Minecraft Java Edition 26.1 on Paper**. Crops grow through
random ticks while their chunks are loaded. Excess animals increase AI and
collision cost on the Raspberry Pi server.

## Farmland fundamentals

- Use a hoe on dirt or grass to create farmland.
- Water hydrates farmland within four horizontal blocks at the same level or one
  block above. One source can hydrate a 9×9 field.
- Wheat, carrots, potatoes, and beetroot need block light 9 or higher at the crop.
- Jumping or falling on farmland can turn it back to dirt. Use slab paths and
  fence animals out.
- Growth is random at the default `randomTickSpeed=3`. Do not raise it greatly
  on this server merely to accelerate crops.
- Dense planting works, but alternating rows of different crop types improves
  the crop growth check.

## Crop requirements

![Bilingual diagram of a nine-by-nine hydrated field with center water](../assets/player-guides/diagrams/farm-layout.svg)

| Crop/resource | Plant on | Harvest and replant | Bone meal |
|---|---|---|---|
| Wheat | Wheat Seeds on farmland | Harvest when fully yellow for wheat and seeds | Yes |
| Carrot | Carrot on farmland | Harvest the large orange-root stage; replant some | Yes |
| Potato | Potato on farmland | Replant some; Poisonous Potatoes cannot be planted | Yes |
| Beetroot | Beetroot Seeds on farmland | Drops beetroot and seeds; fewer visual stages | Yes |
| Pumpkin/Melon | Seeds on farmland | Stem remains and creates fruit on adjacent suitable soil; leave one side open | On stem |
| Sugar Cane | Suitable soil directly adjacent to water | Naturally grows to 3; leave the bottom and harvest above | No in Java |
| Cactus | Sand or Red Sand | Naturally grows to 3; breaks if a block touches any horizontal side | No |
| Bamboo | Dirt, sand, moss, and other suitable ground | Grows tall; leave the base and harvest above | Yes |
| Cocoa | Side of a Jungle Log | Large brown pod drops three beans | Yes |
| Nether Wart | Soul Sand | Mature red stage drops 2–4; no water or light needed | No |
| Kelp | Top of an underwater block | Leave lower kelp and harvest upward | Yes |
| Sweet Berries | Dirt, grass, podzol, and similar blocks | Use a mature bush; beware thorn movement damage | Yes |
| Glow Berries | Cave Vines from a block underside | Use fruiting vine; shears can stop growth | Yes |
| Mushrooms | Suitable low-light block; mycelium/podzol relax light limits | Slowly spread; grow huge with enough space | Huge growth |
| Chorus Fruit | Chorus Flower on End Stone | Flowers build stems; break low stems to cascade harvest | Limited |
| Torchflower | Torchflower Seeds on farmland | Sniffer-found seed; mature plant does not duplicate seed | Yes |
| Pitcher Plant | Pitcher Pod on farmland | Grows two blocks tall; Sniffers find pods | Yes |

Pumpkin and melon automation can pulse observers and pistons frequently. Build
only the needed capacity and use water streams to reduce hopper count.

## Shared breeding rules

- Feed two eligible adults the matching food to enter love mode and produce a baby.
- Most parents have a five-minute cooldown and babies mature in about 20 minutes.
  Growth food normally removes 10% of the remaining growth time per feeding.
- Some animals must be tamed, need nearby blocks, or return to a home location
  before laying eggs.

## Breeding foods

![Bilingual quick map of common animal breeding foods](../assets/player-guides/diagrams/breeding-foods.svg)

| Animal | Breeding food | Additional condition/result |
|---|---|---|
| Cow/Mooshroom | Wheat | Produces calf; Mooshrooms breed with Mooshrooms |
| Sheep | Wheat | Baby color may combine parent dyes |
| Goat | Wheat | Normal/screaming trait has its own chances |
| Pig | Carrot, Potato, Beetroot | Same foods tempt pigs |
| Chicken | Wheat/Melon/Pumpkin/Beetroot Seeds, Torchflower Seeds, Pitcher Pods | Egg hatching is separate from breeding |
| Rabbit | Carrot, Golden Carrot, Dandelion | Variant follows parents or local biome |
| Horse/Donkey | Golden Carrot or Golden Apple | Both adults must be tamed |
| Mule | Tamed Horse + Donkey | Mule offspring is sterile |
| Llama/Trader Llama | Hay Bale | Tamed adults; trader llama can breed after separation from trader |
| Wolf | Meat and fish | Tamed wolves must be sufficiently healed |
| Cat | Raw Cod or Raw Salmon | Two tamed cats |
| Ocelot | Raw Cod or Raw Salmon | Trusting state; offspring remain ocelots, not cats |
| Fox | Sweet Berries or Glow Berries | Baby trusts the breeder but is not a tamed pet |
| Panda | Bamboo | Each parent needs sufficient nearby bamboo blocks |
| Bee | Flowers | Provide hive capacity; pollination can accelerate crops |
| Turtle | Seagrass | One parent returns to its home beach to lay eggs |
| Hoglin | Crimson Fungus | Fear of warped fungus/portals can interrupt breeding |
| Strider | Warped Fungus | Shivers and slows outside lava |
| Axolotl | Bucket of Tropical Fish | A loose fish item does not work; blue offspring is rare |
| Frog | Slimeball | Frogspawn→Tadpole→variant based on maturation temperature |
| Camel | Cactus | Produces baby camel |
| Sniffer | Torchflower Seeds | Drops a Sniffer Egg; hatches faster on Moss |
| Armadillo | Spider Eye | Will not eat while rolled up in fear |
| Nautilus | Pufferfish or Bucket of Pufferfish | Used for taming and breeding; suffocates on land |

## Feedable but not normally breedable

- Camel Husks eat Rabbit Feet and Zombie Horses eat Red Mushrooms, but these
  undead mounts do not breed like ordinary livestock.
- Parrots can be tamed and fed seeds but cannot breed. Cookies fatally poison
  parrots—never feed one.
- Happy Ghasts respond to Snowballs but have no two-adult breeding cycle.
- Mules can be fed, healed, and grown but are sterile.

## The 26.1 Golden Dandelion

Use a **Golden Dandelion**, crafted from a Dandelion and Gold Nuggets, on a baby
mob to pause or resume growth. Downward green particles mean paused; upward
particles mean resumed.

- It cannot affect baby villagers or undead babies.
- Pausing is decorative. Do not use it on livestock intended to mature for food,
  leather, or wool.
- A second use resumes the growth timer.

## Bees and pollination

After collecting pollen, bees flying home over wheat, potatoes, carrots,
beetroot, pumpkin/melon stems, or sweet berries can advance crop growth. Put a
lit campfire under a hive before harvesting honey. Use Silk Touch to move a nest
with bees inside.

## Pi-friendly farm design

- Do not stack dozens or hundreds of animals in one pen; retain only useful
  breeding stock per species.
- Drops, minecarts, hoppers, villagers, and animals all cost tick time. Keep
  collection bursts short and stop automation when storage is full.
- Avoid chunk loaders and permanently pulsing clocks. Start with a scale that
  produces only while a player is nearby.
- Compare `/tools` server score and the admin TPS/performance panel before and
  after expanding a farm.

## Research baseline

- [Minecraft Java Edition 26.1: Golden Dandelion](https://feedback.minecraft.net/hc/en-us/articles/44551668333837-Minecraft-Java-Edition-26-1)
- [Minecraft Java Edition 1.21.11: Nautilus breeding](https://www.minecraft.net/en-us/article/minecraft-java-edition-1-21-11)
- [Minecraft 26.1 generated animal-food tags](https://github.com/misode/mcmeta/tree/26.1-data-json/data/minecraft/tags/item)
- [Caves & Cliffs Part I: amethyst, copper, and glow berries](https://www.minecraft.net/en-us/article/caves---cliffs--part-i-out-today-java)
