package io.github.pachir1su.raspimcops;

import java.util.List;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.entity.Projectile;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockExplodeEvent;
import org.bukkit.event.block.BlockPistonExtendEvent;
import org.bukkit.event.block.BlockPistonRetractEvent;
import org.bukkit.event.block.BlockPlaceEvent;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityExplodeEvent;
import org.bukkit.event.hanging.HangingBreakByEntityEvent;
import org.bukkit.event.player.PlayerBucketEmptyEvent;
import org.bukkit.event.player.PlayerBucketFillEvent;
import org.bukkit.event.player.PlayerInteractEntityEvent;
import org.bukkit.event.player.PlayerInteractEvent;

/** Event-level spawn safe zone with a persistent owner toggle. */
public final class SpawnProtectionService implements Listener {
    private final RaspiMcOpsPlugin plugin;

    public SpawnProtectionService(RaspiMcOpsPlugin plugin) {
        this.plugin = plugin;
    }

    public World protectedWorld() {
        String worldName = plugin.getConfig().getString("spawn-protection.world", "");
        World configuredWorld = worldName == null || worldName.isBlank()
            ? null
            : Bukkit.getWorld(worldName);
        List<World> worlds = Bukkit.getWorlds();
        return configuredWorld != null ? configuredWorld : (worlds.isEmpty() ? null : worlds.getFirst());
    }

    public boolean isEnabled() {
        return plugin.getConfig().getBoolean("spawn-protection.enabled", true);
    }

    public boolean isProtected(Location location) {
        World world = protectedWorld();
        if (!isEnabled() || world == null || !world.equals(location.getWorld())) {
            return false;
        }
        int radius = plugin.getConfig().getInt("spawn-protection.radius", 16);
        SpawnRegion region = new SpawnRegion(
            world.getSpawnLocation().getBlockX(),
            world.getSpawnLocation().getBlockZ(),
            radius
        );
        return region.contains(location.getBlockX(), location.getBlockZ());
    }

    public boolean setEnabled(boolean enabled) {
        plugin.getConfig().set("spawn-protection.enabled", enabled);
        plugin.saveConfig();
        return enabled;
    }

    public boolean toggle() {
        return setEnabled(!isEnabled());
    }

    public String status() {
        World world = protectedWorld();
        int radius = plugin.getConfig().getInt("spawn-protection.radius", 16);
        return "spawn protection: %s, world=%s, radius=%d".formatted(
            isEnabled() ? "on" : "off",
            world == null ? "unavailable" : world.getName(),
            radius
        );
    }

    public boolean handleCommand(CommandSender sender, String[] args) {
        String action = args.length == 0 ? "status" : args[0].toLowerCase();
        if (!action.equals("status") && !sender.hasPermission("raspimcops.spawn.manage")) {
            sender.sendMessage("You do not have permission to change spawn protection.");
            return true;
        }
        switch (action) {
            case "status" -> sender.sendMessage(status());
            case "on" -> {
                setEnabled(true);
                sender.sendMessage("spawn protection enabled");
            }
            case "off" -> {
                setEnabled(false);
                sender.sendMessage("spawn protection disabled");
            }
            case "toggle" -> sender.sendMessage(toggle() ? "spawn protection enabled" : "spawn protection disabled");
            default -> sender.sendMessage("Usage: /spawnprotection <status|on|off|toggle>");
        }
        return true;
    }

    private boolean canBypass(Player player) {
        return player.hasPermission("raspimcops.spawn.bypass");
    }

    private void deny(Player player) {
        player.sendActionBar(net.kyori.adventure.text.Component.text("Spawn safe zone is protected."));
    }

    private Player responsiblePlayer(Entity entity) {
        if (entity instanceof Player player) {
            return player;
        }
        if (entity instanceof Projectile projectile && projectile.getShooter() instanceof Player player) {
            return player;
        }
        return null;
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onBreak(BlockBreakEvent event) {
        if (isProtected(event.getBlock().getLocation()) && !canBypass(event.getPlayer())) {
            event.setCancelled(true);
            deny(event.getPlayer());
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onPlace(BlockPlaceEvent event) {
        if (isProtected(event.getBlock().getLocation()) && !canBypass(event.getPlayer())) {
            event.setCancelled(true);
            deny(event.getPlayer());
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onInteract(PlayerInteractEvent event) {
        Block block = event.getClickedBlock();
        if (block != null && isProtected(block.getLocation()) && !canBypass(event.getPlayer())) {
            event.setCancelled(true);
            deny(event.getPlayer());
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onInteractEntity(PlayerInteractEntityEvent event) {
        if (isProtected(event.getRightClicked().getLocation()) && !canBypass(event.getPlayer())) {
            event.setCancelled(true);
            deny(event.getPlayer());
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onDamage(EntityDamageByEntityEvent event) {
        Player player = responsiblePlayer(event.getDamager());
        if (player != null && isProtected(event.getEntity().getLocation()) && !canBypass(player)) {
            event.setCancelled(true);
            deny(player);
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onHangingBreak(HangingBreakByEntityEvent event) {
        Player player = responsiblePlayer(event.getRemover());
        if (player != null && isProtected(event.getEntity().getLocation()) && !canBypass(player)) {
            event.setCancelled(true);
            deny(player);
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onBucketEmpty(PlayerBucketEmptyEvent event) {
        if (isProtected(event.getBlockClicked().getLocation()) && !canBypass(event.getPlayer())) {
            event.setCancelled(true);
            deny(event.getPlayer());
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onBucketFill(PlayerBucketFillEvent event) {
        if (isProtected(event.getBlockClicked().getLocation()) && !canBypass(event.getPlayer())) {
            event.setCancelled(true);
            deny(event.getPlayer());
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onPistonExtend(BlockPistonExtendEvent event) {
        if (event.getBlocks().stream().anyMatch(block -> isProtected(block.getRelative(event.getDirection()).getLocation()))) {
            event.setCancelled(true);
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onPistonRetract(BlockPistonRetractEvent event) {
        if (event.getBlocks().stream().anyMatch(block -> isProtected(block.getLocation()))) {
            event.setCancelled(true);
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onBlockExplode(BlockExplodeEvent event) {
        event.blockList().removeIf(block -> isProtected(block.getLocation()));
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onEntityExplode(EntityExplodeEvent event) {
        event.blockList().removeIf(block -> isProtected(block.getLocation()));
    }
}
