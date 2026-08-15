"""Panel annotations that must stay readable in the assembled supplements.

Two defects were found on the rendered 14 August 2026 figures:

* Supplementary Figure 3 printed the panel letter on top of the effect block,
  so eight of the nine panels read "Apaired-unit ratio ...".
* Supplementary Figure 4 carried no spatial reference at all.

The 14 August 2026 restyle of Supplementary Figure 3 moved the effect numbers
into a header above each medium's group.  The clearance guard therefore reads
the band the panel letter covers instead of one named text block, and a second
guard holds every number of the statistics table on the panel.

These tests read the built panel SVGs, so they guard what a reader sees.
"""

from __future__ import annotations

import csv
import importlib.util
import re
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from flagella_repro.theme import MINIMUM_ON_PAGE_FONT_PT

ROOT = Path(__file__).parents[1]
PT_PER_MM = 72.0 / 25.4
TRANSLATE_RE = re.compile(r"translate\(\s*([-0-9.eE]+)[\s,]+([-0-9.eE]+)")
FONT_SIZE_RE = re.compile(r"font-size:\s*([0-9.]+)px")
# The micro sign and the Greek letter mu look alike; accept either.
SCALE_LABEL_RE = re.compile(r"^20\s*[µμ]m$")
SVG_TEXT = "{http://www.w3.org/2000/svg}text"


def _load(relative: str, name: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _assembler():
    return _load("analyses/assembly/assemble_svg.py", "flagella_svg_assembler")


def _texts(path: Path) -> list[ET.Element]:
    return list(ET.parse(path).getroot().iter(SVG_TEXT))


def _translate_mm(node: ET.Element) -> tuple[float, float] | None:
    """Return the offset of one matplotlib text node, in millimetres.

    The panel SVG viewBox is in points, and matplotlib positions a text it draws
    on the figure with a ``translate`` transform.  Tick labels and axis labels
    carry ``x``/``y`` attributes instead, and the function returns ``None`` for
    them.  The y offset runs down from the top of the panel.
    """
    match = TRANSLATE_RE.search(node.get("transform", ""))
    if not match:
        return None
    return (float(match.group(1)) / PT_PER_MM, float(match.group(2)) / PT_PER_MM)


def _fixed(value: float) -> str:
    """Format one effect number as the builder prints it.

    Example:
        >>> _fixed(-0.0004)
        '0.00'
    """
    text = f"{value:.2f}"
    return "0.00" if text == "-0.00" else text


def _panel_svg(figure: str, label: str, stem: str) -> Path:
    path = ROOT / "build" / "panels" / figure / label / f"{stem}_{label}.svg"
    if not path.is_file():
        pytest.skip(f"{path} is not built")
    return path


def test_panel_letter_reach_matches_the_assembler_geometry() -> None:
    """The assembler states how far the panel letter reaches into the panel."""
    assembler = _assembler()
    assert assembler.PANEL_LABEL_OFFSET_MM == 2.0
    assert assembler.PANEL_LABEL_FONT_SIZE_MM == 5.2
    assert assembler.PANEL_LABEL_REACH_MM == pytest.approx(2.0456)


def _declared_constant(relative: str, name: str) -> float:
    """Return one module-level float constant, without importing the builder.

    A builder sets global matplotlib state when it is imported, so the tests
    read the declaration instead.
    """
    source = (ROOT / relative).read_text(encoding="utf-8")
    match = re.search(rf"^{name}\s*=\s*([0-9.]+)$", source, re.MULTILINE)
    assert match, name
    return float(match.group(1))


def test_supplementary_figure_3_indent_clears_the_panel_letter() -> None:
    """The declared indent leaves air between the letter and the effect block."""
    clearance = _declared_constant(
        "analyses/supplementary_03/build_s3.py", "PANEL_LETTER_CLEARANCE_MM"
    )
    assert clearance > _assembler().PANEL_LABEL_REACH_MM


@pytest.mark.parametrize("label", list("ABCDEFGHI"))
def test_supplementary_figure_3_top_band_clears_the_panel_letter(label: str) -> None:
    """No text in the band the panel letter occupies starts inside the letter.

    The 14 August 2026 restyle moved the effect numbers out of the panel corner
    and into a header above each medium's group, so the guard no longer names
    one text block.  It reads the band the letter covers and holds whatever the
    builder draws there.
    """
    path = _panel_svg("Supplementary_Figure_3", label, "S3")
    reach = _assembler().PANEL_LABEL_REACH_MM
    band = _declared_constant("analyses/supplementary_03/build_s3.py", "PANEL_LETTER_BAND_MM")
    placed = [(node, _translate_mm(node)) for node in _texts(path)]
    inside = [(node, offset) for node, offset in placed if offset and offset[1] < band]
    assert inside, label
    for node, offset in inside:
        assert offset[0] > reach, (label, node.text)


@pytest.mark.parametrize("label", list("ABCDEFGHI"))
def test_supplementary_figure_3_panel_states_both_paired_effects(label: str) -> None:
    """Every number the withdrawn corner block printed is still on the panel.

    The restyle replaced the three-line block with one header per medium.  The
    estimate, both interval bounds and the unit count of both media must still
    print, and they must be the numbers the statistics table records.
    """
    table = (
        ROOT
        / "build"
        / "statistics"
        / "Supplementary_Figure_3"
        / label
        / f"S3_{label}_paired_effect_statistics.csv"
    )
    if not table.is_file():
        pytest.skip(f"{table} is not built")
    path = _panel_svg("Supplementary_Figure_3", label, "S3")
    printed = {(node.text or "").strip() for node in _texts(path)}
    with table.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["medium"] for row in rows} == {"agarose", "liquid"}, label
    for row in rows:
        estimate, low, high = (
            _fixed(float(row[key])) for key in ("estimate", "ci95_low", "ci95_high")
        )
        assert estimate in printed, (label, row["medium"], estimate)
        assert f"({low}, {high})" in printed, (label, row["medium"], low, high)
        assert f"{row['n_paired_units']} units" in printed, (label, row["medium"])


@pytest.mark.parametrize("label", list("ABCDEF"))
def test_supplementary_figure_4_carries_a_legible_scale_bar(label: str) -> None:
    """Every trajectory map states its scale, at a size a reader can print."""
    assert _declared_constant("analyses/supplementary_04/build_s4.py", "SCALE_BAR_UM") == 20.0
    path = _panel_svg("Supplementary_Figure_4", label, "S4")
    labels = [node for node in _texts(path) if SCALE_LABEL_RE.match((node.text or "").strip())]
    assert len(labels) == 1, label
    match = FONT_SIZE_RE.search(labels[0].get("style", ""))
    assert match, labels[0].get("style")
    assert float(match.group(1)) >= MINIMUM_ON_PAGE_FONT_PT, label
