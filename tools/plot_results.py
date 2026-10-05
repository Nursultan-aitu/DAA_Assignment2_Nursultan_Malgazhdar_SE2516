#!/usr/bin/env python3
"""Create the assignment's PNG figures from measured CSV files.

Usage: python tools/plot_results.py
Requires matplotlib and pandas; no data or timings are synthesized.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator, ScalarFormatter
import pandas as pd

COLORS = {"DynamicArray": "#4C72B0", "MyLinkedList": "#DD8452", "MinHeap": "#55A868"}
COUNTER_COLORS = {"steps": "#4C72B0", "moves": "#DD8452", "comparisons": "#55A868"}
SHORT_NAMES = {"DynamicArray": "Array", "MyLinkedList": "List", "MinHeap": "Heap"}
COUNTERS = ["steps", "moves", "comparisons"]
SIZES = [100, 1000, 10000, 100000]


def read_results(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, keep_default_na=False)
    required = {"workload", "variant", "structure", "n", "time_ms", "steps", "moves", "comparisons"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing CSV columns: {required - set(frame.columns)}")
    expected = set()
    for n in SIZES:
        for workload in ["W1", "W2", "W3"]:
            for variant in (["head", "middle"] if workload == "W3" else ["-"]):
                for structure in ["DynamicArray", "MyLinkedList"]:
                    expected.add((workload, variant, structure, n))
        expected.add(("W4", "-", "MinHeap", n))
    actual = list(frame[["workload", "variant", "structure", "n"]].itertuples(index=False, name=None))
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError(f"Expected exactly 36 unique cases. Missing: {expected - set(actual)}; extra: {set(actual) - expected}")
    if (frame[["time_ms", "steps", "moves", "comparisons"]] < 0).any().any():
        raise ValueError("Times and counters must be non-negative")
    return frame


def series(part: pd.DataFrame, column: str, label: str, color: str,
           linestyle: str = "-", marker: str = "o", divisor: float = 1.0) -> dict:
    """Keep exactly the four measured samples; divisor is used only for bytes to MB."""
    ordered = part.sort_values("n")
    return {"x": ordered.n.to_list(), "y": (ordered[column] / divisor).to_list(),
            "label": label, "color": color, "linestyle": linestyle, "marker": marker}


def time_series(rows: pd.DataFrame, compact: bool = False) -> list[dict]:
    lines = []
    variants = ["head", "middle"] if (rows.workload == "W3").all() else ["-"]
    for structure in rows.structure.unique():
        name = SHORT_NAMES[structure] if compact else structure
        for variant in variants:
            part = rows[(rows.structure == structure) & (rows.variant == variant)]
            label = name if variant == "-" else f"{name} {variant}"
            dash = "--" if variant == "middle" or (variant == "-" and structure == "MyLinkedList") else "-"
            marker = "s" if dash == "--" else "o"
            lines.append(series(part, "time_ms", label, COLORS[structure], dash, marker))
    return lines


def operation_series(rows: pd.DataFrame, compact: bool = False) -> tuple[list[dict], str]:
    lines, notes = [], []
    workload = rows.workload.iloc[0]
    active = [metric for metric in COUNTERS if (rows[metric] != 0).any()]
    zero = [metric for metric in COUNTERS if metric not in active]
    if zero:
        notes.append("; ".join(f"{metric.capitalize()} = 0" for metric in zero) + ".")
    if workload == "W2":
        notes.append("Steps and comparisons nearly overlap; list steps = comparisons - 500.")
    if workload == "W3":
        notes.append("Array steps = moves + 1,000; its curves nearly overlap.")
    variants = ["head", "middle"] if workload == "W3" else ["-"]
    for structure in rows.structure.unique():
        name = SHORT_NAMES[structure] if compact else structure
        for variant in variants:
            part = rows[(rows.structure == structure) & (rows.variant == variant)]
            for metric in active:
                if workload == "W4":
                    label = metric.capitalize()
                    color = COUNTER_COLORS[metric]
                    dash, marker = {"steps": ("-", "o"), "moves": ("--", "s"),
                                    "comparisons": (":", "^")}[metric]
                elif workload == "W3":
                    label = f"{name} {variant} / {metric}"
                    color = COLORS[structure]
                    dash, marker = {("head", "steps"): ("-", "o"),
                                    ("head", "moves"): ("--", "x"),
                                    ("middle", "steps"): (":", "s"),
                                    ("middle", "moves"): ("-.", "+")}[variant, metric]
                else:
                    label = name if len(active) == 1 else f"{name} / {metric}"
                    color = COLORS[structure]
                    dash, marker = ("-", "o") if metric == "steps" else ("--", "x")
                    if len(active) == 1 and structure == "MyLinkedList":
                        dash, marker = "--", "s"
                lines.append(series(part, metric, label, color, dash, marker))
    return lines, " ".join(notes)


def draw_axis(ax, lines: list[dict], title: str, ylabel: str, *, compact=False,
              allow_log=True) -> None:
    for line in lines:
        ax.plot(line["x"], line["y"], label=line["label"], color=line["color"],
                linestyle=line["linestyle"], marker=line["marker"],
                linewidth=1.7, markersize=5, markeredgewidth=1.1,
                markerfacecolor="white" if line["marker"] not in ["x", "+"] else line["color"])
    ax.set_xscale("log")
    ax.set_xticks(SIZES, [r"$10^2$", r"$10^3$", r"$10^4$", r"$10^5$"])
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xlim(75, 140000)
    ax.set_xlabel("n (input size)")
    values = [value for line in lines for value in line["y"]]
    log_y = allow_log and bool(values) and min(values) > 0 and max(values) / min(values) >= 50
    if log_y:
        ax.set_yscale("log")
        ax.set_ylabel(f"{ylabel} (log scale)")
        ax.yaxis.set_minor_locator(NullLocator())
    else:
        ax.set_ylim(bottom=0)
        ax.set_ylabel(ylabel)
        formatter = ScalarFormatter(useMathText=True)
        formatter.set_powerlimits((-3, 5))
        ax.yaxis.set_major_formatter(formatter)
        if not values or max(values) == 0:
            ax.set_ylim(0, 1)
            ax.set_yticks([0])
    ax.set_title(title, loc="center", fontweight="normal", fontsize=12, pad=12)
    ax.set_facecolor("white")
    ax.grid(True, which="major", color="#D0D0D0", linewidth=.7)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("black")
        spine.set_linewidth(.8)
    if lines:
        ax.legend(loc="center left", bbox_to_anchor=(1.035, .5), borderaxespad=0,
                  frameon=True, fancybox=False, edgecolor="#C8C8C8", fontsize=11, handlelength=2.0,
                  handletextpad=.5, labelspacing=.7)


def save_single(lines: list[dict], title: str, ylabel: str, target: Path,
                note: str = "", *, allow_log=True) -> None:
    fig = plt.figure(figsize=(8.8, 4.9), facecolor="white")
    ax = fig.add_axes([.105, .20, .56, .66])
    draw_axis(ax, lines, title, ylabel, allow_log=allow_log)
    if note:
        fig.text(.5, .055, note, ha="center", va="center", fontsize=10.5, color="black")
    fig.savefig(target, dpi=240, facecolor="white", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def save_pair(left_lines: list[dict], right_lines: list[dict], left_title: str,
              right_title: str, left_ylabel: str, right_ylabel: str, target: Path,
              note: str = "") -> None:
    # Even at 210 points tall in the PDF, 12-point axis text remains over 7.5 points.
    # Fixed space to the right of each axis is reserved for its outside legend.
    fig = plt.figure(figsize=(10.0, 4.45), facecolor="white")
    left = fig.add_axes([.075, .22, .245, .65])
    right = fig.add_axes([.54, .22, .235, .65])
    draw_axis(left, left_lines, left_title, left_ylabel, compact=True)
    draw_axis(right, right_lines, right_title, right_ylabel, compact=True)
    if note:
        fig.text(.5, .045, note, ha="center", va="center", fontsize=10.5, color="black")
    fig.savefig(target, dpi=240, facecolor="white", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def save_workload(frame: pd.DataFrame, workload: str, target: Path) -> None:
    rows = frame[frame.workload == workload]
    times = time_series(rows)
    counts, note = operation_series(rows)
    names = {"W1": "Random access", "W2": "Search", "W3": "Insert and remove", "W4": "Priority processing"}
    output = target.parent
    save_single(times, f"{workload}: {names[workload]} time", "Time (ms)", output / f"{workload}_time.png")
    count_label = "Steps" if workload == "W1" else "Operations"
    save_single(counts, f"{workload}: {names[workload]} operations", count_label,
                output / f"{workload}_operations.png", note)
    compact_counts, _ = operation_series(rows, compact=True)
    save_pair(time_series(rows, compact=True), compact_counts,
              f"{workload}: median time", f"{workload}: operation counts",
              "Time (ms)", count_label, target, note)


def save_bonus(root: Path, output: Path) -> None:
    heap_csv = root / "results" / "build_heap.csv"
    if heap_csv.exists():
        frame = pd.read_csv(heap_csv)
        time_lines, comparison_lines = [], []
        for i, (method, part) in enumerate(frame.groupby("method", sort=False)):
            color = ["#4C72B0", "#DD8452"][i % 2]
            label = "Floyd" if method == "Floyd" else "Repeated insert"
            dash, marker = ("-", "o") if method == "Floyd" else ("--", "s")
            time_lines.append(series(part, "time_ms", label, color, dash, marker))
            comparison_lines.append(series(part, "comparisons", label, color, dash, marker))
        save_single(time_lines, "Heap construction time", "Time (ms)", output / "build_heap_time.png")
        save_single(comparison_lines, "Heap construction comparisons", "Comparisons", output / "build_heap_comparisons.png")
        save_pair(time_lines, comparison_lines, "Heap construction time", "Element comparisons",
                  "Time (ms)", "Comparisons", output / "bonus_build_heap.png")
    memory_csv = root / "results" / "memory.csv"
    if memory_csv.exists():
        frame = pd.read_csv(memory_csv)
        lines = []
        styles = [("-", "o"), ("--", "s"), (":", "^")]
        for i, (structure, part) in enumerate(frame.groupby("structure", sort=False)):
            dash, marker = styles[i % len(styles)]
            lines.append(series(part, "bytes", structure, COLORS[structure], dash, marker, divisor=1_000_000))
        note = "MB = 1,000,000 bytes. DynamicArray and MinHeap have equal measured footprints."
        save_single(lines, "Memory footprint", "Memory (MB)", output / "memory.png", note)
        # A wider companion keeps text readable in the report's 163-point slot.
        fig = plt.figure(figsize=(9.6, 3.0), facecolor="white")
        ax = fig.add_axes([.10, .26, .59, .58])
        draw_axis(ax, lines, "Memory footprint", "Memory (MB)", compact=True)
        fig.text(.5, .035, note, ha="center", va="center", fontsize=10.5, color="black")
        fig.savefig(output / "bonus_memory.png", dpi=240, facecolor="white", bbox_inches="tight", pad_inches=0.12)
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                         "axes.titlesize": 12, "axes.labelsize": 12,
                         "xtick.labelsize": 12, "ytick.labelsize": 12,
                         "text.color": "black", "axes.labelcolor": "black",
                         "xtick.color": "black", "ytick.color": "black"})
    output = args.project / "results" / "plots"
    output.mkdir(parents=True, exist_ok=True)
    frame = read_results(args.project / "results" / "results.csv")
    for workload in ["W1", "W2", "W3", "W4"]:
        save_workload(frame, workload, output / f"{workload}.png")
    save_bonus(args.project, output)
    print(f"Saved individual time/operation charts, paired report charts and available bonus figures to {output}")


if __name__ == "__main__":
    main()
