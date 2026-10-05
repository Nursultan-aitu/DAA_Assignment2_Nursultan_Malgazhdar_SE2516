package edu.daa;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class DynamicArrayTest extends IntSequenceContractTest {
    @Override
    IntSequence newSequence() {
        return new DynamicArray();
    }

    @Test
    void getUsesOneArrayReadAtEveryIndex() {
        DynamicArray array = new DynamicArray();
        for (int i = 0; i < 40; i++) {
            array.add(i);
        }
        for (int index : new int[] {0, 19, 39}) {
            array.metrics().reset();
            assertEquals(index, array.get(index));
            assertEquals(1, array.metrics().steps());
            assertEquals(0, array.metrics().moves());
            assertEquals(0, array.metrics().comparisons());
        }
    }

    @Test
    void insertingAtHeadRecordsElementMoves() {
        DynamicArray array = new DynamicArray();
        array.add(10);
        array.add(20);
        array.add(30);
        array.metrics().reset();
        array.add(0, 5);
        assertTrue(array.metrics().moves() >= 3, "the three existing values must move");
        assertEquals(5, array.get(0));
        assertEquals(30, array.get(3));
    }
}
