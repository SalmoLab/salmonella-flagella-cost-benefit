#!/usr/bin/env python3
"""Regenerate Supplementary Figure 3 paired motility panels.

The panels follow Figure 7A-C.  One panel holds one metric and one strain pair.
Inside the panel the two media stand side by side as two groups of paired
violins, so a reader sees how liquid differs from agarose.  The earlier version
put both media on one strain tick and delivered that comparison as three lines
of text in the panel corner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator

from flagella_repro.theme import (
    DENSITY_MARKER_SIZE,
    MINIMUM_ON_PAGE_FONT_PT,
    PALETTE,
    POINT_MARKER_SIZE,
    SUMMARY_INK,
    apply_publication_style,
    get_strain_style,
    marker_edge,
    panel_box_mm,
    panel_figsize,
    save_figure,
)

apply_publication_style()
# Panel-specific salt keeps this builder's SVG element ids stable and distinct
# from the ids emitted by the sibling builders.
matplotlib.rcParams["svg.hashsalt"] = "flagella-supplementary-04"


PROJECT = Path(__file__).resolve().parents[2]
INPUT = PROJECT / "data/processed/supplementary_03/motility_competition_paired_measurements.csv"
SOURCE_DIR = PROJECT / "data/source_data/supplementary_03"
BUILD_STATS = PROJECT / "build/statistics/Supplementary_Figure_3"
PANEL_ROOT = PROJECT / "analyses/supplementary_03"
FIGURE_ID = "Supplementary_Figure_3"
PAIRS = [("WT", "PproA"), ("WT", "PproB"), ("PproA", "PproB")]
# Paired experimental units per strain pair, in the column order of ``PAIRS``.
# Every metric of a column reads the same paired set, so one count per column
# and medium pins the whole grid.
EXPECTED_UNITS = [
    {"agarose": 18, "liquid": 16},
    {"agarose": 18, "liquid": 18},
    {"agarose": 18, "liquid": 16},
]
# Axis labels are wrapped for the 55 x 56 mm assembly slot.  The quantity, the
# symbol and the unit are unchanged; only the line breaks are new.
#
# The median effective-diffusivity row was withdrawn on 12 August 2026.  It read
# from the same input file as Figure 7 and repeated Figure 7A-C with a different
# within-unit summary.  Three metrics against three strain pairs give panels A-I.
#
# A metric on a log axis takes a paired ratio; a bounded fraction takes a paired
# difference.  Both are computed on the paired experimental unit, never on
# pooled trajectories.
METRICS = [
    ("speed_med", "Median speed\n(µm/s)", True, "ratio"),
    ("swim_frac", "Swimming fraction", False, "difference"),
    ("tau", "Directional\npersistence (s)", True, "ratio"),
]
PANELS = "ABCDEFGHI"
# One shape vocabulary for medium across the whole motility story, shared with
# Figure 7A-D: filled circle is agarose, open square is liquid.
MEDIUMS = [("agarose", "o", True), ("liquid", "s", False)]
# Figure 7A-C names the plotted strains by construct id and reads the shared
# strain styles.  Supplementary Figure 3 now reads the same three entries, so
# both figures take their colours from one place.  The three colours are
# unchanged: WT #7F7F7F, PproA #FC9272, PproB #DE2D26.
PHENOTYPE_STYLE_IDS = {"WT": "TH5861", "PproA": "EM9661", "PproB": "EM9660"}
GRID_COLOR = PALETTE["neutral"]["grid"]
NEUTRAL_LINE = PALETTE["neutral"]["technical"]
BACKGROUND = PALETTE["neutral"]["background"]
# Progressively denser decade subdivisions.  The first entry that puts at least
# three labelled ticks inside the view wins, so a narrow log range still gets
# readable tick labels and a wide one does not get crowded.
LOG_SUBS = (
    (1.0,),
    (1.0, 3.0),
    (1.0, 2.0, 5.0),
    (1.0, 1.5, 2.0, 3.0, 5.0, 7.0),
)

# Panel geometry, in millimetres of the 55 x 48 mm assembly box.  The axes are
# placed by hand, as in Figure 7A-C: constrained_layout would size each panel's
# left margin from its own tick labels, so the three panels of a row would not
# share one baseline.
#
# The box was 55 x 56 mm while every panel printed the contrast wording under
# its axes.  That wording moved to the legend and to the effect table, and the
# 8 mm it cost each panel came out of the figure: Supplementary Figure 3 now
# stands 166 mm tall, under the 185 mm the publisher allows for a caption of
# fewer than 300 words.  The plotted area keeps 29.6 mm of height, which is the
# row height of Figure 7A-C.
AXES_LEFT_MM = 13.0
AXES_RIGHT_MARGIN_MM = 1.5
AXES_BOTTOM_MM = 6.0
AXES_TOP_MARGIN_MM = 12.4
# Two groups of two strains, with a gap between the media, exactly as Figure 7A-C
# places them.  The gap is what turns the medium comparison into a picture.
GROUP_POSITIONS = {"agarose": (0.0, 1.0), "liquid": (2.5, 3.5)}
XLIM = (-0.7, 4.2)
# One horizontal offset per paired unit, used at both strains, so every joining
# line starts and ends on its own two markers.
UNIT_OFFSET = 0.20
VIOLIN_WIDTH = 0.80
VIOLIN_ALPHA = 0.28
PAIR_LINE_WIDTH = 0.35
OPEN_MARKER_EDGE_WIDTH = 0.45
# The summary diamond with its 95 % interval is the collection's summary mark;
# Figure 4, Figure 5 and Figure 6 draw the same diamond in the same ink.
POINT_MARKER_PT = float(np.sqrt(POINT_MARKER_SIZE))
SUMMARY_EDGE_WIDTH = 0.55
SUMMARY_CAPSIZE = 1.5
SUMMARY_LINE_WIDTH = 0.7
# The header above a group and the contrast line below the axes.  Both print at
# the tick size, which keeps a margin above the 6 pt floor.
ANNOTATION_FONT_PT = 6.5
assert ANNOTATION_FONT_PT >= MINIMUM_ON_PAGE_FONT_PT
ANNOTATION_LINESPACING = 1.15
# The assembler prints the panel letter 2 mm left of the panel box in 5.2 mm
# bold Arial, so the letter reaches about 2.05 mm into the panel.  Nothing this
# builder draws in the top band of a panel may start left of this.  The check is
# no longer a matter of one text block: ``_assert_clear_of_panel_letter`` reads
# the rendered extent of every text and fails the build if one of them reaches
# into the letter.
PANEL_LETTER_CLEARANCE_MM = 2.8
assert AXES_LEFT_MM >= PANEL_LETTER_CLEARANCE_MM
# Height of the band the panel letter occupies, measured from the panel top.
PANEL_LETTER_BAND_MM = 5.2
# The paired bootstrap resamples paired experimental units with replacement.
# The seed is derived from the panel and the medium, so ``--panel A`` and
# ``--panel all`` write the same numbers.
BOOTSTRAP_SEED = 20260812
BOOTSTRAP_ITERATIONS = 10_000


def _strain_color(strain: str) -> str:
    return get_strain_style(PHENOTYPE_STYLE_IDS[strain])["color"]


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact(path: Path, rows: int | None = None) -> dict[str, object]:
    value: dict[str, object] = {
        "relative_path": path.relative_to(PROJECT).as_posix(),
        "sha256": _sha(path),
        "bytes": path.stat().st_size,
    }
    if rows is not None:
        value["rows"] = rows
    return value


def _long(data: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for left, right in PAIRS:
        for metric, *_ in METRICS:
            cols = ["metadata_key", "pair", "medium", f"{metric}_{left}", f"{metric}_{right}"]
            if not set(cols).issubset(data.columns):
                continue
            part = (
                data[cols]
                .rename(
                    columns={f"{metric}_{left}": "left_value", f"{metric}_{right}": "right_value"}
                )
                .copy()
            )
            part["left_value"] = pd.to_numeric(part.left_value, errors="coerce")
            part["right_value"] = pd.to_numeric(part.right_value, errors="coerce")
            part = part[np.isfinite(part.left_value) & np.isfinite(part.right_value)]
            part["left_label"] = left
            part["right_label"] = right
            part["metric"] = metric
            parts.append(part)
    return pd.concat(parts, ignore_index=True)


def _plotted(values: np.ndarray, is_log: bool) -> np.ndarray:
    """Return the quantity the axes carries.

    A ratio metric is drawn as log10 on a linear axis and the ticks print the
    original unit, as in Figure 7A-C.  A matplotlib log axis would estimate the
    violin density in the original unit and then stretch it, which would misdraw
    the distribution.

    Example:
        >>> _plotted(np.array([1.0, 100.0]), True)
        array([0., 2.])
    """
    return np.log10(values) if is_log else np.asarray(values, dtype=float)


def _row_limits(long: pd.DataFrame, metric: str, is_log: bool) -> tuple[float, float]:
    """Return the axis limits one metric row shares across its three panels.

    The three panels of a row read one axis, so a reader compares the strain
    pairs directly instead of re-reading three different scales.  The limits
    hold every plotted unit of the row, because a violin states the distribution
    of the same units and a clipped point would contradict it.

    Example:
        >>> frame = pd.DataFrame(
        ...     {"metric": ["m", "m"], "left_value": [1.0, 2.0], "right_value": [3.0, 4.0]}
        ... )
        >>> low, high = _row_limits(frame, "m", False)
        >>> round(low, 3), round(high, 3)
        (0.79, 4.21)
    """
    sub = long[long.metric == metric]
    values = sub[["left_value", "right_value"]].to_numpy(dtype=float).ravel()
    values = values[np.isfinite(values)]
    if is_log:
        values = _plotted(values[values > 0], True)
    low, high = float(values.min()), float(values.max())
    pad = max(0.07 * (high - low), 0.02)
    return low - pad, high + pad


def _log_ticks(low: float, high: float) -> list[float]:
    """Return original-unit ticks inside a log10 view range.

    Example:
        >>> _log_ticks(math.log10(9.0), math.log10(40.0))
        [10.0, 20.0, 50.0]
    """
    inside: list[float] = []
    for subs in LOG_SUBS:
        candidates: list[float] = []
        decade = math.floor(low)
        while decade <= math.ceil(high):
            candidates.extend(sub * 10.0**decade for sub in subs)
            decade += 1
        inside = sorted(value for value in candidates if low <= math.log10(value) <= high)
        if len(inside) >= 3:
            return inside
    return inside


def _paired_effect(
    one: pd.DataFrame, kind: str, seed_key: tuple[int, int]
) -> dict[str, float | int]:
    """Return the paired effect of one medium with a bootstrap 95 % CI.

    The unit of analysis is the paired experimental unit: one ``metadata_key``
    carries both strains in the same medium, so the contrast is taken within a
    unit and the bootstrap resamples units, never trajectories.  A ratio metric
    is averaged as a log contrast and reported on the original scale; a bounded
    fraction is averaged as a difference.

    Example:
        >>> frame = pd.DataFrame({"left_value": [1.0, 2.0], "right_value": [2.0, 4.0]})
        >>> round(_paired_effect(frame, "ratio", (0, 0))["estimate"], 6)
        2.0
    """
    left = one.left_value.to_numpy(dtype=float)
    right = one.right_value.to_numpy(dtype=float)
    contrast = np.log(right) - np.log(left) if kind == "ratio" else right - left
    count = contrast.size
    rng = np.random.default_rng([BOOTSTRAP_SEED, *seed_key])
    draws = contrast[rng.integers(0, count, size=(BOOTSTRAP_ITERATIONS, count))].mean(axis=1)
    estimate = float(contrast.mean())
    low, high = (float(value) for value in np.quantile(draws, [0.025, 0.975]))
    if kind == "ratio":
        estimate, low, high = (float(np.exp(value)) for value in (estimate, low, high))
    return {
        "estimate": estimate,
        "ci95_low": low,
        "ci95_high": high,
        "n_paired_units": int(count),
    }


def panel_effects(sub: pd.DataFrame, panel: str, kind: str) -> pd.DataFrame:
    """Return the paired effect of every medium of one panel, agarose first.

    The ``contrast`` column names what the estimate divides or subtracts.  The
    panel no longer prints that wording, so the table has to carry it.
    """
    index = ord(panel) - ord("A")
    _, col = divmod(index, 3)
    left, right = PAIRS[col]
    rows = []
    for medium_index, (medium, *_) in enumerate(MEDIUMS):
        one = sub[sub.medium == medium]
        rows.append(
            {
                "panel_id": f"S3_{panel}",
                "medium": medium,
                "effect": kind,
                "contrast": _contrast(left, right, kind),
                **_paired_effect(one, kind, (index, medium_index)),
            }
        )
    return pd.DataFrame(rows)


def _fixed(value: float) -> str:
    """Format one effect number, without printing a rounded zero as negative.

    Example:
        >>> _fixed(-0.0004)
        '0.00'
    """
    text = f"{value:.2f}"
    return "0.00" if text == "-0.00" else text


def _contrast(left: str, right: str, kind: str) -> str:
    """Return what the annotated estimate divides or subtracts.

    Example:
        >>> _contrast("WT", "PproA", "ratio")
        'PproA/WT'
    """
    return f"{right}/{left}" if kind == "ratio" else f"{right} - {left}"


def _group_header(medium: str, filled: bool, row: pd.Series) -> str:
    """Return the four-line header that stands above one medium's group.

    The header names the fill convention where the convention is used, states
    the paired effect of that medium and states how many paired units carry it.
    Those are the numbers the withdrawn corner block used to print.

    The estimate and its interval take one line each.  On one line the widest
    header, ``-0.27 (-0.31, -0.22)``, is 19.1 mm wide and leaves only 1.6 mm of
    white between the two media, so the two blocks read as one run of numbers.
    """
    return (
        f"{medium} ({'filled' if filled else 'open'})\n"
        f"{_fixed(row.estimate)}\n"
        f"({_fixed(row.ci95_low)}, {_fixed(row.ci95_high)})\n"
        f"{int(row.n_paired_units)} units"
    )


def _summary_bounds(row: pd.Series, kind: str, reference: float) -> tuple[float, float, float]:
    """Place the paired effect and its interval on the plotted axis.

    The paired estimate is a ratio or a difference, which the metric axis does
    not carry by itself.  Anchoring it at the reference strain's plotted mean
    does carry it: for a ratio metric the plotted quantity is log10, so the
    paired log ratio is an offset; for the bounded fraction the paired
    difference is an offset already.  The anchored estimate therefore lands
    exactly on the second strain's own plotted mean, and the bar states the
    interval that the paired bootstrap produced.

    Example:
        >>> row = pd.Series({"estimate": 2.0, "ci95_low": 1.0, "ci95_high": 4.0})
        >>> [round(value, 3) for value in _summary_bounds(row, "ratio", 1.0)]
        [1.301, 1.0, 1.602]
    """
    if kind == "ratio":
        shift = [math.log10(float(row[key])) for key in ("estimate", "ci95_low", "ci95_high")]
    else:
        shift = [float(row[key]) for key in ("estimate", "ci95_low", "ci95_high")]
    return (reference + shift[0], reference + shift[1], reference + shift[2])


def _draw_group(
    ax: plt.Axes,
    one: pd.DataFrame,
    strains: tuple[str, str],
    positions: tuple[float, float],
    marker: str,
    filled: bool,
    is_log: bool,
) -> tuple[float, float]:
    """Draw one medium's paired violins and return the two plotted group means.

    One marker is one paired experimental unit.  A thin line joins the two
    strains measured in the same ``metadata_key``, so the reader sees the
    within-unit contrast that the bootstrap actually resamples.
    """
    values = {
        strains[0]: _plotted(one.left_value.to_numpy(dtype=float), is_log),
        strains[1]: _plotted(one.right_value.to_numpy(dtype=float), is_log),
    }
    for strain, position in zip(strains, positions, strict=True):
        column = values[strain]
        if column.size >= 3 and float(np.ptp(column)) > 0.0:
            parts = ax.violinplot(
                [column], positions=[position], widths=VIOLIN_WIDTH, showextrema=False
            )
            body = parts["bodies"][0]
            body.set_facecolor(_strain_color(strain))
            body.set_edgecolor("none")
            body.set_alpha(VIOLIN_ALPHA)
            body.set_zorder(0)
    offsets = np.linspace(-UNIT_OFFSET, UNIT_OFFSET, len(one))
    for offset, first, second in zip(offsets, values[strains[0]], values[strains[1]], strict=True):
        ax.plot(
            [positions[0] + offset, positions[1] + offset],
            [first, second],
            color=NEUTRAL_LINE,
            lw=PAIR_LINE_WIDTH,
            zorder=1,
        )
    for strain, position in zip(strains, positions, strict=True):
        fill = _strain_color(strain)
        edge, edge_width = marker_edge(fill)
        ax.scatter(
            position + offsets,
            values[strain],
            s=DENSITY_MARKER_SIZE,
            marker=marker,
            facecolor=fill if filled else BACKGROUND,
            edgecolor=edge if filled else fill,
            linewidths=edge_width if filled else OPEN_MARKER_EDGE_WIDTH,
            zorder=2,
        )
    return (float(values[strains[0]].mean()), float(values[strains[1]].mean()))


def _draw_summary(
    ax: plt.Axes, position: float, center: float, bounds: tuple[float, float] | None = None
) -> None:
    """Draw one summary diamond, with its 95 % interval when it carries one.

    The first strain of a group is the reference the paired contrast divides by,
    so its diamond carries no bar of its own.
    """
    error = None if bounds is None else [[center - bounds[0]], [bounds[1] - center]]
    ax.errorbar(
        position,
        center,
        yerr=error,
        fmt="D",
        ms=POINT_MARKER_PT,
        markerfacecolor=SUMMARY_INK,
        markeredgecolor=SUMMARY_INK,
        markeredgewidth=SUMMARY_EDGE_WIDTH,
        color=SUMMARY_INK,
        capsize=SUMMARY_CAPSIZE,
        lw=SUMMARY_LINE_WIDTH,
        zorder=4,
    )


def _mm_axes(
    fig: plt.Figure,
    box_mm: tuple[float, float],
    rectangle_mm: tuple[float, float, float, float],
) -> plt.Axes:
    """Add one axes placed in millimetres of the panel's assembly box.

    Example:
        >>> figure = plt.figure(figsize=(55 / 25.4, 56 / 25.4))
        >>> axes = _mm_axes(figure, (55.0, 56.0), (13.0, 9.6, 40.5, 35.0))
    """
    width_mm, height_mm = box_mm
    left, bottom, width, height = rectangle_mm
    return fig.add_axes((left / width_mm, bottom / height_mm, width / width_mm, height / height_mm))


def _assert_clear_of_panel_letter(fig: plt.Figure, box_mm: tuple[float, float]) -> None:
    """Fail the build if any text in the top band reaches into the panel letter.

    The assembler prints the letter over the top left corner of the panel.  The
    check reads the rendered extent of every text this builder drew, so it holds
    whatever the layout becomes.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    height_mm = box_mm[1]
    for text in fig.findobj(plt.Text):
        if not text.get_text().strip() or not text.get_visible():
            continue
        extent = text.get_window_extent(renderer)
        left_mm = extent.x0 / fig.dpi * 25.4
        top_mm = height_mm - extent.y1 / fig.dpi * 25.4
        if top_mm < PANEL_LETTER_BAND_MM and left_mm < PANEL_LETTER_CLEARANCE_MM:
            raise AssertionError(f"{text.get_text()!r} reaches into the panel letter")


def _draw_panel(long: pd.DataFrame, panel: str, effects: pd.DataFrame) -> Path:
    index = ord(panel) - ord("A")
    row_index, col = divmod(index, 3)
    metric, ylabel, is_log, kind = METRICS[row_index]
    left, right = PAIRS[col]
    sub = long[(long.metric == metric) & (long.left_label == left) & (long.right_label == right)]
    box = panel_box_mm(FIGURE_ID, panel)
    fig = plt.figure(figsize=panel_figsize(FIGURE_ID, panel))
    ax = _mm_axes(
        fig,
        box,
        (
            AXES_LEFT_MM,
            AXES_BOTTOM_MM,
            box[0] - AXES_LEFT_MM - AXES_RIGHT_MARGIN_MM,
            box[1] - AXES_BOTTOM_MM - AXES_TOP_MARGIN_MM,
        ),
    )
    indexed = effects.set_index("medium")
    for medium, marker, filled in MEDIUMS:
        positions = GROUP_POSITIONS[medium]
        one = sub[sub.medium == medium]
        means = _draw_group(ax, one, (left, right), positions, marker, filled, is_log)
        effect_row = indexed.loc[medium]
        center, low, high = _summary_bounds(effect_row, kind, means[0])
        # The anchored estimate must land on the second strain's own plotted
        # mean, or the diamond and the annotated number would be different
        # statistics.
        assert abs(center - means[1]) < 1e-12, (panel, medium, center, means[1])
        _draw_summary(ax, positions[0], means[0])
        _draw_summary(ax, positions[1], means[1], (low, high))
        fig.text(
            (
                AXES_LEFT_MM
                + (sum(positions) / 2.0 - XLIM[0])
                / (XLIM[1] - XLIM[0])
                * (box[0] - AXES_LEFT_MM - AXES_RIGHT_MARGIN_MM)
            )
            / box[0],
            1.0 - 0.9 / box[1],
            _group_header(medium, filled, effect_row),
            ha="center",
            va="top",
            color=SUMMARY_INK,
            fontsize=ANNOTATION_FONT_PT,
            linespacing=ANNOTATION_LINESPACING,
        )

    low, high = _row_limits(long, metric, is_log)
    ax.set_ylim(low, high)
    if is_log:
        ticks = _log_ticks(low, high)
        ax.set_yticks([math.log10(value) for value in ticks], [f"{value:g}" for value in ticks])
    else:
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4, steps=[1, 2, 2.5, 5, 10]))
    ax.set_xlim(*XLIM)
    ax.set_xticks([*GROUP_POSITIONS["agarose"], *GROUP_POSITIONS["liquid"]], [left, right] * 2)
    ax.set_ylabel(ylabel, labelpad=1.5, linespacing=1.1)
    ax.tick_params(axis="both", pad=1.5)
    ax.grid(axis="y", color=GRID_COLOR, lw=0.4)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    # What the estimate divides is stated in the figure legend and in the
    # ``contrast`` column of the effect table, as Figure 7A-C states what its D
    # ratio divides.  Printing it in every panel cost 3.5 mm of panel height
    # nine times over, which is 8 mm of a figure that stood 5 mm above the
    # 185 mm height the publisher allows for a caption under 300 words.
    _assert_clear_of_panel_letter(fig, box)
    output = PROJECT / f"build/panels/{FIGURE_ID}/{panel}/S3_{panel}.png"
    save_figure(fig, output.with_suffix(""))
    return output


def build(panel: str) -> None:
    data = pd.read_csv(INPUT, low_memory=False)
    long = _long(data)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    index = ord(panel) - ord("A")
    row, col = divmod(index, 3)
    metric, _, is_log, kind = METRICS[row]
    left, right = PAIRS[col]
    sub = long[
        (long.metric == metric) & (long.left_label == left) & (long.right_label == right)
    ].copy()
    source = SOURCE_DIR / f"S3_{panel}_paired_points.csv"
    sub.to_csv(source, index=False)
    effects = panel_effects(sub, panel, kind)
    # The three panel counts are pinned: a silent change of the paired set would
    # change every annotated effect.
    expected = EXPECTED_UNITS[col]
    actual = {item.medium: item.n_paired_units for item in effects.itertuples()}
    assert actual == expected, (panel, actual)
    effect_table = SOURCE_DIR / f"S3_{panel}_paired_effect.csv"
    effects.to_csv(effect_table, index=False)
    # The same table under the canonical statistics tree, so every number the
    # panel prints is machine-readable where a reader of Figure 7 looks for it.
    statistics_dir = BUILD_STATS / panel
    statistics_dir.mkdir(parents=True, exist_ok=True)
    statistics_table = statistics_dir / f"S3_{panel}_paired_effect_statistics.csv"
    effects.to_csv(statistics_table, index=False)
    output = _draw_panel(long, panel, effects)
    panel_dir = PANEL_ROOT / f"panel_{panel.lower()}"
    config_path = panel_dir / "config/panel.json"
    wrapper_path = panel_dir / "scripts/reproduce.py"
    provenance = {
        "schema_version": "1.0.0",
        "panel_id": f"S3_{panel}",
        "status": "partial_reproduction",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "analyses/supplementary_03/build_s3.py",
            "--panel",
            panel,
        ],
        "inputs": [
            _artifact(Path(__file__).resolve()),
            _artifact(config_path),
            _artifact(wrapper_path),
            _artifact(INPUT, len(data)),
        ],
        "outputs": [
            _artifact(source, len(sub)),
            _artifact(effect_table, len(effects)),
            _artifact(statistics_table, len(effects)),
            _artifact(output),
            _artifact(output.with_suffix(".svg")),
            _artifact(output.with_suffix(".pdf")),
        ],
        "software": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "matplotlib": matplotlib.__version__,
            "numpy": np.__version__,
        },
        "parameters": {
            "layout": "one metric and one strain pair per panel, the two media side by side",
            "center": "one paired block-level value per strain",
            "line": "paired metadata_key within medium",
            "unit_of_analysis": "paired experimental unit (one metadata_key, one medium)",
            "violin": "kernel density of the plotted unit values, on the plotted scale",
            "plotted_quantity": "log10 of the metric" if is_log else "the metric",
            "log_scale": is_log,
            "summary_mark": (
                "diamond at the group mean of the plotted quantity; the second "
                "strain's bar is the paired 95 % interval anchored at the first "
                "strain's mean"
            ),
            "shared_axis": "the three panels of a metric row share one y range",
            "effect": kind,
            "effect_estimator": (
                "mean paired log contrast, back-transformed"
                if kind == "ratio"
                else "mean paired difference"
            ),
            "interval": "percentile bootstrap over paired experimental units, 95 %",
            "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
            "n_paired_units": actual,
            "statistical_test": "none in plotted panel",
            "multiplicity_correction": "not applicable",
        },
        "random_seeds": {"paired_effect_bootstrap": [BOOTSTRAP_SEED, index]},
        "limitations": [
            "Starts from the legacy-derived block-level table rather than raw trajectories.",
            "The annotated effect is a paired estimate with a bootstrap interval, not a test.",
            "Final manuscript assembly and visual acceptance remain separate.",
        ],
    }
    rendered = json.dumps(provenance, indent=2) + "\n"
    (panel_dir / "metadata/provenance.json").write_text(rendered, encoding="utf-8")
    # The central audit tree is keyed by figure number, not by the historical
    # directory name, so it matches tools/sync_revision_provenance.py.
    central = PROJECT / "metadata/provenance/supplementary_03" / f"S3_{panel}.json"
    central.parent.mkdir(parents=True, exist_ok=True)
    central.write_text(rendered, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", choices=[*PANELS, "all"], default="all")
    args = parser.parse_args()
    for panel in PANELS if args.panel == "all" else [args.panel]:
        build(panel)


if __name__ == "__main__":
    main()
