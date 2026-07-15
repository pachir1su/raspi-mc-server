"""Keep Discord's visible slash-command surface deliberately small."""

from discord import app_commands


VISIBLE_TOP_LEVEL_COMMANDS = frozenset({"server", "admin", "my-tools", "upload"})


def pruneCommandTree(tree: app_commands.CommandTree) -> list[str]:
    """Remove legacy top-level commands after cogs register their callbacks."""
    removedNames = []
    for command in list(tree.get_commands()):
        if command.name not in VISIBLE_TOP_LEVEL_COMMANDS:
            tree.remove_command(command.name)
            removedNames.append(command.name)
    return removedNames
