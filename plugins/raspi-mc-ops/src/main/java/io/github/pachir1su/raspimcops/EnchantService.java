package io.github.pachir1su.raspimcops;

import java.util.Locale;
import java.util.regex.Pattern;
import org.bukkit.Bukkit;
import org.bukkit.NamespacedKey;
import org.bukkit.Registry;
import org.bukkit.command.CommandSender;
import org.bukkit.enchantments.Enchantment;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;

/**
 * {@code /enchantheld <player> <enchant> <level>} — applies an enchantment to a
 * player's held item without vanilla's compatibility or max-level checks, using
 * {@link ItemStack#addUnsafeEnchantment}. Owner-only cheat surface driven by the
 * Discord bot; vanilla {@code /enchant} refuses e.g. Sharpness on a pickaxe or
 * levels above the natural cap, which is exactly what issue #62 wants to allow.
 */
final class EnchantService {

    /** Same shape the bot validates: 1-16 Java chars, or a dot-prefixed Bedrock name. */
    private static final Pattern SERVER_PLAYER_NAME = Pattern.compile(
        "(?:[A-Za-z0-9_]{1,16}|\\.[A-Za-z0-9_]{1,32})"
    );

    /** Enchantment ids are lowercase resource keys, optionally minecraft:-prefixed. */
    private static final Pattern ENCHANT_ID = Pattern.compile("[a-z0-9_]{1,64}");

    /** Data value cap: enchantment level is stored as a short, so keep it sane. */
    static final int MAX_LEVEL = 255;

    private final RaspiMcOpsPlugin plugin;

    EnchantService(RaspiMcOpsPlugin plugin) {
        this.plugin = plugin;
    }

    /** Parse and clamp a level string to 1..MAX_LEVEL, or throw for non-numbers. */
    static int parseLevel(String raw) {
        int value;
        try {
            value = Integer.parseInt(raw.trim());
        } catch (NumberFormatException ex) {
            throw new IllegalArgumentException("Level must be a whole number: " + raw);
        }
        return Math.max(1, Math.min(MAX_LEVEL, value));
    }

    /** Normalize an enchant id to a bare lowercase key, rejecting unsafe input. */
    static String normalizeEnchantId(String raw) {
        String cleaned = raw.trim().toLowerCase(Locale.ROOT);
        if (cleaned.startsWith("minecraft:")) {
            cleaned = cleaned.substring("minecraft:".length());
        }
        if (!ENCHANT_ID.matcher(cleaned).matches()) {
            throw new IllegalArgumentException("Invalid enchantment id: " + raw);
        }
        return cleaned;
    }

    boolean handleCommand(CommandSender sender, String[] args) {
        if (!sender.hasPermission("raspimcops.enchant")) {
            sender.sendMessage("You do not have permission to use this command.");
            return true;
        }
        if (args.length != 3) {
            sender.sendMessage("Usage: /enchantheld <exact-player-name> <enchant> <level>");
            return true;
        }
        String playerName = args[0];
        if (!SERVER_PLAYER_NAME.matcher(playerName).matches()) {
            sender.sendMessage("Invalid exact player name.");
            return true;
        }
        Player player = Bukkit.getPlayerExact(playerName);
        if (player == null) {
            sender.sendMessage("Player is not online: " + playerName);
            return true;
        }
        String enchantId = normalizeEnchantId(args[1]);
        int level = parseLevel(args[2]);
        Enchantment enchantment = resolve(enchantId);
        if (enchantment == null) {
            sender.sendMessage("Unknown enchantment: " + enchantId);
            return true;
        }
        ItemStack held = player.getInventory().getItemInMainHand();
        if (held == null || held.getType().isAir()) {
            sender.sendMessage(playerName + " is not holding an item.");
            return true;
        }
        // Unsafe = skip target-compatibility and max-level checks on purpose.
        held.addUnsafeEnchantment(enchantment, level);
        sender.sendMessage("Enchanted " + playerName + "'s "
            + held.getType().getKey().getKey() + " with " + enchantId + " " + level + ".");
        return true;
    }

    /** Look up an enchantment by its resource key via the registry. */
    private Enchantment resolve(String enchantId) {
        NamespacedKey key = NamespacedKey.minecraft(enchantId);
        return Registry.ENCHANTMENT.get(key);
    }
}
