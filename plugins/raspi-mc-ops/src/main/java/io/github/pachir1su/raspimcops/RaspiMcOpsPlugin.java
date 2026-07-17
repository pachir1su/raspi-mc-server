package io.github.pachir1su.raspimcops;

import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;

/** Paper entry point for bounded RCON helpers and event-driven safety features. */
public final class RaspiMcOpsPlugin extends JavaPlugin {
    private static final Pattern SERVER_PLAYER_NAME = Pattern.compile(
        "(?:[A-Za-z0-9_]{1,16}|\\.[A-Za-z0-9_]{1,32})"
    );

    private SpawnProtectionService spawnProtection;
    private ContainerLockService containerLock;
    private EnchantService enchant;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        spawnProtection = new SpawnProtectionService(this);
        containerLock = new ContainerLockService(this);
        enchant = new EnchantService(this);
        Bukkit.getPluginManager().registerEvents(new ChatLogService(this), this);
        Bukkit.getPluginManager().registerEvents(spawnProtection, this);
        Bukkit.getPluginManager().registerEvents(containerLock, this);

        requireCommand("raspiops").setExecutor(this);
        requireCommand("spawnprotection").setExecutor(this);
        requireCommand("chestlock").setExecutor(this);
        requireCommand("enchantheld").setExecutor(this);
        getLogger().info(
            "RaspiMcOps enabled: chat log=%s, %s, %s".formatted(
                getConfig().getBoolean("chat-log.enabled", true),
                spawnProtection.status(),
                containerLock.status()
            )
        );
    }

    private org.bukkit.command.PluginCommand requireCommand(String name) {
        org.bukkit.command.PluginCommand command = getCommand(name);
        if (command == null) {
            throw new IllegalStateException("plugin.yml command is missing: " + name);
        }
        return command;
    }

    @Override
    public boolean onCommand(
        CommandSender sender,
        Command command,
        String label,
        String[] args
    ) {
        try {
            return switch (command.getName().toLowerCase(Locale.ROOT)) {
                case "raspiops" -> handleRaspiOps(sender, args);
                case "spawnprotection" -> spawnProtection.handleCommand(sender, args);
                case "chestlock" -> containerLock.handleCommand(sender, args);
                case "enchantheld" -> enchant.handleCommand(sender, args);
                default -> false;
            };
        } catch (RuntimeException error) {
            getLogger().warning("Command failed: " + error.getMessage());
            sender.sendMessage("Command failed safely: " + error.getMessage());
            return true;
        }
    }

    /** Route the narrow console helpers the Discord bot depends on. */
    private boolean handleRaspiOps(CommandSender sender, String[] args) {
        if (!sender.hasPermission("raspimcops.rescue")) {
            sender.sendMessage("You do not have permission to use this command.");
            return true;
        }
        if (args.length == 1 && args[0].equalsIgnoreCase("weather")) {
            return handleWeatherQuery(sender);
        }
        if (args.length != 2 || !args[0].equalsIgnoreCase("rescue")) {
            sender.sendMessage("Usage: /raspiops <rescue <exact-player-name>|weather>");
            return true;
        }
        String playerName = args[1];
        if (!SERVER_PLAYER_NAME.matcher(playerName).matches()) {
            sender.sendMessage("Invalid exact player name.");
            return true;
        }
        Player player = Bukkit.getPlayerExact(playerName);
        if (player == null) {
            sender.sendMessage("Player is not online: " + playerName);
            return true;
        }
        List<World> worlds = Bukkit.getWorlds();
        if (worlds.isEmpty()) {
            sender.sendMessage("No world is loaded.");
            return true;
        }
        Location destination = worlds.getFirst().getSpawnLocation().clone().add(0.5, 0, 0.5);
        if (!player.teleport(destination)) {
            sender.sendMessage("Paper rejected the spawn teleport.");
            return true;
        }
        sender.sendMessage("Teleported " + playerName + " to " + destination.getWorld().getName()
            + " spawn at " + destination.getBlockX() + " " + destination.getBlockY()
            + " " + destination.getBlockZ());
        return true;
    }

    /** Read-only weather report for the primary world: clear, rain, or thunder. */
    private boolean handleWeatherQuery(CommandSender sender) {
        List<World> worlds = Bukkit.getWorlds();
        if (worlds.isEmpty()) {
            sender.sendMessage("No world is loaded.");
            return true;
        }
        World world = worlds.getFirst();
        String state = world.isThundering() ? "thunder" : world.hasStorm() ? "rain" : "clear";
        sender.sendMessage("weather: " + state);
        return true;
    }
}
