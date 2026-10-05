package edu.daa;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Arrays;
import java.util.PriorityQueue;
import java.util.Random;
import org.junit.jupiter.api.Test;

class MinHeapTest {
    @Test
    void emptyHeapRejectsPeekAndExtraction() {
        MinHeap heap = new MinHeap();
        assertEquals(0, heap.size());
        assertTrue(heap.isValidHeap());
        assertThrows(IllegalStateException.class, heap::peekMin);
        assertThrows(IllegalStateException.class, heap::extractMin);
        assertEquals(0, heap.size());
    }

    @Test
    void singleElementPeekIsNonDestructive() {
        MinHeap heap = new MinHeap();
        heap.insert(37);
        assertTrue(heap.isValidHeap());
        assertEquals(37, heap.peekMin());
        assertEquals(37, heap.peekMin());
        assertEquals(1, heap.size());
        assertEquals(37, heap.extractMin());
        assertTrue(heap.isValidHeap());
        assertEquals(0, heap.size());
        assertThrows(IllegalStateException.class, heap::extractMin);
    }

    @Test
    void descendingInsertionsMaintainHeapInvariantAndSortOnExtraction() {
        MinHeap heap = new MinHeap();
        for (int i = 300; i >= -300; i--) {
            heap.insert(i);
            assertTrue(heap.isValidHeap(), "after insertion of " + i);
            assertEquals(i, heap.peekMin());
        }
        for (int i = -300; i <= 300; i++) {
            assertEquals(i, heap.extractMin());
            assertTrue(heap.isValidHeap(), "after extraction of " + i);
        }
        assertEquals(0, heap.size());
    }

    @Test
    void ascendingInsertionsAndOddSizesKeepHeapValid() {
        MinHeap heap = new MinHeap();
        for (int i = 0; i < 129; i++) {
            heap.insert(i);
            assertTrue(heap.isValidHeap());
        }
        for (int i = 0; i < 129; i++) {
            assertEquals(i, heap.extractMin());
            assertTrue(heap.isValidHeap());
        }
    }

    @Test
    void duplicatesAndExtremeIntsDoNotOverflowComparisons() {
        int[] values = {Integer.MAX_VALUE, Integer.MIN_VALUE, 0, -1, 0,
                Integer.MAX_VALUE, Integer.MIN_VALUE, 1};
        assertInsertionAndExtraction(values);
    }

    @Test
    void equalValuesPreserveEveryOccurrence() {
        int[] values = new int[80];
        Arrays.fill(values, 7);
        assertInsertionAndExtraction(values);
    }

    @Test
    void randomMixedOperationsMatchPriorityQueue() {
        for (long seed : new long[] {42, 2026, 99117}) {
            MinHeap actual = new MinHeap();
            PriorityQueue<Integer> expected = new PriorityQueue<>();
            Random random = new Random(seed);
            for (int operation = 0; operation < 3000; operation++) {
                if (expected.isEmpty() || random.nextInt(100) < 55) {
                    int value = random.nextInt();
                    expected.add(value);
                    actual.insert(value);
                } else {
                    assertEquals(expected.remove().intValue(), actual.extractMin());
                }
                assertEquals(expected.size(), actual.size());
                assertTrue(actual.isValidHeap(), "seed " + seed + ", op " + operation);
                if (!expected.isEmpty()) {
                    assertEquals(expected.element().intValue(), actual.peekMin());
                }
            }
            while (!expected.isEmpty()) {
                assertEquals(expected.remove().intValue(), actual.extractMin());
                assertTrue(actual.isValidHeap());
            }
            assertEquals(0, actual.size());
        }
    }

    @Test
    void heapCanBeReusedAfterDraining() {
        MinHeap heap = new MinHeap();
        for (int round = 0; round < 8; round++) {
            heap.insert(9);
            heap.insert(-3);
            assertTrue(heap.isValidHeap());
            assertEquals(-3, heap.extractMin());
            assertTrue(heap.isValidHeap());
            assertEquals(9, heap.extractMin());
            assertTrue(heap.isValidHeap());
            assertEquals(0, heap.size());
        }
    }

    @Test
    void heapMetricsCanBeResetWithoutChangingValues() {
        MinHeap heap = new MinHeap();
        heap.insert(30);
        heap.insert(20);
        heap.insert(10);
        assertTrue(heap.metrics().steps() > 0);
        assertTrue(heap.metrics().moves() > 0);
        assertTrue(heap.metrics().comparisons() > 0);
        heap.metrics().reset();
        assertEquals(0, heap.metrics().steps());
        assertEquals(0, heap.metrics().moves());
        assertEquals(0, heap.metrics().comparisons());
        assertEquals(10, heap.extractMin());
        assertEquals(20, heap.extractMin());
        assertEquals(30, heap.extractMin());
    }

    @Test
    void heapDiagnosticsAreReadOnlyAndDoNotChangeMetrics() {
        MinHeap heap = new MinHeap();
        heap.insert(7);
        heap.insert(2);
        heap.insert(9);
        heap.metrics().reset();
        assertTrue(heap.isValidHeap());
        int[] snapshot = heap.toArray();
        assertEquals(heap.size(), snapshot.length);
        snapshot[0] = Integer.MIN_VALUE;
        assertTrue(heap.isValidHeap());
        assertEquals(0, heap.metrics().steps());
        assertEquals(0, heap.metrics().moves());
        assertEquals(0, heap.metrics().comparisons());
        assertEquals(2, heap.peekMin());
    }

    @Test
    void buildHeapUsesDefensiveCopyAndReturnsAllValuesInOrder() {
        MinHeap heap = new MinHeap();
        int[] values = {14, 5, 6, 3, 19, 0, -7, Integer.MAX_VALUE, Integer.MIN_VALUE, 5};
        int[] expected = values.clone();
        heap.buildHeap(values);
        assertArrayEquals(expected, values, "building must not rearrange the caller's array");
        assertEquals(values.length, heap.size());
        assertTrue(heap.isValidHeap());
        Arrays.fill(values, 99);
        Arrays.sort(expected);
        for (int value : expected) {
            assertEquals(value, heap.extractMin());
            assertTrue(heap.isValidHeap());
        }
    }

    @Test
    void buildHeapHandlesEmptySingletonAndReplacement() {
        MinHeap heap = new MinHeap();
        heap.buildHeap(new int[0]);
        assertEquals(0, heap.size());
        assertTrue(heap.isValidHeap());
        heap.insert(99);
        heap.buildHeap(new int[] {4});
        assertEquals(1, heap.size());
        assertEquals(4, heap.peekMin());
        assertTrue(heap.isValidHeap());
        heap.buildHeap(new int[] {8, 2, 6});
        assertEquals(3, heap.size());
        assertTrue(heap.isValidHeap());
        assertEquals(2, heap.extractMin());
        assertEquals(6, heap.extractMin());
        assertEquals(8, heap.extractMin());
        heap.insert(17);
        heap.buildHeap(new int[0]);
        assertEquals(0, heap.size());
        assertTrue(heap.isValidHeap());
        assertThrows(IllegalStateException.class, heap::peekMin);
        heap.insert(-11);
        assertEquals(-11, heap.extractMin());
    }

    @Test
    void randomBuildHeapMatchesSortedInputForBoundarySizes() {
        Random random = new Random(42);
        for (int size : new int[] {0, 1, 2, 3, 15, 16, 17, 31, 32, 33, 1000}) {
            int[] input = new int[size];
            for (int i = 0; i < size; i++) {
                input[i] = random.nextInt(2001) - 1000;
            }
            MinHeap heap = new MinHeap();
            heap.buildHeap(input);
            assertTrue(heap.isValidHeap(), "build size " + size);
            Arrays.sort(input);
            for (int value : input) {
                assertEquals(value, heap.extractMin());
                assertTrue(heap.isValidHeap());
            }
            assertEquals(0, heap.size());
        }
    }

    private static void assertInsertionAndExtraction(int[] values) {
        MinHeap heap = new MinHeap();
        for (int value : values) {
            heap.insert(value);
            assertTrue(heap.isValidHeap());
        }
        int[] expected = values.clone();
        Arrays.sort(expected);
        for (int value : expected) {
            assertEquals(value, heap.extractMin());
            assertTrue(heap.isValidHeap());
        }
        assertEquals(0, heap.size());
    }
}
