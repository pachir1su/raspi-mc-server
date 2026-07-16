package io.github.pachir1su.deathbox;

import org.bukkit.Location;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.inventory.ItemStack;

import java.util.ArrayList;
import java.util.List;
import java.util.logging.Level;

/**
 * Captures a player's drops at death and stows them in a protected box. Runs at
 * NORMAL priority so gravestone-style plugins at higher priority win, and skips
 * keepInventory or empty-drop deaths entirely.
 */
final class DeathListener implements Listener {

    private final DeathBoxPlugin plugin;

    DeathListener(DeathBoxPlugin plugin) {
        this.plugin = plugin;
    }

    @EventHandler(priority = EventPriority.NORMAL)
    public void onDeath(PlayerDeathEvent event) {
        DeathBoxConfig cfg = plugin.config();
        if (!cfg.enabled || event.getKeepInventory()) {
            return;
        }
        List<ItemStack> drops = event.getDrops();
        if (drops.isEmpty()) {
            return;
        }

        // Snapshot the real stacks (metadata intact), then decide what to do.
        List<ItemStack> captured = new ArrayList<>();
        for (ItemStack item : drops) {
            if (item != null && !item.getType().isAir()) {
                captured.add(item);
            }
        }
        if (captured.isEmpty()) {
            return;
        }

        Player player = event.getEntity();
        Location death = player.getLocation();
        String boxId = plugin.index().newId();
        Messages msg = plugin.messages();

        // Anti-grief cap (#65): a player at the physical-box limit gets a virtual
        // box instead of another unbreakable chest at someone else's doorstep.
        boolean atBoxLimit = cfg.maxPhysicalBoxesPerPlayer > 0
                && plugin.index().countPhysicalOwnedBy(player.getUniqueId())
                        >= cfg.maxPhysicalBoxesPerPlayer;

        Placement.Placed placed = atBoxLimit
                ? null
                : plugin.placement().place(death, cfg, boxId, player.getUniqueId());
        if (placed != null) {
            drops.clear();
            Placement.fill(placed.inventory, captured, placed.blocks.get(0).getLocation());
            Location box = placed.blocks.get(0).getLocation();
            plugin.index().put(BoxRecord.physical(boxId, player.getUniqueId(), player.getName(), box));
            player.sendMessage(msg.get("death.stored",
                    "x", box.getBlockX(), "y", box.getBlockY(), "z", box.getBlockZ(),
                    "world", box.getWorld().getName()));
            return;
        }

        // No safe spot, or the player is at the box cap. Keep the items rather
        // than dropping them into danger, holding them in a virtual box.
        if (cfg.fallbackVirtualBox) {
            try {
                String encoded = Items.encode(captured.toArray(new ItemStack[0]));
                drops.clear();
                plugin.index().put(BoxRecord.virtual(boxId, player.getUniqueId(), player.getName(), encoded));
                player.sendMessage(
                        msg.get(atBoxLimit ? "death.limit-virtual" : "death.virtual", "id", boxId));
            } catch (Exception ex) {
                plugin.getLogger().log(Level.SEVERE, "Failed to store a virtual death box; leaving vanilla drops", ex);
            }
        }
        // else: leave the drops untouched so vanilla handles them.
    }
}
