package edu.daa;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class MyLinkedListTest extends IntSequenceContractTest {
    @Override
    IntSequence newSequence() {
        return new MyLinkedList();
    }

    @Test
    void getCountsEachNextLinkTraversal() {
        MyLinkedList list = new MyLinkedList();
        for (int i = 0; i < 40; i++) {
            list.add(i);
        }
        for (int index : new int[] {0, 19, 39}) {
            list.metrics().reset();
            assertEquals(index, list.get(index));
            assertEquals(index, list.metrics().steps());
            assertEquals(0, list.metrics().moves());
            assertEquals(0, list.metrics().comparisons());
        }
    }

    @Test
    void headMutationsCountReferenceChanges() {
        MyLinkedList list = new MyLinkedList();
        list.add(10);
        list.add(20);
        list.metrics().reset();
        list.add(0, 5);
        assertEquals(0, list.metrics().steps());
        assertTrue(list.metrics().moves() > 0);
        list.metrics().reset();
        assertEquals(5, list.remove(0));
        assertTrue(list.metrics().moves() > 0);
    }
}
