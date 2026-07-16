package io.github.pachir1su.raspimcops;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.Tag;
import org.bukkit.block.Block;
import org.bukkit.block.BlockFace;
import org.bukkit.block.DoubleChest;
import org.bukkit.block.TileState;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockPlaceEvent;
import org.bukkit.event.inventory.InventoryOpenEvent;
import org.bukkit.inventory.BlockInventoryHolder;
import org.bukkit.inventory.InventoryHolder;
import org.bukkit.persistence.PersistentDataType;

/** Per-placer container locks with a persistent owner toggle (issue #37). */
public final class ContainerLockService implements Listener {
    private static final BlockFace[] CHEST_NEIGHBORS = {
        BlockFace.NORTH, BlockFace.SOUTH, BlockFace.EAST, BlockFace.WEST
    };

    private final RaspiMcOpsPlugin plugin;
    private final NamespacedKey ownerKey;

    public ContainerLockService(RaspiMcOpsPlugin plugin) {
        this.plugin = plugin;
        this.ownerKey = new NamespacedKey(plugin, "container-owner");
    }

    public boolean isEnabled() {
        return plugin.getConfig().getBoolean("chest-lock.enabled", true);
    }

    public boolean setEnabled(boolean enabled) {
        plugin.getConfig().set("chest-lock.enabled", enabled);
        plugin.saveConfig();
        return enabled;
    }

    public boolean toggle() {
        return setEnabled(!isEnabled());
    }

    public String status() {
        return "chest lock: %s".formatted(isEnabled() ? "on" : "off");
    }

    public boolean handleCommand(CommandSender sender, String[] args) {
        String action = args.length == 0 ? "status" : args[0].toLowerCase();
        if (!action.equals("status") && !sender.hasPermission("raspimcops.chestlock.manage")) {
            sender.sendMessage("You do not have permission to change chest lock.");
            return true;
        }
        switch (action) {
            case "status" -> sender.sendMessage(status());
            case "on" -> {
                setEnabled(true);
                sender.sendMessage("chest lock enabled");
            }
            case "off" -> {
                setEnabled(false);
                sender.sendMessage("chest lock disabled");
            }
            case "toggle" -> sender.sendMessage(toggle() ? "chest lock enabled" : "chest lock disabled");
            default -> sender.sendMessage("Usage: /chestlock <status|on|off|toggle>");
        }
        return true;
    }

    private static boolean isLockable(Material material) {
        return material == Material.CHEST
            || material == Material.TRAPPED_CHEST
            || material == Material.BARREL
            || Tag.SHULKER_BOXES.isTagged(material);
    }

    /** Return the recorded placer, or null for unowned or non-tile blocks. */
    private UUID ownerOf(Block block) {
        if (!(block.getState() instanceof TileState state)) {
            return null;
        }
        String stored = state.getPersistentDataContainer().get(ownerKey, PersistentDataType.STRING);
        if (stored == null) {
            return null;
        }
        try {
            return UUID.fromString(stored);
        } catch (IllegalArgumentException error) {
            return null;
        }
    }

    private boolean deniesAccess(Block block, Player player) {
        UUID owner = ownerOf(block);
        return owner != null
            && !owner.equals(player.getUniqueId())
            && !player.hasPermission("raspimcops.chestlock.bypass");
    }

    private void deny(Player player) {
        player.sendActionBar(net.kyori.adventure.text.Component.text("This container is locked by its owner."));
    }

    /** Both halves of a double chest, or the single backing block otherwise. */
    private List<Block> holderBlocks(InventoryHolder holder) {
        List<Block> blocks = new ArrayList<>(2);
        if (holder instanceof DoubleChest doubleChest) {
            if (doubleChest.getLeftSide() instanceof BlockInventoryHolder left) {
                blocks.add(left.getBlock());
            }
            if (doubleChest.getRightSide() instanceof BlockInventoryHolder right) {
                blocks.add(right.getBlock());
            }
        } else if (holder instanceof BlockInventoryHolder blockHolder) {
            blocks.add(blockHolder.getBlock());
        }
        return blocks;
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onPlace(BlockPlaceEvent event) {
        Block block = event.getBlock();
        if (!isLockable(block.getType())) {
            return;
        }
        Player player = event.getPlayer();
        // Refuse extending a foreign locked chest into a shared double chest.
        if (isEnabled()
            && (block.getType() == Material.CHEST || block.getType() == Material.TRAPPED_CHEST)) {
            for (BlockFace face : CHEST_NEIGHBORS) {
                Block neighbor = block.getRelative(face);
                if (neighbor.getType() == block.getType() && deniesAccess(neighbor, player)) {
                    event.setCancelled(true);
                    deny(player);
                    return;
                }
            }
        }
        if (block.getState() instanceof TileState state) {
            state.getPersistentDataContainer().set(
                ownerKey, PersistentDataType.STRING, player.getUniqueId().toString()
            );
            state.update();
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onOpen(InventoryOpenEvent event) {
        if (!isEnabled() || !(event.getPlayer() instanceof Player player)) {
            return;
        }
        for (Block block : holderBlocks(event.getInventory().getHolder())) {
            if (deniesAccess(block, player)) {
                event.setCancelled(true);
                deny(player);
                return;
            }
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onBreak(BlockBreakEvent event) {
        Block block = event.getBlock();
        if (isEnabled() && isLockable(block.getType()) && deniesAccess(block, event.getPlayer())) {
            event.setCancelled(true);
            deny(event.getPlayer());
        }
    }
}
