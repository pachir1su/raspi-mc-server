package io.github.pachir1su.raspimcops;

import io.papermc.paper.event.player.AsyncChatEvent;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import net.kyori.adventure.text.serializer.plain.PlainTextComponentSerializer;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;

/** Append only real player chat events; no player means no file writes or polling. */
public final class ChatLogService implements Listener {
    private final RaspiMcOpsPlugin plugin;
    private final Object writeLock = new Object();

    public ChatLogService(RaspiMcOpsPlugin plugin) {
        this.plugin = plugin;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onChat(AsyncChatEvent event) {
        if (!plugin.getConfig().getBoolean("chat-log.enabled", true)) {
            return;
        }
        String message = PlainTextComponentSerializer.plainText()
            .serialize(event.message())
            .replace('\r', ' ')
            .replace('\n', ' ');
        String playerName = event.getPlayer().getName().replace('\r', '_').replace('\n', '_');
        String line = "%s <%s> %s%n".formatted(Instant.now(), playerName, message);
        synchronized (writeLock) {
            appendLine(line);
        }
    }

    /** Create the configured log lazily on the first actual chat message. */
    private void appendLine(String line) {
        String configuredName = plugin.getConfig().getString("chat-log.file", "chat.log");
        String safeName = configuredName != null && configuredName.matches("[A-Za-z0-9_.-]{1,64}")
            ? configuredName
            : "chat.log";
        Path path = plugin.getDataFolder().toPath().resolve(safeName);
        try {
            Files.createDirectories(path.getParent());
            Files.writeString(
                path,
                line,
                StandardCharsets.UTF_8,
                StandardOpenOption.CREATE,
                StandardOpenOption.APPEND
            );
        } catch (IOException error) {
            plugin.getLogger().warning("Could not append chat log: " + error.getMessage());
        }
    }
}
