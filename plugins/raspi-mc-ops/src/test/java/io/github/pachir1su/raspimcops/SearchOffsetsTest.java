package io.github.pachir1su.raspimcops;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class SearchOffsetsTest {
    @Test
    void startsAtDeathBlockAndStaysBounded() {
        var offsets = SearchOffsets.around(2);
        assertEquals(new SearchOffsets.Offset(0, 0, 0), offsets.getFirst());
        assertTrue(offsets.stream().allMatch(value -> Math.abs(value.x()) <= 2));
        assertTrue(offsets.stream().allMatch(value -> Math.abs(value.z()) <= 2));
        assertTrue(offsets.stream().allMatch(value -> Math.abs(value.y()) <= 2));
    }

    @Test
    void rejectsExpensiveSearches() {
        assertThrows(IllegalArgumentException.class, () -> SearchOffsets.around(17));
    }
}
