package edu.daa;

/** Shared primitive-int API used by the same benchmark for both sequences. */
public interface IntSequence {
    void add(int value);
    void add(int index, int value);
    int remove(int index);
    int get(int index);
    boolean contains(int value);
    int size();
    Metrics metrics();
}
