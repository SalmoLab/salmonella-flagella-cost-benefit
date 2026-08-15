#!/usr/bin/env python3
"""Build Supplementary Figure 5: speed against effective diffusivity, three panels.

The probability contours moved out of main Figure 7 because a 55 mm box cannot
hold them legibly.  Here each phenotype pair gets a full-width 173 mm strip with
agarose and liquid side by side.

Four design decisions carry the figure:

1.  The two phenotypes of a pair differ in kind, not in shade.  The first is a
    filled translucent band, the second is an outline.  Panel C puts two
    neighbouring reds against each other, and a fill against a line stays
    separable where two line colours do not.
2.  The kernel density is evaluated on a grid that is padded by four kernel
    bandwidths beyond the data.  The Figure 7 grid stops at 60 µm/s and
    log10 D_eff = -1.3, so its outer contour runs into the grid edge and is cut.
    A contour truncated by the evaluation grid is not a 95 % region.  This module
    widens the grid and asserts that the density on every grid border stays below
    the outer level, so every contour closes inside the grid.
3.  The contour levels are fixed at 50 % and 95 % in advance and are never
    retuned.  Tightening the outer level always increases apparent separation,
    because the tails are where the two clouds overlap most, so the level is a
    free knob that the data does not constrain.  The honest way to show the
    difference is to add a marginal density per axis, not to shrink a contour.
4.  A contour pools 7 213 to 13 874 trajectories, while every test in the
    manuscript uses the paired experimental unit.  Each axes therefore carries
    one centroid marker per phenotype at the mean of the 16 to 18 per-unit
    centroids in the (speed, log10 D_eff) plane, with 95 % confidence whiskers
    from a paired-unit bootstrap that shares Figure 7's seed and iteration
    count.  The centroid, not the contour, is the inferential mark.

The direct-pair dataset is not re-derived here.  ``checked_csv``,
``load_direct_tracks`` and ``PANEL_SPECS`` are imported from
``analyses/figure_07_revision/build_figure_07_revision.py``, so this figure
provably plots the same trajectories and the same paired-unit filter as Figure 7.
``BOOTSTRAP_SEED`` and ``BOOTSTRAP_ITERATIONS`` are imported from the same
module, so the centroid intervals use Figure 7's bootstrap convention.

Run:
    PYTHONPATH=$PWD/src MPLBACKEND=Agg .venv/bin/python \
        analyses/supplementary_05/build_supplementary_05.py --panel all
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import sys
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

import matplotlib
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import to_rgba
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy.stats import gaussian_kde

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))

from flagella_repro.theme import (  # noqa: E402
    KEY_SWATCH,
    MINIMUM_ON_PAGE_FONT_PT,
    PALETTE,
    POINT_MARKER_SIZE,
    SUMMARY_INK,
    TICK_FONT_PT,
    apply_publication_style,
    get_strain_style,
    marker_edge,
    panel_figsize,
    save_figure,
)

FIGURE_ID = "Supplementary_Figure_5"
FIGURE_07_BUILDER = PROJECT / "analyses/figure_07_revision/build_figure_07_revision.py"
INPUT_DIR = PROJECT / "data/processed/figure_07_revision"
BUILD_PANELS = PROJECT / f"build/panels/{FIGURE_ID}"
BUILD_STATS = PROJECT / f"build/statistics/{FIGURE_ID}"
PANEL_ROOT = PROJECT / "analyses/supplementary_05"
CENTRAL_PROVENANCE = PROJECT / "metadata/provenance/supplementary_05"

MEDIA = ("agarose", "liquid")
PANELS = ("A", "B", "C")
# Two levels, not three.  The reader needs the core and the extent; a middle ring
# adds a third closed curve per phenotype without adding information.
CONTOUR_MASSES = (0.50, 0.95)
# Four kernel bandwidths of padding put the grid border at exp(-8) of the local
# kernel peak, far below the 95 % level.  ``_check_closed`` proves it per panel.
GRID_PAD_BANDWIDTHS = 4.0
GRID_RESOLUTION = 260
# The filled phenotype needs two clearly different tints, because the pale
# PproA salmon of panel C loses its inner band at a smaller step.  The tints are
# lighter than the first draft used, because the centroid markers now carry the
# inference and the pooled contour must read as the background layer.
FILL_ALPHA_95 = 0.18
FILL_ALPHA_50 = 0.42
CONTOUR_LINEWIDTHS = (0.45, 0.8)
# The marginal densities are drawn on 200 points, which is smooth at the 8 mm
# strip height the assembly box allows.
MARGINAL_RESOLUTION = 200
MARGINAL_FILL_ALPHA = 0.42
# The centroid mark sits on top of its own translucent band, so a plain marker
# in the same hue would disappear.  A halo in the page background separates
# every inferential mark from the pooled layer beneath it.
CENTROID_HALO_WIDTH = 1.4
CENTROID_WHISKER_WIDTH = 0.9
CENTROID_CAP_SIZE = 1.6
# The grid Figure 7 uses, kept here only to record the fix in the audit table.
FIGURE_07_GRID = {"speed_um_s": (3.0, 60.0), "log10_diffusivity": (-1.3, 3.0)}

PHENOTYPE_STYLE_IDS = {"WT": "TH5861", "PproA": "EM9661", "PproB": "EM9660"}
REFERENCE_COLOR = PALETTE["neutral"]["reference"]
BACKGROUND_COLOR = PALETTE["neutral"]["background"]
# Text with a subscript is typeset by mathtext at 0.7x the requested size, which
# would print below the 6 pt floor.  Every label therefore stays plain.
DIFFUSIVITY_AXIS_LABEL = "log10 effective diffusivity, D_eff (µm²/s)"
SPEED_AXIS_LABEL = "Swimming speed (µm/s)"
CENTROID_KEY_LABEL = "Unit centroid, 95 % CI"
# Every panel renders at its assembly box, so the smallest size requested here is
# the smallest size on the page.  Nothing in this figure goes below the tick size.
ANNOTATION_FONT_PT = TICK_FONT_PT
assert ANNOTATION_FONT_PT >= MINIMUM_ON_PAGE_FONT_PT

# The pooling sentence used to print under every panel.  It now belongs to the
# figure caption, because it states one fact about the whole figure and three
# copies of it cost three lines of panel height that the marginals need.  The
# statement itself must survive: it is the honesty that justifies the figure
# being supplementary.  ``figure_caption_sentences`` is the single source the
# README and the provenance both quote, so the wording cannot drift.
CAPTION_SENTENCES = (
    (
        "The 50 % and 95 % probability contours pool all trajectories of a phenotype, "
        "so the inferential unit is the paired experiment and not the trajectory."
    ),
    (
        "The two contour levels were fixed at 50 % and 95 % in advance and were not "
        "retuned to separate the phenotypes, and the kernel-density grid is padded by "
        "four kernel bandwidths per axis so no contour is clipped by the grid."
    ),
    (
        "Marginal kernel densities above and to the right of each axes use the same "
        "fill-against-outline convention as the contours."
    ),
    (
        "The centroid marker of a phenotype is the mean of its per-unit centroids in "
        "the (speed, log10 D_eff) plane, and its whiskers are 95 % confidence "
        "intervals from a paired-unit bootstrap with 10 000 resamples at a fixed seed."
    ),
    (
        "A whisker that does not extend past its marker denotes a confidence interval "
        "narrower than the marker, and the thin connector joins the two centroids of a "
        "pair."
    ),
    (
        "Each whisker is a marginal interval for one phenotype, so two whiskers may "
        "overlap while the paired difference excludes zero; the paired differences and "
        "their intervals are reported in the statistics table, not read off the panel."
    ),
)


def figure_caption_sentences() -> tuple[str, ...]:
    """Return the caption sentences this figure requires, in reading order.

    The panels no longer print any of these.  The build writes them beside the
    statistics table so the legend author quotes the same wording the code
    implements.

    Example:
        >>> figure_caption_sentences()[1].startswith("The two contour levels")
        True
    """
    return CAPTION_SENTENCES


def _load_figure_07_builder():
    """Import the Figure 7 builder as a module without modifying or running it."""
    spec = importlib.util.spec_from_file_location(
        "figure_07_revision_for_s6", FIGURE_07_BUILDER
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import {FIGURE_07_BUILDER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIGURE_07 = _load_figure_07_builder()
# The names the Figure 7 builder guarantees.  Importing them, rather than
# copying them, is what makes the shared dataset and the shared bootstrap
# convention checkable.
checked_csv = FIGURE_07.checked_csv
load_direct_tracks = FIGURE_07.load_direct_tracks
PANEL_SPECS = FIGURE_07.PANEL_SPECS
BOOTSTRAP_SEED = FIGURE_07.BOOTSTRAP_SEED
BOOTSTRAP_ITERATIONS = FIGURE_07.BOOTSTRAP_ITERATIONS


def unit_centroids(direct: pd.DataFrame) -> pd.DataFrame:
    """Return one centroid per paired unit, medium and phenotype.

    A unit centroid is the arithmetic mean of its trajectories on both plotted
    axes.  The diffusivity mean is taken on the log10 scale, which is the scale
    the panel draws and the same aggregation Figure 7 uses for its unit means.
    """
    return direct.groupby(["metadata_key", "medium", "phenotype"], as_index=False).agg(
        speed_um_s=("speed_um_s", "mean"),
        log10_diffusivity=("log10_diffusivity", "mean"),
        n_trajectories=("speed_um_s", "size"),
    )


def _paired_wide(centroids: pd.DataFrame, medium: str) -> pd.DataFrame:
    """Return the units of one medium with a column per phenotype and axis."""
    return (
        centroids[centroids.medium == medium]
        .pivot(
            index="metadata_key",
            columns="phenotype",
            values=["speed_um_s", "log10_diffusivity"],
        )
        .dropna()
        .sort_index()
    )


def _bootstrap_cell(
    wide: pd.DataFrame,
    phenotypes: tuple[str, str],
    contrast: tuple[str, str],
    rng: np.random.Generator,
) -> tuple[dict[str, float], list[dict[str, float]]]:
    """Bootstrap the two phenotype centroids and their paired difference.

    One resample draws paired units with replacement and keeps both phenotypes
    of a drawn unit together, so the difference interval respects the pairing.
    The same resample indices serve both marginal centroids and the difference,
    which is why a single ``rng.integers`` call feeds all three.
    """
    numerator, denominator = contrast
    axes = ("speed_um_s", "log10_diffusivity")
    values = np.stack(
        [np.column_stack([wide[axis, name].to_numpy() for axis in axes]) for name in phenotypes]
    )
    n = values.shape[1]
    draws = rng.integers(0, n, size=(BOOTSTRAP_ITERATIONS, n))
    means = values[:, draws, :].mean(axis=2)
    positions: list[dict[str, float]] = []
    for index, name in enumerate(phenotypes):
        entry: dict[str, float] = {"phenotype": name, "n_paired_units": n}
        for axis_index, axis in enumerate(axes):
            low, high = np.quantile(means[index, :, axis_index], [0.025, 0.975])
            entry[axis] = float(values[index, :, axis_index].mean())
            entry[f"{axis}_ci95_low"] = float(low)
            entry[f"{axis}_ci95_high"] = float(high)
        positions.append(entry)
    order = [phenotypes.index(numerator), phenotypes.index(denominator)]
    difference = values[order[0]] - values[order[1]]
    bootstrap_difference = means[order[0]] - means[order[1]]
    row: dict[str, float] = {"n_paired_units": n}
    for axis_index, axis in enumerate(axes):
        low, high = np.quantile(bootstrap_difference[:, axis_index], [0.025, 0.975])
        row[f"delta_{axis}"] = float(difference[:, axis_index].mean())
        row[f"delta_{axis}_ci95_low"] = float(low)
        row[f"delta_{axis}_ci95_high"] = float(high)
    return row, positions


@lru_cache(maxsize=1)
def centroid_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return the per-phenotype centroid table and the paired-difference table.

    One generator seeded at ``BOOTSTRAP_SEED`` walks the panels in the order
    A, B, C with agarose before liquid, exactly as ``decomposition_tables`` in
    the Figure 7 builder does.  Building a single panel therefore yields the
    same numbers as building all three, and the cache makes the pass run once.

    Example:
        >>> positions, differences = centroid_tables()
        >>> len(differences)
        6
    """
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    position_rows: list[dict[str, object]] = []
    difference_rows: list[dict[str, object]] = []
    for panel, spec in PANEL_SPECS.items():
        centroids = unit_centroids(load_direct_tracks(panel))
        phenotypes = tuple(spec["phenotypes"])
        numerator, denominator = spec["contrast"]
        for medium in MEDIA:
            wide = _paired_wide(centroids, medium)
            if len(wide) != spec["expected"][medium]:
                raise AssertionError(f"panel {panel} {medium} has {len(wide)} paired units")
            row, positions = _bootstrap_cell(wide, phenotypes, spec["contrast"], rng)
            for entry in positions:
                position_rows.append({"panel": panel, "medium": medium, **entry})
            difference_rows.append(
                {
                    "panel": panel,
                    "medium": medium,
                    "comparison": f"{numerator} minus {denominator}",
                    **row,
                }
            )
    return pd.DataFrame(position_rows), pd.DataFrame(difference_rows)


def style_for(phenotype: str) -> dict[str, str]:
    """Return the shared theme style of one phenotype."""
    return get_strain_style(PHENOTYPE_STYLE_IDS[phenotype])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _artifact(path: Path, rows: int | None = None) -> dict[str, object]:
    item: dict[str, object] = {
        "relative_path": path.relative_to(PROJECT).as_posix(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }
    if rows is not None:
        item["rows"] = rows
    return item


def kernel_bandwidths(kde: gaussian_kde, x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Return the kernel standard deviation along each axis, in data units.

    ``gaussian_kde`` scales the sample covariance by ``factor**2``, so the kernel
    standard deviation on an axis is ``factor`` times the sample deviation.

    Example:
        >>> rng = np.random.default_rng(0)
        >>> a, b = rng.normal(size=200), rng.normal(size=200)
        >>> bw = kernel_bandwidths(gaussian_kde(np.vstack([a, b])), a, b)
        >>> all(value > 0 for value in bw)
        True
    """
    return (kde.factor * float(np.std(x, ddof=1)), kde.factor * float(np.std(y, ddof=1)))


def density_grid(
    samples: dict[str, tuple[np.ndarray, np.ndarray]],
    *,
    pad_bandwidths: float = GRID_PAD_BANDWIDTHS,
    resolution: int = GRID_RESOLUTION,
) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Evaluate one shared kernel-density grid for every phenotype of a medium.

    The grid spans the union of the samples, padded by ``pad_bandwidths`` kernel
    bandwidths on each side, so no contour can reach a grid border.  Both
    phenotypes share the lattice, which keeps their contours directly comparable.

    Complexity is O(resolution**2) kernel evaluations per phenotype, about
    68 000 points here, which takes well under a second per phenotype.
    """
    estimators = {name: gaussian_kde(np.vstack(values)) for name, values in samples.items()}
    x_low, x_high, y_low, y_high = [], [], [], []
    for name, (x, y) in samples.items():
        bandwidth_x, bandwidth_y = kernel_bandwidths(estimators[name], x, y)
        x_low.append(float(x.min()) - pad_bandwidths * bandwidth_x)
        x_high.append(float(x.max()) + pad_bandwidths * bandwidth_x)
        y_low.append(float(y.min()) - pad_bandwidths * bandwidth_y)
        y_high.append(float(y.max()) + pad_bandwidths * bandwidth_y)
    x_axis = np.linspace(min(x_low), max(x_high), resolution)
    y_axis = np.linspace(min(y_low), max(y_high), resolution)
    xx, yy = np.meshgrid(x_axis, y_axis)
    flat = np.vstack([xx.ravel(), yy.ravel()])
    densities = {name: estimator(flat).reshape(xx.shape) for name, estimator in estimators.items()}
    return xx, yy, densities


def hdr_thresholds(density: np.ndarray, masses: tuple[float, ...] = CONTOUR_MASSES) -> list[float]:
    """Return highest-density-region levels, ascending, for the given masses.

    The grid is uniform, so every cell carries the same area and the probability
    mass inside a level is the sorted cumulative sum of the density values.
    """
    flat = np.sort(density.ravel())[::-1]
    cumulative = np.cumsum(flat) / flat.sum()
    thresholds = []
    for mass in masses:
        index = min(int(np.searchsorted(cumulative, mass)), len(flat) - 1)
        thresholds.append(float(flat[index]))
    return sorted(thresholds)


def border_maximum(density: np.ndarray) -> float:
    """Return the largest density value on the four edges of the grid."""
    edges = np.concatenate([density[0, :], density[-1, :], density[:, 0], density[:, -1]])
    return float(edges.max())


def region_bounds(
    xx: np.ndarray, yy: np.ndarray, density: np.ndarray, level: float
) -> tuple[float, float, float, float]:
    """Return the bounding box of the region enclosed by one density level."""
    mask = density >= level
    return (
        float(xx[mask].min()),
        float(xx[mask].max()),
        float(yy[mask].min()),
        float(yy[mask].max()),
    )


def panel_density(panel: str, direct: pd.DataFrame) -> dict[str, dict[str, object]]:
    """Compute the shared grid, the levels and the closure check for one panel."""
    spec = PANEL_SPECS[panel]
    result: dict[str, dict[str, object]] = {}
    for medium in MEDIA:
        medium_data = direct[direct.medium == medium]
        samples = {
            phenotype: (
                medium_data.loc[medium_data.phenotype == phenotype, "speed_um_s"].to_numpy(),
                medium_data.loc[
                    medium_data.phenotype == phenotype, "log10_diffusivity"
                ].to_numpy(),
            )
            for phenotype in spec["phenotypes"]
        }
        xx, yy, densities = density_grid(samples)
        levels = {name: hdr_thresholds(values) for name, values in densities.items()}
        for name, values in densities.items():
            outer, inner = levels[name]
            if not outer < inner < float(values.max()):
                raise AssertionError(f"panel {panel} {medium} {name} has degenerate levels")
            if border_maximum(values) >= outer:
                raise AssertionError(
                    f"panel {panel} {medium} {name}: the 95 % contour reaches the grid border"
                )
        result[medium] = {
            "xx": xx,
            "yy": yy,
            "densities": densities,
            "levels": levels,
            # The marginal strips re-use the same trajectory arrays the joint
            # density was built from, so no marginal can disagree with a contour.
            "samples": samples,
            "n_units": int(medium_data.metadata_key.nunique()),
            "n_trajectories": {
                phenotype: int((medium_data.phenotype == phenotype).sum())
                for phenotype in spec["phenotypes"]
            },
        }
    return result


def audit_table(panel: str, computed: dict[str, dict[str, object]]) -> pd.DataFrame:
    """Record the grid extents, the levels and the closure margin of one panel."""
    rows = []
    for medium, entry in computed.items():
        xx, yy = entry["xx"], entry["yy"]
        for phenotype, density in entry["densities"].items():
            outer, inner = entry["levels"][phenotype]
            left, right, bottom, top = region_bounds(xx, yy, density, outer)
            rows.append(
                {
                    "panel": panel,
                    "medium": medium,
                    "phenotype": phenotype,
                    "n_trajectories": entry["n_trajectories"][phenotype],
                    "n_paired_units": entry["n_units"],
                    "figure_07_grid_speed_min": FIGURE_07_GRID["speed_um_s"][0],
                    "figure_07_grid_speed_max": FIGURE_07_GRID["speed_um_s"][1],
                    "figure_07_grid_log10_diffusivity_min": FIGURE_07_GRID["log10_diffusivity"][0],
                    "figure_07_grid_log10_diffusivity_max": FIGURE_07_GRID["log10_diffusivity"][1],
                    "grid_speed_min": float(xx.min()),
                    "grid_speed_max": float(xx.max()),
                    "grid_log10_diffusivity_min": float(yy.min()),
                    "grid_log10_diffusivity_max": float(yy.max()),
                    "level_50": inner,
                    "level_95": outer,
                    "border_maximum_density": border_maximum(density),
                    "border_over_level_95": border_maximum(density) / outer,
                    "contour_95_speed_min": left,
                    "contour_95_speed_max": right,
                    "contour_95_log10_diffusivity_min": bottom,
                    "contour_95_log10_diffusivity_max": top,
                }
            )
    return pd.DataFrame(rows)


def _axes_limits(
    computed: dict[str, dict[str, object]],
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return shared axis limits that hold every contour of the panel."""
    left, right, bottom, top = [], [], [], []
    for entry in computed.values():
        for phenotype, density in entry["densities"].items():
            outer = entry["levels"][phenotype][0]
            bounds = region_bounds(entry["xx"], entry["yy"], density, outer)
            left.append(bounds[0])
            right.append(bounds[1])
            bottom.append(bounds[2])
            top.append(bounds[3])
    x_low, x_high = min(left), max(right)
    y_low, y_high = min(bottom), max(top)
    x_pad = 0.05 * (x_high - x_low)
    y_span = y_high - y_low
    # The reference line at D_eff = 1 must stay inside the axes, and the lower
    # band carries the counts, so the bottom gets more room than the top.
    return (
        (x_low - x_pad, x_high + x_pad),
        (min(y_low, 0.0) - 0.22 * y_span, max(y_high, 0.0) + 0.06 * y_span),
    )


def marginal_density(values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Return a kernel density on ``grid``, rescaled to a peak of one.

    Each marginal strip is a shape comparison between two phenotypes measured
    on different trajectory counts, so the strip shows relative shape and not
    absolute probability density.  Scaling both curves to the same peak is what
    makes the horizontal shift readable in an 8 mm strip.

    Example:
        >>> grid = np.linspace(-3.0, 3.0, 51)
        >>> float(marginal_density(np.random.default_rng(0).normal(size=500), grid).max())
        1.0
    """
    curve = gaussian_kde(values)(grid)
    return curve / float(curve.max())


def _draw_marginals(
    ax_top,
    ax_right,
    entry: dict[str, object],
    order: tuple[str, str],
    colors: dict[str, str],
) -> None:
    """Draw the speed and diffusivity marginals of one medium.

    The filled phenotype is a filled band and the outlined phenotype is a line,
    the same distinction the contours use, so a reader who has learned the key
    once reads all four marks.
    """
    filled = order[0]
    samples = entry["samples"]
    x_grid = np.linspace(*ax_top.get_xlim(), MARGINAL_RESOLUTION)
    y_grid = np.linspace(*ax_right.get_ylim(), MARGINAL_RESOLUTION)
    for phenotype in order:
        speed, diffusivity = samples[phenotype]
        color = colors[phenotype]
        speed_curve = marginal_density(speed, x_grid)
        diffusivity_curve = marginal_density(diffusivity, y_grid)
        if phenotype == filled:
            ax_top.fill_between(
                x_grid, 0.0, speed_curve, color=to_rgba(color, MARGINAL_FILL_ALPHA), lw=0.0
            )
            ax_right.fill_betweenx(
                y_grid, 0.0, diffusivity_curve, color=to_rgba(color, MARGINAL_FILL_ALPHA), lw=0.0
            )
        else:
            ax_top.plot(x_grid, speed_curve, color=color, lw=0.9)
            ax_right.plot(diffusivity_curve, y_grid, color=color, lw=0.9)
    for strip in (ax_top, ax_right):
        for spine in strip.spines.values():
            spine.set_visible(False)
        # A strip shares one axis with the main axes, and shared axes share the
        # tick locator.  Clearing the ticks with ``set_xticks([])`` would strip
        # the main axes of its own numbers, so the strip only switches its own
        # tick marks and labels off.
        strip.tick_params(
            which="both",
            bottom=False,
            top=False,
            left=False,
            right=False,
            labelbottom=False,
            labeltop=False,
            labelleft=False,
            labelright=False,
        )
        strip.patch.set_alpha(0.0)
    ax_top.set_ylim(0.0, 1.14)
    ax_right.set_xlim(0.0, 1.14)


def _draw_centroids(ax, positions: pd.DataFrame, order: tuple[str, str], colors) -> None:
    """Draw one centroid marker per phenotype with paired-bootstrap whiskers.

    The centroid is the inferential mark of the panel, so it sits above every
    contour and carries a halo in the page background colour.  Without the halo
    the marker of the filled phenotype would sit invisibly inside its own band.
    """
    halo = [path_effects.withStroke(linewidth=CENTROID_HALO_WIDTH, foreground=BACKGROUND_COLOR)]
    indexed = positions.set_index("phenotype")
    first, second = (indexed.loc[name] for name in order)
    # A single connector states the paired shift the difference table reports.
    # It belongs to neither phenotype, so it takes the shared summary ink.
    ax.plot(
        [first.speed_um_s, second.speed_um_s],
        [first.log10_diffusivity, second.log10_diffusivity],
        color=SUMMARY_INK,
        lw=0.8,
        zorder=5,
        path_effects=halo,
    )
    for index, phenotype in enumerate(order):
        row = indexed.loc[phenotype]
        color = colors[phenotype]
        # Capped whiskers, because an uncapped bar shorter than the marker reads
        # as a smudge.  Some intervals here are narrower than the marker itself,
        # which is the finding: the between-unit uncertainty is far smaller than
        # the pooled trajectory spread the contour draws.
        ax.errorbar(
            [row.speed_um_s],
            [row.log10_diffusivity],
            xerr=[
                [row.speed_um_s - row.speed_um_s_ci95_low],
                [row.speed_um_s_ci95_high - row.speed_um_s],
            ],
            yerr=[
                [row.log10_diffusivity - row.log10_diffusivity_ci95_low],
                [row.log10_diffusivity_ci95_high - row.log10_diffusivity],
            ],
            fmt="none",
            ecolor=color,
            elinewidth=CENTROID_WHISKER_WIDTH,
            capsize=CENTROID_CAP_SIZE,
            capthick=CENTROID_WHISKER_WIDTH,
            zorder=6,
            path_effects=halo,
        )
        if index == 0:
            edge_color, edge_width = marker_edge(color)
            ax.scatter(
                [row.speed_um_s],
                [row.log10_diffusivity],
                s=POINT_MARKER_SIZE,
                color=color,
                edgecolor=edge_color,
                linewidth=edge_width,
                zorder=7,
                path_effects=halo,
            )
        else:
            # The outlined phenotype keeps its outline identity here too: an
            # open ring against a solid disc separates the pair at a glance,
            # which two neighbouring reds could not do by hue.
            ax.scatter(
                [row.speed_um_s],
                [row.log10_diffusivity],
                s=POINT_MARKER_SIZE,
                facecolor=BACKGROUND_COLOR,
                edgecolor=color,
                linewidth=1.0,
                zorder=7,
                path_effects=halo,
            )


def draw_panel(
    panel: str, computed: dict[str, dict[str, object]], positions: pd.DataFrame
) -> list[Path]:
    """Draw one phenotype pair at its full-width assembly box.

    The panel renders at ``panel_figsize``, so the assembler scales it by one and
    every point size requested here is the point size on the printed page.  Each
    medium occupies a 2x2 sub-grid: the main axes, a speed marginal above it and
    a diffusivity marginal to its right.
    """
    spec = PANEL_SPECS[panel]
    order = tuple(spec["phenotypes"])
    filled, outlined = order
    colors = {name: style_for(name)["color"] for name in order}
    fill_color, line_color = colors[filled], colors[outlined]
    fig = plt.figure(figsize=panel_figsize(FIGURE_ID, panel), constrained_layout=True)
    outer = fig.add_gridspec(1, 2, wspace=0.14)
    x_limits, y_limits = _axes_limits(computed)
    main_axes = []
    for column, medium in enumerate(MEDIA):
        inner = outer[0, column].subgridspec(
            2, 2, width_ratios=[8.5, 1.0], height_ratios=[1.0, 5.4], wspace=0.02, hspace=0.06
        )
        shared = main_axes[0] if main_axes else None
        ax = fig.add_subplot(inner[1, 0], sharex=shared, sharey=shared)
        ax_top = fig.add_subplot(inner[0, 0], sharex=ax)
        ax_right = fig.add_subplot(inner[1, 1], sharey=ax)
        main_axes.append(ax)
        entry = computed[medium]
        xx, yy = entry["xx"], entry["yy"]
        for phenotype in order:
            density = entry["densities"][phenotype]
            level_95, level_50 = entry["levels"][phenotype]
            if phenotype == filled:
                ax.contourf(
                    xx,
                    yy,
                    density,
                    levels=[level_95, level_50, float(density.max())],
                    colors=[to_rgba(fill_color, FILL_ALPHA_95), to_rgba(fill_color, FILL_ALPHA_50)],
                    zorder=1,
                )
            else:
                ax.contour(
                    xx,
                    yy,
                    density,
                    levels=[level_95, level_50],
                    colors=[line_color],
                    linewidths=list(CONTOUR_LINEWIDTHS),
                    zorder=2,
                )
        ax.axhline(0, color=REFERENCE_COLOR, lw=0.7, ls="--", zorder=3)
        ax.set_xlim(*x_limits)
        ax.set_ylim(*y_limits)
        ax.set_xlabel(SPEED_AXIS_LABEL)
        ax_top.set_title(medium.capitalize(), pad=2.0)
        _draw_marginals(ax_top, ax_right, entry, order, colors)
        _draw_centroids(ax, positions[positions.medium == medium], order, colors)
        counts = entry["n_trajectories"]
        ax.text(
            0.99,
            0.02,
            f"{entry['n_units']} paired experiments\n"
            + "\n".join(f"{name} {counts[name]:,} trajectories" for name in order),
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=TICK_FONT_PT,
            linespacing=1.12,
            zorder=4,
        )
    main_axes[0].set_ylabel(DIFFUSIVITY_AXIS_LABEL)
    plt.setp(main_axes[1].get_yticklabels(), visible=False)
    # The key entry for the centroid stands for a concept, not a strain, so it
    # takes the neutral key swatch rather than borrowing a strain colour.  It
    # shows both mark shapes, because the panel repeats the fill-against-outline
    # distinction on the centroids and a single shape would name only half of it.
    marker_size_pt = float(np.sqrt(POINT_MARKER_SIZE))
    centroid_key = (
        Line2D(
            [0],
            [0],
            color=KEY_SWATCH,
            lw=CENTROID_WHISKER_WIDTH,
            marker="o",
            markersize=marker_size_pt,
            markerfacecolor=KEY_SWATCH,
            markeredgecolor="none",
        ),
        Line2D(
            [0],
            [0],
            color=KEY_SWATCH,
            lw=CENTROID_WHISKER_WIDTH,
            marker="o",
            markersize=marker_size_pt,
            markerfacecolor=BACKGROUND_COLOR,
            markeredgecolor=KEY_SWATCH,
            markeredgewidth=1.0,
        ),
    )
    handles = [
        Patch(facecolor=to_rgba(fill_color, FILL_ALPHA_50), edgecolor="none", label=filled),
        Line2D([0], [0], color=line_color, lw=1.2, label=outlined),
        centroid_key,
        Line2D([0], [0], color=REFERENCE_COLOR, lw=0.7, ls="--", label="D_eff = 1"),
    ]
    fig.legend(
        handles=handles,
        labels=[filled, outlined, CENTROID_KEY_LABEL, "D_eff = 1"],
        handler_map={tuple: HandlerTuple(ndivide=2, pad=0.2)},
        loc="outside upper center",
        ncol=4,
        frameon=False,
        handlelength=1.6,
        handletextpad=0.4,
        columnspacing=1.6,
        borderpad=0.0,
    )
    return save_figure(fig, BUILD_PANELS / f"{panel}/S5_{panel}")


def write_provenance(
    panel: str,
    graphics: list[Path],
    tables: list[tuple[Path, int]],
    computed: dict[str, dict[str, object]],
    differences: pd.DataFrame,
) -> Path:
    """Write panel-local and central provenance with hashes taken from disk."""
    spec = PANEL_SPECS[panel]
    inputs = [
        _artifact(Path(__file__).resolve()),
        _artifact(FIGURE_07_BUILDER),
        _artifact(INPUT_DIR / "direct_pair_track_measurements.csv.gz"),
        _artifact(INPUT_DIR / "paired_experimental_unit_measurements.csv"),
    ]
    document = {
        "schema_version": "1.0.0",
        "panel_id": f"S5_{panel}",
        "status": "partial_reproduction",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python",
            "analyses/supplementary_05/build_supplementary_05.py",
            "--panel",
            panel,
        ],
        "backend": "Python 3.12",
        "inputs": inputs,
        "outputs": [
            *[_artifact(path, rows) for path, rows in tables],
            *[_artifact(path) for path in graphics],
        ],
        "software": {
            "python": platform.python_version(),
            "matplotlib": matplotlib.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": __import__("scipy").__version__,
        },
        "random_seeds": {"paired_unit_bootstrap": BOOTSTRAP_SEED},
        "parameters": {
            "contrast": f"{spec['phenotypes'][0]} versus {spec['phenotypes'][1]}",
            "contour_probability_mass": list(CONTOUR_MASSES),
            "contour_levels_pre_specified": (
                "The 50 % and 95 % masses were fixed before the panels were drawn and were "
                "not retuned to separate the phenotypes; a tighter outer level always "
                "increases apparent separation because the tails carry the overlap."
            ),
            "density_estimator": "scipy.stats.gaussian_kde, Scott bandwidth rule",
            "density_grid_resolution": GRID_RESOLUTION,
            "density_grid_padding_bandwidths": GRID_PAD_BANDWIDTHS,
            "figure_07_density_grid": FIGURE_07_GRID,
            "marginal_density_resolution": MARGINAL_RESOLUTION,
            "marginal_density_scaling": "each marginal is rescaled to a peak of one",
            "unit_centroid_definition": (
                "arithmetic mean of speed and of log10 D_eff over the trajectories of one "
                "metadata_key, medium and phenotype"
            ),
            "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
            "bootstrap_resampling_unit": "paired experimental unit, both phenotypes drawn together",
            "direct_pair_filter": (
                "metadata keys from the reciprocal-label paired-unit tables, imported from "
                "analyses/figure_07_revision/build_figure_07_revision.py"
            ),
            "deterministic": (
                "gaussian_kde and the grid are deterministic; the only random draw is the "
                "paired-unit bootstrap, which runs once for all six panel-medium cells from "
                "a generator seeded at BOOTSTRAP_SEED"
            ),
        },
        "figure_caption_sentences": list(figure_caption_sentences()),
        "results": {
            medium: {
                "n_paired_units": entry["n_units"],
                "n_trajectories": entry["n_trajectories"],
                "border_over_level_95": {
                    phenotype: border_maximum(density) / entry["levels"][phenotype][0]
                    for phenotype, density in entry["densities"].items()
                },
                "paired_centroid_difference": {
                    key: int(value) if key == "n_paired_units" else float(value)
                    for key, value in differences[differences.medium == medium]
                    .iloc[0]
                    .drop(labels=["panel", "medium", "comparison"])
                    .items()
                },
                "comparison": str(
                    differences.loc[differences.medium == medium, "comparison"].iloc[0]
                ),
            }
            for medium, entry in computed.items()
        },
        "limitations": [
            (
                "The run starts from migrated direct-pair track and paired-unit tables, "
                "not from raw tracking acquisitions."
            ),
            (
                "The contours pool trajectories within a phenotype, so they show the "
                "trajectory distribution and not the between-experiment uncertainty; the "
                "paired experiment remains the inferential unit and is quantified in "
                "Figure 7D."
            ),
            (
                "The kernel density is a smoothed description, so the contours and the "
                "marginals extend a little beyond the measured speed and diffusivity range."
            ),
            (
                "The centroid whiskers are marginal 95 % intervals on each axis "
                "separately, so the pair of whiskers is a cross and not a joint "
                "two-dimensional confidence region, and two overlapping whiskers do not "
                "imply an absent paired difference."
            ),
            (
                "This supplementary figure is new in the 12 August 2026 revision and has "
                "no frozen 9 July reference to accept against."
            ),
        ],
        "interpretation_limit": (
            "A contour is a probability region of pooled trajectories, not a confidence "
            "region for a phenotype mean."
        ),
    }
    rendered = json.dumps(document, indent=2) + "\n"
    panel_metadata = PANEL_ROOT / f"panel_{panel.lower()}/metadata"
    panel_metadata.mkdir(parents=True, exist_ok=True)
    (panel_metadata / "provenance.json").write_text(rendered, encoding="utf-8")
    CENTRAL_PROVENANCE.mkdir(parents=True, exist_ok=True)
    central = CENTRAL_PROVENANCE / f"S5_{panel}.json"
    central.write_text(rendered, encoding="utf-8")
    return central


def build(panel: str, *, check_only: bool = False) -> dict[str, object]:
    """Build one panel and return its counts and its closure margins."""
    direct = load_direct_tracks(panel)
    computed = panel_density(panel, direct)
    summary = {
        "paired_units": {medium: computed[medium]["n_units"] for medium in MEDIA},
        "trajectories": {medium: computed[medium]["n_trajectories"] for medium in MEDIA},
        "maximum_border_over_level_95": max(
            border_maximum(density) / computed[medium]["levels"][phenotype][0]
            for medium in MEDIA
            for phenotype, density in computed[medium]["densities"].items()
        ),
    }
    all_positions, all_differences = centroid_tables()
    positions = all_positions[all_positions.panel == panel].reset_index(drop=True)
    differences = all_differences[all_differences.panel == panel].reset_index(drop=True)
    summary["paired_centroid_difference"] = {
        row.medium: {
            "comparison": row.comparison,
            "n_paired_units": int(row.n_paired_units),
            "delta_speed_um_s": [
                row.delta_speed_um_s,
                row.delta_speed_um_s_ci95_low,
                row.delta_speed_um_s_ci95_high,
            ],
            "delta_log10_diffusivity": [
                row.delta_log10_diffusivity,
                row.delta_log10_diffusivity_ci95_low,
                row.delta_log10_diffusivity_ci95_high,
            ],
        }
        for row in differences.itertuples()
    }
    if check_only:
        return summary
    stats_dir = BUILD_STATS / panel
    stats_dir.mkdir(parents=True, exist_ok=True)
    tables = []
    for frame, name in (
        (audit_table(panel, computed), f"S5_{panel}_contour_grid_audit.csv"),
        (positions, f"S5_{panel}_unit_centroids.csv"),
        (differences, f"S5_{panel}_paired_centroid_differences.csv"),
    ):
        path = stats_dir / name
        frame.to_csv(path, index=False)
        tables.append((path, len(frame)))
    caption_path = stats_dir / f"S5_{panel}_caption_sentences.txt"
    caption_path.write_text("\n".join(figure_caption_sentences()) + "\n", encoding="utf-8")
    # The provenance schema verifies a declared row count by parsing the file,
    # which it can only do for CSV, CSV.GZ and Parquet.  The caption is plain
    # text, so it is registered without a row count.
    tables.append((caption_path, None))
    graphics = draw_panel(panel, computed, positions)
    summary["provenance"] = (
        write_provenance(panel, graphics, tables, computed, differences)
        .relative_to(PROJECT)
        .as_posix()
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Supplementary Figure 5 panels.")
    parser.add_argument("--panel", choices=[*PANELS, "all"], default="all")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    apply_publication_style()
    selected = list(PANELS) if args.panel == "all" else [args.panel]
    results = {panel: build(panel, check_only=args.check) for panel in selected}
    print(json.dumps(results, indent=2, default=float))


if __name__ == "__main__":
    main()
