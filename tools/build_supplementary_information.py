#!/usr/bin/env python3
"""Assemble one printable Supplementary Information PDF.

Nature Communications asks for a single Supplementary Information document, not
five loose figure files.  This tool builds it from artefacts the repository
already produces, so nothing here is retyped:

* the five assembled supplementary figure SVGs under ``build/figures/``,
  inlined at their true 180 mm width and never rescaled to fit a page;
* their legends, read from ``docs/revision_2026-08-12/legends.md``;
* Supplementary Table X, read from
  ``docs/revision_2026-08-12/supplementary_table_X_motility_parameters.md``.

The layout runs on A4 with 15 mm side margins, which is the widest page that
holds a 180 mm figure, and prints on any office printer.  Each page is written
as an SVG, converted to PDF by ``rsvg-convert``, and the pages are joined by
Ghostscript.  Both are external programs; CairoSVG is broken on this host and is
not used.

Text is laid out here rather than by the renderer, because SVG 1.1 has no line
wrapping.  Line widths are measured with FreeType on the same font file that
fontconfig gives ``rsvg-convert``, so the measured break points are the ones the
renderer draws.

Usage::

    python tools/build_supplementary_information.py --root .
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from matplotlib import font_manager
from matplotlib.ft2font import FT2Font, LoadFlags

#: Measure without hinting, and at a high resolution.  Hinted advances are
#: rounded to a whole pixel, which at 9 pt and 72 dpi is about a tenth of an em.
#: That rounding shifts every word and the drawn line stops matching the
#: measured one.
MEASURE_OVERSAMPLE = 100

# --- page geometry, in millimetres -------------------------------------------

PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0
MARGIN_LEFT_MM = 15.0
MARGIN_RIGHT_MM = 15.0
MARGIN_TOP_MM = 20.0
MARGIN_BOTTOM_MM = 18.0

#: The figures are 180 mm wide.  The content column is exactly that width, so no
#: figure is ever scaled.
CONTENT_WIDTH_MM = PAGE_WIDTH_MM - MARGIN_LEFT_MM - MARGIN_RIGHT_MM
#: Running text is set narrower than the figures.  A 180 mm measure at 9 pt runs
#: to about 110 characters a line, which is too wide to read comfortably.
TEXT_WIDTH_MM = 150.0
CONTENT_TOP_MM = MARGIN_TOP_MM
CONTENT_BOTTOM_MM = PAGE_HEIGHT_MM - MARGIN_BOTTOM_MM

PT_PER_MM = 72.0 / 25.4
MM_PER_PT = 25.4 / 72.0

# --- type scale, in points ---------------------------------------------------

TITLE_PT = 17.0
SUBTITLE_PT = 10.0
LEGEND_HEAD_PT = 10.0
BODY_PT = 9.0
BODY_LEADING_PT = 12.4
TABLE_PT = 7.0
TABLE_LEADING_PT = 8.8
CONTENTS_PT = 9.5
CONTENTS_LEADING_PT = 14.0
FOOTER_PT = 7.5

INK = "#111111"
QUIET_INK = "#555555"
RULE_INK = "#999999"

# Vertical space, in millimetres.
SPACE_AFTER_FIGURE_MM = 3.5
SPACE_AFTER_LEGEND_HEAD_MM = 1.2
SPACE_AFTER_PARAGRAPH_MM = 2.2
SPACE_AFTER_HEADING_MM = 1.6
SPACE_BEFORE_HEADING_MM = 4.0

DOCUMENT_TITLE = "Supplementary Information"

# --- fonts -------------------------------------------------------------------

#: One style name for each face the document uses.  ``fc-match`` resolves the
#: family the same way ``rsvg-convert`` does, so the measured width is the drawn
#: width.
FONT_QUERIES = {
    "regular": ("Arial", "Arial"),
    "bold": ("Arial:bold", "Arial"),
    "italic": ("Arial:italic", "Arial"),
    "mono": ("Courier New", "Courier New"),
}
FONT_WEIGHTS = {"regular": "normal", "bold": "bold", "italic": "normal", "mono": "normal"}
FONT_STYLES = {"regular": "normal", "bold": "normal", "italic": "italic", "mono": "normal"}


class Faces:
    """Resolve and measure the four faces the document draws."""

    def __init__(self) -> None:
        self._fonts: dict[str, FT2Font] = {}
        self._files: dict[str, str] = {}
        self._cache: dict[tuple[str, str, float], float] = {}
        for style, (query, family) in FONT_QUERIES.items():
            path = self._resolve(query, family)
            self._files[style] = path
            self._fonts[style] = FT2Font(path)

    @staticmethod
    def _resolve(query: str, family: str) -> str:
        """Ask fontconfig for the file, and fall back to matplotlib."""
        if shutil.which("fc-match"):
            found = subprocess.run(
                ["fc-match", "-f", "%{file}", query],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()
            if found and Path(found).is_file():
                return found
        weight = "bold" if ":bold" in query else "normal"
        italic = "italic" if ":italic" in query else "normal"
        properties = font_manager.FontProperties(family=family, weight=weight, style=italic)
        return font_manager.findfont(properties)

    @property
    def files(self) -> dict[str, str]:
        return dict(self._files)

    def width_pt(self, text: str, style: str, size_pt: float) -> float:
        """Return the advance width of ``text`` in points."""
        if not text:
            return 0.0
        key = (style, text, size_pt)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        font = self._fonts[style]
        font.set_size(size_pt, 72 * MEASURE_OVERSAMPLE)
        font.set_text(text, 0.0, flags=LoadFlags.NO_HINTING)
        width = font.get_width_height()[0] / 64.0 / MEASURE_OVERSAMPLE
        self._cache[key] = width
        return width

    def width_mm(self, text: str, style: str, size_pt: float) -> float:
        return self.width_pt(text, style, size_pt) * MM_PER_PT


# --- rich text ---------------------------------------------------------------


@dataclass(frozen=True)
class Run:
    """One stretch of text in one face."""

    text: str
    style: str = "regular"


@dataclass(frozen=True)
class Word:
    """One unbreakable stretch of text.

    ``space_before`` is false where a line may break without a space, which is
    what an underscore inside a parameter name gives a table cell.
    """

    runs: tuple[Run, ...]
    space_before: bool = True

    def width_mm(self, faces: Faces, size_pt: float) -> float:
        return sum(faces.width_mm(run.text, run.style, size_pt) for run in self.runs)


INLINE_PATTERN = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+?`)", re.DOTALL)


def parse_inline(markdown: str) -> list[Run]:
    """Split one markdown paragraph into styled runs.

    Only the three inline forms the sources use are handled: ``**bold**``,
    ``*italic*`` and ``` `code` ```.  An unknown form stays literal, which is
    visible rather than silently dropped.
    """
    runs: list[Run] = []
    for piece in INLINE_PATTERN.split(markdown):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
            runs.append(Run(piece[2:-2], "bold"))
        elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
            runs.append(Run(piece[1:-1], "italic"))
        elif piece.startswith("`") and piece.endswith("`") and len(piece) > 2:
            runs.append(Run(piece[1:-1], "mono"))
        else:
            runs.append(Run(piece, "regular"))
    return runs


#: A parameter name such as ``stall_rotational_diffusion_scale`` carries no
#: space, so a table cell can only wrap it after an underscore.
BREAK_AFTER_UNDERSCORE = re.compile(r"(?<=_)")


def split_words(runs: Sequence[Run], break_underscores: bool = False) -> list[Word]:
    """Break styled runs into whitespace-separated words, keeping the styles."""
    words: list[Word] = []
    current: list[Run] = []
    glued = False

    def flush(next_glued: bool) -> None:
        nonlocal current, glued
        if current:
            words.append(Word(tuple(current), space_before=not glued))
            current = []
        glued = next_glued

    for run in runs:
        for part in re.split(r"(\s+)", run.text):
            if not part:
                continue
            if part.isspace():
                flush(False)
                continue
            fragments = BREAK_AFTER_UNDERSCORE.split(part) if break_underscores else [part]
            for index, fragment in enumerate(fragments):
                if not fragment:
                    continue
                if index > 0:
                    flush(True)
                current.append(Run(fragment, run.style))
    flush(False)
    return words


def wrap(
    faces: Faces,
    runs: Sequence[Run],
    size_pt: float,
    width_mm: float,
    break_underscores: bool = False,
) -> list[list[Word]]:
    """Greedily wrap styled runs to a measured width."""
    space_mm = faces.width_mm(" ", "regular", size_pt)
    lines: list[list[Word]] = []
    line: list[Word] = []
    used = 0.0
    for word in split_words(runs, break_underscores):
        advance = word.width_mm(faces, size_pt)
        gap = (space_mm if word.space_before else 0.0) if line else 0.0
        if line and used + gap + advance > width_mm:
            lines.append(line)
            line, used = [word], advance
        else:
            line.append(word)
            used += gap + advance
    if line:
        lines.append(line)
    return lines or [[]]


def line_width_mm(faces: Faces, words: Sequence[Word], size_pt: float) -> float:
    space_mm = faces.width_mm(" ", "regular", size_pt)
    total = 0.0
    for index, word in enumerate(words):
        if index and word.space_before:
            total += space_mm
        total += word.width_mm(faces, size_pt)
    return total


# --- SVG emission ------------------------------------------------------------


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text_element(
    x_mm: float,
    y_mm: float,
    words: Sequence[Word],
    size_pt: float,
    faces: Faces,
    fill: str = INK,
    anchor: str = "start",
) -> str:
    """Draw one already-wrapped line as a single ``<text>`` element.

    Every word is placed at its own measured ``x``.  That keeps the drawn line
    identical to the measured one and removes any dependence on how the renderer
    collapses white space.
    """
    if not words:
        return ""
    size_mm = size_pt * MM_PER_PT
    space_mm = faces.width_mm(" ", "regular", size_pt)
    total = line_width_mm(faces, words, size_pt)
    if anchor == "middle":
        cursor = x_mm - total / 2.0
    elif anchor == "end":
        cursor = x_mm - total
    else:
        cursor = x_mm
    spans: list[str] = []
    for index, word in enumerate(words):
        if index and word.space_before:
            cursor += space_mm
        for run in word.runs:
            spans.append(
                '<tspan x="{:.4f}" font-family="{}" font-weight="{}" '
                'font-style="{}">{}</tspan>'.format(
                    cursor,
                    "Courier New" if run.style == "mono" else "Arial",
                    FONT_WEIGHTS[run.style],
                    FONT_STYLES[run.style],
                    escape(run.text),
                )
            )
            cursor += faces.width_mm(run.text, run.style, size_pt)
    return '<text y="{:.4f}" font-size="{:.4f}" fill="{}" xml:space="preserve">{}</text>'.format(
        y_mm, size_mm, fill, "".join(spans)
    )


NAMESPACE_PATTERN = re.compile(r'xmlns:([A-Za-z0-9_.-]+)="([^"]+)"')


def read_figure_svg(path: Path) -> tuple[str, dict[str, str], float, float]:
    """Return the inner markup, extra namespaces, and the declared size in mm."""
    source = path.read_text(encoding="utf-8")
    open_match = re.search(r"<svg\b[^>]*>", source, re.DOTALL)
    if open_match is None:
        raise ValueError(f"{path} carries no <svg> element")
    header = open_match.group(0)
    namespaces = dict(NAMESPACE_PATTERN.findall(header))
    width = re.search(r'\bwidth="([0-9.]+)mm"', header)
    height = re.search(r'\bheight="([0-9.]+)mm"', header)
    view_box = re.search(r'\bviewBox="([-0-9.eE ]+)"', header)
    if width is None or height is None or view_box is None:
        raise ValueError(f"{path} does not declare width, height and viewBox in mm")
    box = [float(value) for value in view_box.group(1).split()]
    if abs(box[2] - float(width.group(1))) > 1e-6 or abs(box[3] - float(height.group(1))) > 1e-6:
        raise ValueError(
            f"{path} has a viewBox that is not one user unit per millimetre; "
            "the page cannot inline it without scaling"
        )
    close = source.rindex("</svg>")
    inner = source[open_match.end() : close]
    return inner, namespaces, float(width.group(1)), float(height.group(1))


# --- laid-out items ----------------------------------------------------------


@dataclass
class Item:
    """One atomic thing on a page: a line of text, a rule, or a whole figure."""

    height_mm: float
    render: Callable[[float], str]
    break_before_ok: bool = True
    anchor: str | None = None
    space_after_mm: float = 0.0


@dataclass
class Block:
    """A run of items that the page filler treats as one unit of content."""

    items: list[Item] = field(default_factory=list)


# --- source parsing ----------------------------------------------------------


@dataclass
class LegendSection:
    key: str
    title: str
    paragraphs: list[str]


HEADING_PATTERN = re.compile(r"^##\s+(.*?)\s*\|\s*(.*)$")


def parse_legends(path: Path) -> dict[str, LegendSection]:
    """Read the legend source and return one section per figure heading."""
    sections: dict[str, LegendSection] = {}
    key: str | None = None
    title = ""
    buffer: list[str] = []
    paragraphs: list[str] = []

    def flush_paragraph() -> None:
        nonlocal buffer
        if buffer:
            paragraphs.append(" ".join(line.strip() for line in buffer).strip())
            buffer = []

    def flush_section() -> None:
        nonlocal paragraphs
        flush_paragraph()
        if key is not None:
            sections[key] = LegendSection(key, title, [p for p in paragraphs if p])
        paragraphs = []

    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            flush_section()
            key, title = match.group(1).strip(), match.group(2).strip()
            continue
        if line.startswith("#"):
            continue
        if not line.strip():
            flush_paragraph()
            continue
        buffer.append(line)
    flush_section()
    return sections


@dataclass
class TableDocument:
    title: str
    intro: list[str]
    header: list[str]
    rows: list[list[str]]
    notes_heading: str
    notes: list[str]


def parse_table_document(path: Path) -> TableDocument:
    """Read the Supplementary Table X markdown into its parts."""
    lines = path.read_text(encoding="utf-8").splitlines()
    title = ""
    intro: list[str] = []
    header: list[str] = []
    rows: list[list[str]] = []
    notes_heading = "Notes"
    notes: list[str] = []
    buffer: list[str] = []
    state = "intro"

    def flush(into: list[str]) -> None:
        nonlocal buffer
        if buffer:
            into.append(" ".join(item.strip() for item in buffer).strip())
            buffer = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            continue
        if stripped.startswith("## "):
            flush(intro if state == "intro" else notes)
            notes_heading = stripped[3:].strip()
            state = "notes"
            continue
        if stripped.startswith("|"):
            flush(intro if state == "intro" else notes)
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            if not header:
                header = cells
            else:
                rows.append(cells)
            continue
        if stripped.startswith("- "):
            flush(intro if state == "intro" else notes)
            buffer = [stripped[2:]]
            continue
        if not stripped:
            flush(intro if state == "intro" else notes)
            continue
        buffer.append(stripped)
    flush(intro if state == "intro" else notes)
    if not header or not rows:
        raise ValueError(f"{path} carries no markdown table")
    return TableDocument(title, intro, header, rows, notes_heading, notes)


# --- document construction ---------------------------------------------------


class Builder:
    """Turn parsed sources into a list of blocks."""

    def __init__(self, faces: Faces) -> None:
        self.faces = faces

    def paragraph(
        self,
        markdown: str,
        size_pt: float = BODY_PT,
        leading_pt: float = BODY_LEADING_PT,
        width_mm: float = TEXT_WIDTH_MM,
        x_mm: float = MARGIN_LEFT_MM,
        fill: str = INK,
        space_after_mm: float = SPACE_AFTER_PARAGRAPH_MM,
        keep_lines: int = 0,
    ) -> list[Item]:
        lines = wrap(self.faces, parse_inline(markdown), size_pt, width_mm)
        leading_mm = leading_pt * MM_PER_PT
        items: list[Item] = []
        for index, line in enumerate(lines):
            # Orphan and widow control: never leave one line of a paragraph
            # alone at a page boundary.
            allowed = index == 0 or (index >= 2 and index <= len(lines) - 2)
            if index < keep_lines:
                allowed = False
            items.append(
                Item(
                    height_mm=leading_mm,
                    render=(
                        lambda y, line=line, size_pt=size_pt, x_mm=x_mm, fill=fill: text_element(
                            x_mm, y + size_pt * MM_PER_PT * 0.78, line, size_pt, self.faces, fill
                        )
                    ),
                    break_before_ok=allowed,
                )
            )
        if items:
            items[-1].space_after_mm = space_after_mm
        return items

    def heading(self, text: str, size_pt: float, space_before_mm: float = 0.0) -> list[Item]:
        line = wrap(self.faces, [Run(text, "bold")], size_pt, CONTENT_WIDTH_MM)[0]
        height = size_pt * MM_PER_PT * 1.30 + space_before_mm
        return [
            Item(
                height_mm=height,
                render=lambda y, line=line, size_pt=size_pt, space=space_before_mm: text_element(
                    MARGIN_LEFT_MM,
                    y + space + size_pt * MM_PER_PT,
                    line,
                    size_pt,
                    self.faces,
                ),
                break_before_ok=True,
                space_after_mm=SPACE_AFTER_HEADING_MM,
            )
        ]

    def figure(self, svg_path: Path, key: str) -> tuple[list[Item], dict[str, str]]:
        inner, namespaces, width_mm, height_mm = read_figure_svg(svg_path)
        if abs(width_mm - CONTENT_WIDTH_MM) > 1e-6:
            raise ValueError(
                f"{svg_path} is {width_mm} mm wide; the page column is "
                f"{CONTENT_WIDTH_MM} mm and the figure is never rescaled"
            )
        available = CONTENT_BOTTOM_MM - CONTENT_TOP_MM
        if height_mm > available:
            raise ValueError(
                f"{svg_path} is {height_mm} mm high; one A4 page holds "
                f"{available:.1f} mm and this tool never splits a figure"
            )

        def render(y: float, inner: str = inner) -> str:
            return f'<g transform="translate({MARGIN_LEFT_MM:.4f} {y:.4f})">{inner}</g>'

        item = Item(
            height_mm=height_mm,
            render=render,
            break_before_ok=True,
            anchor=key,
            space_after_mm=SPACE_AFTER_FIGURE_MM,
        )
        return [item], namespaces

    def table(self, document: TableDocument) -> list[Item]:
        """Lay out the parameter table, with the header repeated on every page."""
        faces = self.faces
        columns = len(document.header)
        pad_mm = 1.6
        # Automatic column widths.  ``smallest`` is the width of the longest
        # fragment that cannot be broken, ``largest`` the width of the whole
        # cell on one line.  Spare width is shared in proportion to how much
        # each column would still like.
        smallest: list[float] = []
        largest: list[float] = []
        for index in range(columns):
            cells = [document.header[index]] + [row[index] for row in document.rows]
            fragments = [
                word.width_mm(faces, TABLE_PT)
                for cell in cells
                for word in split_words([Run(cell, "bold")], break_underscores=True)
            ]
            smallest.append(max(fragments) + 2 * pad_mm)
            largest.append(
                max(faces.width_mm(cell, "bold", TABLE_PT) for cell in cells) + 2 * pad_mm
            )
        if sum(smallest) > CONTENT_WIDTH_MM:
            raise ValueError(
                "the parameter table does not fit a 180 mm column even when every "
                "cell wraps; reduce the table font or split the table"
            )
        spare = CONTENT_WIDTH_MM - sum(smallest)
        appetite = [large - small for large, small in zip(largest, smallest, strict=True)]
        demand = sum(appetite)
        widths = [
            small + (spare * want / demand if demand > 0 else spare / columns)
            for small, want in zip(smallest, appetite, strict=True)
        ]
        edges = [MARGIN_LEFT_MM]
        for width in widths:
            edges.append(edges[-1] + width)

        leading_mm = TABLE_LEADING_PT * MM_PER_PT

        def cell_lines(row: Sequence[str]) -> list[list[list[Word]]]:
            return [
                wrap(
                    faces,
                    [Run(row[index], "regular")],
                    TABLE_PT,
                    widths[index] - 2 * pad_mm,
                    break_underscores=True,
                )
                for index in range(columns)
            ]

        def row_items(row: Sequence[str], style: str, rule_above: bool) -> list[Item]:
            wrapped = cell_lines(row)
            depth = max(len(lines) for lines in wrapped)
            height = depth * leading_mm + 1.0

            def render(y: float, wrapped: list[list[list[Word]]] = wrapped, style: str = style,
                       rule_above: bool = rule_above, height: float = height) -> str:
                parts: list[str] = []
                if rule_above:
                    parts.append(
                        f'<line x1="{MARGIN_LEFT_MM:.3f}" y1="{y:.3f}" '
                        f'x2="{edges[-1]:.3f}" y2="{y:.3f}" '
                        f'stroke="{RULE_INK}" stroke-width="0.2"/>'
                    )
                for index, lines in enumerate(wrapped):
                    for line_index, line in enumerate(lines):
                        styled = [
                            Word(
                                tuple(Run(run.text, style) for run in word.runs),
                                space_before=word.space_before,
                            )
                            for word in line
                        ]
                        parts.append(
                            text_element(
                                edges[index] + pad_mm,
                                y + 1.0 + (line_index + 0.78) * leading_mm,
                                styled,
                                TABLE_PT,
                                faces,
                            )
                        )
                return "".join(parts)

            return [Item(height_mm=height, render=render, break_before_ok=True)]

        items: list[Item] = []
        items += row_items(document.header, "bold", rule_above=True)
        items[-1].break_before_ok = True
        for index, row in enumerate(document.rows):
            row_item = row_items(row, "regular", rule_above=index == 0)[0]
            # The header must not be the last thing on a page.
            row_item.break_before_ok = index > 0
            items.append(row_item)

        def closing_rule(y: float) -> str:
            return (
                f'<line x1="{MARGIN_LEFT_MM:.3f}" y1="{y:.3f}" x2="{edges[-1]:.3f}" y2="{y:.3f}" '
                f'stroke="{RULE_INK}" stroke-width="0.2"/>'
            )

        items.append(
            Item(height_mm=0.4, render=closing_rule, break_before_ok=False,
                 space_after_mm=SPACE_AFTER_PARAGRAPH_MM)
        )
        return items


# --- page filling ------------------------------------------------------------


@dataclass
class Page:
    placements: list[tuple[float, Item]] = field(default_factory=list)


def fill_pages(items: Sequence[Item]) -> list[Page]:
    """Place items down the page, moving a group when it does not fit."""
    pages: list[Page] = []
    current: list[tuple[float, Item]] = []
    y = CONTENT_TOP_MM
    index = 0
    while index < len(items):
        item = items[index]
        if y + item.height_mm > CONTENT_BOTTOM_MM and current:
            # Walk back to the nearest allowed break, so a heading travels with
            # its paragraph and a figure with its legend heading.
            cut = len(current)
            while cut > 0 and not current[cut - 1][1].break_before_ok:
                cut -= 1
            if cut == 0:
                cut = len(current)
            moved = current[cut:]
            pages.append(Page(current[:cut]))
            current = []
            y = CONTENT_TOP_MM
            for _, moved_item in moved:
                current.append((y, moved_item))
                y += moved_item.height_mm + moved_item.space_after_mm
            continue
        current.append((y, item))
        y += item.height_mm + item.space_after_mm
        index += 1
    if current:
        pages.append(Page(current))
    return pages


def page_svg(page: Page, number: int, total: int, namespaces: dict[str, str], faces: Faces) -> str:
    declarations = "".join(f' xmlns:{prefix}="{uri}"' for prefix, uri in sorted(namespaces.items()))
    body = "".join(item.render(y) for y, item in page.placements)
    footer_words = wrap(
        faces,
        [Run(f"{DOCUMENT_TITLE} — page {number} of {total}", "regular")],
        FOOTER_PT,
        CONTENT_WIDTH_MM,
    )[0]
    footer = text_element(
        PAGE_WIDTH_MM / 2.0,
        PAGE_HEIGHT_MM - MARGIN_BOTTOM_MM + 8.0,
        footer_words,
        FOOTER_PT,
        faces,
        fill=QUIET_INK,
        anchor="middle",
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg"{declarations} '
        f'width="{PAGE_WIDTH_MM}mm" height="{PAGE_HEIGHT_MM}mm" '
        f'viewBox="0 0 {PAGE_WIDTH_MM} {PAGE_HEIGHT_MM}" version="1.1">'
        f'<rect x="0" y="0" width="{PAGE_WIDTH_MM}" height="{PAGE_HEIGHT_MM}" fill="white"/>'
        f"{body}{footer}</svg>\n"
    )


# --- external programs -------------------------------------------------------


def require(program: str, hint: str) -> str:
    path = shutil.which(program)
    if path is None:
        raise SystemExit(f"{program} is not on PATH; {hint}")
    return path


def svg_to_pdf(svg: Path, pdf: Path) -> None:
    subprocess.run(
        ["rsvg-convert", "--format", "pdf", "--output", str(pdf), str(svg)],
        check=True,
        capture_output=True,
    )


def join_pdfs(pages: Sequence[Path], output: Path, title: str) -> None:
    marks = output.with_suffix(".pdfmark")
    marks.write_text(
        "[ /Title ({title}) /Author () /Subject () /DOCINFO pdfmark\n".format(
            title=title.replace("(", r"\(").replace(")", r"\)")
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "gs",
            "-dBATCH",
            "-dNOPAUSE",
            "-q",
            "-sDEVICE=pdfwrite",
            "-dPDFSETTINGS=/prepress",
            "-dAutoRotatePages=/None",
            f"-sOutputFile={output}",
            *[str(page) for page in pages],
            str(marks),
        ],
        check=True,
        capture_output=True,
    )
    marks.unlink()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --- the document ------------------------------------------------------------

FIGURE_KEYS = [
    ("Supplementary Figure S1", "Supplementary_Figure_1"),
    ("Supplementary Figure S2", "Supplementary_Figure_2"),
    ("Supplementary Figure S3", "Supplementary_Figure_3"),
    ("Supplementary Figure S4", "Supplementary_Figure_4"),
    ("Supplementary Figure S5", "Supplementary_Figure_5"),
]


def figure_svg_path(root: Path, folder: str) -> Path:
    directory = root / "build" / "figures" / folder
    candidates = sorted(directory.glob("*.svg"))
    if len(candidates) != 1:
        raise SystemExit(
            f"{directory} holds {len(candidates)} SVG files; build the figures first"
        )
    return candidates[0]


def build_body(
    root: Path, builder: Builder, legends: dict[str, LegendSection], table: TableDocument
) -> tuple[list[Item], dict[str, str], list[Path]]:
    items: list[Item] = []
    namespaces: dict[str, str] = {}
    sources: list[Path] = []
    for key, folder in FIGURE_KEYS:
        section = legends.get(key)
        if section is None:
            raise SystemExit(f"{key} has no legend in the legend source")
        svg = figure_svg_path(root, folder)
        sources.append(svg)
        figure_items, figure_namespaces = builder.figure(svg, key)
        namespaces.update(figure_namespaces)
        items += figure_items
        head = builder.heading(f"{key} | {section.title}", LEGEND_HEAD_PT)
        head[0].break_before_ok = False
        head[0].space_after_mm = SPACE_AFTER_LEGEND_HEAD_MM
        items += head
        for index, paragraph in enumerate(section.paragraphs):
            items += builder.paragraph(paragraph, keep_lines=2 if index == 0 else 0)

    table_head = builder.heading(
        table.title, LEGEND_HEAD_PT, space_before_mm=SPACE_BEFORE_HEADING_MM
    )
    table_head[0].anchor = "Supplementary Table X"
    items += table_head
    for paragraph in table.intro:
        items += builder.paragraph(paragraph)
    items += builder.table(table)
    items += builder.heading(table.notes_heading, BODY_PT + 0.5)
    for note in table.notes:
        items += builder.paragraph("• " + note, width_mm=TEXT_WIDTH_MM)
    return items, namespaces, sources


def build_front(
    builder: Builder, entries: Sequence[tuple[str, str, int]], total_pages: int
) -> list[Item]:
    faces = builder.faces
    items: list[Item] = []
    title_line = wrap(faces, [Run(DOCUMENT_TITLE, "bold")], TITLE_PT, CONTENT_WIDTH_MM)[0]
    items.append(
        Item(
            height_mm=TITLE_PT * MM_PER_PT * 1.5,
            render=lambda y: text_element(
                MARGIN_LEFT_MM, y + TITLE_PT * MM_PER_PT, title_line, TITLE_PT, faces
            ),
        )
    )
    items += builder.paragraph(
        "Reproducible analyses and figures for *The cost-benefit trade-off of "
        "peritrichous flagellation in bacteria*. Every figure is drawn at its "
        "submission width of 180 mm. Every legend is the registered legend of "
        "that figure. Every number in a legend is recomputed from the source "
        "table named in the figure-number register.",
        size_pt=SUBTITLE_PT,
        leading_pt=13.5,
        space_after_mm=8.0,
    )
    items += builder.heading("Contents", LEGEND_HEAD_PT)
    leading_mm = CONTENTS_LEADING_PT * MM_PER_PT
    for label, title, page in entries:
        entry_runs = [Run(label, "bold"), Run(" | " + title, "regular")]
        left = wrap(faces, entry_runs, CONTENTS_PT, TEXT_WIDTH_MM)
        right = wrap(faces, [Run(str(page), "regular")], CONTENTS_PT, 20.0)[0]
        for index, line in enumerate(left):
            items.append(
                Item(
                    height_mm=leading_mm,
                    render=(
                        lambda y, line=line, index=index, right=right: text_element(
                            MARGIN_LEFT_MM,
                            y + CONTENTS_PT * MM_PER_PT * 0.78,
                            line,
                            CONTENTS_PT,
                            faces,
                        )
                        + (
                            text_element(
                                MARGIN_LEFT_MM + CONTENT_WIDTH_MM,
                                y + CONTENTS_PT * MM_PER_PT * 0.78,
                                right,
                                CONTENTS_PT,
                                faces,
                                anchor="end",
                            )
                            if index == 0
                            else ""
                        )
                    ),
                    break_before_ok=index == 0,
                )
            )
        items[-1].space_after_mm = 1.4
    items += builder.paragraph(
        f"The document has {total_pages} pages. It is set on A4 with 15 mm side "
        "margins, which is the widest page that carries a 180 mm figure "
        "unscaled.",
        space_after_mm=0.0,
    )
    return items


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()

    require("rsvg-convert", "install it with `brew install librsvg`")
    require("gs", "install Ghostscript with `brew install ghostscript`")

    reports = root / "docs" / "revision_2026-08-12"
    legend_source = reports / "legends.md"
    table_source = reports / "supplementary_table_X_motility_parameters.md"
    legends = parse_legends(legend_source)
    table = parse_table_document(table_source)

    faces = Faces()
    builder = Builder(faces)
    body, namespaces, figure_sources = build_body(root, builder, legends, table)

    # Two passes: the contents list needs the page numbers, and the page numbers
    # need the length of the contents list.
    front_pages = 1
    for _ in range(4):
        pages = fill_pages(body)
        anchors: dict[str, int] = {}
        for number, page in enumerate(pages, start=front_pages + 1):
            for _, item in page.placements:
                if item.anchor and item.anchor not in anchors:
                    anchors[item.anchor] = number
        entries = [
            (key, legends[key].title, anchors[key]) for key, _ in FIGURE_KEYS if key in anchors
        ]
        entries.append(
            ("Supplementary Table X", table.title.split(".", 1)[-1].strip(),
             anchors["Supplementary Table X"])
        )
        front = build_front(builder, entries, front_pages + len(pages))
        front_page_list = fill_pages(front)
        if len(front_page_list) == front_pages:
            break
        front_pages = len(front_page_list)
    else:
        raise SystemExit("the contents list did not settle on a page count")

    all_pages = front_page_list + pages
    total = len(all_pages)

    output_dir = root / "build" / "supplementary_information"
    page_dir = output_dir / "pages"
    if page_dir.exists():
        shutil.rmtree(page_dir)
    page_dir.mkdir(parents=True, exist_ok=True)

    page_pdfs: list[Path] = []
    for number, page in enumerate(all_pages, start=1):
        svg_path = page_dir / f"page_{number:02d}.svg"
        pdf_path = page_dir / f"page_{number:02d}.pdf"
        svg_path.write_text(page_svg(page, number, total, namespaces, faces), encoding="utf-8")
        svg_to_pdf(svg_path, pdf_path)
        page_pdfs.append(pdf_path)

    output = output_dir / "Supplementary_Information.pdf"
    join_pdfs(page_pdfs, output, DOCUMENT_TITLE)

    manifest = {
        "artifact": "Supplementary_Information.pdf",
        "pages": total,
        "page_size_mm": [PAGE_WIDTH_MM, PAGE_HEIGHT_MM],
        "margins_mm": {
            "left": MARGIN_LEFT_MM,
            "right": MARGIN_RIGHT_MM,
            "top": MARGIN_TOP_MM,
            "bottom": MARGIN_BOTTOM_MM,
        },
        "figure_width_mm": CONTENT_WIDTH_MM,
        "text_measure_mm": TEXT_WIDTH_MM,
        "renderer": subprocess.run(
            ["rsvg-convert", "--version"], capture_output=True, text=True, check=True
        ).stdout.splitlines()[0],
        "joiner": subprocess.run(
            ["gs", "--version"], capture_output=True, text=True, check=True
        ).stdout.strip(),
        "fonts": faces.files,
        "contents": [
            {"label": label, "title": title, "page": page} for label, title, page in entries
        ],
        "sources": [
            {
                "path": str(path.relative_to(root)),
                "sha256": sha256_file(path),
            }
            for path in [legend_source, table_source, *figure_sources]
        ],
        "sha256": sha256_file(output),
    }
    (output_dir / "Supplementary_Information.manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {output.relative_to(root)} with {total} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
