"""Shared publication theme and semantic color vocabulary.

All plotting code should request styles by biological identity rather than
copying color literals.  SVG and PDF output retain editable text.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import yaml


def _collection_root() -> Path:
    candidates = [Path(__file__).resolve(), Path.cwd().resolve()]
    for candidate in candidates:
        for parent in (candidate, *candidate.parents):
            if (parent / "config" / "palette.yaml").is_file():
                return parent
    raise FileNotFoundError("cannot locate config/palette.yaml from package or working directory")


COLLECTION_ROOT = _collection_root()
PALETTE_PATH = COLLECTION_ROOT / "config" / "palette.yaml"


def _load_palette() -> dict[str, Any]:
    loaded = yaml.safe_load(PALETTE_PATH.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"palette must be a mapping: {PALETTE_PATH}")
    return loaded


PALETTE: dict[str, Any] = _load_palette()
SECTOR_COLORS: dict[str, str] = dict(PALETTE["sectors"])
STRAIN_STYLES: dict[str, dict[str, str]] = {
    str(key): dict(value) for key, value in PALETTE["strain_styles"].items()
}
ANTC_COLORS: dict[str, str] = {str(key): value for key, value in PALETTE["antc"].items()}
PROMOTER_COLORS: dict[str, str] = dict(PALETTE["promoter"])
MUTANT_COLORS: dict[str, str] = dict(PALETTE["mutants"])
ALLOCATION_COLORS: dict[str, str] = {str(key): value for key, value in PALETTE["allocation"].items()}

# One ink for every summary mark, and one swatch for a key that stands for a
# concept rather than a strain.
SUMMARY_INK: str = PALETTE["neutral"]["summary"]
KEY_SWATCH: str = PALETTE["neutral"]["key_swatch"]

# Marker policy.  Sizes are matplotlib ``s`` in points squared.  Every panel
# renders at its assembly box, so a size declared here is the printed size.
POINT_MARKER_SIZE = 20.0
DENSITY_MARKER_SIZE = 9.0
# A fill this light disappears on white without help.  Such marks take a thin
# edge drawn in a darkened version of their own fill, never a black rim, so the
# mark stays inside its own colour family.
LIGHT_FILL_LUMINANCE = 0.75
LIGHT_FILL_EDGE_WIDTH = 0.3

# Stacked-segment policy.  Two sector colours that are far apart in normal
# vision can land on the same colour under red-green colour blindness.  Under
# the Machado, Oliveira & Fernandes (2009) deuteranomaly simulation at severity
# 100, the CAM02-UCS distance between Lpb #1B9E77 and Fla #E7298A falls from
# 61.7 to 3.7, which is below the discrimination threshold; Rib against Etc
# falls from 25.9 to 6.3, and Etc against Tra from 33.9 to 9.7.  Lpb and Fla are
# neighbours in the sector stack, so a deuteranope cannot see where one segment
# ends and the next begins.
#
# Every stacked bar therefore draws a thin separator in the background colour
# between its segments.  The separator restores every boundary at once and
# changes no sector colour, which is what the collaborator asked for.  The
# background is at least CAM02-UCS 24.4 from every sector under the same
# simulation, so the line reads against all eight.
#
# The width is 0.3 pt.  A panel renders at its assembly box, so that is 0.106 mm
# on the page: above the 0.1 mm minimum stroke that print production holds, and
# below the width at which the line starts to read as a data element.  It costs
# 0.3 pt of the thinnest segment that a reader can see today, which is Tra at
# about 1.5 pt.
SEGMENT_SEPARATOR_COLOR: str = PALETTE["neutral"]["background"]
SEGMENT_SEPARATOR_WIDTH = 0.3


def _relative_luminance(color: str) -> float:
    """Return the WCAG relative luminance of a hex colour, 0 (black) to 1."""
    red, green, blue = (int(color.lstrip("#")[index : index + 2], 16) / 255 for index in (0, 2, 4))

    def channel(value: float) -> float:
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)


def marker_edge(fill: str) -> tuple[str, float]:
    """Return the (edgecolor, linewidth) a data marker of this fill should use.

    Markers carry no border by default: a white rim eats into the mark and a
    black rim competes with the data. Only a near-white fill gets an edge, and
    that edge is a darkened version of the fill itself.

    Example:
        >>> marker_edge("#DE2D26")
        ('none', 0.0)
    """
    if _relative_luminance(fill) < LIGHT_FILL_LUMINANCE:
        return ("none", 0.0)
    red, green, blue = (int(fill.lstrip("#")[index : index + 2], 16) for index in (0, 2, 4))
    darker = "#" + "".join(f"{int(channel * 0.55):02X}" for channel in (red, green, blue))
    return (darker, LIGHT_FILL_EDGE_WIDTH)

# Nature Communications states the printed column widths: "A single column width
# measures 88 mm and a double column width measures 180 mm."  The Nature branded
# research journals artwork guide repeats the pair as "1-column width: 88 mm" and
# "2-column width: 180 mm" for original research content.  Both pages were read on
# 14 August 2026.  The collection declared 183 mm and 89 mm before, which no
# publisher page supports.
#
# The 3 mm came out of the outer page margins, not out of the panels.  Every
# assembly row keeps a 3.5 mm margin on each side now, down from 5.0 mm.  Every
# panel box and every gutter keeps its former size.  Panels therefore render at an
# unchanged scale, so no on-page font size moved.  A uniform 180/183 rescale would
# have shrunk all 61 panels and pushed marginal text below the 6 pt floor.
DOUBLE_COLUMN_MM = 180.0
SINGLE_COLUMN_MM = 88.0
MM_PER_INCH = 25.4
FIXED_OUTPUT_DATE = datetime(2026, 8, 12, tzinfo=UTC)

# Every panel must render at the exact physical size of its slot in the figure
# assembly.  The assembler scales each panel by min(box / viewBox), so a panel
# drawn on a larger canvas is shrunk and its text shrinks with it.  Rendering at
# the declared box size keeps that scale at 1.0, so a point size requested here
# is the same point size on the printed page.
BASE_FONT_PT = 8.0
TICK_FONT_PT = 7.0
MINIMUM_ON_PAGE_FONT_PT = 6.0


def mm_to_inches(value_mm: float) -> float:
    return float(value_mm) / MM_PER_INCH


@lru_cache(maxsize=1)
def _panel_boxes() -> dict[tuple[str, str], tuple[float, float]]:
    """Map (figure_id, panel_label) to that panel's assembly box in millimetres."""
    boxes: dict[tuple[str, str], tuple[float, float]] = {}
    for path in sorted((COLLECTION_ROOT / "config").glob("assembly_*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        figure_id = str(document["figure_id"])
        for panel in document.get("panels", []):
            label = panel.get("label")
            if not label:
                continue
            boxes[(figure_id, str(label))] = (float(panel["width"]), float(panel["height"]))
    if not boxes:
        raise FileNotFoundError("no assembly configuration defines panel boxes")
    return boxes


def panel_box_mm(figure_id: str, panel_label: str) -> tuple[float, float]:
    """Return the width and height in millimetres of a panel's assembly slot."""
    try:
        return _panel_boxes()[(str(figure_id), str(panel_label))]
    except KeyError as error:
        raise KeyError(f"no assembly box for {figure_id} panel {panel_label}") from error


def panel_figsize(figure_id: str, panel_label: str) -> tuple[float, float]:
    """Return the matplotlib figsize in inches that renders a panel at 1:1.

    Example:
        >>> fig, ax = plt.subplots(figsize=panel_figsize("Figure_2", "A"))
    """
    width_mm, height_mm = panel_box_mm(figure_id, panel_label)
    return (mm_to_inches(width_mm), mm_to_inches(height_mm))


def apply_publication_style(*, has_seaborn: bool = True) -> None:
    """Apply the single canonical manuscript plotting style."""
    if has_seaborn:
        try:
            import seaborn as sns

            sns.set_theme(style="ticks", context="paper")
        except ImportError:
            pass
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            # One typeface, with metric-compatible substitutes for hosts that
            # lack it.  Helvetica and Nimbus Sans share Arial's metrics, so a
            # substitution does not move any label.
            "font.sans-serif": ["Arial", "Helvetica", "Nimbus Sans", "Liberation Sans"],
            "font.size": BASE_FONT_PT,
            "axes.labelsize": BASE_FONT_PT,
            "axes.titlesize": BASE_FONT_PT,
            "xtick.labelsize": TICK_FONT_PT,
            "ytick.labelsize": TICK_FONT_PT,
            "legend.fontsize": TICK_FONT_PT,
            "legend.title_fontsize": TICK_FONT_PT,
            "axes.linewidth": 0.65,
            "lines.linewidth": 1.0,
            "xtick.major.width": 0.65,
            "ytick.major.width": 0.65,
            "xtick.major.size": 2.5,
            "ytick.major.size": 2.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            # Seaborn leaves spines and grid at its own defaults, which are the
            # only inks in the collection that trace to no palette entry.
            "axes.edgecolor": PALETTE["neutral"]["text"],
            "grid.color": PALETTE["neutral"]["grid"],
            "figure.facecolor": PALETTE["neutral"]["background"],
            "savefig.facecolor": PALETTE["neutral"]["background"],
            "text.color": PALETTE["neutral"]["text"],
            "axes.labelcolor": PALETTE["neutral"]["text"],
            "xtick.color": PALETTE["neutral"]["text"],
            "ytick.color": PALETTE["neutral"]["text"],
            "svg.fonttype": "none",
            "svg.hashsalt": "flagella-manuscript-revision-2026-08-12",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def get_sector_color(sector: str) -> str:
    try:
        return SECTOR_COLORS[sector]
    except KeyError as error:
        raise KeyError(f"unknown protein sector: {sector!r}") from error


def get_strain_style(strain: str) -> dict[str, str]:
    """Return a defensive copy so callers cannot mutate the shared theme."""
    try:
        return deepcopy(STRAIN_STYLES[str(strain)])
    except KeyError as error:
        raise KeyError(f"unknown strain: {strain!r}") from error


def get_condition_color(family: str, condition: str | float | int) -> str:
    palettes: Mapping[str, Mapping[str, str]] = {
        "antc": ANTC_COLORS,
        "promoter": PROMOTER_COLORS,
        "mutant": MUTANT_COLORS,
        "allocation": ALLOCATION_COLORS,
    }
    if family not in palettes:
        raise KeyError(f"unknown condition family: {family!r}")
    key = str(condition)
    try:
        return palettes[family][key]
    except KeyError as error:
        raise KeyError(f"unknown {family} condition: {condition!r}") from error


def save_figure(
    figure: plt.Figure,
    stem: str | Path,
    *,
    dpi: int = 300,
    close: bool = True,
) -> list[Path]:
    """Write deterministic, editable SVG/PDF plus review PNG."""
    output_stem = Path(stem)
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    outputs = [output_stem.with_suffix(suffix) for suffix in (".svg", ".pdf", ".png")]
    creator = "flagella-manuscript-reproducibility"
    figure.savefig(
        outputs[0],
        metadata={"Creator": creator, "Date": FIXED_OUTPUT_DATE.isoformat()},
    )
    figure.savefig(
        outputs[1],
        metadata={
            "Creator": creator,
            "CreationDate": FIXED_OUTPUT_DATE,
            "ModDate": FIXED_OUTPUT_DATE,
        },
    )
    figure.savefig(outputs[2], dpi=dpi, metadata={"Software": creator})
    if close:
        plt.close(figure)
    return outputs
