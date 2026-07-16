package io.github.pachir1su.raspimcops;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

class EnchantServiceTest {

    @Test
    void clampsLevelIntoDataRange() {
        assertEquals(1, EnchantService.parseLevel("1"));
        assertEquals(20, EnchantService.parseLevel("20"));
        assertEquals(1, EnchantService.parseLevel("0"));
        assertEquals(1, EnchantService.parseLevel("-5"));
        assertEquals(EnchantService.MAX_LEVEL, EnchantService.parseLevel("9999"));
    }

    @Test
    void rejectsNonNumericLevel() {
        assertThrows(IllegalArgumentException.class, () -> EnchantService.parseLevel("five"));
    }

    @Test
    void normalizesEnchantIds() {
        assertEquals("sharpness", EnchantService.normalizeEnchantId("Sharpness"));
        assertEquals("sharpness", EnchantService.normalizeEnchantId("minecraft:sharpness"));
        assertEquals("silk_touch", EnchantService.normalizeEnchantId("  SILK_TOUCH  "));
    }

    @Test
    void rejectsUnsafeEnchantIds() {
        assertThrows(IllegalArgumentException.class,
            () -> EnchantService.normalizeEnchantId("sharpness; op me"));
        assertThrows(IllegalArgumentException.class,
            () -> EnchantService.normalizeEnchantId(""));
    }
}
