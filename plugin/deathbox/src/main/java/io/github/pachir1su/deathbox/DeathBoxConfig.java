package io.github.pachir1su.deathbox;

import org.bukkit.configuration.file.FileConfiguration;

/** Typed, validated view over config.yml. */
final class DeathBoxConfig {

    enum Container {
        DOUBLE_CHEST(54),
        CHEST(27),
        BARREL(27);

        final int slots;

        Container(int slots) {
            this.slots = slots;
        }
    }

    final boolean enabled;
    final Container container;
    final int searchRadius;
    final int expireHours;
    final boolean friendsCanOpen;
    final boolean fallbackVirtualBox;

    private DeathBoxConfig(boolean enabled, Container container, int searchRadius,
                           int expireHours, boolean friendsCanOpen, boolean fallbackVirtualBox) {
        this.enabled = enabled;
        this.container = container;
        this.searchRadius = searchRadius;
        this.expireHours = expireHours;
        this.friendsCanOpen = friendsCanOpen;
        this.fallbackVirtualBox = fallbackVirtualBox;
    }

    static DeathBoxConfig from(FileConfiguration c) {
        Container container = switch (c.getString("container", "double-chest").toLowerCase()) {
            case "chest" -> Container.CHEST;
            case "barrel" -> Container.BARREL;
            default -> Container.DOUBLE_CHEST;
        };
        // Clamp the radius so a misconfiguration can never trigger a huge search.
        int radius = Math.max(1, Math.min(8, c.getInt("search-radius", 4)));
        int expire = Math.max(0, c.getInt("expire-hours", 0));
        return new DeathBoxConfig(
                c.getBoolean("enabled", true),
                container,
                radius,
                expire,
                c.getBoolean("friends-can-open", false),
                c.getBoolean("fallback-virtual-box", true));
    }
}
