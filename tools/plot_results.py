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
from matplotlib.lines import Line2D
from matplotlib.ticker import ScalarFormatter
import pandas as pd

COLORS = {"DynamicArray": "#096F85", "MyLinkedList": "#D26631", "MinHeap": "#7254A8"}
METRICS = [("time_ms", "Median time", "milliseconds"), ("steps", "Steps", "operations"),
           ("moves", "Moves", "operations"), ("comparisons", "Comparisons", "operations")]
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


def style_axis(ax, ylabel: str) -> None:
    ax.set_xscale("log")
    ax.set_xticks(SIZES, ["100", "1k", "10k", "100k"])
    ax.set_xlabel("Initial size n")
    ax.set_ylabel(ylabel)
    ax.grid(True, which="major", color="#DCE4E8", linewidth=0.65)
    ax.set_axisbelow(True)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    for side in ["bottom", "left"]:
        ax.spines[side].set_color("#B7C5CD")


def panel(ax, rows: pd.DataFrame, metric: str, title: str, unit: str) -> None:
    for structure, part in rows.groupby("structure", sort=False):
        part = part.sort_values("n")
        ax.plot(part.n, part[metric], marker="o", markersize=4.5, linewidth=1.8,
                color=COLORS.get(structure, "#096F85"), label=structure)
    style_axis(ax, unit)
    values = rows[metric]
    if metric == "time_ms" and (values > 0).all():
        ax.set_yscale("log")
        ax.set_ylabel("milliseconds (log scale)")
    else:
        ax.set_ylim(bottom=0)
        formatter = ScalarFormatter(useMathText=True)
        formatter.set_powerlimits((-3, 4))
        ax.yaxis.set_major_formatter(formatter)
        if (values == 0).all():
            ax.set_ylim(0, 1)
            ax.set_yticks([0])
            ax.text(0.5, 0.48, "No counted operations", transform=ax.transAxes,
                    ha="center", va="center", color="#6A7E89", fontsize=10)
    ax.set_title(title, loc="left", fontweight="bold", pad=8)


def save_workload(frame: pd.DataFrame, workload: str, target: Path) -> None:
    selected = frame[frame.workload == workload]
    if workload == "W3":
        fig, axes = plt.subplots(2, 2, figsize=(9.6, 5.0))
        for row, variant in enumerate(["head", "middle"]):
            part = selected[selected.variant == variant]
            panel(axes[row, 0], part, "time_ms", f"{variant.capitalize()} | Median time", "milliseconds")
            ax = axes[row, 1]
            for structure, series in part.groupby("structure", sort=False):
                series = series.sort_values("n")
                for metric, linestyle, marker in [("steps", "-", "o"), ("moves", "--", "x")]:
                    ax.plot(series.n, series[metric], color=COLORS[structure], linestyle=linestyle,
                            marker=marker, markersize=5, linewidth=1.8, label=f"{structure}: {metric}")
            style_axis(ax, "operations")
            ax.set_ylim(bottom=0)
            formatter = ScalarFormatter(useMathText=True)
            formatter.set_powerlimits((-3, 4))
            ax.yaxis.set_major_formatter(formatter)
            ax.set_title(f"{variant.capitalize()} | Steps and moves", loc="left", fontweight="bold", pad=8)
        title = "W3  |  1,000 insertions + 1,000 removals"
        fig.subplots_adjust(left=.10, right=.975, bottom=.16, top=.80, hspace=.94, wspace=.30)
        handles = [Line2D([0], [0], color=COLORS[name], linewidth=2, label=name)
                   for name in ["DynamicArray", "MyLinkedList"]]
        handles.extend([Line2D([0], [0], color="#455C68", linestyle="-", marker="o", label="Steps"),
                        Line2D([0], [0], color="#455C68", linestyle="--", marker="x", label="Moves")])
        fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(.045, .932),
                   ncol=4, frameon=False, fontsize=10)
        fig.text(.055, .025, "Comparisons = 0 throughout; array steps = moves + 1,000 (curves nearly overlap).",
                 fontsize=10, color="#566B78")
    else:
        fig, axes = plt.subplots(2, 2, figsize=(9.6, 4.9))
        for ax, (metric, title, unit) in zip(axes.flat, METRICS):
            panel(ax, selected, metric, title, unit)
        title = {"W1": "W1  |  10,000 random reads", "W2": "W2  |  1,000 searches: 50% hits",
                 "W4": "W4  |  n inserts + n minimum extractions"}[workload]
        fig.subplots_adjust(left=.10, right=.975, bottom=.12, top=.81, hspace=.65, wspace=.29)
    fig.suptitle(title, x=.055, y=.985, ha="left", fontsize=15, fontweight="bold", color="#173A4B")
    if workload != "W3":
        handles, labels = axes.flat[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(.045, .934),
                   ncol=3, frameon=False, fontsize=11)
    fig.savefig(target, dpi=240, facecolor="white")
    plt.close(fig)


def save_bonus(root: Path, output: Path) -> None:
    heap_csv = root / "results" / "build_heap.csv"
    if heap_csv.exists():
        frame = pd.read_csv(heap_csv)
        fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.2))
        palette = ["#7254A8", "#096F85"]
        for i, (method, part) in enumerate(frame.groupby("method", sort=False)):
            part = part.sort_values("n")
            for ax, metric in zip(axes, ["time_ms", "comparisons"]):
                ax.plot(part.n, part[metric], marker="o", color=palette[i % len(palette)], label=method)
        for ax, ylabel in zip(axes, ["milliseconds", "comparisons"]):
            style_axis(ax, ylabel)
            ax.set_ylim(bottom=0)
        axes[0].set_title("Build time", loc="left", fontweight="bold")
        axes[1].set_title("Element comparisons", loc="left", fontweight="bold")
        fig.suptitle("Bonus B | Heap construction", x=.06, ha="left", fontweight="bold", fontsize=14)
        fig.legend(*axes[0].get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.045, .92),
                   ncol=2, frameon=False)
        fig.subplots_adjust(left=.10, right=.97, bottom=.19, top=.70, wspace=.31)
        fig.savefig(output / "bonus_build_heap.png", dpi=240, facecolor="white")
        plt.close(fig)
    memory_csv = root / "results" / "memory.csv"
    if memory_csv.exists():
        frame = pd.read_csv(memory_csv)
        fig, ax = plt.subplots(figsize=(9.6, 2.6))
        for structure, part in frame.groupby("structure", sort=False):
            part = part.sort_values("n")
            ax.plot(part.n, part.bytes / 1_000_000, marker="o", color=COLORS.get(structure), label=structure)
        style_axis(ax, "Retained graph size (MB)")
        ax.set_ylim(bottom=0)
        fig.suptitle("Bonus A | Memory footprint", x=.065, ha="left", fontweight="bold", fontsize=13)
        fig.legend(*ax.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(.05, .92),
                   ncol=3, frameon=False, fontsize=10)
        fig.subplots_adjust(left=.10, right=.97, bottom=.25, top=.65)
        fig.savefig(output / "bonus_memory.png", dpi=240, facecolor="white")
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.titlesize": 11, "axes.labelsize": 10,
                         "xtick.labelsize": 10, "ytick.labelsize": 10})
    output = args.project / "results" / "plots"
    output.mkdir(parents=True, exist_ok=True)
    frame = read_results(args.project / "results" / "results.csv")
    for workload in ["W1", "W2", "W3", "W4"]:
        save_workload(frame, workload, output / f"{workload}.png")
    save_bonus(args.project, output)
    print(f"Saved four workload figures and available bonus figures to {output}")


if __name__ == "__main__":
    main()
