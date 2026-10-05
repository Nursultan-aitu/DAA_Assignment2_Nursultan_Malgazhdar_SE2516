package edu.daa;

/**
 * A primitive-int array that doubles its capacity when full and never shrinks.
 * A step is one array-cell read; a move is one write relocating an existing
 * element. The initial store of a newly supplied value is not a move.
 * Only comparisons between element values contribute to comparisons.
 */
public final class DynamicArray implements IntSequence {
    private int[] elements = new int[16];
    private int size;
    private final Metrics metrics = new Metrics();

    @Override
    public void add(int value) {
        add(size, value);
    }

    @Override
    public void add(int index, int value) {
        checkInsertionIndex(index);
        ensureCapacity();
        // Moving backward preserves every element that has not yet been read.
        for (int i = size; i > index; i--) {
            writeMoved(i, read(i - 1));
        }
        elements[index] = value; // First placement of an external value.
        size++;
    }

    @Override
    public int remove(int index) {
        checkElementIndex(index);
        int removed = read(index);
        for (int i = index; i < size - 1; i++) {
            writeMoved(i, read(i + 1));
        }
        size--;
        // The unused int cell needs no clearing and capacity is retained.
        return removed;
    }

    @Override
    public int get(int index) {
        checkElementIndex(index);
        return read(index);
    }

    @Override
    public boolean contains(int value) {
        // Invariant: every position in [0, i) has been checked and differs
        // from value. If the loop finishes, this covers all live elements.
        for (int i = 0; i < size; i++) {
            int current = read(i);
            metrics.compare();
            if (current == value) {
                return true;
            }
        }
        return false;
    }

    @Override
    public int size() {
        return size;
    }

    @Override
    public Metrics metrics() {
        return metrics;
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

    private void checkElementIndex(int index) {
        if (index < 0 || index >= size) {
            throw new IndexOutOfBoundsException("index=" + index + ", size=" + size);
        }
    }

    private void checkInsertionIndex(int index) {
        if (index < 0 || index > size) {
            throw new IndexOutOfBoundsException("index=" + index + ", size=" + size);
        }
    }
}
