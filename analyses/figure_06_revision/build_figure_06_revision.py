#!/usr/bin/env python3
"""Build revised Figure 6 panels from checksum-frozen processed inputs.

The quantitative panels are reproducible.  The four representative microscopy
fields in panel E deliberately remain calibrated-image placeholders: the legacy
composite does not preserve raw fields or a pixel-to-length calibration, so this
script never invents a scale bar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, Polygon
from matplotlib.ticker import MaxNLocator
from scipy import stats

PROJECT = Path(__file__).resolve().parents[2]
SOURCE_PACKAGE = PROJECT / "src/flagella_repro"
loaded_package = sys.modules.get("flagella_repro")
if loaded_package is not None and SOURCE_PACKAGE not in [Path(item).resolve() for item in getattr(loaded_package, "__path__", [])]:
    for name in [item for item in sys.modules if item == "flagella_repro" or item.startswith("flagella_repro.")]:
        del sys.modules[name]
sys.path.insert(0, str(PROJECT / "src"))

from flagella_repro.theme import (  # noqa: E402
    DENSITY_MARKER_SIZE,
    KEY_SWATCH,
    MINIMUM_ON_PAGE_FONT_PT,
    PALETTE,
    POINT_MARKER_SIZE,
    SUMMARY_INK,
    apply_publication_style,
    get_condition_color,
    get_strain_style,
    marker_edge,
    panel_box_mm,
    panel_figsize,
    save_figure,
)

FIGURE_ID = "Figure_6"
NEUTRAL: dict[str, str] = PALETTE["neutral"]
# Outlines and rules reuse the shared neutral vocabulary; no panel-local hues.
LINE_GREY = NEUTRAL["reference"]
PLACEHOLDER_FILL = NEUTRAL["grid"]
GRID_COLOR = NEUTRAL["grid"]

# matplotlib sizes a scatter by area in points squared and a Line2D marker by
# diameter in points, so a line-drawn mark takes the square root of the theme
# size to print at the same physical size as its scatter counterpart.
POINT_MARKER_PT = float(np.sqrt(POINT_MARKER_SIZE))
DENSITY_MARKER_PT = float(np.sqrt(DENSITY_MARKER_SIZE))

INPUT_DIR = PROJECT / "data/processed/figure_06_revision"
SOURCE_DIR = PROJECT / "data/source_data/figure_06_revision"
BUILD_SOURCE = PROJECT / "build/source_data/Figure_6"
BUILD_STATS = PROJECT / "build/statistics/Figure_6"
BUILD_PANELS = PROJECT / "build/panels/Figure_6"
SCHEMATIC_SOURCE = PROJECT / "assets/schematics/competition_design/competition_scheme_source.pptx"

EXPECTED_SHA256 = {
    "figure_06A_ptet_motility_measurements.csv": "792d40886bd8c7b720db3a00f380a6f9f4e63d7eee0b605aa4d222f8e34bbc50",
    "figure_06B_ppro_motility_measurements.csv": "698161ef215086cc60fa61c18cb09122f0606c725a15d201027a11d291f07cf8",
    "figure_06C_hook_histogram_counts.csv": "18ecf2cddd647bc161071d39691aa856dc349be209be915133d6ea6b16b3d7a2",
    "figure_06E_competition_per_cell.csv": "0d823a3905b8259a0cd2888c46b5219bdfd63c9ab967a84c84c51244206b7b31",
    "competition_scheme_source.pptx": "fc70af99e68f06eba7a122121987f1024cdb34188bf6cb232ca79321409d56a9",
}

# The archived panel A table states the anhydrotetracycline dose in ng/µL, in
# both its ``Strain`` and its ``condition`` column.  That unit is wrong.  Marc
# Erhardt confirmed on 15 August 2026 that the series is ng/mL, the unit the
# panel axis, the figure legend and the July 2026 reference figure all print.
# The same correction was applied to Figure 1 on the same day.
#
# The copy under ``data/processed/`` stays byte-identical: ``data/`` is a
# read-only, out-of-git input tree, and this builder, its provenance record and
# ``config/artifacts.csv`` all pin that file by sha256.  The correction is
# therefore applied once, here, as the table enters the build.  Only the unit
# label changes; every dose number stays as recorded.
LEGACY_INDUCER_UNIT = " ng/ul"
CURRENT_INDUCER_UNIT = " ng/mL"

ANTC_ORDER = ["WT", "0 ng/mL AnTc", "0.25 ng/mL AnTc", "0.5 ng/mL AnTc", "1 ng/mL AnTc", "2 ng/mL AnTc", "4 ng/mL AnTc"]
PROMOTER_ORDER = ["WT", "Ppro1", "PproA", "PproB", "PproD"]
SPATIAL_ORDER = ["Center", "Middle", "Out"]
STRAIN_TO_ALIAS = {"EM16115": "PproA", "EM16309": "PproB"}
STRAIN_ALIAS_ORDER = ["PproA", "PproB"]
REGION_ORDER = [1, 2, 3, 4]
# Hook counts are shown on a discrete integer axis.  Counts of 11 and above
# collapse into the top bin, which the axis labels "11+".
HOOK_BINS = np.arange(0, 12)
HOOK_TOP_BIN = 11

# The panel-local font sizes for keys and notes.  A panel renders at its
# assembly box, so a declared point equals a printed point; every size here
# stays above the 6.0 pt on-page floor.
KEY_FONT_PT = 6.4
ANNOTATION_FONT_PT = MINIMUM_ON_PAGE_FONT_PT

# Panels A and B share one unit of analysis: the independent experiment.  In
# panel A that unit is the experimental day, which carries three or four
# soft-agar wells; in panel B it is the replicate, which carries a single
# measurement.  Both panels therefore draw the same three layers: every
# individual measurement as a light descriptive cloud, one mark per independent
# unit, and the mean with its 95 % confidence interval across those units.  The
# light layer only appears where a unit holds more than one measurement.
UNIT_SPREAD = 0.20
OBSERVATION_SPREAD = 0.05
OBSERVATION_ALPHA = 0.40

# Panel E shows the spread that the July bar chart showed, named correctly.
# The spread is across imaging fields (ROIs) of one competition experiment.
# It is not biological error, so the key names the unit and shows no test.
PANEL_E_SPREAD_LABEL = "±1 SD across fields"
INTERVAL_LABEL = "mean +/- 1 SD across imaging fields (ROIs) of one competition experiment"

# The recorded refusal, kept verbatim: the four microscopy fields of panel E
# stay placeholders until calibrated originals and an intended physical length
# arrive.  The panel shows this instead of a guessed scale bar, and the figure
# legend repeats it as a sentence.
PLACEHOLDER_NOTE = "Calibrated microscopy\nfield required"
PLACEHOLDER_SCALE_NOTE = "scale not inferred"
# One word per line, so the note fits inside a 13 mm placeholder box.
PLACEHOLDER_BOX_LABEL = PLACEHOLDER_NOTE.replace("\n", " ").replace(" ", "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_csv(name: str) -> pd.DataFrame:
    path = INPUT_DIR / name
    actual = sha256_file(path)
    if actual != EXPECTED_SHA256[name]:
        raise ValueError(f"checksum mismatch for {path}: {actual}")
    return pd.read_csv(path)


def state_inducer_unit(frame: pd.DataFrame) -> pd.DataFrame:
    """Return the table with the anhydrotetracycline dose stated in ng/mL.

    Two columns carry the unit inside a condition string, so the function
    rewrites every text column: ``0.25 ng/ul AnTc`` becomes
    ``0.25 ng/mL AnTc``.  Every dose number stays as recorded.

    >>> state_inducer_unit(pd.DataFrame({"condition": ["0.5 ng/ul AnTc"]})).condition[0]
    '0.5 ng/mL AnTc'
    """
    frame = frame.copy()
    for column in frame.columns:
        if frame[column].dtype != object:
            continue
        frame[column] = frame[column].map(
            lambda value: value.replace(LEGACY_INDUCER_UNIT, CURRENT_INDUCER_UNIT)
            if isinstance(value, str)
            else value
        )
    return frame


def t_interval(values: pd.Series, confidence: float = 0.95) -> tuple[float, float, float]:
    clean = pd.to_numeric(values, errors="raise").to_numpy(dtype=float)
    mean = float(clean.mean())
    if len(clean) < 2:
        return mean, np.nan, np.nan
    half = float(stats.t.ppf((1 + confidence) / 2, len(clean) - 1) * stats.sem(clean))
    return mean, mean - half, mean + half


def _write_table(frame: pd.DataFrame, panel: str, filename: str, *, statistics: bool = False) -> list[Path]:
    roots = [SOURCE_DIR / panel, BUILD_SOURCE / panel]
    if statistics:
        roots = [SOURCE_DIR / panel, BUILD_STATS / panel]
    outputs: list[Path] = []
    for root in roots:
        root.mkdir(parents=True, exist_ok=True)
        path = root / filename
        compression = {"method": "gzip", "compresslevel": 6, "mtime": 0} if path.suffix == ".gz" else None
        frame.to_csv(path, index=False, compression=compression)
        outputs.append(path)
    return outputs


def _jitter(n: int, width: float = 0.13) -> np.ndarray:
    return np.linspace(-width, width, n) if n > 1 else np.zeros(n)


def _draw_unit_condition(
    ax: plt.Axes,
    position: int,
    color: str,
    frame: pd.DataFrame,
    unit_column: str,
    value_column: str,
    summary_row: pd.Series,
) -> None:
    """Draw one condition of panel A or panel B with the shared geometry.

    The three layers are the same in both panels: every individual measurement
    as a light cloud around its own unit, one filled mark per independent unit,
    and the mean with its 95 % confidence interval across units.  A unit that
    holds a single measurement gets no cloud, because the measurement and the
    unit are then the same number.

    Example:
        >>> _draw_unit_condition(ax, 0, "#7F7F7F", wells, "day_repeat_id",
        ...                      "motility_value", summary.iloc[0])
    """
    edge_color, edge_width = marker_edge(color)
    units = sorted(frame[unit_column].astype(str).unique())
    offsets = _jitter(len(units), UNIT_SPREAD)
    unit_means = []
    for offset, unit in zip(offsets, units, strict=True):
        values = pd.to_numeric(
            frame.loc[frame[unit_column].astype(str) == unit, value_column], errors="raise"
        ).to_numpy(dtype=float)
        if len(values) > 1:
            ax.scatter(
                position + offset + _jitter(len(values), OBSERVATION_SPREAD),
                values,
                s=DENSITY_MARKER_SIZE,
                color=color,
                alpha=OBSERVATION_ALPHA,
                edgecolor=edge_color,
                linewidth=edge_width,
                zorder=2,
            )
        unit_means.append(float(values.mean()))
    ax.scatter(
        position + offsets,
        np.asarray(unit_means),
        s=POINT_MARKER_SIZE,
        color=color,
        edgecolor=edge_color,
        linewidth=edge_width,
        zorder=3,
    )
    mean = float(summary_row["mean"])
    ax.errorbar(
        position,
        mean,
        yerr=[[mean - float(summary_row["ci95_low"])], [float(summary_row["ci95_high"]) - mean]],
        fmt="D",
        ms=POINT_MARKER_PT,
        markerfacecolor=SUMMARY_INK,
        markeredgecolor=SUMMARY_INK,
        markeredgewidth=0.55,
        color=SUMMARY_INK,
        capsize=1.5,
        lw=0.7,
        zorder=4,
    )


def _unit_panel_key(fig: plt.Figure, unit_label: str, *, has_observations: bool) -> None:
    """Name every mark of a motility panel in a key of short names."""
    handles = []
    if has_observations:
        handles.append(
            Line2D([], [], marker="o", ls="none", color=KEY_SWATCH, markersize=DENSITY_MARKER_PT,
                   markeredgewidth=0.0, alpha=OBSERVATION_ALPHA, label="Well measurement")
        )
    handles.extend(
        [
            Line2D([], [], marker="o", ls="none", color=KEY_SWATCH, markersize=POINT_MARKER_PT,
                   markeredgewidth=0.0, label=unit_label),
            Line2D([], [], marker="D", ls="none", markerfacecolor=SUMMARY_INK,
                   markeredgecolor=SUMMARY_INK, markeredgewidth=0.55,
                   markersize=POINT_MARKER_PT, label="Mean ± 95% CI"),
        ]
    )
    fig.legend(
        handles=handles,
        frameon=False,
        loc="outside lower center",
        ncols=1,
        handlelength=1.0,
        handletextpad=0.4,
        labelspacing=0.15,
        borderpad=0.0,
        borderaxespad=0.0,
        fontsize=KEY_FONT_PT,
    )


def _summary_rows(frame: pd.DataFrame, order: list[str], unit: str, value: str) -> pd.DataFrame:
    rows = []
    for condition in order:
        values = frame.loc[frame.condition == condition, value]
        mean, low, high = t_interval(values)
        rows.append(
            {
                "condition": condition,
                "mean": mean,
                "ci95_low": low,
                "ci95_high": high,
                "n_independent_units": int(frame.loc[frame.condition == condition, unit].nunique()),
                "independent_unit": unit,
            }
        )
    return pd.DataFrame(rows)


def panel_a(*, check_only: bool = False) -> dict[str, object]:
    raw = state_inducer_unit(checked_csv("figure_06A_ptet_motility_measurements.csv"))
    day = raw.groupby(["condition", "day_repeat_id"], as_index=False).agg(
        relative_motility=("motility_value", "mean"),
        n_wells=("motility_value", "size"),
    )
    day["condition"] = pd.Categorical(day.condition, ANTC_ORDER, ordered=True)
    day = day.sort_values(["condition", "day_repeat_id"]).reset_index(drop=True)
    day["condition"] = day.condition.astype("object")
    summary = _summary_rows(day, ANTC_ORDER, "day_repeat_id", "relative_motility")
    assert summary.set_index("condition").loc["WT", "n_independent_units"] == 2
    assert set(summary.loc[summary.condition != "WT", "n_independent_units"]) == {4}
    if check_only:
        return {"days": len(day), "conditions": len(summary)}
    well_columns = ["condition", "day_repeat_id", "replicate_id", "motility_value", "source_file"]
    wells = raw[well_columns].copy()
    wells["condition"] = pd.Categorical(wells.condition, ANTC_ORDER, ordered=True)
    wells = wells.sort_values(["condition", "day_repeat_id", "replicate_id"]).reset_index(drop=True)
    wells["condition"] = wells.condition.astype("object")
    _write_table(wells, "A", "Figure_6A_well_measurements.csv")
    _write_table(day, "A", "Figure_6A_day_level_points.csv")
    _write_table(summary, "A", "Figure_6A_summary_95ci.csv", statistics=True)

    # Render at the exact assembly slot size so a declared point equals a
    # printed point; the assembler then only converts points to millimetres.
    fig, ax = plt.subplots(figsize=panel_figsize(FIGURE_ID, "A"), constrained_layout=True)
    labels = ["WT", "0", "0.25", "0.5", "1", "2", "4"]
    colors = [get_strain_style("TH9677")["color"]] + [
        get_condition_color("antc", value) for value in [0, 0.25, 0.5, 1, 2, 4]
    ]
    for pos, (condition, color) in enumerate(zip(ANTC_ORDER, colors, strict=True)):
        _draw_unit_condition(
            ax,
            pos,
            color,
            wells.loc[wells.condition == condition],
            "day_repeat_id",
            "motility_value",
            summary.loc[summary.condition == condition].iloc[0],
        )
    ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right", rotation_mode="anchor")
    ax.set_xlabel("AnTc (ng/mL)", labelpad=1.5)
    ax.set_ylabel("Relative soft-agar\nmotility (%)", labelpad=1.5)
    ax.tick_params(axis="both", pad=1.5)
    ax.set_xlim(-0.6, len(labels) - 0.4)
    ax.set_ylim(0, max(130, float(wells.motility_value.max()) * 1.08))
    ax.axhline(100, color=NEUTRAL["technical"], lw=0.65, zorder=0)
    _unit_panel_key(fig, "Day mean (analysis unit)", has_observations=True)
    save_figure(fig, BUILD_PANELS / "A/Figure_6A")
    return {"days": len(day), "conditions": len(summary)}


def panel_b(*, check_only: bool = False) -> dict[str, object]:
    points = checked_csv("figure_06B_ppro_motility_measurements.csv")
    points = points.rename(columns={"motility_value": "relative_motility"})
    summary = _summary_rows(points, PROMOTER_ORDER, "replicate_id", "relative_motility")
    wt = points.loc[points.condition == "WT", ["replicate_id", "relative_motility"]].rename(columns={"relative_motility": "wt"})
    tests = []
    for condition in PROMOTER_ORDER[1:]:
        other = points.loc[points.condition == condition, ["replicate_id", "relative_motility"]].rename(columns={"relative_motility": "other"})
        paired = wt.merge(other, on="replicate_id", validate="one_to_one")
        delta = paired.other - paired.wt
        effect, low, high = t_interval(delta)
        statistic, pvalue = stats.ttest_rel(paired.other, paired.wt)
        tests.append({"comparison": f"{condition} - WT", "mean_paired_difference": effect, "ci95_low": low, "ci95_high": high, "paired_t": statistic, "exact_p_value": pvalue, "n_pairs": len(paired)})
    tests_frame = pd.DataFrame(tests)
    assert set(summary.n_independent_units) == {6}
    if check_only:
        return {"points": len(points), "pairs_per_comparison": 6}
    _write_table(points, "B", "Figure_6B_replicate_points.csv")
    _write_table(summary, "B", "Figure_6B_summary_95ci.csv", statistics=True)
    _write_table(tests_frame, "B", "Figure_6B_paired_statistics.csv", statistics=True)

    colors = [get_strain_style("TH9677")["color"]] + [get_condition_color("promoter", item) for item in PROMOTER_ORDER[1:]]
    fig, ax = plt.subplots(figsize=panel_figsize(FIGURE_ID, "B"), constrained_layout=True)
    for pos, (condition, color) in enumerate(zip(PROMOTER_ORDER, colors, strict=True)):
        _draw_unit_condition(
            ax,
            pos,
            color,
            points.loc[points.condition == condition],
            "replicate_id",
            "relative_motility",
            summary.loc[summary.condition == condition].iloc[0],
        )
    ax.set_xticks(range(len(PROMOTER_ORDER)), PROMOTER_ORDER, rotation=45, ha="right", rotation_mode="anchor")
    ax.set_xlabel("flhDC promoter", labelpad=1.5)
    ax.set_ylabel("Relative soft-agar\nmotility (%)", labelpad=1.5)
    ax.tick_params(axis="both", pad=1.5)
    ax.axhline(100, color=NEUTRAL["technical"], lw=0.65, zorder=0)
    ax.set_xlim(-0.6, len(PROMOTER_ORDER) - 0.4)
    ax.set_ylim(0, 195)
    # Each replicate carries one measurement, so the measurement and the
    # independent unit are the same number and the panel draws one mark for it.
    _unit_panel_key(fig, "Replicate (analysis unit)", has_observations=False)
    save_figure(fig, BUILD_PANELS / "B/Figure_6B")
    return {"points": len(points), "pairs_per_comparison": 6}


def _expanded_hook_cells(histogram: pd.DataFrame) -> pd.DataFrame:
    expanded = histogram.loc[histogram.index.repeat(histogram.count_cells)].copy()
    expanded["cell_index"] = expanded.groupby("condition").cumcount() + 1
    return expanded[["condition", "cell_index", "hook_count", "source_file"]].reset_index(drop=True)


def panel_c(*, check_only: bool = False) -> dict[str, object]:
    histogram = checked_csv("figure_06C_hook_histogram_counts.csv")
    cells = _expanded_hook_cells(histogram)
    audit = cells.groupby("condition", as_index=False).agg(mean_hooks=("hook_count", "mean"), median_hooks=("hook_count", "median"), q1=("hook_count", lambda x: x.quantile(0.25)), q3=("hook_count", lambda x: x.quantile(0.75)), n_cells=("hook_count", "size"))
    audit["condition"] = pd.Categorical(audit.condition, SPATIAL_ORDER, ordered=True)
    audit = audit.sort_values("condition").reset_index(drop=True)
    expected = {"Center": 0.4396887159533074, "Middle": 2.657587548638132, "Out": 3.9221789883268483}
    for condition, value in expected.items():
        actual = float(audit.loc[audit.condition == condition, "mean_hooks"].iloc[0])
        assert np.isclose(actual, value, atol=1e-12)
    assert set(audit.n_cells) == {257}
    if check_only:
        return {"cells": len(cells), "means": expected}
    _write_table(cells, "C", "Figure_6C_cell_points.csv")
    _write_table(audit, "C", "Figure_6C_numeric_audit.csv", statistics=True)

    # Hook count is an integer, so a kernel density smears the zero class.  The
    # panel therefore uses the ``discrete_count`` geometry of Figure 1C, 1D and
    # 1H and of Figure 7E-G: one mark per observed integer whose half-width
    # follows the square root of its cell frequency, individual cell dots where
    # a count is carried by twelve cells or fewer, and a black bar at the mean.
    # These cells come from one plate, so there is no replicate layer and the
    # bar is the mean of the cells themselves.
    color = get_strain_style("TH9677")["color"]
    edge_color, edge_width = marker_edge(color)
    axis_max = int(cells.hook_count.max())
    fig, ax = plt.subplots(figsize=panel_figsize(FIGURE_ID, "C"), constrained_layout=True)
    fig.get_layout_engine().set(w_pad=0.012, h_pad=0.012, wspace=0.0, hspace=0.0)
    for pos, condition in enumerate(SPATIAL_ORDER):
        subset = cells.loc[cells.condition == condition]
        table = subset.groupby("hook_count", as_index=False).size()
        table = table.rename(columns={"size": "frequency"})
        max_frequency = max(1.0, float(table.frequency.max()))
        for row in table.itertuples(index=False):
            value = float(row.hook_count)
            frequency = float(row.frequency)
            half_width = 0.04 + 0.24 * np.sqrt(frequency / max_frequency)
            if frequency <= 12:
                xs = np.linspace(pos - half_width, pos + half_width, int(frequency))
                ax.scatter(xs, np.full(len(xs), value), s=DENSITY_MARKER_SIZE, color=color,
                           alpha=0.25, edgecolor=edge_color, linewidth=edge_width)
            else:
                ax.hlines(value, pos - half_width, pos + half_width, color=color,
                          alpha=0.72, linewidth=1.15)
        mean = float(subset.hook_count.mean())
        deviation = float(subset.hook_count.std(ddof=1))
        ax.hlines(mean, pos - 0.32, pos + 0.32, color=SUMMARY_INK, linewidth=0.9, zorder=3)
        ax.text(pos, axis_max + 0.4, f"{mean:.2f}±{deviation:.2f}\nN={len(subset)}", ha="center",
                va="bottom", linespacing=1.05, fontsize=ANNOTATION_FONT_PT)
    ax.set_xticks(range(len(SPATIAL_ORDER)), SPATIAL_ORDER)
    ax.set_xlabel("Soft-agar plate position", labelpad=1.5)
    ax.set_ylabel("Hooks per cell", labelpad=1.5)
    ax.tick_params(axis="both", pad=1.5)
    ax.set_xlim(-0.6, len(SPATIAL_ORDER) - 0.4)
    # The annotation block sits above the tallest count, so the upper limit
    # adds room for two lines of 6 pt text.
    ax.set_ylim(-0.7, axis_max + max(3.2, 0.22 * axis_max))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6, steps=[1, 2, 2.5, 5, 10]))
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.5, alpha=0.8)
    ax.set_axisbelow(True)
    fig.legend(
        handles=[
            Line2D([], [], color=color, linewidth=1.2, label="Cell-count frequency"),
            Line2D([], [], color=SUMMARY_INK, linewidth=1.2, label="Mean of all cells"),
        ],
        frameon=False,
        loc="outside lower center",
        ncols=1,
        handlelength=1.2,
        handletextpad=0.5,
        labelspacing=0.15,
        borderpad=0.0,
        borderaxespad=0.0,
        fontsize=KEY_FONT_PT,
    )
    save_figure(fig, BUILD_PANELS / "C/Figure_6C")
    return {"cells": len(cells), "means": expected}


def read_schematic_source_text() -> list[str]:
    if sha256_file(SCHEMATIC_SOURCE) != EXPECTED_SHA256["competition_scheme_source.pptx"]:
        raise ValueError("competition schematic source checksum mismatch")
    with ZipFile(SCHEMATIC_SOURCE) as archive:
        root = ET.fromstring(archive.read("ppt/slides/slide1.xml"))
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    return [node.text for node in root.findall(".//a:t", ns) if node.text]


def _draw_flask(ax: plt.Axes, x: float, y: float, color: str, label: str, *, width: float = 11.0, height: float = 12.0) -> None:
    """Draw one culture flask centred on ``(x, y)``; sizes are millimetres."""
    half, neck = width / 2, width * 0.19
    top, shoulder, base = y + height * 0.52, y + height * 0.12, y - height * 0.48
    outline = [(x - neck, top), (x + neck, top), (x + neck, shoulder), (x + half, base), (x - half, base), (x - neck, shoulder)]
    ax.add_patch(Polygon(outline, closed=True, facecolor=NEUTRAL["background"], edgecolor=LINE_GREY, lw=0.7))
    ax.add_patch(Ellipse((x, base + height * 0.13), width * 0.82, height * 0.20, facecolor=color, edgecolor="none", alpha=0.45))
    ax.text(x, base - 1.1, label, ha="center", va="top")


def _draw_cell(ax: plt.Axes, x: float, y: float, color: str, angle: float) -> None:
    ax.add_patch(Ellipse((x, y), 2.8, 1.2, angle=angle, facecolor=color, edgecolor=NEUTRAL["text"], lw=0.3))


def _arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float]) -> None:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=6, lw=0.7, color=LINE_GREY, shrinkA=0, shrinkB=0))


def panel_d(*, check_only: bool = False) -> dict[str, object]:
    text_runs = read_schematic_source_text()
    collapsed = "".join(text_runs).replace(" ", "")
    assert all(region in text_runs for region in ["R1", "R2", "R3", "R4"])
    assert "PproA" in collapsed and "PproB" in collapsed
    elements = pd.DataFrame(
        [
            {"element": "culture_1", "source_text": "PproA-fhlDC", "canonical_text": "PproA-flhDC", "action": "correct source label transposition"},
            {"element": "culture_2", "source_text": "PproB-fhlDC", "canonical_text": "PproB-flhDC", "action": "correct source label transposition"},
            {"element": "competition", "source_text": "mixed cells", "canonical_text": "1:1 competition", "action": "redrawn as editable vector"},
            {"element": "plate", "source_text": "soft-agar plate", "canonical_text": "soft-agar expansion", "action": "redrawn as editable vector"},
            *[{"element": region, "source_text": region, "canonical_text": region, "action": "retained"} for region in ["R1", "R2", "R3", "R4"]],
        ]
    )
    if check_only:
        return {"source_sha256": sha256_file(SCHEMATIC_SOURCE), "text_runs": text_runs}
    _write_table(elements, "D", "Figure_6D_schematic_elements.csv")

    color_a = get_condition_color("promoter", "PproA")
    color_b = get_condition_color("promoter", "PproB")
    # The schematic is laid out directly in millimetres of the assembly slot,
    # so every label carries the theme point size onto the printed page.
    width_mm, height_mm = panel_box_mm(FIGURE_ID, "D")
    fig = plt.figure(figsize=panel_figsize(FIGURE_ID, "D"))
    ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_xlim(0, width_mm)
    ax.set_ylim(0, height_mm)
    ax.axis("off")

    # Step 1: two separately grown cultures.
    _draw_flask(ax, 11, 57, color_a, "PproA-flhDC")
    _draw_flask(ax, 11, 40, color_b, "PproB-flhDC")

    # Step 2: mix the cultures one to one.
    _arrow(ax, (21.5, 42), (33, 42))
    ax.text(28, 46.2, "combine 1:1", ha="center", va="center")
    ax.add_patch(Circle((52, 42), 9.0, facecolor=NEUTRAL["background"], edgecolor=LINE_GREY, lw=0.7))
    offsets = [(-4.2, 2.6), (0.5, 4.0), (3.7, -0.8), (-1.6, -3.2), (4.5, 3.4), (-4.8, -2.1)]
    for index, (dx, dy) in enumerate(offsets):
        _draw_cell(ax, 52 + dx, 42 + dy, color_a if index % 2 == 0 else color_b, 25 if index % 3 else -30)
    ax.text(52, 53.6, "mixed population", ha="center", va="center")

    # Step 3: spot the mixture on soft agar.  The elbow carries the flow from
    # the upper row down into the lower row of the schematic.
    ax.plot([52, 52, 16], [32.5, 27, 27], color=LINE_GREY, lw=0.7, solid_capstyle="butt", zorder=1)
    _arrow(ax, (16, 27.4), (16, 24.0))
    ax.text(34.5, 29.6, "spot on soft agar", ha="center", va="center")
    # The rings mark how far the population has expanded, nothing else.  They
    # were a green-yellow halo with a salmon core, which reads as "the plate
    # centre is PproA".  The schematic makes no such claim: strain identity per
    # region is measured in panel E.  The rings are therefore neutral greys that
    # darken inward, and no ring carries a strain colour.
    for radius, ring, alpha in [
        (9.5, NEUTRAL["grid"], 0.9),
        (6.9, NEUTRAL["technical"], 0.9),
        (3.8, NEUTRAL["reference"], 0.75),
    ]:
        ax.add_patch(Circle((16, 13.5), radius, facecolor=ring, edgecolor=LINE_GREY if radius == 9.5 else "none", lw=0.6, alpha=alpha))
    ax.text(16, 1.8, "soft-agar expansion", ha="center", va="center")

    # Step 4: sample four regions of the expansion front.  The regions stay
    # dashed outlines: no calibrated microscopy field backs them.
    _arrow(ax, (27, 13.5), (41.5, 13.5))
    ax.text(37, 20.6, "sample the\nexpansion front", ha="center", va="center", linespacing=1.15)
    for index, x in enumerate(np.linspace(48, 78, 4), start=1):
        ax.add_patch(Circle((x, 13.5), 4.1, facecolor=PLACEHOLDER_FILL, edgecolor=NEUTRAL["text"], lw=0.6, linestyle=(0, (2, 1.4))))
        ax.text(x, 13.5, f"R{index}", ha="center", va="center")
    ax.text(63, 5.0, "quantify strain identity\nand hooks per cell", ha="center", va="center", linespacing=1.15)
    save_figure(fig, BUILD_PANELS / "D/Figure_6D")
    return {"source_sha256": sha256_file(SCHEMATIC_SOURCE), "text_runs": text_runs}


def _competition_cells() -> pd.DataFrame:
    raw = checked_csv("figure_06E_competition_per_cell.csv")
    numeric = ["fluor_em16309", "fluor_em16115", "foci_number"]
    valid = raw[numeric].notna().all(axis=1) & (raw.fluor_em16309 != raw.fluor_em16115)
    cells = raw.loc[valid].copy()
    cells["strain"] = np.where(cells.fluor_em16309 > cells.fluor_em16115, "EM16309", "EM16115")
    cells["strain_alias"] = cells.strain.map(STRAIN_TO_ALIAS)
    cells["hook_count"] = pd.to_numeric(cells.foci_number, errors="raise").round().astype(int)
    return cells


def _roi_hook_fractions(cells: pd.DataFrame) -> pd.DataFrame:
    """Return, per imaging field, the fraction of cells with one strain and hook bin.

    The denominator is every assigned cell of the imaging field (ROI), both
    strains together.  A strain's fractions therefore sum to that strain's
    share of the region, not to one.  Hook counts of 11 and above collapse
    into the top bin.

    Example:
        >>> table = _roi_hook_fractions(_competition_cells())
        >>> float(table.fraction_of_roi_cells.max()) <= 1.0
        True
    """
    frame = cells[["region_id", "roi_id", "strain_alias", "hook_count"]].copy()
    frame["hook_bin"] = np.clip(frame.hook_count, 0, HOOK_TOP_BIN)
    fields = frame[["region_id", "roi_id"]].drop_duplicates()
    grid = fields.merge(pd.DataFrame({"strain_alias": STRAIN_ALIAS_ORDER}), how="cross").merge(
        pd.DataFrame({"hook_bin": HOOK_BINS}), how="cross"
    )
    keys = ["region_id", "roi_id", "strain_alias", "hook_bin"]
    counts = frame.groupby(keys, as_index=False).size().rename(columns={"size": "n_cells"})
    field_keys = ["region_id", "roi_id"]
    sizes = frame.groupby(field_keys, as_index=False).size()
    totals = sizes.rename(columns={"size": "n_cells_in_roi"})
    table = grid.merge(counts, on=keys, how="left").fillna({"n_cells": 0})
    table = table.merge(totals, on=["region_id", "roi_id"], validate="many_to_one")
    table["n_cells"] = table.n_cells.astype(int)
    table["fraction_of_roi_cells"] = table.n_cells / table.n_cells_in_roi
    return table.sort_values(keys).reset_index(drop=True)


def _roi_fraction_summary(table: pd.DataFrame) -> pd.DataFrame:
    """Return the mean and sample standard deviation of the ROI fractions.

    The spread is the sample standard deviation (ddof = 1) across the imaging
    fields of one region.  It describes field-to-field variation inside a
    single competition experiment, not biological variation.
    """
    summary = table.groupby(["region_id", "strain_alias", "hook_bin"], as_index=False).agg(
        mean_fraction=("fraction_of_roi_cells", "mean"),
        sd_fraction=("fraction_of_roi_cells", "std"),
        n_rois=("fraction_of_roi_cells", "size"),
    )
    summary["interval"] = INTERVAL_LABEL
    return summary.sort_values(["region_id", "strain_alias", "hook_bin"]).reset_index(drop=True)


def _check_roi_summary(
    summary: pd.DataFrame,
    rois_per_region: dict[int, int],
    shares: dict[str, float],
) -> None:
    """Guard the reproduced spread against the values traced from the raw table."""
    targets = {
        (1, "PproA", 0): (0.52, 0.06),
        (1, "PproA", 1): (0.24, 0.05),
        (1, "PproA", 2): (0.09, 0.02),
        (1, "PproA", 3): (0.03, 0.01),
        (3, "PproB", 0): (0.05, 0.10),
        (3, "PproB", 1): (0.07, 0.03),
        (3, "PproB", 2): (0.14, 0.04),
        (3, "PproB", 3): (0.18, 0.04),
    }
    indexed = summary.set_index(["region_id", "strain_alias", "hook_bin"])
    for key, (mean, sd) in targets.items():
        row = indexed.loc[key]
        assert np.isclose(float(row.mean_fraction), mean, atol=5e-3), key
        assert np.isclose(float(row.sd_fraction), sd, atol=5e-3), key
    assert rois_per_region == {1: 18, 2: 13, 3: 13, 4: 12}
    expected_shares = {
        "1_PproA": 0.910, "1_PproB": 0.090,
        "2_PproA": 0.775, "2_PproB": 0.225,
        "3_PproA": 0.209, "3_PproB": 0.791,
        "4_PproA": 0.000, "4_PproB": 1.000,
    }
    for key, value in expected_shares.items():
        assert np.isclose(shares[key], value, atol=5e-4), key


def panel_e(*, check_only: bool = False) -> dict[str, object]:
    cells = _competition_cells()
    audit = cells.groupby(["region_id", "strain_alias"], as_index=False).agg(n_cells=("hook_count", "size"), mean_hooks=("hook_count", "mean"), sd_hooks=("hook_count", "std"), n_rois=("roi_id", "nunique"))
    composition = cells.groupby(["region_id", "strain_alias"], as_index=False).size().rename(columns={"size": "n_cells"})
    composition["fraction_region"] = composition.n_cells / composition.groupby("region_id").n_cells.transform("sum")
    r1 = composition[(composition.region_id == 1) & (composition.strain_alias == "PproA")].iloc[0]
    r4 = composition[(composition.region_id == 4) & (composition.strain_alias == "PproB")].iloc[0]
    r4_hooks = audit[(audit.region_id == 4) & (audit.strain_alias == "PproB")].iloc[0]
    assert np.isclose(r1.fraction_region, 4392 / 4817, atol=1e-12)
    assert np.isclose(r4.fraction_region, 1.0, atol=1e-12)
    assert np.isclose(r4_hooks.mean_hooks, 5.810344827586207, atol=1e-12)

    roi_fractions = _roi_hook_fractions(cells)
    summary = _roi_fraction_summary(roi_fractions)
    field_counts = cells.groupby("region_id").roi_id.nunique()
    rois_per_region = {int(region): int(count) for region, count in field_counts.items()}
    share_series = summary.groupby(["region_id", "strain_alias"]).mean_fraction.sum()
    shares = {
        f"{int(region)}_{alias}": float(share) for (region, alias), share in share_series.items()
    }
    _check_roi_summary(summary, rois_per_region, shares)
    result = {
        "assigned_cells": len(cells),
        "r1_pproa_fraction": float(r1.fraction_region),
        "r4_pprob_mean_hooks": float(r4_hooks.mean_hooks),
        "rois_per_region": rois_per_region,
        "strain_share_per_region": {key: round(value, 4) for key, value in shares.items()},
        "displayed_interval": INTERVAL_LABEL,
    }
    if check_only:
        return result
    _write_table(cells[["region_id", "roi_id", "cell_index", "strain", "strain_alias", "hook_count", "source_file"]], "E", "Figure_6E_assigned_cell_points.csv")
    _write_table(roi_fractions, "E", "Figure_6E_roi_hook_fractions.csv")
    _write_table(summary, "E", "Figure_6E_roi_fraction_mean_sd.csv")
    _write_table(audit, "E", "Figure_6E_numeric_audit.csv", statistics=True)
    _write_table(composition, "E", "Figure_6E_region_composition.csv", statistics=True)

    color_a = get_condition_color("promoter", "PproA")
    color_b = get_condition_color("promoter", "PproB")
    fig = plt.figure(figsize=panel_figsize(FIGURE_ID, "E"))
    grid = fig.add_gridspec(2, 4, height_ratios=[0.58, 1.0])
    indexed = summary.set_index(["region_id", "strain_alias"]).sort_index()
    for col, region in enumerate(REGION_ORDER):
        image_ax = fig.add_subplot(grid[0, col])
        image_ax.set_facecolor(PLACEHOLDER_FILL)
        # The box states what is missing.  It never states a length.
        image_ax.text(0.5, 0.5, PLACEHOLDER_BOX_LABEL, ha="center", va="center",
                      color=NEUTRAL["text"], fontsize=ANNOTATION_FONT_PT, linespacing=1.15)
        image_ax.set_title(f"Region {region}", pad=2.0)
        image_ax.set_xticks([])
        image_ax.set_yticks([])
        for spine in image_ax.spines.values():
            spine.set_visible(True)
            spine.set_color(NEUTRAL["text"])
            spine.set_linestyle((0, (2.5, 1.6)))
            spine.set_linewidth(0.65)

        ax = fig.add_subplot(grid[1, col])
        # The two strains sit on the same integer hook bin, so a small offset
        # keeps the two error bars apart where the distributions cross.
        for alias, color, offset in [("PproA", color_a, -0.17), ("PproB", color_b, 0.17)]:
            rows = indexed.loc[(region, alias)].sort_values("hook_bin")
            mean = rows.mean_fraction.to_numpy(dtype=float)
            spread = np.nan_to_num(rows.sd_fraction.to_numpy(dtype=float))
            position = rows.hook_bin.to_numpy(dtype=float) + offset
            # The region means take the theme density size.  The former 1.5 pt
            # marker printed at about 1.8 pt squared, below any print threshold.
            ax.errorbar(position, mean, yerr=spread, fmt="-o", ms=DENSITY_MARKER_PT, lw=0.7,
                        color=color, elinewidth=0.5, capsize=0.8, capthick=0.5, label=alias)
        ax.set_xlim(-0.6, 11.6)
        ax.set_ylim(0, 0.62)
        ax.set_xticks([0, 4, 8, 11], ["0", "4", "8", "11+"])
        ax.set_yticks([0.0, 0.2, 0.4, 0.6])
        if col == 0:
            ax.set_ylabel("Fraction of all\ncells in region", linespacing=1.15)
        else:
            ax.set_yticklabels([])
    fig.subplots_adjust(left=0.175, right=0.975, bottom=0.215, top=0.95, hspace=0.22, wspace=0.26)
    fig.supxlabel("Hooks per cell", y=0.115, va="center")
    # The key names every mark in short names.  The sentences that explain the
    # single experiment and the imaging fields live in the figure legend.
    handles = [
        Line2D([], [], marker="o", ms=DENSITY_MARKER_PT, lw=0.7, color=color, label=alias)
        for alias, color in [("PproA", color_a), ("PproB", color_b)]
    ]
    handles.append(
        Line2D([], [], marker="|", ms=5.0, ls="none", color=KEY_SWATCH, markeredgewidth=1.1,
               label=PANEL_E_SPREAD_LABEL)
    )
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.012), ncols=3,
               frameon=False, handlelength=1.1, columnspacing=1.2, handletextpad=0.4,
               fontsize=KEY_FONT_PT)
    save_figure(fig, BUILD_PANELS / "E/Figure_6E")
    return result


def write_provenance(results: dict[str, object]) -> None:
    inputs = []
    for path in [
        Path(__file__),
        INPUT_DIR / "figure_06A_ptet_motility_measurements.csv",
        INPUT_DIR / "figure_06B_ppro_motility_measurements.csv",
        INPUT_DIR / "figure_06C_hook_histogram_counts.csv",
        INPUT_DIR / "figure_06E_competition_per_cell.csv",
        SCHEMATIC_SOURCE,
    ]:
        inputs.append({"relative_path": path.relative_to(PROJECT).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    outputs = []
    paths = [*BUILD_PANELS.rglob("Figure_6*.*"), *BUILD_SOURCE.rglob("*"), *BUILD_STATS.rglob("*")]
    for path in sorted(item for item in paths if item.is_file()):
        outputs.append({"relative_path": path.relative_to(PROJECT).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    document = {
        "schema_version": "1.0.0",
        "figure_id": "Figure_6_revision",
        "generated_at_utc": datetime(2026, 8, 12, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        "command": [".venv/bin/python", "analyses/figure_06_revision/build_figure_06_revision.py"],
        "backend": "Python 3.12",
        "inputs": inputs,
        "software": {
            "python": platform.python_version(),
            "matplotlib": matplotlib.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "parameters": {
            "backend": "Python 3.12",
            "scientific_values_are_in_source_data": True,
            "stars_displayed": False,
        },
        "random_seeds": {},
        "results": results,
        "outputs": outputs,
        "limitations": [
            f"Panel E microscopy placeholders are intentional: raw calibrated fields and crop metadata have not been supplied; {PLACEHOLDER_SCALE_NOTE}.",
            "Panel E ROI identities are retained, but biological-repeat identities are not present in the migrated table.",
            "The competition experiment has no biological replication: it is one experiment. Panel E ROIs are imaging fields inside a plate region, so the plotted mean and standard deviation describe field-to-field variation only.",
            "Panel C pools cells from one soft-agar plate, so its discrete-count display carries no replicate layer and stays descriptive.",
            "Panels A and B share the independent experiment as their unit of analysis. Panel A "
            "has two experimental days for WT and four for every AnTc condition, an asymmetry "
            "that day means alone do not show.",
        ],
    }
    (Path(__file__).parent / "provenance.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    for panel, result in results.items():
        panel_inputs = {
            "A": [INPUT_DIR / "figure_06A_ptet_motility_measurements.csv"],
            "B": [INPUT_DIR / "figure_06B_ppro_motility_measurements.csv"],
            "C": [INPUT_DIR / "figure_06C_hook_histogram_counts.csv"],
            "D": [SCHEMATIC_SOURCE],
            "E": [INPUT_DIR / "figure_06E_competition_per_cell.csv"],
        }[panel]
        panel_limitations = [
            "The canonical run starts from migrated processed measurement tables, not raw acquisitions.",
            "The revised panel has not yet passed visual acceptance against the July reference.",
        ]
        if panel == "A":
            panel_limitations.append(
                "The unit of analysis is the experimental day. WT was measured on two days "
                "(R1, R4) and every AnTc condition on four, so the WT interval rests on two "
                "units. Day averaging hides that asymmetry, which is why every well is drawn."
            )
            panel_limitations.append(
                "Each value is normalised to the same-day WT mean, so both WT day means are "
                "100 % by construction and the WT confidence interval has zero width. The WT "
                "wells show the true well-to-well spread of the reference."
            )
        if panel == "B":
            panel_limitations.append(
                "The unit of analysis is the independent replicate, which carries a single "
                "measurement, so the measurement and the unit are the same number and the "
                "panel draws one mark for both."
            )
        if panel == "D":
            panel_limitations.append(
                f"Microscopy regions are intentional placeholders: raw calibrated fields, crop metadata and the intended scale-bar length have not been supplied; {PLACEHOLDER_SCALE_NOTE}."
            )
            panel_limitations.append(
                "The soft-agar rings of the schematic are neutral greys that mark expansion distance only; the schematic makes no claim about which strain occupies which ring."
            )
        if panel == "C":
            panel_limitations.append(
                "The panel pools 257 cells per position from one soft-agar plate; there is no replicate layer, so the drawn mean is descriptive and supports no inference between plate positions."
            )
        if panel == "E":
            panel_limitations.append(
                "ROI identities are retained, but biological-repeat identities are not present in the migrated table; the display is descriptive."
            )
            panel_limitations.append(
                "The competition experiment has no biological replication: it is one experiment. The ROIs are imaging fields inside a plate region (18, 13, 13, 12 fields for regions 1 to 4), so the plotted mean and standard deviation describe field-to-field variation, not biological error."
            )
        panel_doc = {
            "schema_version": "1.0.0",
            "panel_id": f"F6_{panel}",
            "status": "partial_reproduction",
            "generated_at_utc": document["generated_at_utc"],
            "command": [".venv/bin/python", "analyses/figure_06_revision/build_figure_06_revision.py", "--panel", panel],
            "backend": document["backend"],
            "inputs": [{"relative_path": path.relative_to(PROJECT).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in [Path(__file__), *panel_inputs]],
            "outputs": [item for item in outputs if f"/Figure_6/{panel}/" in item["relative_path"] or f"Figure_6{panel}_" in item["relative_path"]],
            "software": document["software"],
            "parameters": document["parameters"],
            "random_seeds": document["random_seeds"],
            "results": result,
            "limitations": panel_limitations,
        }
        metadata = Path(__file__).parent / f"panel_{panel.lower()}/metadata"
        metadata.mkdir(parents=True, exist_ok=True)
        (metadata / "provenance.json").write_text(json.dumps(panel_doc, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", choices=["A", "B", "C", "D", "E", "all"], default="all")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    apply_publication_style()
    builders = {"A": panel_a, "B": panel_b, "C": panel_c, "D": panel_d, "E": panel_e}
    selected = list(builders) if args.panel == "all" else [args.panel]
    results = {panel: builders[panel](check_only=args.check) for panel in selected}
    if not args.check:
        write_provenance(results)
    print(json.dumps(results, indent=2, default=float))


if __name__ == "__main__":
    main()
