package io.github.pachir1su.deathbox;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.World;

import java.util.UUID;

/**
 * One tracked box. Physical boxes carry a world/coordinates; virtual fallback
 * boxes carry {@code items} (a base64 blob) instead of a location.
 */
final class BoxRecord {

    final String id;
    final UUID owner;
    final String ownerName;
    final long created;      // epoch millis
    final boolean virtual;

    // Physical boxes only.
    final String world;
    final int x;
    final int y;
    final int z;

    // Virtual boxes only.
    final String items;

    private BoxRecord(String id, UUID owner, String ownerName, long created, boolean virtual,
                      String world, int x, int y, int z, String items) {
        this.id = id;
        this.owner = owner;
        this.ownerName = ownerName;
        this.created = created;
        this.virtual = virtual;
        this.world = world;
        this.x = x;
        this.y = y;
        this.z = z;
        this.items = items;
    }

    static BoxRecord physical(String id, UUID owner, String ownerName, Location loc) {
        return new BoxRecord(id, owner, ownerName, System.currentTimeMillis(), false,
                loc.getWorld().getName(), loc.getBlockX(), loc.getBlockY(), loc.getBlockZ(), null);
    }

    static BoxRecord virtual(String id, UUID owner, String ownerName, String items) {
        return new BoxRecord(id, owner, ownerName, System.currentTimeMillis(), true,
                null, 0, 0, 0, items);
    }

    /** Rehydrate from a config section's map. */
    static BoxRecord fromMap(String id, java.util.Map<String, Object> m) {
        boolean virtual = Boolean.TRUE.equals(m.get("virtual"));
        return new BoxRecord(
                id,
                UUID.fromString(String.valueOf(m.get("owner"))),
                String.valueOf(m.getOrDefault("owner-name", "?")),
                m.get("created") instanceof Number n ? n.longValue() : 0L,
                virtual,
                virtual ? null : String.valueOf(m.get("world")),
                asInt(m.get("x")), asInt(m.get("y")), asInt(m.get("z")),
                virtual ? String.valueOf(m.get("items")) : null);
    }

    java.util.Map<String, Object> toMap() {
        java.util.Map<String, Object> m = new java.util.LinkedHashMap<>();
        m.put("owner", owner.toString());
        m.put("owner-name", ownerName);
        m.put("created", created);
        m.put("virtual", virtual);
        if (virtual) {
            m.put("items", items);
        } else {
            m.put("world", world);
            m.put("x", x);
            m.put("y", y);
            m.put("z", z);
        }
        return m;
    }

    /** Physical location, or null for a virtual box or an unloaded world. */
    Location location() {
        if (virtual) {
            return null;
        }
        World w = Bukkit.getWorld(world);
        return w == null ? null : new Location(w, x, y, z);
    }

    private static int asInt(Object o) {
        return o instanceof Number n ? n.intValue() : 0;
    }
}
