#!/usr/bin/env python3
"""Build the five-page report from this project's source and recorded results.

Run tools/plot_results.py first. This script never invents experimental values.
Usage: python tools/build_report.py [--project PATH]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from plot_results import read_results

PAGE_W, PAGE_H = 595.28, 841.89
LEFT, RIGHT, BOTTOM = 43, 43, 45
WIDTH = PAGE_W - LEFT - RIGHT
INK = colors.HexColor("#173A4B")
TEAL = colors.HexColor("#096F85")
MUTED = colors.HexColor("#566B78")


def register_fonts() -> None:
    # Matplotlib ships a portable Unicode font, including Θ and Ω.
    from matplotlib import get_data_path
    fonts = Path(get_data_path()) / "fonts" / "ttf"
    pdfmetrics.registerFont(TTFont("Report", str(fonts / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("Report-Bold", str(fonts / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily("Report", normal="Report", bold="Report-Bold", italic="Report", boldItalic="Report-Bold")


class Report:
    def __init__(self, path: Path):
        self.canvas = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
        self.canvas.setTitle("Assignment 2 - Data Structures: Experimental Report")
        self.canvas.setSubject("Primitive int data structures, loop invariants, and reproducible benchmarks")
        self.page = 0
        self.y = 0

    def start(self, title: str, subtitle: str) -> None:
        if self.page:
            self.canvas.showPage()
        self.page += 1
        self.canvas.setFillColor(TEAL)
        self.canvas.rect(LEFT, PAGE_H - 43, 35, 4, fill=1, stroke=0)
        self.canvas.setFont("Report-Bold", 8)
        self.canvas.setFillColor(MUTED)
        self.canvas.drawString(LEFT + 46, PAGE_H - 42, "DESIGN AND ANALYSIS OF ALGORITHMS  /  ASSIGNMENT 2")
        self.y = PAGE_H - 66
        self.text(title, size=21, leading=26, bold=True, gap=5)
        self.text(subtitle, size=9.2, leading=13.2, color=MUTED, gap=17)
        self.canvas.setStrokeColor(colors.HexColor("#D9E3E8"))
        self.canvas.line(LEFT, 34, PAGE_W - RIGHT, 34)
        self.canvas.setFillColor(MUTED)
        self.canvas.setFont("Report", 7.4)
        self.canvas.drawString(LEFT, 22, "Measured results and source-aligned analysis | primitive int storage")
        self.canvas.drawRightString(PAGE_W - RIGHT, 22, f"{self.page} / 5")

    def text(self, text: str, *, size=9.3, leading=13.1, bold=False, gap=8, color=INK,
             x=None, width=None) -> float:
        style = ParagraphStyle("report", fontName="Report-Bold" if bold else "Report", fontSize=size,
                               leading=leading, textColor=color, alignment=TA_LEFT,
                               spaceAfter=0, allowWidows=0, allowOrphans=0)
        paragraph = Paragraph(text, style)
        px, pw = LEFT if x is None else x, WIDTH if width is None else width
        _, height = paragraph.wrap(pw, 1000)
        if self.y - height < BOTTOM:
            raise ValueError(f"Report page {self.page} overflow: {text[:80]}")
        paragraph.drawOn(self.canvas, px, self.y - height)
        self.y -= height + gap
        return height

    def heading(self, text: str, gap=6) -> None:
        self.text(text, size=11.2, leading=15, bold=True, color=TEAL, gap=gap)

    def image(self, path: Path, height: float, *, width=WIDTH, x=LEFT, gap=8) -> None:
        if self.y - height < BOTTOM:
            raise ValueError(f"Report page {self.page} image overflow: {path.name}")
        self.canvas.drawImage(str(path), x, self.y - height, width=width, height=height,
                              preserveAspectRatio=True, anchor="c", mask="auto")
        self.y -= height + gap

    def finish(self) -> None:
        if self.page != 5:
            raise ValueError(f"Expected exactly five pages, got {self.page}")
        self.canvas.save()


def metadata(root: Path) -> dict[str, str]:
    values = {}
    environment = root / "results" / "environment.properties"
    if environment.exists():
        for line in environment.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    personal = root / "metadata.json"
    if personal.exists():
        values.update(json.loads(personal.read_text(encoding="utf-8-sig")))
    return values


def row(frame, workload, structure, n=100000, variant="-"):
    selected = frame[(frame.workload == workload) & (frame.structure == structure)
                     & (frame.n == n) & (frame.variant == variant)]
    if len(selected) != 1:
        raise ValueError("Missing or duplicate report comparison")
    return selected.iloc[0]


def ratio(numerator, denominator) -> str:
    return f"{numerator / denominator:,.2f}" if denominator else "undefined"


def fmt(value, decimals=3) -> str:
    return f"{float(value):,.{decimals}f}"


def complexity_table(report: Report) -> None:
    report.heading("Complexity of all 13 required operations")
    rows = [
        ["Operation", "Best", "Average /\naggregate*", "Worst", "Aux.\nworst", "Why"],
        ["Array add(x)", "Θ(1)", "Θ(1) amort.", "Θ(n)", "Θ(n)", "Doubling copies n items; copies sum geometrically."],
        ["Array add(i,x)", "Θ(1)", "Θ(n)", "Θ(n)", "Θ(n)", "Shift n-i cells; possibly allocate a larger array."],
        ["Array remove(i)", "Θ(1)", "Θ(n)", "Θ(n)", "Θ(1)", "Shift n-i-1 cells; capacity is retained."],
        ["Array get(i)", "Θ(1)", "Θ(1)", "Θ(1)", "Θ(1)", "One bounds check and one indexed cell read."],
        ["Array contains(x)", "Θ(1)", "Θ(n)", "Θ(n)", "Θ(1)", "Stop at first hit or scan all n live cells."],
        ["List add(x)", "Θ(1)", "Θ(1)", "Θ(1)", "Θ(1)", "Tail pointer avoids traversal; allocate one node."],
        ["List add(i,x)", "Θ(1)", "Θ(n)", "Θ(n)", "Θ(1)", "Head/tail are direct; otherwise find predecessor."],
        ["List remove(i)", "Θ(1)", "Θ(n)", "Θ(n)", "Θ(1)", "Head is direct; otherwise find predecessor."],
        ["List get(i)", "Θ(1)", "Θ(n)", "Θ(n)", "Θ(1)", "Follow exactly i next links from the head."],
        ["List contains(x)", "Θ(1)", "Θ(n)", "Θ(n)", "Θ(1)", "Scan nodes until a hit or the null successor."],
        ["Heap insert(x)", "Θ(1)", "Ω(1), O(log n)\namort. bounds*", "Θ(n)", "Θ(n)", "Bubble up log n levels; resizing can copy n cells."],
        ["Heap peekMin()", "Θ(1)", "Θ(1)", "Θ(1)", "Θ(1)", "The minimum is at array index 0."],
        ["Heap extractMin()", "Θ(1)", "Ω(1), O(log n)*", "Θ(log n)", "Θ(1)", "Replace root; bubble down; no capacity shrink."],
    ]
    style = ParagraphStyle("cell", fontName="Report", fontSize=7.3, leading=9.7, textColor=INK)
    hstyle = ParagraphStyle("header", parent=style, fontName="Report-Bold", textColor=colors.white)
    data = [[Paragraph(escape(cell).replace("\n", "<br/>"), hstyle if i == 0 else style)
             for cell in values] for i, values in enumerate(rows)]
    table = Table(data, colWidths=[94, 38, 83, 45, 43, WIDTH - 303], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#EDF4F6"), colors.white]),
        ("LINEBELOW", (0, 0), (-1, 0), .5, TEAL),
    ]))
    _, height = table.wrap(WIDTH, 1000)
    table.drawOn(report.canvas, LEFT, report.y - height)
    report.y -= height + 10


def page_one(report: Report, meta: dict) -> None:
    identity = " | ".join(str(meta[k]) for k in ["author", "group", "date"] if meta.get(k))
    report.start("Data structures, measured", "Assignment 2 - In-Memory Workload Engine" + (" | " + escape(identity) if identity else ""))
    report.text("<b>Implementation.</b> DynamicArray and MinHeap store primitive ints in arrays with initial capacity 16, "
                "double when full, and retain capacity after removals. MyLinkedList is singly linked with head and tail "
                "references; each node stores an int. The two sequences share IntSequence, so identical workloads exercise both.", gap=10)
    complexity_table(report)
    report.text("<b>Assumptions.</b> n is the live size before a valid operation; indexed averages use a uniform valid index. "
                "Search averages assume a fixed positive miss probability (50% in W2), so the average is Θ(n) even with duplicates. "
                "An immediate match gives the best case; a miss gives the worst case.", size=8.1, leading=11.3, gap=7)
    report.text("<b>*Average is not amortized.</b> No universal tight average bound is asserted for heap operations without an input distribution. "
                "The listed heap bounds are non-tight; insert's O(log n) is an aggregate amortized upper bound including growth. "
                "An individual insertion that resizes costs Θ(n), even if its bubbling is short. Array append is Θ(1) amortized, not Θ(1) worst case.", size=8.1, leading=11.3, gap=7)
    report.text("<b>Space.</b> Auxiliary space excludes retained storage and includes a temporary replacement array during growth. "
                "Retained storage is Θ(capacity) for the array/heap and Θ(n) for the list; retained capacity can reflect a larger historical size. "
                "Bonus buildHeap takes Θ(n) time in every case and Θ(n) auxiliary space for its defensive copy.", size=8.1, leading=11.3, gap=0)


def page_two(report: Report, meta: dict) -> None:
    report.start("Why the operations are correct", "Two loop invariants and a reproducible measurement contract")
    report.heading("1  DynamicArray.contains(value)")
    report.text("<b>Invariant.</b> Before iteration i, 0 ≤ i ≤ size and every live position j with 0 ≤ j &lt; i has been inspected and differs from value. "
                "The array and size are unchanged.<br/>"
                "<b>Initialization.</b> i = 0, so the inspected prefix is empty and the statement holds.<br/>"
                "<b>Maintenance.</b> read(i) returns the current element. Equality returns true with a witnessed match. Otherwise that element also differs; "
                "incrementing i extends the inspected prefix by one and preserves the invariant.<br/>"
                "<b>Termination.</b> The loop either returns true at a match or ends with i = size. In the latter case every live value differs and false is correct. "
                "The nonnegative variant size-i decreases on each continuing iteration.<br/>"
                "<b>Conclusion.</b> Both return paths exactly implement membership; metric increments do not modify stored elements.", size=9, leading=12.8, gap=14)
    report.heading("2  MinHeap.bubbleDown(index)")
    report.text("<b>Precondition and invariant.</b> Let r be the index passed to this call. Its two child subtrees are already heaps. "
                "Before every iteration, within the original subtree rooted at r, only edges from the current index to its children may violate heap order; "
                "the repaired path above it is ordered and its ancestors remain no larger than values below them. The subtree's multiset is unchanged.<br/>"
                "<b>Initialization.</b> After extractMin, only the replaced root can violate order. During Floyd's build, previously processed child subtrees are heaps. "
                "The path above the initial index is empty; no claim about ancestors outside the subtree at r is required.<br/>"
                "<b>Maintenance.</b> The code selects the smaller existing child. If the current value is no larger, it returns with the subtree ordered. "
                "Otherwise swapping lifts the smaller child above both child roots and moves the only possible violation into that child's position. "
                "Its child subtrees remain heaps, and a swap preserves the multiset.<br/>"
                "<b>Termination.</b> Each swap descends one tree level. At a leaf (index ≥ size/2), or at the early return, no violating child edge remains.<br/>"
                "<b>Conclusion.</b> The original subtree becomes a min-heap containing the same values. For extractMin, the original root was minimum and the remaining heap is restored.", size=9, leading=12.8, gap=14)
    report.heading("Measurement contract")
    report.text("<b>Data and repetition.</b> Every case recreates new Random(42) and the same nonnegative input values. Sizes are 100, 1,000, 10,000 and 100,000. "
                "Twenty discarded preheat cycles at n = 1,000 precede two per-case warm-ups and five measured runs; results.csv stores median wall time "
                "and deterministic counters. There are 36 cases and 180 measured runs, "
                "also preserved in raw_runs.csv. Setup and query generation are excluded from W1-W3; counters reset after filling.", size=8.6, leading=12, gap=7)
    report.text("<b>Counting.</b> A step is an array-cell read or a next-reference read (including a successor read for rewiring or null). A move is a write relocating "
                "an existing array value or an explicit list head/tail/next update. First placement of an external array value is excluded. Comparisons count "
                "element values, not loop bounds. Counters run inside timed operations; these categories are not CPU instruction counts.", size=8.6, leading=12, gap=7)
    keys = ["java.version", "java.vm.name", "os.name", "os.arch", "available.processors"]
    if meta.get("cpu.model"):
        keys.append("cpu.model")
    env = "; ".join(f"{key}: {meta.get(key, 'not recorded')}" for key in keys)
    report.text("<b>Recorded environment.</b> " + escape(env) + ".", size=8.2, leading=11.5, gap=0)


def page_three(report: Report, root: Path, frame: pd.DataFrame) -> None:
    report.start("Access and search", "Identical input and query streams expose traversal cost and storage-layout effects")
    a1, l1 = row(frame, "W1", "DynamicArray"), row(frame, "W1", "MyLinkedList")
    report.image(root / "results/plots/W1.png", 256, gap=4)
    report.text(f"<b>W1.</b> 10,000 uniformly sampled get(index) calls. At n = 100,000: array {fmt(a1.time_ms)} ms, list {fmt(l1.time_ms)} ms; "
                f"steps {int(a1.steps):,} versus {int(l1.steps):,}. Array reads stay constant per query; list traversal grows with the index.", size=8.8, leading=12.2, gap=16)
    a2, l2 = row(frame, "W2", "DynamicArray"), row(frame, "W2", "MyLinkedList")
    report.image(root / "results/plots/W2.png", 256, gap=4)
    report.text(f"<b>W2.</b> 500 hits sampled from the data and 500 guaranteed negative misses, shuffled before timing. At n = 100,000: array "
                f"{fmt(a2.time_ms)} ms, list {fmt(l2.time_ms)} ms. Both make {int(a2.comparisons):,} element comparisons; "
                "a matching node needs no successor read, so list steps are 500 below its comparisons. Repeated input values can shorten hit scans.", size=8.8, leading=12.2, gap=0)


def page_four(report: Report, root: Path, frame: pd.DataFrame) -> None:
    report.start("Updates and priority processing", "Boundary insertion, indexed traversal, and heap repair are different workloads")
    report.image(root / "results/plots/W3.png", 263, gap=4)
    ah, lh = row(frame, "W3", "DynamicArray", variant="head"), row(frame, "W3", "MyLinkedList", variant="head")
    report.text(f"<b>W3.</b> First 1,000 insertions, then 1,000 removals, at index 0 or the original n/2 (fixed throughout). At n = 100,000, "
                f"head updates take {fmt(ah.time_ms)} ms for the array and {fmt(lh.time_ms)} ms for the list. "
                "The list rewires a constant number of links at the head; the array shifts the live suffix. Middle list updates must find their predecessor.", size=8.8, leading=12.2, gap=15)
    report.image(root / "results/plots/W4.png", 247, gap=4)
    heap = row(frame, "W4", "MinHeap")
    report.text(f"<b>W4.</b> Insert n values into an empty heap, then extract n minima. At n = 100,000 this takes {fmt(heap.time_ms)} ms with "
                f"{int(heap.comparisons):,} element comparisons. The timed loop includes checksum accumulation and non-decreasing-order validation; "
                "those validation comparisons are excluded from the structure's counter. The final heap must be empty. Growth copies are included.", size=8.8, leading=12.2, gap=0)


def discussion(frame: pd.DataFrame, root: Path) -> list[str]:
    a1, l1 = row(frame, "W1", "DynamicArray"), row(frame, "W1", "MyLinkedList")
    a2, l2 = row(frame, "W2", "DynamicArray"), row(frame, "W2", "MyLinkedList")
    ah, lh = row(frame, "W3", "DynamicArray", variant="head"), row(frame, "W3", "MyLinkedList", variant="head")
    am, lm = row(frame, "W3", "DynamicArray", variant="middle"), row(frame, "W3", "MyLinkedList", variant="middle")
    return [
        f"At n = 100,000, W1's list/array time ratio is {ratio(l1.time_ms, a1.time_ms)}×, consistent with {int(l1.steps):,} next-link reads versus 10,000 array reads.",
        "A contiguous int array packs nearby values into cache lines, so scanning it can benefit from spatial locality and hardware prefetching.",
        f"W2 performs {int(a2.comparisons):,} comparisons in each structure at n = 100,000, yet its list/array time ratio is {ratio(l2.time_ms, a2.time_ms)}×.",
        "A node traversal depends on the previous pointer load, and separate object headers and links increase memory traffic; equal counted steps therefore need not imply equal elapsed time.",
        "The W2 timing is consistent with these layout effects but does not isolate cache misses or garbage-collection pauses, which were not measured separately.",
        f"For W3 head updates at n = 100,000, array/list time is {ratio(ah.time_ms, lh.time_ms)}× and list link updates total {int(lh.moves):,}, making this list suitable for head edits and tail appends.",
        f"At the middle index, array and list take {fmt(am.time_ms)} and {fmt(lm.time_ms)} ms respectively, because an index-based list must locate the predecessor before constant-size rewiring.",
        "Removing the last list element still requires traversal in this singly linked design, so a tail reference alone does not make every boundary removal constant time.",
        "MinHeap is suitable for repeatedly selecting the next minimum-priority job, with constant-time peeking and logarithmic worst-case extraction rather than arbitrary positional access.",
        "Array growth contributes occasional linear spikes, while retained capacity improves subsequent updates at the cost of memory that does not shrink after removals.",
        "These measurements include counter increments and use one JVM process with 20 preheat cycles, two per-case warm-ups and five timed repetitions, so tiny cases and scheduler noise still limit cross-machine conclusions.",
        "The operation counts support the asymptotic analysis, while median times describe this run and cannot by themselves establish a universal speed ranking.",
    ]


def page_five(report: Report, root: Path, frame: pd.DataFrame) -> None:
    report.start("Interpreting the evidence", "Twelve discussion sentences, followed by the optional experiments")
    for number, sentence in enumerate(discussion(frame, root), 1):
        report.text(f"<b>{number:02d}.</b> " + sentence, size=8.5, leading=11.6, gap=4)
    report.y -= 5
    memory_path, build_path = root / "results/memory.csv", root / "results/build_heap.csv"
    if memory_path.exists() and build_path.exists():
        report.heading("Bonus experiments", gap=4)
        report.image(root / "results/plots/bonus_memory.png", 145, gap=5)
        memory, build = pd.read_csv(memory_path), pd.read_csv(build_path)
        sizes = memory[memory.n == 100000].set_index("structure").bytes
        sample = build[build.n == 100000].set_index("method")
        report.text(f"<b>JOL.</b> At n = 100,000 the retained reachable graph is {sizes['DynamicArray']/1e6:.3f} MB (array), "
                    f"{sizes['MyLinkedList']/1e6:.3f} MB (list), and {sizes['MinHeap']/1e6:.3f} MB (heap), including wrapper objects, "
                    "metrics and spare capacity. A node takes 24 bytes here: 12-byte header + 4-byte int + 4-byte reference + 4-byte alignment padding; "
                    "the arrays retain 131,072 slots. MB = 1,000,000 bytes; "
                    "VM layout details are recorded in jol_vm_details.txt; Serviceability Agent attachment was unavailable, so no address claims are made.", size=8.0, leading=10.9, gap=6)
        report.text(f"<b>Floyd.</b> At n = 100,000, bottom-up construction uses {int(sample.loc['Floyd', 'comparisons']):,} comparisons "
                    f"and {fmt(sample.loc['Floyd', 'time_ms'])} ms versus {int(sample.loc['RepeatedInsert', 'comparisons']):,} comparisons "
                    f"and {fmt(sample.loc['RepeatedInsert', 'time_ms'])} ms for repeated insertion. Summing nodes by height gives "
                    "Σ n·h/2^(h+1) = O(n); the input copy supplies Ω(n). Repeated insertion has O(n log n) worst-case total time, "
                    "but random input can cause short upward paths, so a log-factor speedup is not guaranteed.", size=8.0, leading=10.9, gap=7)
        report.text('Sources: DAA Assignment 2 - Data Structures (provided course brief); '
                    '<link href="https://github.com/openjdk/jol" color="#096F85">OpenJDK Java Object Layout (JOL)</link>. '
                    'All plotted observations come from this project\'s CSV files.', size=7.6, leading=10.2, color=MUTED, gap=0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.project.resolve()
    frame = read_results(root / "results/results.csv")
    for workload in ["W1", "W2", "W3", "W4"]:
        if not (root / f"results/plots/{workload}.png").exists():
            raise FileNotFoundError("Run tools/plot_results.py before building the report")
    register_fonts()
    report = Report(root / "REPORT.pdf")
    page_one(report, metadata(root))
    page_two(report, metadata(root))
    page_three(report, root, frame)
    page_four(report, root, frame)
    page_five(report, root, frame)
    report.finish()
    print(f"Saved exactly five pages to {root / 'REPORT.pdf'}")


if __name__ == "__main__":
    main()
