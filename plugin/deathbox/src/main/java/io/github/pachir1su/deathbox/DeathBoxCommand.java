package io.github.pachir1su.deathbox;

import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

/** /deathbox locate | list | recover &lt;id&gt; | purge &lt;id&gt; confirm */
final class DeathBoxCommand implements CommandExecutor, TabCompleter {

    private final DeathBoxPlugin plugin;

    DeathBoxCommand(DeathBoxPlugin plugin) {
        this.plugin = plugin;
    }

    private Messages msg() {
        return plugin.messages();
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        String sub = args.length == 0 ? "help" : args[0].toLowerCase();
        switch (sub) {
            case "locate" -> locate(sender, args);
            case "list" -> list(sender, args);
            case "recover" -> recover(sender, args);
            case "purge" -> purge(sender, args);
            default -> sender.sendMessage(msg().get("cmd.usage"));
        }
        return true;
    }

    private UUID resolveOwner(CommandSender sender, String[] args) {
        if (args.length >= 2) {
            if (!sender.hasPermission("deathbox.admin")) {
                deny(sender);
                return null;
            }
            OfflinePlayer target = Bukkit.getOfflinePlayer(args[1]);
            if (!target.hasPlayedBefore() && !target.isOnline()) {
                sender.sendMessage(msg().get("cmd.player-not-found", "name", args[1]));
                return null;
            }
            return target.getUniqueId();
        }
        if (sender instanceof Player player) {
            return player.getUniqueId();
        }
        sender.sendMessage(msg().get("cmd.console-usage"));
        return null;
    }

    private void locate(CommandSender sender, String[] args) {
        UUID owner = resolveOwner(sender, args);
        if (owner == null) return;
        List<BoxRecord> boxes = plugin.index().ownedBy(owner);
        if (boxes.isEmpty()) {
            sender.sendMessage(msg().get("cmd.none"));
            return;
        }
        sender.sendMessage(msg().get("cmd.newest", "desc", describe(boxes.get(0))));
    }

    private void list(CommandSender sender, String[] args) {
        UUID owner = resolveOwner(sender, args);
        if (owner == null) return;
        List<BoxRecord> boxes = plugin.index().ownedBy(owner);
        if (boxes.isEmpty()) {
            sender.sendMessage(msg().get("cmd.none"));
            return;
        }
        sender.sendMessage(msg().get("cmd.list-header", "count", boxes.size()));
        for (BoxRecord box : boxes) {
            sender.sendMessage(msg().get("cmd.list-item", "id", box.id, "desc", describe(box)));
        }
    }

    private void recover(CommandSender sender, String[] args) {
        if (!sender.hasPermission("deathbox.admin")) {
            deny(sender);
            return;
        }
        if (args.length < 2) {
            sender.sendMessage(msg().get("cmd.recover-usage"));
            return;
        }
        if (!(sender instanceof Player player)) {
            sender.sendMessage(msg().get("cmd.recover-ingame"));
            return;
        }
        BoxRecord box = plugin.index().get(args[1]);
        if (box == null) {
            sender.sendMessage(msg().get("cmd.no-box", "id", args[1]));
            return;
        }
        if (!box.virtual) {
            sender.sendMessage(msg().get("cmd.recover-physical", "id", box.id, "desc", describe(box)));
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
            sender.sendMessage(msg().get("cmd.recovered", "id", box.id, "owner", box.ownerName));
        } catch (Exception ex) {
            sender.sendMessage(msg().get("cmd.recover-failed", "id", box.id));
            plugin.getLogger().warning("Failed to recover box " + box.id + ": " + ex.getMessage());
        }
    }

    private void purge(CommandSender sender, String[] args) {
        if (!sender.hasPermission("deathbox.admin")) {
            deny(sender);
            return;
        }
        if (args.length < 2) {
            sender.sendMessage(msg().get("cmd.purge-usage"));
            return;
        }
        BoxRecord box = plugin.index().get(args[1]);
        if (box == null) {
            sender.sendMessage(msg().get("cmd.no-box", "id", args[1]));
            return;
        }
        if (args.length < 3 || !args[2].equalsIgnoreCase("confirm")) {
            sender.sendMessage(msg().get("cmd.purge-confirm", "id", box.id));
            return;
        }
        plugin.purgeBox(box);
        sender.sendMessage(msg().get("cmd.purged", "id", box.id));
    }

    private String describe(BoxRecord box) {
        if (box.virtual) {
            return msg().get("desc.virtual", "id", box.id);
        }
        return msg().get("desc.physical", "x", box.x, "y", box.y, "z", box.z, "world", box.world);
    }

    private void deny(CommandSender sender) {
        sender.sendMessage(msg().get("cmd.deny"));
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
                && (args[0].equalsIgnoreCase("locate") || args[0].equalsIgnoreCase("list"))) {
            return null; // default to online player names
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
