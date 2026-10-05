package edu.daa;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Random;
import org.openjdk.jol.info.GraphLayout;
import org.openjdk.jol.vm.VM;

/** Deterministic workloads; construction/query generation stay outside W1-W3 timers. */
public final class Benchmark {
    private static final int[] SIZES = {100, 1_000, 10_000, 100_000};
    private static final int WARMUP_RUNS = 2;
    private static final int MEASURED_RUNS = 5;
    private static final int PREHEAT_CYCLES = 20;
    private static volatile long sink;

    private record Sample(long nanos, long steps, long moves, long comparisons, long checksum) { }

    private Benchmark() { }

    public static void main(String[] args) throws IOException {
        Path results = Path.of("results");
        Files.createDirectories(results);
        writeEnvironment(results);
        preheat();
        try (BufferedWriter csv = Files.newBufferedWriter(results.resolve("results.csv"), StandardCharsets.UTF_8);
             BufferedWriter raw = Files.newBufferedWriter(results.resolve("raw_runs.csv"), StandardCharsets.UTF_8)) {
            csv.write("workload,variant,structure,n,time_ms,steps,moves,comparisons\n");
            raw.write("workload,variant,structure,n,run,time_ms,steps,moves,comparisons,checksum\n");
            for (int n : SIZES) {
                for (int structure = 0; structure < 2; structure++) {
                    measure(csv, raw, "W1", "-", structure, n);
                    measure(csv, raw, "W2", "-", structure, n);
                    measure(csv, raw, "W3", "head", structure, n);
                    measure(csv, raw, "W3", "middle", structure, n);
                }
                measure(csv, raw, "W4", "-", 2, n);
            }
        }
        measureBuildHeap(results);
        measureMemory(results);
        System.out.println("Finished: 36 benchmark cases, 180 measured runs; bonus CSV files written.");
        System.out.println("Consumed checksum: " + sink);
    }

    private static void preheat() {
        // Exercise every kernel before the smallest cases so initial JIT work
        // is less likely to dominate them. These runs are never recorded.
        for (int cycle = 0; cycle < PREHEAT_CYCLES; cycle++) {
            for (int structure = 0; structure < 2; structure++) {
                consume(execute("W1", "-", structure, 1_000));
                consume(execute("W2", "-", structure, 1_000));
                consume(execute("W3", "head", structure, 1_000));
                consume(execute("W3", "middle", structure, 1_000));
            }
            consume(execute("W4", "-", 2, 1_000));
            MinHeap heap = new MinHeap();
            heap.buildHeap(data(1_000, new Random(42)));
            sink ^= heap.peekMin();
        }
        System.out.println("Discarded " + PREHEAT_CYCLES + " global preheat cycles at n=1000.");
    }

    private static void measure(BufferedWriter csv, BufferedWriter raw, String workload,
                                String variant, int structure, int n) throws IOException {
        String name = structure == 0 ? "DynamicArray" : structure == 1 ? "MyLinkedList" : "MinHeap";
        for (int run = 0; run < WARMUP_RUNS; run++) {
            consume(execute(workload, variant, structure, n));
        }
        long[] times = new long[MEASURED_RUNS];
        Sample reference = null;
        for (int run = 0; run < MEASURED_RUNS; run++) {
            Sample sample = execute(workload, variant, structure, n);
            consume(sample);
            if (reference != null && (sample.steps != reference.steps || sample.moves != reference.moves
                    || sample.comparisons != reference.comparisons || sample.checksum != reference.checksum)) {
                throw new IllegalStateException("Non-reproducible counters/results: " + workload + "/" + name);
            }
            reference = sample;
            times[run] = sample.nanos;
            raw.write(workload + "," + variant + "," + name + "," + n + "," + (run + 1) + ","
                    + millis(sample.nanos) + "," + sample.steps + "," + sample.moves + ","
                    + sample.comparisons + "," + sample.checksum + "\n");
        }
        long median = median(times);
        csv.write(workload + "," + variant + "," + name + "," + n + "," + millis(median) + ","
                + reference.steps + "," + reference.moves + "," + reference.comparisons + "\n");
        csv.flush();
        raw.flush();
        System.out.println(workload + "/" + variant + " " + name + " n=" + n + ": " + millis(median) + " ms");
    }

    private static Sample execute(String workload, String variant, int structure, int n) {
        // Each case/run recreates exactly the same data and query stream.
        Random random = new Random(42);
        int[] values = data(n, random);
        if (structure == 2) {
            MinHeap heap = new MinHeap();
            long checksum = 0;
            int previous = Integer.MIN_VALUE;
            boolean sorted = true;
            long start = System.nanoTime();
            for (int value : values) { heap.insert(value); }
            for (int i = 0; i < n; i++) {
                int current = heap.extractMin();
                sorted &= previous <= current;
                previous = current;
                checksum = checksum * 31 + current;
            }
            long elapsed = System.nanoTime() - start;
            if (!sorted || heap.size() != 0) { throw new AssertionError("Heap output is not sorted"); }
            return sample(elapsed, heap.metrics(), checksum);
        }

        IntSequence sequence = structure == 0 ? new DynamicArray() : new MyLinkedList();
        for (int value : values) { sequence.add(value); }
        int[] queries = new int[0];
        int[] inserted = new int[0];
        if (workload.equals("W1")) {
            queries = new int[10_000];
            for (int i = 0; i < queries.length; i++) { queries[i] = random.nextInt(n); }
        } else if (workload.equals("W2")) {
            queries = new int[1_000];
            for (int i = 0; i < 500; i++) {
                queries[i] = values[random.nextInt(n)];
                queries[i + 500] = -1 - random.nextInt(1_000_000);
            }
            for (int i = queries.length - 1; i > 0; i--) {
                int j = random.nextInt(i + 1);
                int temporary = queries[i]; queries[i] = queries[j]; queries[j] = temporary;
            }
        } else {
            inserted = data(1_000, random);
        }
        sequence.metrics().reset();
        long checksum = 0;
        long start = System.nanoTime();
        if (workload.equals("W1")) {
            for (int index : queries) { checksum = checksum * 31 + sequence.get(index); }
        } else if (workload.equals("W2")) {
            for (int value : queries) { if (sequence.contains(value)) { checksum++; } }
        } else {
            // Fixed original n/2; all insertions precede removals, valid even for n=100.
            int index = variant.equals("head") ? 0 : n / 2;
            for (int value : inserted) { sequence.add(index, value); }
            for (int i = 0; i < inserted.length; i++) { checksum = checksum * 31 + sequence.remove(index); }
        }
        long elapsed = System.nanoTime() - start;
        if (sequence.size() != n) { throw new AssertionError("Unexpected final sequence size"); }
        if (workload.equals("W2") && checksum != 500) { throw new AssertionError("Search mix is not 50/50"); }
        return sample(elapsed, sequence.metrics(), checksum);
    }

    private static void measureBuildHeap(Path results) throws IOException {
        try (BufferedWriter csv = Files.newBufferedWriter(results.resolve("build_heap.csv"), StandardCharsets.UTF_8)) {
            csv.write("n,method,time_ms,comparisons\n");
            for (int n : SIZES) {
                int[] values = data(n, new Random(42));
                for (int method = 0; method < 2; method++) {
                    long[] times = new long[MEASURED_RUNS];
                    long comparisons = -1;
                    for (int run = -WARMUP_RUNS; run < MEASURED_RUNS; run++) {
                        MinHeap heap = new MinHeap();
                        long start = System.nanoTime();
                        if (method == 0) { heap.buildHeap(values); }
                        else { for (int value : values) { heap.insert(value); } }
                        long elapsed = System.nanoTime() - start;
                        // Correctness check and result consumption excluded from construction timer.
                        if (!heap.isValidHeap() || heap.size() != n) { throw new AssertionError("Invalid constructed heap"); }
                        sink ^= heap.peekMin();
                        if (run >= 0) {
                            times[run] = elapsed;
                            if (comparisons >= 0 && comparisons != heap.metrics().comparisons()) {
                                throw new AssertionError("Non-reproducible buildHeap counters");
                            }
                            comparisons = heap.metrics().comparisons();
                        }
                    }
                    csv.write(n + "," + (method == 0 ? "Floyd" : "RepeatedInsert") + ","
                            + millis(median(times)) + "," + comparisons + "\n");
                }
            }
        }
    }

    private static void measureMemory(Path results) throws IOException {
        Files.writeString(results.resolve("jol_vm_details.txt"), VM.current().details(), StandardCharsets.UTF_8);
        try (BufferedWriter csv = Files.newBufferedWriter(results.resolve("memory.csv"), StandardCharsets.UTF_8)) {
            csv.write("structure,n,bytes\n");
            for (int n : SIZES) {
                int[] values = data(n, new Random(42));
                DynamicArray array = new DynamicArray();
                MyLinkedList list = new MyLinkedList();
                MinHeap heap = new MinHeap();
                for (int value : values) { array.add(value); list.add(value); heap.insert(value); }
                csv.write("DynamicArray," + n + "," + GraphLayout.parseInstance(array).totalSize() + "\n");
                csv.write("MyLinkedList," + n + "," + GraphLayout.parseInstance(list).totalSize() + "\n");
                csv.write("MinHeap," + n + "," + GraphLayout.parseInstance(heap).totalSize() + "\n");
            }
        }
    }

    private static int[] data(int n, Random random) {
        int[] values = new int[n];
        for (int i = 0; i < n; i++) { values[i] = random.nextInt(1_000_000); }
        return values;
    }

    private static Sample sample(long nanos, Metrics metrics, long checksum) {
        return new Sample(nanos, metrics.steps(), metrics.moves(), metrics.comparisons(), checksum);
    }

    private static void consume(Sample sample) { sink ^= sample.checksum; }
    private static String millis(long nanos) { return Double.toString(nanos / 1_000_000.0); }

    private static long median(long[] times) {
        // Only five primitive values: keep the harness independent of collection utilities.
        for (int i = 1; i < times.length; i++) {
            long value = times[i];
            int j = i - 1;
            while (j >= 0 && times[j] > value) { times[j + 1] = times[j]; j--; }
            times[j + 1] = value;
        }
        return times[times.length / 2];
    }

    private static void writeEnvironment(Path results) throws IOException {
        String text = "java.version=" + System.getProperty("java.version") + "\n"
                + "java.vm.name=" + System.getProperty("java.vm.name") + "\n"
                + "os.name=" + System.getProperty("os.name") + "\n"
                + "os.arch=" + System.getProperty("os.arch") + "\n"
                + "available.processors=" + Runtime.getRuntime().availableProcessors() + "\n"
                + "seed=42\npreheat.cycles=" + PREHEAT_CYCLES + "\npreheat.n=1000\nwarmup.runs="
                + WARMUP_RUNS + "\nmeasured.runs=" + MEASURED_RUNS + "\n"
                + "w3.order=1000 inserts then 1000 removes; middle index uses original n/2\n"
                + "timing=W1-W3 setup excluded; W4 insert/extract and sorted check included\n";
        Files.writeString(results.resolve("environment.properties"), text, StandardCharsets.UTF_8);
    }
}
