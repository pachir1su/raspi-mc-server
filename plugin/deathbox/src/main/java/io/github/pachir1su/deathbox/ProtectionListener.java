package io.github.pachir1su.deathbox;

import org.bukkit.block.Block;
import org.bukkit.block.Container;
import org.bukkit.block.DoubleChest;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockExplodeEvent;
import org.bukkit.event.block.BlockPistonExtendEvent;
import org.bukkit.event.block.BlockPistonRetractEvent;
import org.bukkit.event.entity.EntityExplodeEvent;
import org.bukkit.event.inventory.InventoryCloseEvent;
import org.bukkit.event.inventory.InventoryMoveItemEvent;
import org.bukkit.event.inventory.InventoryOpenEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.InventoryHolder;

import java.util.UUID;

/**
 * Keeps a placed box owner-only and tamper-proof: blocks unauthorised opens,
 * hopper siphoning, explosions, piston moves, and manual breaking, and removes
 * the box once it has been emptied.
 */
final class ProtectionListener implements Listener {

    private final DeathBoxPlugin plugin;

    ProtectionListener(DeathBoxPlugin plugin) {
        this.plugin = plugin;
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onOpen(InventoryOpenEvent event) {
        Block block = boxBlock(event.getInventory());
        String boxId = plugin.placement().boxIdAt(block);
        if (boxId == null || !(event.getPlayer() instanceof Player player)) {
            return;
        }
        if (!canOpen(player, block)) {
            event.setCancelled(true);
            player.sendMessage(plugin.messages().get("protect.not-yours"));
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onClose(InventoryCloseEvent event) {
        Block block = boxBlock(event.getInventory());
        String boxId = plugin.placement().boxIdAt(block);
        if (boxId == null) {
            return;
        }
        if (isEmpty(event.getInventory())) {
            final Block anchor = block;
            final String id = boxId;
            // Mutate blocks on the next tick, never inside the event.
            plugin.getServer().getScheduler().runTask(plugin, () -> plugin.removeBox(anchor, id));
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onMove(InventoryMoveItemEvent event) {
        if (isBox(event.getSource()) || isBox(event.getDestination())) {
            event.setCancelled(true);
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onBreak(BlockBreakEvent event) {
        if (plugin.placement().boxIdAt(event.getBlock()) != null) {
            event.setCancelled(true);
            event.getPlayer().sendMessage(plugin.messages().get("protect.break"));
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onEntityExplode(EntityExplodeEvent event) {
        event.blockList().removeIf(b -> plugin.placement().boxIdAt(b) != null);
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onBlockExplode(BlockExplodeEvent event) {
        event.blockList().removeIf(b -> plugin.placement().boxIdAt(b) != null);
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onPistonExtend(BlockPistonExtendEvent event) {
        if (event.getBlocks().stream().anyMatch(b -> plugin.placement().boxIdAt(b) != null)) {
            event.setCancelled(true);
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onPistonRetract(BlockPistonRetractEvent event) {
        if (event.getBlocks().stream().anyMatch(b -> plugin.placement().boxIdAt(b) != null)) {
            event.setCancelled(true);
        }
    }

    private boolean canOpen(Player player, Block block) {
        UUID owner = plugin.placement().ownerAt(block);
        if (owner != null && owner.equals(player.getUniqueId())) {
            return true;
        }
        if (player.hasPermission("deathbox.admin")) {
            return true;
        }
        return plugin.config().friendsCanOpen && player.hasPermission("deathbox.friend");
    }

    private boolean isBox(Inventory inv) {
        return inv != null && plugin.placement().boxIdAt(boxBlock(inv)) != null;
    }

    private static boolean isEmpty(Inventory inv) {
        for (var item : inv.getContents()) {
            if (item != null && !item.getType().isAir()) {
                return false;
            }
        }
        return true;
    }

    /** The container block backing an inventory, or null if it is not a container. */
    private static Block boxBlock(Inventory inv) {
        if (inv == null) {
            return null;
        }
        InventoryHolder holder = inv.getHolder();
        if (holder instanceof DoubleChest dc) {
            if (dc.getLeftSide() instanceof org.bukkit.block.Chest left) {
                return left.getBlock();
            }
            if (dc.getRightSide() instanceof org.bukkit.block.Chest right) {
                return right.getBlock();
            }
            return null;
        }
        if (holder instanceof Container container) {
            return container.getBlock();
        }
        return null;
    }
}
