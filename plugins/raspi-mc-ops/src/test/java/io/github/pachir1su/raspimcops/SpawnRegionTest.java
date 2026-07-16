package io.github.pachir1su.raspimcops;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class SpawnRegionTest {
    @Test
    void usesSquareMinecraftStyleBoundary() {
        SpawnRegion region = new SpawnRegion(10, -5, 16);
        assertTrue(region.contains(26, 11));
        assertFalse(region.contains(27, -5));
    }

    @Test
    void rejectsUnboundedRadius() {
        assertThrows(IllegalArgumentException.class, () -> new SpawnRegion(0, 0, -1));
        assertThrows(IllegalArgumentException.class, () -> new SpawnRegion(0, 0, 1025));
    }
}
