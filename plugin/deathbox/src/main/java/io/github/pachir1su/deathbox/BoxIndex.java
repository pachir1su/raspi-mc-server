package io.github.pachir1su.deathbox;

import org.bukkit.configuration.file.YamlConfiguration;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Durable index of known boxes, backed by boxes.yml. This is the authority for
 * {@code /deathbox list|locate|recover|purge} and for reconciling records on
 * startup. It is the only on-disk state and it is written atomically.
 *
 * <p>The block's own persistent data still tags each container so access checks
 * work without consulting this file; the index just lets us answer queries and
 * hold virtual fallback boxes without scanning the world.
 */
final class BoxIndex {

    private final File file;
    private final Logger log;
    private final Map<String, BoxRecord> byId = new LinkedHashMap<>();

    BoxIndex(File dataFolder, Logger log) {
        this.file = new File(dataFolder, "boxes.yml");
        this.log = log;
    }

    synchronized void load() {
        byId.clear();
        if (!file.exists()) {
            return;
        }
        YamlConfiguration yaml = YamlConfiguration.loadConfiguration(file);
        var boxes = yaml.getConfigurationSection("boxes");
        if (boxes == null) {
            return;
        }
        for (String id : boxes.getKeys(false)) {
            var section = boxes.getConfigurationSection(id);
            if (section == null) {
                continue;
            }
            try {
                byId.put(id, BoxRecord.fromMap(id, section.getValues(false)));
            } catch (RuntimeException ex) {
                log.log(Level.WARNING, "Skipping unreadable box record " + id, ex);
            }
        }
    }

    synchronized void save() {
        YamlConfiguration yaml = new YamlConfiguration();
        for (BoxRecord r : byId.values()) {
            yaml.createSection("boxes." + r.id, r.toMap());
        }
        try {
            File parent = file.getParentFile();
            if (parent != null) {
                parent.mkdirs();
            }
            File tmp = new File(file.getParentFile(), file.getName() + ".tmp");
            yaml.save(tmp);
            Files.move(tmp.toPath(), file.toPath(),
                    StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException ex) {
            log.log(Level.SEVERE, "Failed to persist boxes.yml", ex);
        }
    }

    synchronized String newId() {
        String id;
        do {
            id = Long.toString(ThreadLocalRandom.current().nextLong() & Long.MAX_VALUE, 36);
        } while (byId.containsKey(id));
        return id;
    }

    synchronized void put(BoxRecord record) {
        byId.put(record.id, record);
        save();
    }

    synchronized void remove(String id) {
        if (byId.remove(id) != null) {
            save();
        }
    }

    synchronized BoxRecord get(String id) {
        return byId.get(id);
    }

    synchronized List<BoxRecord> all() {
        return new ArrayList<>(byId.values());
    }

    /** Count a player's active PHYSICAL (block) boxes, for the anti-grief cap. */
    synchronized int countPhysicalOwnedBy(UUID owner) {
        int count = 0;
        for (BoxRecord r : byId.values()) {
            if (!r.virtual && r.owner.equals(owner)) {
                count++;
            }
        }
        return count;
    }

    synchronized List<BoxRecord> ownedBy(UUID owner) {
        List<BoxRecord> out = new ArrayList<>();
        for (BoxRecord r : byId.values()) {
            if (r.owner.equals(owner)) {
                out.add(r);
            }
        }
        // Newest first.
        out.sort((a, b) -> Long.compare(b.created, a.created));
        return Collections.unmodifiableList(out);
    }
}
