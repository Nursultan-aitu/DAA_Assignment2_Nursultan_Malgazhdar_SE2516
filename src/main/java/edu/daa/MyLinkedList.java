package edu.daa;

/**
 * Singly linked primitive-int list with a tail pointer for constant-time append.
 * A step is one next-reference read, including a successor read for rewiring
 * or following the last link to null. Node value/head/tail reads are not steps.
 * Every explicit assignment to next, head, or tail is one move; assignments
 * to local variables and the implicit null initialization of nodes are excluded.
 */
public final class MyLinkedList implements IntSequence {
    private static final class Node {
        private final int value;
        private Node next;

        private Node(int value) {
            this.value = value;
        }
    }

    private Node head;
    private Node tail;
    private int size;
    private final Metrics metrics = new Metrics();

    @Override
    public void add(int value) {
        Node node = new Node(value);
        if (size == 0) {
            head = node;
            metrics.move();
        } else {
            tail.next = node;
            metrics.move();
        }
        tail = node;
        metrics.move();
        size++;
    }

    @Override
    public void add(int index, int value) {
        checkInsertionIndex(index);
        if (index == size) {
            add(value);
            return;
        }
        Node node = new Node(value);
        if (index == 0) {
            node.next = head;
            metrics.move();
            head = node;
            metrics.move();
        } else {
            Node previous = nodeAt(index - 1);
            node.next = next(previous);
            metrics.move();
            previous.next = node;
            metrics.move();
        }
        size++;
    }

    @Override
    public int remove(int index) {
        checkElementIndex(index);
        Node removed;
        if (index == 0) {
            removed = head;
            head = next(removed);
            metrics.move();
            if (size == 1) {
                tail = null;
                metrics.move();
            }
        } else {
            Node previous = nodeAt(index - 1);
            removed = next(previous);
            previous.next = next(removed);
            metrics.move();
            if (index == size - 1) {
                tail = previous;
                metrics.move();
            }
        }
        size--;
        return removed.value;
    }

    @Override
    public int get(int index) {
        checkElementIndex(index);
        return nodeAt(index).value;
    }

    @Override
    public boolean contains(int value) {
        Node current = head;
        while (current != null) {
            metrics.compare();
            if (current.value == value) {
                return true;
            }
            current = next(current);
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

    private Node next(Node node) {
        metrics.step();
        return node.next;
    }

    private Node nodeAt(int index) {
        Node current = head;
        for (int i = 0; i < index; i++) {
            current = next(current);
        }
        return current;
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
