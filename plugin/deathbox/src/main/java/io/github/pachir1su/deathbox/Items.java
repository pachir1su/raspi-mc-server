package io.github.pachir1su.deathbox;

import org.bukkit.inventory.ItemStack;
import org.bukkit.util.io.BukkitObjectInputStream;
import org.bukkit.util.io.BukkitObjectOutputStream;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.Base64;

/**
 * Loss-less ItemStack serialisation for virtual fallback boxes.
 *
 * <p>Items are serialised through Bukkit's own object stream, which preserves
 * exact metadata (enchantments, nested shulker contents, custom names). We never
 * turn items into command strings.
 */
final class Items {

    private Items() {
    }

    static String encode(ItemStack[] items) throws IOException {
        try (ByteArrayOutputStream bytes = new ByteArrayOutputStream();
             BukkitObjectOutputStream out = new BukkitObjectOutputStream(bytes)) {
            out.writeInt(items.length);
            for (ItemStack item : items) {
                out.writeObject(item);
            }
            out.flush();
            return Base64.getEncoder().encodeToString(bytes.toByteArray());
        }
    }

    static ItemStack[] decode(String data) throws IOException, ClassNotFoundException {
        byte[] raw = Base64.getDecoder().decode(data);
        try (ByteArrayInputStream bytes = new ByteArrayInputStream(raw);
             BukkitObjectInputStream in = new BukkitObjectInputStream(bytes)) {
            ItemStack[] items = new ItemStack[in.readInt()];
            for (int i = 0; i < items.length; i++) {
                items[i] = (ItemStack) in.readObject();
            }
            return items;
        }
    }
}
