package edu.daa;

import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

/** The same observable contract must hold for both implementations. */
abstract class IntSequenceContractTest {
    abstract IntSequence newSequence();

    @Test
    void emptySequenceHasNoElements() {
        IntSequence sequence = newSequence();
        assertEquals(0, sequence.size());
        assertFalse(sequence.contains(0));
        assertFalse(sequence.contains(Integer.MIN_VALUE));
        assertThrows(IndexOutOfBoundsException.class, () -> sequence.get(0));
        assertThrows(IndexOutOfBoundsException.class, () -> sequence.remove(0));
    }

    @Test
    void singleElementCanBeReadAndRemoved() {
        IntSequence sequence = newSequence();
        sequence.add(71);
        assertEquals(1, sequence.size());
        assertEquals(71, sequence.get(0));
        assertTrue(sequence.contains(71));
        assertEquals(71, sequence.remove(0));
        assertEquals(0, sequence.size());
        assertFalse(sequence.contains(71));
    }

    @Test
    void appendPreservesOrderAcrossRepeatedGrowth() {
        IntSequence sequence = newSequence();
        for (int i = 0; i < 1025; i++) {
            sequence.add(i * 3 - 900);
        }
        assertEquals(1025, sequence.size());
        for (int i = 0; i < sequence.size(); i++) {
            assertEquals(i * 3 - 900, sequence.get(i), "index " + i);
        }
    }

    @Test
    void indexedInsertionAcceptsHeadMiddleAndSize() {
        IntSequence sequence = newSequence();
        sequence.add(0, 20);
        sequence.add(0, 10);
        sequence.add(sequence.size(), 40);
        sequence.add(2, 30);
        assertContents(sequence, List.of(10, 20, 30, 40));
    }

    @Test
    void removalReturnsCorrectValueAndClosesGap() {
        IntSequence sequence = newSequence();
        for (int value : new int[] {10, 20, 30, 40, 50}) {
            sequence.add(value);
        }
        assertEquals(10, sequence.remove(0));
        assertContents(sequence, List.of(20, 30, 40, 50));
        assertEquals(40, sequence.remove(2));
        assertContents(sequence, List.of(20, 30, 50));
        assertEquals(50, sequence.remove(sequence.size() - 1));
        assertContents(sequence, List.of(20, 30));
    }

    @Test
    void allIntValuesAndDuplicatesAreSupported() {
        IntSequence sequence = newSequence();
        List<Integer> values = List.of(Integer.MIN_VALUE, 0, -1, Integer.MAX_VALUE, 0,
                Integer.MIN_VALUE, Integer.MAX_VALUE);
        values.forEach(sequence::add);
        assertContents(sequence, values);
        assertTrue(sequence.contains(Integer.MIN_VALUE));
        assertTrue(sequence.contains(Integer.MAX_VALUE));
        assertTrue(sequence.contains(0));
        assertFalse(sequence.contains(123));
        assertEquals(0, sequence.remove(1));
        assertTrue(sequence.contains(0), "the second zero must remain");
        assertEquals(0, sequence.remove(3));
        assertFalse(sequence.contains(0));
    }

    @Test
    void invalidReadAndRemovalIndexesDoNotModifySequence() {
        IntSequence sequence = newSequence();
        sequence.add(4);
        sequence.add(8);
        for (int index : new int[] {-1, 2, 3, Integer.MIN_VALUE, Integer.MAX_VALUE}) {
            assertThrows(IndexOutOfBoundsException.class, () -> sequence.get(index));
            assertThrows(IndexOutOfBoundsException.class, () -> sequence.remove(index));
            assertContents(sequence, List.of(4, 8));
        }
    }

    @Test
    void invalidInsertionIndexesDoNotModifySequence() {
        IntSequence sequence = newSequence();
        for (int index : new int[] {-1, 1, Integer.MIN_VALUE, Integer.MAX_VALUE}) {
            assertThrows(IndexOutOfBoundsException.class, () -> sequence.add(index, 99));
            assertEquals(0, sequence.size());
        }
        sequence.add(4);
        sequence.add(8);
        for (int index : new int[] {-1, 3, Integer.MIN_VALUE, Integer.MAX_VALUE}) {
            assertThrows(IndexOutOfBoundsException.class, () -> sequence.add(index, 99));
            assertContents(sequence, List.of(4, 8));
        }
    }

    @Test
    void sequenceCanBeReusedAfterRemovingAllElements() {
        IntSequence sequence = newSequence();
        for (int round = 0; round < 5; round++) {
            for (int i = 0; i < 40; i++) {
                sequence.add(i);
            }
            for (int i = 39; i >= 0; i--) {
                assertEquals(i, sequence.remove(sequence.size() - 1));
            }
            assertEquals(0, sequence.size());
            sequence.add(0, -round);
            assertEquals(-round, sequence.remove(0));
        }
    }

    @Test
    void removingTailThenAppendingKeepsLinksAndOrderValid() {
        IntSequence sequence = newSequence();
        sequence.add(1);
        sequence.add(2);
        sequence.add(3);
        assertEquals(3, sequence.remove(2));
        sequence.add(4);
        assertContents(sequence, List.of(1, 2, 4));
        assertEquals(1, sequence.remove(0));
        assertEquals(2, sequence.remove(0));
        assertEquals(4, sequence.remove(0));
        sequence.add(5);
        assertContents(sequence, List.of(5));
    }

    @Test
    void randomMixedOperationsMatchArrayList() {
        for (long seed : new long[] {42, 12345, 987654321}) {
            Random random = new Random(seed);
            IntSequence actual = newSequence();
            List<Integer> expected = new ArrayList<>();
            for (int operation = 0; operation < 2500; operation++) {
                int value = random.nextInt(101) - 50;
                switch (random.nextInt(5)) {
                    case 0 -> {
                        expected.add(value);
                        actual.add(value);
                    }
                    case 1 -> {
                        int index = random.nextInt(expected.size() + 1);
                        expected.add(index, value);
                        actual.add(index, value);
                    }
                    case 2 -> {
                        if (!expected.isEmpty()) {
                            int index = random.nextInt(expected.size());
                            assertEquals(expected.remove(index).intValue(), actual.remove(index));
                        }
                    }
                    case 3 -> {
                        if (!expected.isEmpty()) {
                            int index = random.nextInt(expected.size());
                            assertEquals(expected.get(index).intValue(), actual.get(index));
                        }
                    }
                    default -> assertEquals(expected.contains(value), actual.contains(value));
                }
                assertEquals(expected.size(), actual.size(), "seed " + seed + ", op " + operation);
                // Check full order regularly without making list traversal dominate the test.
                if (operation % 37 == 0) {
                    assertContents(actual, expected);
                }
            }
            assertContents(actual, expected);
        }
    }

    @Test
    void containsCountsOnlyVisitedElementComparisons() {
        IntSequence sequence = newSequence();
        sequence.add(5);
        sequence.add(7);
        sequence.add(7);
        sequence.add(9);
        sequence.metrics().reset();
        assertTrue(sequence.contains(5));
        assertEquals(1, sequence.metrics().comparisons());
        sequence.metrics().reset();
        assertTrue(sequence.contains(7));
        assertEquals(2, sequence.metrics().comparisons());
        sequence.metrics().reset();
        assertTrue(sequence.contains(9));
        assertEquals(4, sequence.metrics().comparisons());
        sequence.metrics().reset();
        assertFalse(sequence.contains(100));
        assertEquals(4, sequence.metrics().comparisons());
        assertEquals(0, sequence.metrics().moves(), "contains is read-only");
    }

    @Test
    void emptySearchDoesNotCompareValues() {
        IntSequence sequence = newSequence();
        assertFalse(sequence.contains(5));
        assertEquals(0, sequence.metrics().comparisons());
        assertEquals(0, sequence.metrics().moves());
    }

    @Test
    void metricsResetPreservesContents() {
        IntSequence sequence = newSequence();
        sequence.add(11);
        sequence.add(22);
        sequence.add(0, 33);
        sequence.contains(22);
        assertTrue(sequence.metrics().moves() > 0, "mutations must count writes or link changes");
        assertTrue(sequence.metrics().comparisons() > 0);
        sequence.metrics().reset();
        assertEquals(0, sequence.metrics().steps());
        assertEquals(0, sequence.metrics().moves());
        assertEquals(0, sequence.metrics().comparisons());
        assertContents(sequence, List.of(33, 11, 22));
    }

    @Test
    void instancesDoNotShareStorageOrCounters() {
        IntSequence first = newSequence();
        IntSequence second = newSequence();
        first.add(17);
        first.contains(17);
        assertEquals(0, second.size());
        assertEquals(0, second.metrics().steps());
        assertEquals(0, second.metrics().moves());
        assertEquals(0, second.metrics().comparisons());
        second.add(23);
        assertContents(first, List.of(17));
        assertContents(second, List.of(23));
    }

    private static void assertContents(IntSequence actual, List<Integer> expected) {
        assertEquals(expected.size(), actual.size());
        for (int i = 0; i < expected.size(); i++) {
            assertEquals(expected.get(i).intValue(), actual.get(i), "index " + i);
        }
    }
}
