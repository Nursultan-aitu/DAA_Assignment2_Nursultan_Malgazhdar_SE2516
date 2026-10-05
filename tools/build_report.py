#!/usr/bin/env python3
"""Create a plain five-page report using the recorded benchmark results."""
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from matplotlib import get_data_path
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from plot_results import read_results

PAGE_W, PAGE_H = 595.28, 841.89
LEFT, RIGHT, BOTTOM = 45, 45, 42
WIDTH = PAGE_W - LEFT - RIGHT


def register_fonts():
    fonts = Path(get_data_path()) / "fonts/ttf"
    pdfmetrics.registerFont(TTFont("Body", str(fonts / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("Body-Bold", str(fonts / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body", boldItalic="Body-Bold")


class Report:
    def __init__(self, path):
        self.canvas = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
        self.canvas.setTitle("Assignment 2 - Data Structures")
        self.canvas.setAuthor("Nursultan Malgazhdar")
        self.page = 0
        self.y = 0

    def start(self, title):
        if self.page:
            self.canvas.showPage()
        self.page += 1
        self.canvas.setFillColor(colors.black)
        self.canvas.setFont("Body", 9)
        self.canvas.drawCentredString(PAGE_W / 2, 23, str(self.page))
        self.y = PAGE_H - 43
        self.text(title, bold=True, size=13, leading=17, gap=13)

    def text(self, content, size=10.2, leading=14, gap=8, bold=False):
        style = ParagraphStyle("plain", fontName="Body-Bold" if bold else "Body",
                               fontSize=size, leading=leading, textColor=colors.black)
        paragraph = Paragraph(content, style)
        _, height = paragraph.wrap(WIDTH, 1000)
        if self.y - height < BOTTOM:
            raise ValueError(f"Page {self.page} overflow: {content[:90]}")
        paragraph.drawOn(self.canvas, LEFT, self.y - height)
        self.y -= height + gap

    def heading(self, title):
        self.text(title, bold=True, size=10.7, leading=14.5, gap=7)

    def image(self, path, height, gap=9):
        if self.y - height < BOTTOM:
            raise ValueError(f"Page {self.page} image overflow: {path}")
        self.canvas.drawImage(str(path), LEFT, self.y - height, width=WIDTH,
                              height=height, preserveAspectRatio=True, anchor="c", mask="auto")
        self.y -= height + gap

    def finish(self):
        if self.page != 5:
            raise ValueError("The assignment report must have five pages")
        self.canvas.save()


def metadata(root):
    result = {}
    for line in (root / "results/environment.properties").read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    result.update(json.loads((root / "metadata.json").read_text(encoding="utf-8-sig")))
    return result


def result(frame, workload, structure, variant="-"):
    rows = frame[(frame.workload == workload) & (frame.structure == structure)
                 & (frame.variant == variant) & (frame.n == 100000)]
    if len(rows) != 1:
        raise ValueError("A report result is missing or duplicated")
    return rows.iloc[0]


def ms(number):
    return f"{number:.3f}"


def complexity_table(report):
    rows = [
        ["Operation", "Best", "Average*", "Worst", "Extra\nspace", "Reason"],
        ["Array add(x)", "Θ(1)", "Ω(1), O(n)", "Θ(n)", "Θ(n)", "Usually one store; a full array copies n values."],
        ["Array add(i,x)", "Θ(1)", "Θ(n)", "Θ(n)", "Θ(n)", "Move values after i; grow if full."],
        ["Array remove(i)", "Θ(1)", "Θ(n)", "Θ(n)", "Θ(1)", "Move values after i one position left."],
        ["Array get(i)", "Θ(1)", "Θ(1)", "Θ(1)", "Θ(1)", "Read the cell at index i directly."],
        ["Array contains(x)", "Θ(1)", "Θ(n)", "Θ(n)", "Θ(1)", "Check values until a match or the end."],
        ["List add(x)", "Θ(1)", "Θ(1)", "Θ(1)", "Θ(1)", "The tail points directly to the last node."],
        ["List add(i,x)", "Θ(1)", "Θ(n)", "Θ(n)", "Θ(1)", "Head/tail are direct; other indices need a walk."],
        ["List remove(i)", "Θ(1)", "Θ(n)", "Θ(n)", "Θ(1)", "Except at the head, find the previous node."],
        ["List get(i)", "Θ(1)", "Θ(n)", "Θ(n)", "Θ(1)", "Follow i links from the head."],
        ["List contains(x)", "Θ(1)", "Θ(n)", "Θ(n)", "Θ(1)", "Check nodes until a match or the end."],
        ["Heap insert(x)", "Θ(1)", "Ω(1), O(n)", "Θ(n)", "Θ(n)", "Move up at most log n levels; growth copies n."],
        ["Heap peekMin()", "Θ(1)", "Θ(1)", "Θ(1)", "Θ(1)", "The smallest value is at index 0."],
        ["Heap extractMin()", "Θ(1)", "Ω(1),\nO(log n)", "Θ(log n)", "Θ(1)", "Replace the root and move down if needed."],
    ]
    normal = ParagraphStyle("cell", fontName="Body", fontSize=8.1, leading=10.8)
    bold = ParagraphStyle("head", parent=normal, fontName="Body-Bold")
    data = [[Paragraph(escape(cell).replace("\n", "<br/>"), bold if i == 0 else normal)
             for cell in row] for i, row in enumerate(rows)]
    table = Table(data, colWidths=[94, 38, 64, 46, 43, WIDTH - 285])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), .35, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    _, height = table.wrap(WIDTH, 1000)
    if report.y - height < BOTTOM:
        raise ValueError("Complexity table does not fit")
    table.drawOn(report.canvas, LEFT, report.y - height)
    report.y -= height + 10


def page_one(report, meta):
    report.start("Assignment 2 - Data Structures")
    report.text(escape(f"{meta['author']}, {meta['group']} | {meta['date']}"), gap=12)
    report.text("This project compares three ways to store integers. DynamicArray keeps values in an array. "
                "MyLinkedList keeps values in nodes connected by links. MinHeap keeps the smallest value at its root. "
                "All values are primitive int values, and the structures do not use ready-made Java collections.")
    report.text("The array and heap start with 16 cells and double their capacity when full. They do not shrink after removal. "
                "The list is singly linked and has both a head and a tail. Invalid indices and empty-heap access throw the required exceptions.")
    report.heading("Time complexity")
    complexity_table(report)
    report.text("Here n is the current number of elements. Θ gives a tight growth rate, O an upper bound, and Ω a lower bound. "
                "For indexed operations, the average assumes each valid index is equally likely. For search, half the queries are misses.", size=9.2, leading=12.4)
    report.text("*Append and heap insertion also depend on whether the array is full. Their average columns show safe bounds, "
                "not one exact random-input average. Over a long sequence, array append is Θ(1) amortized and heap insertion is O(log n) amortized. "
                "Amortized cost spreads occasional expensive resizing across many operations.", size=9.2, leading=12.4)
    report.text("Extra space means memory used during one operation, beyond the stored data. Growing an array needs a new array. "
                "Stored array memory is Θ(capacity), which can exceed the current size after removals; the list stores Θ(n) nodes. "
                "The bonus buildHeap uses Θ(n) time and Θ(n) space for its copy.", size=9.2, leading=12.4, gap=0)


def page_two(report, meta):
    report.start("Correctness and benchmark setup")
    report.heading("1. DynamicArray.contains(value)")
    report.text("Invariant: before iteration i, all elements before i have been checked and none equals the target. "
                "The array and its size do not change.<br/>"
                "Initialization: i is 0, so the checked part is empty and the statement is true.<br/>"
                "Maintenance: if the current value matches, returning true is correct. Otherwise, i increases and the checked part grows by one.<br/>"
                "Termination: i increases each time, so the loop either finds a match or reaches size. At size, every element has been checked.<br/>"
                "Conclusion: the method returns true exactly when the target exists, and false otherwise.")
    report.heading("2. MinHeap.bubbleDown(index)")
    report.text("Invariant: in the subtree handled by this call, only the current node may be larger than its children. "
                "Both child subtrees are heaps. The nodes already fixed above it are no larger than the values below them. No values are added or removed.<br/>"
                "Initialization: after extraction, only the new root may be misplaced. In Floyd's build, the child subtrees have already been fixed.<br/>"
                "Maintenance: the method chooses the smaller child. If the current value is no larger, this part is already a heap. Otherwise, "
                "a swap fixes the current position and moves the possible problem down one level.<br/>"
                "Termination: each swap moves downward, so the method eventually reaches a leaf or a correct position.<br/>"
                "Conclusion: the subtree becomes a min-heap with the same values. After extraction, this restores the remaining heap.")
    report.heading("How the measurements were made")
    report.text("The sizes are 100, 1,000, 10,000 and 100,000. Each run uses new Random(42), so both sequences receive the same "
                "data and queries. The JVM first runs 20 practice cycles at n = 1,000. Each case then has two more warm-ups and five timed runs. "
                "The reported time is the middle of the five sorted times, called the median. There are 36 cases and 180 saved measurements.")
    report.text("For W1-W3, filling the structure and making the queries happen before timing, and counters reset after filling. "
                "W4 includes both insertion and extraction, plus a check that the extracted values never decrease. "
                "The code uses the returned values so the JVM cannot simply discard the measured work.")
    report.text("A step is one array-cell read or one next-link read in the list. A move is one relocation of an existing array value, "
                "or one change to head, tail or next in the list. A comparison compares two element values. "
                "The first store of a new array value, loop bounds and index checks are not counted as moves or element comparisons. "
                "These counters are updated inside the methods.")
    report.text(escape(f"Tests: all 47 JUnit 5 tests passed. Machine: {meta.get('cpu.model', 'CPU not recorded')}; "
                       f"{meta.get('os.name')}; Java {meta.get('java.version')}. Raw runs and VM details are saved in results/."), size=9.3, leading=12.6, gap=0)


def page_three(report, root, frame):
    report.start("Results: access and search")
    report.heading("W1. Random access")
    report.text("After filling each structure, the benchmark makes 10,000 get(index) calls at random indices.")
    report.image(root / "results/plots/W1.png", 218)
    array, linked = result(frame, "W1", "DynamicArray"), result(frame, "W1", "MyLinkedList")
    report.text(f"At n = 100,000, the array takes {ms(array.time_ms)} ms and the list takes {ms(linked.time_ms)} ms. "
                f"The array reads 10,000 cells; the list follows {int(linked.steps):,} links. "
                "The array goes directly to an index, while the list starts from the head.")
    report.heading("W2. Search")
    report.text("There are 1,000 contains(value) queries: 500 values are present and 500 are guaranteed absent.")
    report.image(root / "results/plots/W2.png", 218)
    array, linked = result(frame, "W2", "DynamicArray"), result(frame, "W2", "MyLinkedList")
    report.text(f"At n = 100,000, the times are {ms(array.time_ms)} ms for the array and {ms(linked.time_ms)} ms for the list. "
                f"Both make {int(array.comparisons):,} comparisons. The list has 500 fewer steps because a successful search "
                "stops before reading the next link. Almost equal count lines overlap in the graph.", gap=0)


def page_four(report, root, frame):
    report.start("Results: updates and priority processing")
    report.heading("W3. Insert and remove")
    report.text("Each variant makes 1,000 insertions, then 1,000 removals. Head uses index 0; middle uses the original n / 2 throughout.")
    report.image(root / "results/plots/W3.png", 225)
    ah, lh = result(frame, "W3", "DynamicArray", "head"), result(frame, "W3", "MyLinkedList", "head")
    am, lm = result(frame, "W3", "DynamicArray", "middle"), result(frame, "W3", "MyLinkedList", "middle")
    report.text(f"At n = 100,000, head updates take {ms(ah.time_ms)} ms for the array and {ms(lh.time_ms)} ms for the list. "
                f"Middle updates take {ms(am.time_ms)} and {ms(lm.time_ms)} ms. The list changes 3,000 links in each variant, "
                "but finding the middle adds a long walk. Array steps and moves nearly overlap because they differ by only 1,000.")
    report.heading("W4. Priority processing")
    report.text("The heap receives n values, then extractMin() is called n times. The output is checked to be in non-decreasing order.")
    report.image(root / "results/plots/W4.png", 210)
    heap = result(frame, "W4", "MinHeap")
    report.text(f"At n = 100,000, the total time is {ms(heap.time_ms)} ms and the heap makes {int(heap.comparisons):,} element comparisons. "
                "The heap is empty at the end. Growth copies are included in its counters; the benchmark's ordering checks are not.", gap=0)


def page_five(report, root, frame):
    report.start("Discussion and bonus tasks")
    # Exactly twelve discussion sentences, written as ordinary paragraphs.
    report.text("DynamicArray is a good choice for reading values by index because it reaches the requested cell directly. "
                "MyLinkedList must follow links from the head, so a large index takes more work. "
                "Array values are next to each other in memory, and a CPU cache line can bring several nearby values into the processor at once. "
                "This also helps a simple scan, even when both structures check the same number of values.")
    report.text("List nodes have extra headers and links, and the processor must read each link before it knows where to go next. "
                "More objects also give the garbage collector more objects to manage. "
                "The timings fit these explanations, but this benchmark does not measure cache misses or garbage-collection pauses separately. "
                "A list is useful for repeated changes at the head and, with a tail pointer, for appending values.")
    report.text("Changing the middle by index is slower because the list must first find that position. "
                "MinHeap is useful when the next job should always have the smallest priority value. "
                "Resizing sometimes makes an array or heap insertion expensive, but doubling spreads that copying cost over many insertions. "
                "Warm-ups and median times reduce noise, but background activity and JVM optimisation can still change small timings.")
    report.heading("Bonus A. Memory use")
    report.image(root / "results/plots/bonus_memory.png", 163)
    memory = pd.read_csv(root / "results/memory.csv")
    sizes = memory[memory.n == 100000].set_index("structure").bytes
    report.text(f"JOL reports {sizes['DynamicArray']/1e6:.3f} MB for the array, {sizes['MyLinkedList']/1e6:.3f} MB for the list "
                f"and {sizes['MinHeap']/1e6:.3f} MB for the heap at n = 100,000. This includes the structure, counters and spare cells. "
                "A node uses 24 bytes here: 12 for its header, 4 for the int, 4 for the link and 4 for alignment. "
                "The arrays keep 131,072 cells. MB means 1,000,000 bytes. JOL could not attach its Serviceability Agent, so no object-address claims are made.", size=9.4, leading=12.7)
    report.heading("Bonus B. Building a heap")
    build = pd.read_csv(root / "results/build_heap.csv")
    values = build[build.n == 100000].set_index("method")
    report.text(f"At n = 100,000, Floyd's buildHeap takes {ms(values.loc['Floyd','time_ms'])} ms and "
                f"{int(values.loc['Floyd','comparisons']):,} comparisons. Repeated insertion takes "
                f"{ms(values.loc['RepeatedInsert','time_ms'])} ms and {int(values.loc['RepeatedInsert','comparisons']):,} comparisons. "
                "Floyd starts near the bottom, where most nodes need little work, and then works upwards. "
                "The total is Θ(n), including the input copy. Repeated insertion can take O(n log n) in the worst case, "
                "but random values often move up only a short distance. Its extra graphs are in results/plots/.", size=9.4, leading=12.7)
    report.text('Sources: the Assignment 2 course brief and <link href="https://github.com/openjdk/jol">OpenJDK JOL</link>. '
                'All graph values come from the saved CSV files.', size=8.5, leading=11.5, gap=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    root = parser.parse_args().project.resolve()
    frame = read_results(root / "results/results.csv")
    register_fonts()
    report = Report(root / "REPORT.pdf")
    page_one(report, metadata(root))
    page_two(report, metadata(root))
    page_three(report, root, frame)
    page_four(report, root, frame)
    page_five(report, root, frame)
    report.finish()
    print("Saved plain five-page REPORT.pdf")


if __name__ == "__main__":
    main()
