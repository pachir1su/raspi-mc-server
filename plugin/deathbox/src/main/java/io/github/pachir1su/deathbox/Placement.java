package io.github.pachir1su.deathbox;

import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.block.BlockFace;
import org.bukkit.block.Container;
import org.bukkit.block.DoubleChest;
import org.bukkit.block.TileState;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.bukkit.persistence.PersistentDataType;

import java.util.ArrayList;
import java.util.List;

/**
 * Bounded, safe placement of a box container near a death location.
 *
 * <p>The search is deliberately small (a few blocks around the death block) and
 * never scans a whole chunk. If nothing safe is found the caller falls back to a
 * virtual box, so items are never dropped as vulnerable ground entities.
 */
final class Placement {

    private final Keys keys;

    Placement(Keys keys) {
        this.keys = keys;
    }

    /** The blocks a placed box occupies, so callers can tag and clean them up. */
    static final class Placed {
        final Inventory inventory;
        final List<Block> blocks;

        Placed(Inventory inventory, List<Block> blocks) {
            this.inventory = inventory;
            this.blocks = blocks;
        }
    }

    /**
     * Try to place the configured container near {@code death}, tag it with the
     * owner/box id, and return the writable inventory. Returns null when no safe
     * spot exists.
     */
    Placed place(Location death, DeathBoxConfig cfg, String boxId, java.util.UUID owner) {
        World world = death.getWorld();
        if (world == null) {
            return null;
        }
        boolean doubleChest = cfg.container == DeathBoxConfig.Container.DOUBLE_CHEST;

        for (Block base : candidates(death, cfg.searchRadius)) {
            if (!safe(base)) {
                continue;
            }
            if (doubleChest) {
                Block partner = safePartner(base);
                if (partner == null) {
                    continue;
                }
                Placed placed = buildDoubleChest(base, partner, boxId, owner);
                if (placed != null) {
                    return placed;
                }
            } else {
                return buildSingle(base, cfg.container, boxId, owner);
            }
        }
        return null;
    }

    /** Candidate blocks: rings around the death block, closest first, small dy spread. */
    private List<Block> candidates(Location death, int radius) {
        World world = death.getWorld();
        int bx = death.getBlockX();
        int by = death.getBlockY();
        int bz = death.getBlockZ();
        List<Block> out = new ArrayList<>();
        int[] dys = {0, 1, -1, 2, -2};
        for (int r = 0; r <= radius; r++) {
            for (int dx = -r; dx <= r; dx++) {
                for (int dz = -r; dz <= r; dz++) {
                    // Only the outer ring at this radius, so closer blocks come first.
                    if (Math.max(Math.abs(dx), Math.abs(dz)) != r) {
                        continue;
                    }
                    for (int dy : dys) {
                        int y = by + dy;
                        if (y < world.getMinHeight() || y >= world.getMaxHeight()) {
                            continue;
                        }
                        out.add(world.getBlockAt(bx + dx, y, bz + dz));
                    }
                }
            }
        }
        return out;
    }

    /** A block we may replace with a container. */
    private boolean safe(Block block) {
        if (block == null) {
            return false;
        }
        World world = block.getWorld();
        if (!world.getWorldBorder().isInside(block.getLocation())) {
            return false;
        }
        Material type = block.getType();
        // Never disturb existing containers, spawners, or other player builds; only
        // take genuinely empty/replaceable space, and never liquids.
        if (block.isLiquid()) {
            return false;
        }
        return type.isAir() || block.isReplaceable();
    }

    /** A horizontally-adjacent block that is also safe, for the second chest half. */
    private Block safePartner(Block base) {
        for (BlockFace face : new BlockFace[]{BlockFace.EAST, BlockFace.WEST, BlockFace.SOUTH, BlockFace.NORTH}) {
            Block side = base.getRelative(face);
            if (safe(side)) {
                return side;
            }
        }
        return null;
    }

    private Placed buildSingle(Block block, DeathBoxConfig.Container kind, String boxId, java.util.UUID owner) {
        block.setType(kind == DeathBoxConfig.Container.BARREL ? Material.BARREL : Material.CHEST, false);
        if (!(block.getState() instanceof Container container)) {
            return null;
        }
        tag(container, boxId, owner);
        List<Block> blocks = new ArrayList<>();
        blocks.add(block);
        // Re-read the live state after tagging so we write into the real inventory.
        Container live = (Container) block.getState();
        return new Placed(live.getInventory(), blocks);
    }

    private Placed buildDoubleChest(Block a, Block b, String boxId, java.util.UUID owner) {
        // Facing is perpendicular to the axis joining the two halves so they merge.
        boolean alongX = a.getX() != b.getX();
        BlockFace facing = alongX ? BlockFace.NORTH : BlockFace.EAST;

        if (!formDouble(a, b, facing)) {
            // Restore and give up on this spot.
            a.setType(Material.AIR, false);
            b.setType(Material.AIR, false);
            return null;
        }

        if (!(a.getState() instanceof org.bukkit.block.Chest chestA)
                || !(chestA.getInventory().getHolder() instanceof DoubleChest)) {
            a.setType(Material.AIR, false);
            b.setType(Material.AIR, false);
            return null;
        }

        tag((TileState) a.getState(), boxId, owner);
        tag((TileState) b.getState(), boxId, owner);

        List<Block> blocks = new ArrayList<>();
        blocks.add(a);
        blocks.add(b);
        // The inventory of either half is the shared 54-slot double-chest inventory.
        return new Placed(((org.bukkit.block.Chest) a.getState()).getInventory(), blocks);
    }

    /** Set both halves and confirm they actually merged; flip sides once if not. */
    private boolean formDouble(Block a, Block b, BlockFace facing) {
        setChestHalf(a, facing, org.bukkit.block.data.type.Chest.Type.LEFT);
        setChestHalf(b, facing, org.bukkit.block.data.type.Chest.Type.RIGHT);
        if (isMerged(a)) {
            return true;
        }
        setChestHalf(a, facing, org.bukkit.block.data.type.Chest.Type.RIGHT);
        setChestHalf(b, facing, org.bukkit.block.data.type.Chest.Type.LEFT);
        return isMerged(a);
    }

    private void setChestHalf(Block block, BlockFace facing, org.bukkit.block.data.type.Chest.Type type) {
        block.setType(Material.CHEST, false);
        org.bukkit.block.data.type.Chest data =
                (org.bukkit.block.data.type.Chest) Material.CHEST.createBlockData();
        data.setFacing(facing);
        data.setType(type);
        block.setBlockData(data, false);
    }

    private boolean isMerged(Block block) {
        return block.getState() instanceof org.bukkit.block.Chest chest
                && chest.getInventory().getHolder() instanceof DoubleChest;
    }

    private void tag(TileState state, String boxId, java.util.UUID owner) {
        var pdc = state.getPersistentDataContainer();
        pdc.set(keys.boxId, PersistentDataType.STRING, boxId);
        pdc.set(keys.owner, PersistentDataType.STRING, owner.toString());
        state.update(true, false);
    }

    /** Read the box id tagged on a container block, or null if it is not ours. */
    String boxIdAt(Block block) {
        if (block == null || !(block.getState() instanceof TileState state)) {
            return null;
        }
        return state.getPersistentDataContainer().get(keys.boxId, PersistentDataType.STRING);
    }

    /** Read the owner UUID tagged on a container block, or null. */
    java.util.UUID ownerAt(Block block) {
        if (block == null || !(block.getState() instanceof TileState state)) {
            return null;
        }
        String raw = state.getPersistentDataContainer().get(keys.owner, PersistentDataType.STRING);
        if (raw == null) {
            return null;
        }
        try {
            return java.util.UUID.fromString(raw);
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }

    /** All blocks that make up the box at {@code anchor}: itself plus a merged half. */
    List<Block> siblings(Block anchor, String boxId) {
        List<Block> blocks = new ArrayList<>();
        if (boxId == null || !boxId.equals(boxIdAt(anchor))) {
            return blocks;
        }
        blocks.add(anchor);
        for (BlockFace face : new BlockFace[]{BlockFace.EAST, BlockFace.WEST, BlockFace.SOUTH, BlockFace.NORTH}) {
            Block side = anchor.getRelative(face);
            if (boxId.equals(boxIdAt(side))) {
                blocks.add(side);
                break;
            }
        }
        return blocks;
    }

    /** Write item stacks into a placed inventory, dropping any overflow at loc. */
    static void fill(Inventory inv, List<ItemStack> items, Location loc) {
        List<ItemStack> overflow = new ArrayList<>();
        for (ItemStack item : items) {
            if (item == null || item.getType().isAir()) {
                continue;
            }
            var left = inv.addItem(item);
            overflow.addAll(left.values());
        }
        World world = loc.getWorld();
        if (world != null) {
            for (ItemStack item : overflow) {
                world.dropItemNaturally(loc, item);
            }
        }
    }
}
