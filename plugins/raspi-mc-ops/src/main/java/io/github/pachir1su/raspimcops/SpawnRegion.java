package io.github.pachir1su.raspimcops;

/** Pure spawn-radius geometry kept independent from the Paper runtime. */
public record SpawnRegion(int centerX, int centerZ, int radius) {
    public SpawnRegion {
        if (radius < 0 || radius > 1024) {
            throw new IllegalArgumentException("radius must be between 0 and 1024");
        }
    }

    /** Match Minecraft's square spawn-protection footprint. */
    public boolean contains(int blockX, int blockZ) {
        return Math.max(Math.abs(blockX - centerX), Math.abs(blockZ - centerZ)) <= radius;
    }
}
