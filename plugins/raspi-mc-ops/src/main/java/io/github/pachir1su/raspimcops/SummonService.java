package io.github.pachir1su.raspimcops;

import java.util.List;
import java.util.Locale;
import java.util.concurrent.ThreadLocalRandom;
import java.util.regex.Pattern;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.Registry;
import org.bukkit.World;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.block.Block;
import org.bukkit.command.CommandSender;
import org.bukkit.enchantments.Enchantment;
import org.bukkit.entity.Creeper;
import org.bukkit.entity.Entity;
import org.bukkit.entity.EntityType;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.entity.Villager;
import org.bukkit.inventory.EntityEquipment;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.MerchantRecipe;
import org.bukkit.inventory.meta.Damageable;
import org.bukkit.inventory.meta.EnchantmentStorageMeta;
import org.bukkit.util.Vector;

/**
 * Owner-only mob and villager summons for the Discord admin panel. Every spawn
 * is placed on a searched, non-suffocating spot so mobs never appear inside a
 * wall (issue: "몹 벽에 안 끼게"). Presets and their gates live here — in the
 * Bukkit API rather than raw NBT strings — so they stay valid across the exact
 * item-component format the running server uses.
 */
final class SummonService {

    private static final Pattern SERVER_PLAYER_NAME = Pattern.compile(
        "(?:[A-Za-z0-9_]{1,16}|\\.[A-Za-z0-9_]{1,32})"
    );

    // 벽 회피용 안전 자리 탐색 범위: 대상 Y 기준 위/아래로 이 정도까지만 훑습니다.
    private static final int VERTICAL_SEARCH = 6;
    // 크리퍼 충전: 대상 주변 이 반경 안의 실제 크리퍼만 대상으로 합니다.
    private static final double CHARGE_RADIUS = 30.0;

    private final RaspiMcOpsPlugin plugin;

    SummonService(RaspiMcOpsPlugin plugin) {
        this.plugin = plugin;
    }

    // ── /raspiops summon <player> <preset> ─────────────────────────────
    boolean handleSummon(CommandSender sender, String[] args) {
        // args = [summon, <player>, <preset>]
        if (args.length != 3) {
            sender.sendMessage("Usage: /raspiops summon <exact-player-name> <preset>");
            return true;
        }
        Player player = resolvePlayer(sender, args[1]);
        if (player == null) {
            return true;
        }
        String preset = args[2].toLowerCase(Locale.ROOT);
        switch (preset) {
            case "creeper" -> summonSingle(sender, player, EntityType.CREEPER, 5, null);
            case "charged_creeper" -> chargeNearbyCreeper(sender, player);
            case "boom_creeper" -> summonBoomCreeper(sender, player);
            case "buffed_zombie" -> summonBuffedZombie(sender, player);
            case "skeleton_squad" -> summonSkeletonSquad(sender, player);
            case "trident_drowned" -> summonTridentDrowned(sender, player);
            case "horde" -> summonHorde(sender, player);
            default -> sender.sendMessage("Unknown summon preset: " + preset);
        }
        return true;
    }

    private void summonSingle(
        CommandSender sender, Player player, EntityType type, int distance,
        java.util.function.Consumer<LivingEntity> tweak
    ) {
        Location spot = findSafeSpot(player, distance, false);
        if (spot == null) {
            sender.sendMessage("summon: no safe spot near " + player.getName());
            return;
        }
        Entity entity = spot.getWorld().spawnEntity(spot, type);
        if (tweak != null && entity instanceof LivingEntity living) {
            tweak.accept(living);
        }
        sender.sendMessage("summon: spawned " + type.name().toLowerCase(Locale.ROOT)
            + " at " + describe(spot));
    }

    private void summonBoomCreeper(CommandSender sender, Player player) {
        summonSingle(sender, player, EntityType.CREEPER, 5, living -> {
            if (living instanceof Creeper creeper) {
                creeper.setExplosionRadius(6); // 기본 3 → 겉보기 일반, 폭발만 강화
            }
        });
    }

    private void summonBuffedZombie(CommandSender sender, Player player) {
        summonSingle(sender, player, EntityType.ZOMBIE, 6, living -> {
            equip(living, ironAxe());
            setMaxHealth(living, 40.0);
        });
    }

    private void summonSkeletonSquad(CommandSender sender, Player player) {
        // 파워 2 한 마리, 파워 1 두 마리, 기본 활 한 마리. 활 내구도는 바닥.
        int[] powers = {2, 1, 1, 0};
        int spawned = 0;
        for (int power : powers) {
            Location spot = findSafeSpot(player, 8, false);
            if (spot == null) {
                continue;
            }
            Entity entity = spot.getWorld().spawnEntity(spot, EntityType.SKELETON);
            if (entity instanceof LivingEntity living) {
                equip(living, nearBrokenBow(power));
                spawned++;
            }
        }
        sender.sendMessage("summon: spawned " + spawned + " skeleton(s) near " + player.getName());
    }

    private void summonTridentDrowned(CommandSender sender, Player player) {
        // 물에 있을 때만 — 삼지창 드라운드는 물에서만 자연스럽습니다.
        Location spot = findSafeSpot(player, 4, true);
        if (spot == null) {
            sender.sendMessage("summon: no water near " + player.getName()
                + " (drowned needs the player in or by water)");
            return;
        }
        Entity entity = spot.getWorld().spawnEntity(spot, EntityType.DROWNED);
        if (entity instanceof LivingEntity living) {
            equip(living, new ItemStack(Material.TRIDENT));
        }
        sender.sendMessage("summon: spawned trident drowned at " + describe(spot));
    }

    private void summonHorde(CommandSender sender, Player player) {
        // 물량. 멀리(15~22블록) 흩어서, 각자 안전 자리에. 좀비/스켈레톤 혼합.
        int target = 10;
        int spawned = 0;
        for (int i = 0; i < target; i++) {
            Location spot = findSafeSpot(player, 15 + ThreadLocalRandom.current().nextInt(8), false);
            if (spot == null) {
                continue;
            }
            EntityType type = ThreadLocalRandom.current().nextBoolean()
                ? EntityType.ZOMBIE : EntityType.SKELETON;
            spot.getWorld().spawnEntity(spot, type);
            spawned++;
        }
        sender.sendMessage("summon: spawned a horde of " + spawned + " near " + player.getName());
    }

    private void chargeNearbyCreeper(CommandSender sender, Player player) {
        if (!player.getWorld().isThundering()) {
            sender.sendMessage("summon: not thundering — charged creeper only during a thunderstorm");
            return;
        }
        Creeper nearest = null;
        double best = Double.MAX_VALUE;
        for (Entity entity : player.getNearbyEntities(CHARGE_RADIUS, CHARGE_RADIUS, CHARGE_RADIUS)) {
            if (entity instanceof Creeper creeper && !creeper.isPowered()) {
                double dist = creeper.getLocation().distanceSquared(player.getLocation());
                if (dist < best) {
                    best = dist;
                    nearest = creeper;
                }
            }
        }
        if (nearest == null) {
            sender.sendMessage("summon: no un-charged creeper within " + (int) CHARGE_RADIUS
                + " blocks of " + player.getName());
            return;
        }
        // 실제 낙뢰로 충전 — 뇌우 중 자연 현상과 구분되지 않습니다.
        nearest.getWorld().strikeLightning(nearest.getLocation());
        sender.sendMessage("summon: struck a creeper near " + player.getName() + " to charge it");
    }

    // ── /raspiops villager <player> <profession> <good> <price> ────────
    boolean handleVillager(CommandSender sender, String[] args) {
        // args = [villager, <player>, <profession>, <good>, <price>]
        if (args.length != 5) {
            sender.sendMessage("Usage: /raspiops villager <exact-player-name> <profession> <good> <price>");
            return true;
        }
        Player player = resolvePlayer(sender, args[1]);
        if (player == null) {
            return true;
        }
        int price;
        try {
            price = Math.max(1, Math.min(64, Integer.parseInt(args[4].trim())));
        } catch (NumberFormatException ex) {
            sender.sendMessage("Price must be a whole number of emeralds (1-64).");
            return true;
        }
        ItemStack good = buildGood(args[3].toLowerCase(Locale.ROOT));
        if (good == null) {
            sender.sendMessage("Unknown good: " + args[3]);
            return true;
        }
        Location spot = findSafeSpot(player, 3, false);
        if (spot == null) {
            sender.sendMessage("summon: no safe spot near " + player.getName());
            return true;
        }
        Entity entity = spot.getWorld().spawnEntity(spot, EntityType.VILLAGER);
        if (!(entity instanceof Villager villager)) {
            sender.sendMessage("summon: could not create villager");
            return true;
        }
        applyProfession(villager, args[2].toLowerCase(Locale.ROOT));
        villager.setVillagerLevel(5);
        MerchantRecipe recipe = new MerchantRecipe(good, 9999);
        recipe.addIngredient(new ItemStack(Material.EMERALD, price));
        villager.setRecipes(List.of(recipe));
        sender.sendMessage("summon: spawned a villager selling " + args[3].toLowerCase(Locale.ROOT)
            + " for " + price + " emerald(s) at " + describe(spot));
        return true;
    }

    // ── 안전 자리 탐색 ─────────────────────────────────────────────────
    /**
     * 대상 등 뒤 distance 블록 지점을 기준으로, 발/머리 칸이 통과 가능하고 그
     * 아래가 단단한(또는 water=true면 물인) 안전한 위치를 찾습니다. 못 찾으면
     * null. 격자처럼 정렬되지 않게 좌우 각도에 약간의 지터를 줍니다.
     */
    private Location findSafeSpot(Player player, int distance, boolean water) {
        World world = player.getWorld();
        Location base = player.getLocation();
        Vector dir = base.getDirection().setY(0);
        if (dir.lengthSquared() < 1.0e-6) {
            dir = new Vector(0, 0, 1);
        }
        dir.normalize();
        double jitterAngle = (ThreadLocalRandom.current().nextDouble() - 0.5) * (Math.PI / 3);
        double cos = Math.cos(jitterAngle);
        double sin = Math.sin(jitterAngle);
        double dx = -(dir.getX() * cos - dir.getZ() * sin); // 등 뒤 + 좌우 지터
        double dz = -(dir.getX() * sin + dir.getZ() * cos);
        int x = base.getBlockX() + (int) Math.round(dx * distance);
        int z = base.getBlockZ() + (int) Math.round(dz * distance);
        int startY = base.getBlockY();
        for (int offset = 0; offset <= VERTICAL_SEARCH; offset++) {
            for (int sign : offset == 0 ? new int[] {0} : new int[] {1, -1}) {
                int y = startY + sign * offset;
                if (isSafeStand(world, x, y, z, water)) {
                    return new Location(world, x + 0.5, y, z + 0.5);
                }
            }
        }
        return null;
    }

    private boolean isSafeStand(World world, int x, int y, int z, boolean water) {
        if (y < world.getMinHeight() + 1 || y > world.getMaxHeight() - 2) {
            return false;
        }
        Block feet = world.getBlockAt(x, y, z);
        Block head = world.getBlockAt(x, y + 1, z);
        Block below = world.getBlockAt(x, y - 1, z);
        if (water) {
            return feet.getType() == Material.WATER && head.getType() == Material.WATER;
        }
        return feet.isPassable() && head.isPassable()
            && feet.getType() != Material.LAVA
            && !below.isPassable() && below.getType().isSolid();
    }

    // ── 아이템/속성 헬퍼 ───────────────────────────────────────────────
    private void equip(LivingEntity living, ItemStack weapon) {
        EntityEquipment equipment = living.getEquipment();
        if (equipment != null) {
            equipment.setItemInMainHand(weapon);
            equipment.setItemInMainHandDropChance(0f); // 죽어도 무기 안 떨굼
        }
    }

    private void setMaxHealth(LivingEntity living, double value) {
        Attribute attribute = resolveAttribute("max_health");
        if (attribute == null) {
            return;
        }
        AttributeInstance instance = living.getAttribute(attribute);
        if (instance != null) {
            instance.setBaseValue(value);
            living.setHealth(value);
        }
    }

    private ItemStack ironAxe() {
        return new ItemStack(Material.IRON_AXE);
    }

    private ItemStack nearBrokenBow(int power) {
        ItemStack bow = new ItemStack(Material.BOW);
        if (power > 0) {
            Enchantment enchant = resolveEnchant("power");
            if (enchant != null) {
                bow.addUnsafeEnchantment(enchant, power);
            }
        }
        damageToNearBroken(bow);
        return bow;
    }

    /** 내구도를 거의 0으로 — 최대 내구도 - 1 만큼 손상시킵니다. */
    private void damageToNearBroken(ItemStack item) {
        short max = item.getType().getMaxDurability();
        if (max <= 1) {
            return;
        }
        if (item.getItemMeta() instanceof Damageable meta) {
            meta.setDamage(max - 1);
            item.setItemMeta(meta);
        }
    }

    private ItemStack buildGood(String key) {
        return switch (key) {
            case "mending" -> book("mending", 1);
            case "efficiency5" -> book("efficiency", 5);
            case "protection4" -> book("protection", 4);
            case "unbreaking3" -> book("unbreaking", 3);
            case "fortune3" -> book("fortune", 3);
            case "silk_touch" -> book("silk_touch", 1);
            case "sharpness5" -> book("sharpness", 5);
            case "diamond_sword" -> enchantedTool(Material.DIAMOND_SWORD, "sharpness", 5);
            case "diamond_pickaxe" -> enchantedTool(Material.DIAMOND_PICKAXE, "efficiency", 5);
            case "diamond_helmet" -> enchantedTool(Material.DIAMOND_HELMET, "protection", 4);
            case "diamond_chestplate" -> enchantedTool(Material.DIAMOND_CHESTPLATE, "protection", 4);
            case "diamond_leggings" -> enchantedTool(Material.DIAMOND_LEGGINGS, "protection", 4);
            case "diamond_boots" -> enchantedTool(Material.DIAMOND_BOOTS, "protection", 4);
            case "ender_pearl" -> new ItemStack(Material.ENDER_PEARL);
            case "xp_bottle" -> new ItemStack(Material.EXPERIENCE_BOTTLE);
            case "crossbow" -> new ItemStack(Material.CROSSBOW);
            case "arrows" -> new ItemStack(Material.ARROW, 16);
            default -> null;
        };
    }

    private ItemStack book(String enchantId, int level) {
        ItemStack book = new ItemStack(Material.ENCHANTED_BOOK);
        Enchantment enchant = resolveEnchant(enchantId);
        if (enchant != null && book.getItemMeta() instanceof EnchantmentStorageMeta meta) {
            meta.addStoredEnchant(enchant, level, true);
            book.setItemMeta(meta);
        }
        return book;
    }

    private ItemStack enchantedTool(Material material, String enchantId, int level) {
        ItemStack item = new ItemStack(material);
        Enchantment enchant = resolveEnchant(enchantId);
        if (enchant != null) {
            item.addUnsafeEnchantment(enchant, level);
        }
        return item;
    }

    private void applyProfession(Villager villager, String professionKey) {
        Villager.Profession profession = Registry.VILLAGER_PROFESSION.get(
            NamespacedKey.minecraft(professionKey)
        );
        if (profession != null) {
            villager.setProfession(profession);
        }
    }

    private Enchantment resolveEnchant(String enchantId) {
        return Registry.ENCHANTMENT.get(NamespacedKey.minecraft(enchantId));
    }

    private Attribute resolveAttribute(String attributeId) {
        return Registry.ATTRIBUTE.get(NamespacedKey.minecraft(attributeId));
    }

    private Player resolvePlayer(CommandSender sender, String name) {
        if (!SERVER_PLAYER_NAME.matcher(name).matches()) {
            sender.sendMessage("Invalid exact player name.");
            return null;
        }
        Player player = Bukkit.getPlayerExact(name);
        if (player == null) {
            sender.sendMessage("Player is not online: " + name);
            return null;
        }
        return player;
    }

    private String describe(Location location) {
        return location.getBlockX() + " " + location.getBlockY() + " " + location.getBlockZ();
    }
}
