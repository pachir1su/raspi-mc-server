package io.github.pachir1su.deathbox;

import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.FileConfiguration;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Player-facing text with Korean defaults, overridable from the config's
 * {@code messages:} section (#60). Server owners can translate or reword any
 * line without touching the plugin. Placeholders look like {@code {name}} and
 * are substituted case-sensitively.
 *
 * <p>Legacy §-colour codes are kept in the defaults so the plugin stays free of
 * Adventure API assumptions; {@code sendMessage(String)} renders them.
 */
final class Messages {

    private static final Map<String, String> DEFAULTS = new LinkedHashMap<>();

    static {
        DEFAULTS.put("death.stored",
                "§6[데스박스] §f아이템을 §e{x}, {y}, {z} §7({world})§f 에 보관했어요. "
                        + "언제든 §e/deathbox locate §f로 찾을 수 있어요.");
        DEFAULTS.put("death.virtual",
                "§6[데스박스] §f상자를 놓을 안전한 자리가 없어 아이템을 §e{id} §f상자에 "
                        + "안전하게 보관했어요. 관리자에게 §e/deathbox recover {id} §f를 요청하세요.");
        DEFAULTS.put("death.limit-virtual",
                "§6[데스박스] §f활성 데스박스가 너무 많아 이번 아이템은 §e{id} §f상자에 "
                        + "보관했어요. 관리자에게 §e/deathbox recover {id} §f를 요청하세요.");
        DEFAULTS.put("protect.not-yours", "§6[데스박스] §c다른 사람의 데스박스예요.");
        DEFAULTS.put("protect.break",
                "§6[데스박스] §f상자를 열어 아이템을 꺼내세요. 비면 저절로 사라져요.");
        DEFAULTS.put("cmd.usage", "§6[데스박스] §f/deathbox <locate|list|recover|purge>");
        DEFAULTS.put("cmd.player-not-found",
                "§6[데스박스] §c플레이어 §e{name}§c 을(를) 찾을 수 없어요.");
        DEFAULTS.put("cmd.console-usage",
                "§6[데스박스] §f콘솔에서는: /deathbox locate <플레이어>");
        DEFAULTS.put("cmd.none", "§6[데스박스] §f활성화된 데스박스가 없어요.");
        DEFAULTS.put("cmd.newest", "§6[데스박스] §f가장 최근 상자: {desc}");
        DEFAULTS.put("cmd.list-header", "§6[데스박스] §f상자 ({count}개):");
        DEFAULTS.put("cmd.list-item", "  §7- §e{id} §f{desc}");
        DEFAULTS.put("cmd.recover-usage", "§6[데스박스] §f/deathbox recover <id>");
        DEFAULTS.put("cmd.recover-ingame",
                "§6[데스박스] §c아이템을 받을 공간이 필요하니 게임 안에서 실행하세요.");
        DEFAULTS.put("cmd.no-box", "§6[데스박스] §c§e{id}§c 상자를 찾을 수 없어요.");
        DEFAULTS.put("cmd.recover-physical",
                "§6[데스박스] §f§e{id} §f상자는 {desc} 에 있는 실제 상자예요. "
                        + "회수 대신 직접 방문하세요.");
        DEFAULTS.put("cmd.recovered",
                "§6[데스박스] §f§e{id} §f상자(주인 {owner})를 인벤토리로 회수했어요.");
        DEFAULTS.put("cmd.recover-failed",
                "§6[데스박스] §c§e{id}§c 상자를 해독할 수 없어요. 콘솔을 확인하세요.");
        DEFAULTS.put("cmd.purge-usage", "§6[데스박스] §f/deathbox purge <id> confirm");
        DEFAULTS.put("cmd.purge-confirm",
                "§6[데스박스] §e상자 {id} 와 내용물을 영구 삭제합니다. "
                        + "§f/deathbox purge {id} confirm §e를 다시 실행하세요.");
        DEFAULTS.put("cmd.purged", "§6[데스박스] §f§e{id}§f 상자를 삭제했어요.");
        DEFAULTS.put("cmd.deny", "§6[데스박스] §c그 작업을 할 권한이 없어요.");
        DEFAULTS.put("desc.virtual", "§7(가상 보관 중 — /deathbox recover {id})");
        DEFAULTS.put("desc.physical", "§e{x}, {y}, {z} §7({world})");
    }

    private final Map<String, String> messages = new LinkedHashMap<>(DEFAULTS);

    Messages(FileConfiguration config) {
        ConfigurationSection section = config.getConfigurationSection("messages");
        if (section == null) {
            return;
        }
        for (String key : DEFAULTS.keySet()) {
            String override = section.getString(key);
            if (override != null && !override.isBlank()) {
                messages.put(key, override);
            }
        }
    }

    /** Look up a message and substitute {@code {key}} placeholders in pairs. */
    String get(String key, Object... replacements) {
        String template = messages.getOrDefault(key, key);
        for (int i = 0; i + 1 < replacements.length; i += 2) {
            template = template.replace(
                    "{" + replacements[i] + "}", String.valueOf(replacements[i + 1]));
        }
        return template;
    }
}
