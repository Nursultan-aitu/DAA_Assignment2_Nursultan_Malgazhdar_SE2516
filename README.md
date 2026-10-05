# Assignment 2 - Data Structures

**Nursultan Malgazhdar | SE-2516**  
Design and Analysis of Algorithms

Repository: https://github.com/Nursultan-aitu/DAA_Assignment2_Nursultan_Malgazhdar_SE2516  
Release: branch `main`, tag `v1.0`.

## Build, test, and reproduce

Requires a **JDK 17 or newer**, not only a JRE. The recorded run uses Temurin 21 on Windows 11. Maven Wrapper downloads Maven 3.9.9 automatically; the first run needs internet access for Maven and dependencies. Later runs use the local cache.

On Windows, this script finds JDK 17+ under `JAVA_HOME`, `.jdks`, or the compiler's PATH location. It changes Java settings for this process only:

```powershell
.\run.ps1 -Task test       # build + all 47 JUnit 5 tests
.\run.ps1 -Task benchmark  # compile + all workloads + both bonuses
.\run.ps1 -Task all        # build, test, and generate all CSV results
```

If a local PowerShell execution policy blocks the script, use the Maven Wrapper directly after setting `JAVA_HOME` to a JDK:

```powershell
.\mvnw.cmd clean verify
.\mvnw.cmd compile exec:java
.\mvnw.cmd clean verify exec:java
```

On Linux/macOS with `JAVA_HOME` configured:

```sh
./mvnw clean verify
./mvnw compile exec:java
```

Python 3.11 or newer is needed only to regenerate graphs and the PDF, not to compile or run the Java project:

```sh
python -m pip install -r tools/requirements.txt
python tools/validate_results.py
python tools/plot_results.py
python tools/build_report.py
```

The checked-in CSV files, PNGs, and five-page `REPORT.pdf` are actual generated outputs. Re-running benchmarks overwrites CSVs; regenerate plots/report afterwards so all three remain consistent. Exact operation counts are reproducible; elapsed times vary with the computer, JVM, and background work.

## Contents

```text
src/main/java/edu/daa/  IntSequence, Metrics, DynamicArray, MyLinkedList, MinHeap, Benchmark
src/test/java/edu/daa/  JUnit 5 contract, differential, boundary, metric, and heap tests
results/results.csv    Required 36 summarized benchmark cases
results/raw_runs.csv   All 180 measured runs, with checksums
results/build_heap.csv Bonus: Floyd versus repeated insertion
results/memory.csv     Bonus: reachable object sizes measured using JOL
results/plots/         Four workload PNG figures and two bonus PNG figures
results/environment.properties  JVM, OS, seed, and run configuration
results/jol_vm_details.txt       JOL VM layout diagnostics
tools/                 Validation, plotting, and report generation
metadata.json          Report author, group, and date
REPORT.pdf             Analysis, two proofs, plots, discussion, and bonuses
```

## Structures and error handling

All stored values are primitive `int`; arrays use `int[]` and list nodes contain an `int`. No standard collection implements a structure. Standard collections are used only in tests as reference models. The benchmark uses `java.util.Random`, explicitly required by the assignment.

- `DynamicArray`: capacity starts at 16, doubles when full, and does not shrink. Indexed insertion permits `0 <= index <= size`; get/remove require `0 <= index < size`.
- `MyLinkedList`: singly linked nodes, with head and tail references. Append and head edits take constant time; finding an indexed predecessor requires traversal.
- `MinHeap`: doubling array, bubble-up insert, constant-time peek, bubble-down extraction. `buildHeap(int[])` replaces contents with a defensive copy and Floyd's bottom-up construction. It does not mutate the caller's array.
- Invalid indices throw `IndexOutOfBoundsException`; empty peek/extract throw `IllegalStateException`. `remove(index)` returns the removed value. Metrics accumulate until `metrics().reset()`.

## Workload protocol

Each case uses sizes 100, 1,000, 10,000, and 100,000. Every run recreates `new Random(42)`; base values are in `[0, 1_000_000)`. Each sequence therefore receives the same values and query order.

- W1: 10,000 pre-generated random index reads.
- W2: 1,000 shuffled searches; 500 values selected from the input and 500 negative values guaranteed absent. Duplicates are permitted.
- W3: 1,000 insertions followed by 1,000 removals, separately at index 0 and at the **original** `n / 2`. Inserting first makes the case valid even when `n=100`.
- W4: insert all `n` values and extract all of them, checking non-decreasing output.

The JVM first performs **20 discarded preheat cycles of every workload at n=1,000**, including Floyd construction. Each recorded case then has **two discarded warm-ups followed by five measured runs**. The CSV records their median time. Input generation, filling, and query generation are excluded from W1-W3 timers; counters reset after filling. W4 times insertion plus extraction and its inexpensive ordering/checksum checks. Construction-only bonus timers exclude validation. Counters and checksums must agree across all five runs or the benchmark fails. A volatile checksum consumes results outside the sequence timings. There are 36 required cases and 180 raw measurements.

Global preheating and case warm-ups do not eliminate every JIT/GC effect: small-n results must not be read as precise cross-machine speed ratios. Instrumentation adds overhead to the code being measured. The benchmark measures elapsed time and logical counted operations, not CPU cache-miss hardware events.

## Exact counter conventions

The counters are incremented inside the data-structure operations, not estimated by the harness.

| Counter | Array / heap | List |
|---|---|---|
| steps | One actual array-cell read, including copying during growth and reading the input to buildHeap | One `next` reference read/follow, including a successor read for rewiring and the last link to null |
| moves | One write relocating an existing element: shift, resize copy, root replacement, or each of the two writes in a swap | One explicit assignment to `head`, `tail`, or `next` |
| comparisons | One comparison between stored element values | One comparison between a node value and searched value |

The initial placement of a newly supplied array/heap insertion value is not relocation and is not a move. Index checks, loop bounds, local-variable assignments, implicit field initialization, and harness validation are not element comparisons/moves. List node-value reads and head/tail reads are not traversal steps. Diagnostic heap snapshots/invariant checks intentionally do not modify counters. In W3 the list still reports 3,000 moves; no hidden zero-cost link updates are omitted.

## Testing and bonuses

47 JUnit 5 tests cover empty/singleton/duplicate/extreme-int inputs, first/last/invalid indices, growth, tail repair, reuse after emptying, deterministic metrics, and mixed random operations against `ArrayList`/`PriorityQueue`. Heap tests check the parent-child property after every insertion/extraction and non-decreasing output. Build-heap tests cover replacement, defensive copying, and empty input.

Bonus A uses JOL `GraphLayout.parseInstance(structure).totalSize()`: the reachable structure object, metrics object, node objects or allocated backing array are included. The separate benchmark input array, class metadata, and JVM process overhead are excluded. Arrays retain spare capacity. On this VM nodes occupy 24 bytes; compressed references and 8-byte alignment matter. JOL's Serviceability Agent could not attach on this machine, so its diagnostic file warns that addresses are guessed; no result relies on object addresses.

Bonus B compares Floyd construction with repeated insertion on the same random input. Floyd is Theta(n) including the copy. Repeated insertion has an O(n log n) worst-case bound, but random inputs can give near-linear total work; these measurements are not a proof of an n log n growth rate. Array growth can make an individual heap insertion Theta(n), while doubling keeps the aggregate copying cost linear.

## Git and provenance

Feature branches: `feature/array`, `feature/list`, `feature/heap`, and `feature/metrics`. Main integrates the working project and carries the release tag `v1.0`. Commits are attributed to Codex because this project was generated and checked with AI assistance at the student's request; the history does not imply unaided student authorship.

The assignment permits AI only for explaining concepts and debugging. This generated project needs instructor approval for use as a submission, and the student must be able to explain every submitted line. The PDF's stated deadline is 4 October 2026 at 23:59; the report records the actual preparation date, 5 October 2026.

## References

- Course brief: `DAA_Assignment2_Data_Structures.pdf` (provided separately).
- [Apache Maven Wrapper](https://maven.apache.org/tools/wrapper/) - reproducible Maven bootstrap.
- [OpenJDK JOL](https://github.com/openjdk/jol) - object-layout and reachable-footprint measurement.
- [JOL HotspotUnsafe implementation](https://github.com/openjdk/jol/blob/master/jol-core/src/main/java/org/openjdk/jol/vm/HotspotUnsafe.java) - size measurement and diagnostic address limitations.
