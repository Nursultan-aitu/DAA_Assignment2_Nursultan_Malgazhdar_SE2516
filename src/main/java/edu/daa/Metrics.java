package edu.daa;

/** Counts physical operations, never loop-control or index comparisons. */
public final class Metrics {
    private long steps;
    private long moves;
    private long comparisons;

    public void step() { steps++; }
    public void move() { moves++; }
    public void compare() { comparisons++; }
    public long steps() { return steps; }
    public long moves() { return moves; }
    public long comparisons() { return comparisons; }
    public void reset() { steps = moves = comparisons = 0; }
}
