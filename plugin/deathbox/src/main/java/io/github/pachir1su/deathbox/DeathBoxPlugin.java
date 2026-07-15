package io.github.pachir1su.deathbox;

import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.bukkit.plugin.PluginManager;
import org.bukkit.plugin.java.JavaPlugin;

import java.util.List;

/**
 * DeathBox — on death, a player's dropped items are moved into a protected,
 * owner-only chest instead of being left to burn, explode, or despawn.
 *
 * <p>All work happens on death, on container access, and on a light hourly
 * expiry sweep. The plugin never polls, parses logs, scans entities, or keeps
 * chunks loaded.
 */
public final class DeathBoxPlugin extends JavaPlugin {

    /** Gravestone-style plugins we defer to rather than duplicate items with. */
    private static final List<String> CONFLICTING_PLUGINS = List.of(
            "Graves", "GravesX", "AngelChest", "DeadChest", "SavageDeathChest",
            "GravestoneReborn", "Gravestones", "DeathChest");

    private DeathBoxConfig config;
    private Keys keys;
    private BoxIndex index;
    private Placement placement;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        this.config = DeathBoxConfig.from(getConfig());

        String conflict = detectConflict();
        if (conflict != null) {
            getLogger().warning("Found gravestone plugin '" + conflict
                    + "'. Disabling DeathBox to avoid duplicating items.");
            getServer().getPluginManager().disablePlugin(this);
            return;
        }

        this.keys = new Keys(this);
        this.index = new BoxIndex(getDataFolder(), getLogger());
        this.index.load();
        this.placement = new Placement(keys);

        PluginManager pm = getServer().getPluginManager();
        pm.registerEvents(new DeathListener(this), this);
        pm.registerEvents(new ProtectionListener(this), this);

        var command = new DeathBoxCommand(this);
        var registered = getCommand("deathbox");
        if (registered != null) {
            registered.setExecutor(command);
            registered.setTabCompleter(command);
        }

        // Hourly expiry sweep (no-op when expire-hours is 0). 72000 ticks = 1 hour.
        getServer().getScheduler().runTaskTimer(this, this::expireSweep, 72000L, 72000L);

        getLogger().info("DeathBox enabled (container=" + config.container
                + ", radius=" + config.searchRadius + ", expire-hours=" + config.expireHours + ").");
    }

    private String detectConflict() {
        PluginManager pm = getServer().getPluginManager();
        for (String name : CONFLICTING_PLUGINS) {
            if (pm.getPlugin(name) != null) {
                return name;
            }
        }
        return null;
    }

    DeathBoxConfig config() {
        return config;
    }

    BoxIndex index() {
        return index;
    }

    Placement placement() {
        return placement;
    }

    /** Remove an emptied box: clear its block(s) and forget the record. */
    void removeBox(Block anchor, String boxId) {
        for (Block block : placement.siblings(anchor, boxId)) {
            block.setType(org.bukkit.Material.AIR, false);
        }
        index.remove(boxId);
    }

    /** Delete a box outright (admin purge / expiry), dropping any contents on the ground. */
    void purgeBox(BoxRecord box) {
        if (!box.virtual) {
            Location loc = box.location();
            if (loc != null && loc.getWorld().isChunkLoaded(loc.getBlockX() >> 4, loc.getBlockZ() >> 4)) {
                Block anchor = loc.getBlock();
                if (boxIdMatches(anchor, box.id)) {
                    dropContents(anchor);
                    for (Block block : placement.siblings(anchor, box.id)) {
                        block.setType(org.bukkit.Material.AIR, false);
                    }
                }
            }
        }
        index.remove(box.id);
    }

    private boolean boxIdMatches(Block block, String boxId) {
        return boxId.equals(placement.boxIdAt(block));
    }

    private void dropContents(Block anchor) {
        if (anchor.getState() instanceof org.bukkit.block.Container container) {
            Inventory inv = container.getInventory();
            World world = anchor.getWorld();
            for (ItemStack item : inv.getContents()) {
                if (item != null && !item.getType().isAir()) {
                    world.dropItemNaturally(anchor.getLocation(), item);
                }
            }
            inv.clear();
        }
    }

    /** Remove boxes older than expire-hours. Physical boxes only when loaded. */
    private void expireSweep() {
        if (config.expireHours <= 0) {
            return;
        }
        long cutoff = System.currentTimeMillis() - config.expireHours * 3_600_000L;
        for (BoxRecord box : index.all()) {
            if (box.created > cutoff) {
                continue;
            }
            if (box.virtual) {
                index.remove(box.id);
                continue;
            }
            Location loc = box.location();
            // Leave physical boxes in unloaded chunks for a later sweep — never
            // force-load a chunk just to expire a box.
            if (loc != null && loc.getWorld().isChunkLoaded(loc.getBlockX() >> 4, loc.getBlockZ() >> 4)) {
                purgeBox(box);
            }
        }
    }
}
