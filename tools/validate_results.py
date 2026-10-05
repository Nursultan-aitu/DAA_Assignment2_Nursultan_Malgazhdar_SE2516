"""Validate the benchmark matrix, raw medians, counters, and cross-structure results."""
import csv
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]


def rows(name):
    with (ROOT / "results" / name).open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def key(row):
    return row["workload"], row["variant"], row["structure"], int(row["n"])


def main():
    summary = rows("results.csv")
    raw = rows("raw_runs.csv")
    expected = set()
    for n in (100, 1000, 10000, 100000):
        for structure in ("DynamicArray", "MyLinkedList"):
            for workload, variant in (("W1", "-"), ("W2", "-"), ("W3", "head"), ("W3", "middle")):
                expected.add((workload, variant, structure, n))
        expected.add(("W4", "-", "MinHeap", n))
    assert len(summary) == 36 and {key(row) for row in summary} == expected
    assert len(raw) == 180 and {key(row) for row in raw} == expected
    for row in summary:
        samples = [sample for sample in raw if key(sample) == key(row)]
        assert len(samples) == 5 and {int(s["run"]) for s in samples} == set(range(1, 6))
        assert float(row["time_ms"]) == median(float(s["time_ms"]) for s in samples)
        assert float(row["time_ms"]) > 0
        for counter in ("steps", "moves", "comparisons"):
            assert int(row[counter]) >= 0
            assert {s[counter] for s in samples} == {row[counter]}
        assert len({s["checksum"] for s in samples}) == 1
        if row["structure"] == "DynamicArray":
            if row["workload"] == "W1":
                assert (int(row["steps"]), int(row["moves"]), int(row["comparisons"])) == (10000, 0, 0)
            elif row["workload"] == "W2":
                assert row["steps"] == row["comparisons"] and int(row["moves"]) == 0
            elif row["workload"] == "W3":
                assert int(row["steps"]) == int(row["moves"]) + 1000
        elif row["structure"] == "MyLinkedList":
            if row["workload"] == "W2":
                assert int(row["steps"]) == int(row["comparisons"]) - 500
            elif row["workload"] == "W3":
                assert int(row["moves"]) == 3000 and int(row["comparisons"]) == 0
                expected_steps = 1000 if row["variant"] == "head" else int(row["n"]) * 1000 + 1000
                assert int(row["steps"]) == expected_steps
    for n in (100, 1000, 10000, 100000):
        for workload, variant in (("W1", "-"), ("W2", "-"), ("W3", "head"), ("W3", "middle")):
            matching = [r for r in raw if r["workload"] == workload and r["variant"] == variant and int(r["n"]) == n]
            assert len({r["checksum"] for r in matching}) == 1, "Sequence outputs differ"
        search = [r for r in summary if r["workload"] == "W2" and int(r["n"]) == n]
        assert search[0]["comparisons"] == search[1]["comparisons"]
    assert len(rows("build_heap.csv")) == 8
    assert len(rows("memory.csv")) == 12
    print("PASS: 36 cases, 180 raw runs, medians, counter identities, matching outputs, and bonus CSVs.")


if __name__ == "__main__":
    main()
