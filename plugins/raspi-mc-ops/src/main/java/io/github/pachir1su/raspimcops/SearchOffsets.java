package io.github.pachir1su.raspimcops;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** Produce a deterministic, bounded Death Box search order. */
public final class SearchOffsets {
    private SearchOffsets() {}

    public record Offset(int x, int y, int z) {}

    /** Search nearby horizontal blocks first and never scan outside the configured cube. */
    public static List<Offset> around(int radius) {
        if (radius < 0 || radius > 16) {
            throw new IllegalArgumentException("search radius must be between 0 and 16");
        }
        List<Offset> offsets = new ArrayList<>();
        int[] verticalOffsets = {0, 1, -1, 2, -2};
        for (int y : verticalOffsets) {
            for (int x = -radius; x <= radius; x++) {
                for (int z = -radius; z <= radius; z++) {
                    offsets.add(new Offset(x, y, z));
                }
            }
        }
        offsets.sort(
            Comparator.comparingInt((Offset value) -> Math.abs(value.y()))
                .thenComparingInt(value -> Math.max(Math.abs(value.x()), Math.abs(value.z())))
                .thenComparingInt(value -> Math.abs(value.x()) + Math.abs(value.z()))
        );
        return List.copyOf(offsets);
    }
}
