package edu.daa;

/**
 * Binary min-heap backed by a doubling primitive-int array.
 * Steps count array-cell reads. Moves count writes of existing values during
 * swaps, root replacement, copying, and expansion. The first store of an
 * external insert value is excluded. Comparisons count element comparisons.
 * Diagnostic methods intentionally leave the counters unchanged.
 */
public final class MinHeap {
    private int[] elements = new int[16];
    private int size;
    private final Metrics metrics = new Metrics();

    public void insert(int value) {
        ensureCapacity();
        elements[size] = value; // First placement of an external value.
        size++;
        bubbleUp(size - 1);
    }

    public int peekMin() {
        checkNotEmpty();
        return read(0);
    }

    public int extractMin() {
        checkNotEmpty();
        int minimum = read(0);
        size--;
        if (size > 0) {
            writeMoved(0, read(size));
            bubbleDown(0);
        }
        return minimum;
    }

    /** Replaces this heap using a defensive copy and Floyd's linear build. */
    public void buildHeap(int[] values) {
        if (values == null) {
            throw new NullPointerException("values");
        }
        elements = new int[Math.max(16, values.length)];
        size = values.length;
        for (int i = 0; i < size; i++) {
            metrics.step(); // A read from the caller's input array.
            writeMoved(i, values[i]);
        }
        // All leaves already form heaps. Work upward so each processed node
        // has two valid child heaps before bubbleDown is called.
        for (int i = size / 2 - 1; i >= 0; i--) {
            bubbleDown(i);
        }
    }

    public int size() {
        return size;
    }

    public Metrics metrics() {
        return metrics;
    }

    private void bubbleUp(int index) {
        while (index > 0) {
            int parent = (index - 1) / 2;
            int currentValue = read(index);
            int parentValue = read(parent);
            metrics.compare();
            if (parentValue <= currentValue) {
                return;
            }
            writeMoved(parent, currentValue);
            writeMoved(index, parentValue);
            index = parent;
        }
    }

    private void bubbleDown(int index) {
        // Invariant: the child subtrees of index are heaps. Any remaining
        // violation is between index and its children; the already repaired
        // path above index is ordered. Each swap moves the violation downward.
        while (index < size / 2) {
            int left = 2 * index + 1;
            int right = left + 1;
            int smaller = left;
            int smallerValue = read(left);
            if (right < size) {
                int rightValue = read(right);
                metrics.compare();
                if (rightValue < smallerValue) {
                    smaller = right;
                    smallerValue = rightValue;
                }
            }
            int currentValue = read(index);
            metrics.compare();
            if (currentValue <= smallerValue) {
                return;
            }
            writeMoved(index, smallerValue);
            writeMoved(smaller, currentValue);
            index = smaller;
        }
    }

    private int read(int index) {
        metrics.step();
        return elements[index];
    }

    private void writeMoved(int index, int value) {
        elements[index] = value;
        metrics.move();
    }

    private void ensureCapacity() {
        if (size < elements.length) {
            return;
        }
        int[] expanded = new int[elements.length * 2];
        for (int i = 0; i < size; i++) {
            expanded[i] = read(i);
            metrics.move();
        }
        elements = expanded;
    }

    private void checkNotEmpty() {
        if (size == 0) {
            throw new IllegalStateException("Heap is empty");
        }
    }

    /** Package-private, uninstrumented invariant check for tests. */
    boolean isValidHeap() {
        for (int child = 1; child < size; child++) {
            if (elements[(child - 1) / 2] > elements[child]) {
                return false;
            }
        }
        return true;
    }

    /** Package-private defensive snapshot; diagnostics must not alter metrics. */
    int[] toArray() {
        int[] result = new int[size];
        for (int i = 0; i < size; i++) {
            result[i] = elements[i];
        }
        return result;
    }
}
