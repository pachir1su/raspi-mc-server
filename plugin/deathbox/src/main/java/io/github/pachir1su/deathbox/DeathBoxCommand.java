package io.github.pachir1su.deathbox;

import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/** /deathbox locate | list | recover &lt;id&gt; | purge &lt;id&gt; confirm */
final class DeathBoxCommand implements CommandExecutor, TabCompleter {

    private final DeathBoxPlugin plugin;

    DeathBoxCommand(DeathBoxPlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        String sub = args.length == 0 ? "help" : args[0].toLowerCase();
        switch (sub) {
            case "locate" -> locate(sender);
            case "list" -> list(sender);
            case "recover" -> recover(sender, args);
            case "purge" -> purge(sender, args);
            default -> sender.sendMessage("§6[DeathBox] §f/deathbox <locate|list|recover|purge>");
        }
        return true;
    }

    private void locate(CommandSender sender) {
        if (!(sender instanceof Player player)) {
            sender.sendMessage("§6[DeathBox] §cOnly players have death boxes.");
            return;
        }
        List<BoxRecord> boxes = plugin.index().ownedBy(player.getUniqueId());
        if (boxes.isEmpty()) {
            player.sendMessage("§6[DeathBox] §fYou have no active death boxes.");
            return;
        }
        player.sendMessage("§6[DeathBox] §fNewest box: " + describe(boxes.get(0)));
    }

    private void list(CommandSender sender) {
        if (!(sender instanceof Player player)) {
            sender.sendMessage("§6[DeathBox] §cOnly players have death boxes.");
            return;
        }
        List<BoxRecord> boxes = plugin.index().ownedBy(player.getUniqueId());
        if (boxes.isEmpty()) {
            player.sendMessage("§6[DeathBox] §fYou have no active death boxes.");
            return;
        }
        player.sendMessage("§6[DeathBox] §fYour boxes (" + boxes.size() + "):");
        for (BoxRecord box : boxes) {
            player.sendMessage("  §7- §e" + box.id + " §f" + describe(box));
        }
    }

    private void recover(CommandSender sender, String[] args) {
        if (!sender.hasPermission("deathbox.admin")) {
            deny(sender);
            return;
        }
        if (args.length < 2) {
            sender.sendMessage("§6[DeathBox] §f/deathbox recover <id>");
            return;
        }
        if (!(sender instanceof Player player)) {
            sender.sendMessage("§6[DeathBox] §cRun this in-game so the items have somewhere to go.");
            return;
        }
        BoxRecord box = plugin.index().get(args[1]);
        if (box == null) {
            sender.sendMessage("§6[DeathBox] §cNo box with id §e" + args[1] + "§c.");
            return;
        }
        if (!box.virtual) {
            sender.sendMessage("§6[DeathBox] §fBox §e" + box.id + " §fis a physical chest at "
                    + describe(box) + ". Visit it instead of recovering.");
            return;
        }
        try {
            ItemStack[] items = Items.decode(box.items);
            for (ItemStack item : items) {
                if (item == null || item.getType().isAir()) {
                    continue;
                }
                for (ItemStack leftover : player.getInventory().addItem(item).values()) {
                    player.getWorld().dropItemNaturally(player.getLocation(), leftover);
                }
            }
            plugin.index().remove(box.id);
            sender.sendMessage("§6[DeathBox] §fRecovered box §e" + box.id + " §f(owner "
                    + box.ownerName + ") into your inventory.");
        } catch (Exception ex) {
            sender.sendMessage("§6[DeathBox] §cCould not decode box §e" + box.id + "§c; see console.");
            plugin.getLogger().warning("Failed to recover box " + box.id + ": " + ex.getMessage());
        }
    }

    private void purge(CommandSender sender, String[] args) {
        if (!sender.hasPermission("deathbox.admin")) {
            deny(sender);
            return;
        }
        if (args.length < 2) {
            sender.sendMessage("§6[DeathBox] §f/deathbox purge <id> confirm");
            return;
        }
        BoxRecord box = plugin.index().get(args[1]);
        if (box == null) {
            sender.sendMessage("§6[DeathBox] §cNo box with id §e" + args[1] + "§c.");
            return;
        }
        if (args.length < 3 || !args[2].equalsIgnoreCase("confirm")) {
            sender.sendMessage("§6[DeathBox] §eThis permanently deletes box " + box.id
                    + " and its contents. Re-run §f/deathbox purge " + box.id + " confirm§e to proceed.");
            return;
        }
        plugin.purgeBox(box);
        sender.sendMessage("§6[DeathBox] §fPurged box §e" + box.id + "§f.");
    }

    private String describe(BoxRecord box) {
        if (box.virtual) {
            return "§7(held virtually — /deathbox recover " + box.id + ")";
        }
        return "§e" + box.x + ", " + box.y + ", " + box.z + " §7(" + box.world + ")";
    }

    private void deny(CommandSender sender) {
        sender.sendMessage("§6[DeathBox] §cYou don't have permission for that.");
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (args.length == 1) {
            List<String> subs = new ArrayList<>(List.of("locate", "list"));
            if (sender.hasPermission("deathbox.admin")) {
                subs.add("recover");
                subs.add("purge");
            }
            return prefix(subs, args[0]);
        }
        if (args.length == 2 && sender.hasPermission("deathbox.admin")
                && (args[0].equalsIgnoreCase("recover") || args[0].equalsIgnoreCase("purge"))) {
            List<String> ids = plugin.index().all().stream().map(b -> b.id).collect(Collectors.toList());
            return prefix(ids, args[1]);
        }
        if (args.length == 3 && args[0].equalsIgnoreCase("purge")) {
            return prefix(List.of("confirm"), args[2]);
        }
        return List.of();
    }

    private static List<String> prefix(List<String> options, String typed) {
        String lower = typed.toLowerCase();
        return options.stream().filter(o -> o.toLowerCase().startsWith(lower)).collect(Collectors.toList());
    }
}
