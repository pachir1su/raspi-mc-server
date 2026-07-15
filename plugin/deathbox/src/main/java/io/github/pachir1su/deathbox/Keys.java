package io.github.pachir1su.deathbox;

import org.bukkit.NamespacedKey;
import org.bukkit.plugin.Plugin;

/** Namespaced keys used to tag box containers via the persistent data API. */
final class Keys {

    final NamespacedKey boxId;
    final NamespacedKey owner;

    Keys(Plugin plugin) {
        this.boxId = new NamespacedKey(plugin, "box_id");
        this.owner = new NamespacedKey(plugin, "owner_uuid");
    }
}
