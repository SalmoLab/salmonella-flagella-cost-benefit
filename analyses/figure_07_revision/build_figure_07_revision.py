#!/usr/bin/env python3
"""Build revised Figure 7, diagnostics, and the effective-diffusivity audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MaxNLocator, NullLocator
from scipy.stats import gaussian_kde

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
    TICK_FONT_PT,
    apply_publication_style,
    get_strain_style,
    marker_edge,
    panel_box_mm,
    panel_figsize,
    save_figure,
)

INPUT_DIR = PROJECT / "data/processed/figure_07_revision"
SOURCE_DIR = PROJECT / "data/source_data/figure_07_revision"
BUILD_SOURCE = PROJECT / "build/source_data/Figure_7"
BUILD_STATS = PROJECT / "build/statistics/Figure_7"
BUILD_PANELS = PROJECT / "build/panels/Figure_7"
# Diagnostic renderings live here.  build_candidates.py writes the two reviewed
# A-C designs under build/diagnostics/Figure_7_candidates.
BUILD_DIAGNOSTICS = PROJECT / "build/diagnostics/Figure_7"

FIGURE_ID = "Figure_7"
# Semantic neutrals come from the shared palette so no panel carries its own
# colour vocabulary.
REFERENCE_COLOR = PALETTE["neutral"]["reference"]
TECHNICAL_COLOR = PALETTE["neutral"]["technical"]
TEXT_COLOR = PALETTE["neutral"]["text"]
GRID_COLOR = PALETTE["neutral"]["grid"]
BACKGROUND_COLOR = PALETTE["neutral"]["background"]
# Panel D previously drew its two component rows in the ΔflhDC blue and the
# ΔflgE orange, which are strain colours that Figure 3B and 3C spend on those
# two deletion mutants.  The rows are already separated by y position, tick text
# and bar height, so colour carries nothing here and is surrendered: both
# component rows use the neutral concept swatch and the product row the summary
# ink.  The two hues then keep meaning the deletion mutants across the
# collection.
COMPONENT_INK = KEY_SWATCH
PRODUCT_INK = SUMMARY_INK
# One shape vocabulary for medium across the whole motility story: filled circle
# is agarose and open square is liquid, in Figure 7A-D and in Supplementary
# Figure S3.
MEDIUM_MARKERS = {"agarose": "o", "liquid": "s"}
# Text with a subscript is typeset by mathtext at 0.7x the requested size, which
# would print below the 6 pt floor.  Panel labels therefore stay plain, as in
# analyses/figure_05.
DIFFUSIVITY_AXIS_LABEL = "Unit mean log10\nD_eff (µm²/s)"
SPEED_AXIS_LABEL = "Unit mean\nspeed (µm/s)"
# The speed row plots log10 speed on a linear axis and prints the raw speed on
# the ticks.  A matplotlib log axis would estimate the violin density in linear
# speed and then stretch it, which would misdraw the distribution summary.
SPEED_TICKS_UM_S = (10.0, 20.0, 30.0, 40.0)
SPEED_YLIM_LOG10 = (np.log10(9.6), np.log10(43.0))
DIFFUSIVITY_YLIM_LOG10 = (-0.25, 2.35)
# Panels A-C place their axes by hand, in millimetres of the 55 x 84 mm assembly
# box.  constrained_layout would size each panel's left margin from its own tick
# labels, so the three panels of the strip would not share one baseline.
AC_LEFT_MM = 13.0
AC_RIGHT_MARGIN_MM = 1.5
AC_BOTTOM_MM = 10.5
AC_ROW_HEIGHT_MM = 29.0
AC_ROW_GAP_MM = 6.5
# Panel D also places its axes by hand.  The three subplots must be exactly the
# same width, or one ratio would print as different bar lengths in different
# subplots and the shared axis would not be shared in the way that matters.
D_LEFT_MM = 14.0
D_RIGHT_MARGIN_MM = 8.0
D_GAP_MM = 7.0
D_BOTTOM_MM = 14.0
D_TOP_MARGIN_MM = 10.0
# One symmetric log ratio axis for all three subplots, so the dashed reference
# at 1 sits in the same place and equal bar lengths mean equal effects.  The
# approved 0.25 to 4 window would clip panel C: its agarose D_eff ratio is 4.10
# with an upper bound of 5.76.  The window therefore opens to 1/6.5 to 6.5,
# which is still symmetric about 1 and holds every bound.
D_XLIM = (1.0 / 6.5, 6.5)
D_XTICKS = (0.2, 0.5, 1.0, 2.0, 5.0)
# Figure 1 sets its per-group numbers at the 6 pt floor because seven
# conditions share 54 mm.  Panels E-G carry two groups in 55 mm, so the same
# numbers fit at the tick size and keep a margin above the floor.
ANNOTATION_FONT_PT = TICK_FONT_PT
assert ANNOTATION_FONT_PT >= MINIMUM_ON_PAGE_FONT_PT

TRACK_SHA = "e6eb9f1aabff24207d9eceeee459bdf0c57d16b2c979c9b7bbccc19141d742ff"
UNIT_SHA = "e593124975f362714d5b7dc99bc21ea2b9f47b92c23e9ca337ac3a3f7478d59e"
HOOK_CELL_SHA = "dcc9d66eda5612d1b46e831a59884f9ba0a61ba77b1f734b9b907a0608bd2603"
HOOK_REPEAT_SHA = "eb5667dfa7ba725850ef169e5f90167a05787de4e82d6a047674a038c8b465bd"
BOOTSTRAP_SEED = 20260812
BOOTSTRAP_ITERATIONS = 10_000
CONTOUR_MASSES = (0.50, 0.80, 0.95)
MEDIA = ("agarose", "liquid")
# Panels E-G clip the hook axis at 20 hooks per cell.  24 of the 29,789 scored
# cells lie above that, and an unclipped axis would compress the 0-10 range that
# carries the phenotype difference.  Every panel names its off-scale cells.
HOOK_AXIS_CAP = 20
PHENOTYPE_STYLE_IDS = {"WT": "TH5861", "PproA": "EM9661", "PproB": "EM9660"}
PANEL_SPECS = {
    "A": {"title": "WT vs PproA", "phenotypes": ("WT", "PproA"), "pairs": (("EM16106", "EM16115"), ("EM16107", "EM16114")), "unit_source": "fig1_raw_paired_units_wt_vs_pproA.csv", "contrast": ("PproA", "WT"), "expected": {"agarose": 18, "liquid": 16}},
    "B": {"title": "WT vs PproB", "phenotypes": ("WT", "PproB"), "pairs": (("EM16106", "EM16310"), ("EM16107", "EM16309")), "unit_source": "fig1_raw_paired_units_wt_vs_pproB.csv", "contrast": ("PproB", "WT"), "expected": {"agarose": 18, "liquid": 18}},
    "C": {"title": "PproA vs PproB", "phenotypes": ("PproA", "PproB"), "pairs": (("EM16309", "EM16115"), ("EM16310", "EM16114")), "unit_source": "fig1_raw_paired_units_ppro.csv", "contrast": ("PproB", "PproA"), "expected": {"agarose": 18, "liquid": 16}},
}
HOOK_MAP = {"E": "A", "F": "B", "G": "C"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


_PARSED_INPUTS: dict[str, pd.DataFrame] = {}


def checked_csv(name: str, expected: str) -> pd.DataFrame:
    """Read one checksum-pinned processed table and return a private copy.

    The checksum is recomputed on every call.  Only the parse is memoised, so
    repeated callers -- panels A-C, panel D and the supplementary contour figure
    all read the same trajectory table -- each still receive an independent
    frame they may mutate.
    """
    path = INPUT_DIR / name
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"checksum mismatch for {path}: {actual}")
    if name not in _PARSED_INPUTS:
        _PARSED_INPUTS[name] = pd.read_csv(path)
    return _PARSED_INPUTS[name].copy()


def _write_table(frame: pd.DataFrame, panel: str, filename: str, *, statistics: bool = False) -> list[Path]:
    roots = [SOURCE_DIR / panel, BUILD_SOURCE / panel]
    if statistics:
        roots = [SOURCE_DIR / panel, BUILD_STATS / panel]
    outputs = []
    for root in roots:
        root.mkdir(parents=True, exist_ok=True)
        path = root / filename
        compression = {"method": "gzip", "compresslevel": 6, "mtime": 0} if path.suffix == ".gz" else None
        frame.to_csv(path, index=False, compression=compression)
        outputs.append(path)
    return outputs


def style_for(phenotype: str) -> dict[str, str]:
    return get_strain_style(PHENOTYPE_STYLE_IDS[phenotype])


def load_direct_tracks(panel: str) -> pd.DataFrame:
    tracks = checked_csv("direct_pair_track_measurements.csv.gz", TRACK_SHA)
    units = checked_csv("paired_experimental_unit_measurements.csv", UNIT_SHA)
    spec = PANEL_SPECS[panel]
    allowed_keys = set(units.loc[units._source_table == spec["unit_source"], "metadata_key"])
    direct = tracks.loc[
        tracks.metadata_key.isin(allowed_keys)
        & tracks.phenotype.isin(spec["phenotypes"])
        & tracks.medium.isin(["agarose", "liquid"])
    ].copy()
    pair_tuples = set(zip(direct.strain_1, direct.strain_2, strict=False))
    assert pair_tuples <= set(spec["pairs"])
    counts = direct.groupby("medium").metadata_key.nunique().to_dict()
    assert counts == spec["expected"], (panel, counts)
    direct["log10_diffusivity"] = np.log10(pd.to_numeric(direct.diffcoeff_cve_mean, errors="raise"))
    direct["speed_um_s"] = pd.to_numeric(direct.meanspeed, errors="raise")
    assert np.isfinite(direct[["speed_um_s", "log10_diffusivity"]]).all().all()
    return direct


def hdr_levels(x: np.ndarray, y: np.ndarray, masses: tuple[float, ...] = CONTOUR_MASSES) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[float]]:
    """Return the density grid and the highest-density thresholds for one cloud.

    Figure 7 no longer draws contours; the speed-versus-diffusivity contour
    panel moved to the supplementary figure, whose builder imports this helper.
    The function stays here because it is defined against the same checksum-
    pinned trajectory table that ``load_direct_tracks`` returns.
    """
    x_grid = np.linspace(3.0, 60.0, 150)
    y_grid = np.linspace(-1.3, 3.0, 160)
    xx, yy = np.meshgrid(x_grid, y_grid)
    density = gaussian_kde(np.vstack([x, y]))(np.vstack([xx.ravel(), yy.ravel()])).reshape(xx.shape)
    flat = np.sort(density.ravel())[::-1]
    cumulative = np.cumsum(flat) / flat.sum()
    thresholds = []
    for mass in masses:
        index = min(int(np.searchsorted(cumulative, mass)), len(flat) - 1)
        thresholds.append(float(flat[index]))
    return xx, yy, density, sorted(thresholds)


def _mm_axes(
    fig: plt.Figure,
    box_mm: tuple[float, float],
    rectangle_mm: tuple[float, float, float, float],
) -> plt.Axes:
    """Add one axes placed in millimetres of the panel's assembly box.

    Example:
        >>> figure = plt.figure(figsize=(55 / 25.4, 84 / 25.4))
        >>> axes = _mm_axes(figure, (55.0, 84.0), (13.0, 10.5, 40.5, 29.0))
    """
    width_mm, height_mm = box_mm
    left, bottom, width, height = rectangle_mm
    return fig.add_axes((left / width_mm, bottom / height_mm, width / width_mm, height / height_mm))


def _paired_unit_row(
    ax: plt.Axes,
    panel: str,
    units: pd.DataFrame,
    column: str,
    positions: dict[str, tuple[float, float]],
) -> None:
    """Draw one metric of one phenotype pair as paired experimental units.

    One marker is one paired experimental unit.  A thin line joins the two
    phenotypes measured in the same ``metadata_key``, so the reader sees the
    within-unit contrast that the bootstrap actually resamples.  Medium is
    carried by marker shape and fill -- filled circle is agarose, open square is
    liquid -- as well as by the gap between the two groups.
    """
    spec = PANEL_SPECS[panel]
    first, second = spec["phenotypes"]
    for medium in MEDIA:
        left, right = positions[medium]
        wide = _paired_unit_means(units, medium, column)
        if len(wide) != spec["expected"][medium]:
            raise AssertionError(f"panel {panel} {medium} has {len(wide)} paired units")
        for phenotype, position in zip((first, second), (left, right), strict=True):
            parts = ax.violinplot(
                [wide[phenotype].to_numpy()], positions=[position], widths=0.80, showextrema=False
            )
            body = parts["bodies"][0]
            body.set_facecolor(style_for(phenotype)["color"])
            body.set_edgecolor("none")
            body.set_alpha(0.28)
            body.set_zorder(0)
        # One horizontal offset per unit, used for both phenotypes, so every
        # joining line starts and ends on its own two markers.
        offsets = np.linspace(-0.20, 0.20, len(wide))
        for offset, (_, row) in zip(offsets, wide.iterrows(), strict=True):
            ax.plot(
                [left + offset, right + offset],
                [row[first], row[second]],
                color=TECHNICAL_COLOR,
                lw=0.35,
                zorder=1,
            )
        for phenotype, position in zip((first, second), (left, right), strict=True):
            fill = style_for(phenotype)["color"]
            edge, edge_width = marker_edge(fill)
            open_marker = medium == "liquid"
            ax.scatter(
                position + offsets,
                wide[phenotype].to_numpy(),
                s=DENSITY_MARKER_SIZE,
                marker=MEDIUM_MARKERS[medium],
                facecolor=BACKGROUND_COLOR if open_marker else fill,
                edgecolor=fill if open_marker else edge,
                linewidths=0.45 if open_marker else edge_width,
                zorder=2,
            )


def _paired_unit_panel(panel: str, units: pd.DataFrame, ratios: pd.DataFrame) -> list[Path]:
    """Draw one phenotype pair as a two-row block of paired experimental units.

    The assembler scales a panel by min(box / viewBox).  A panel drawn at its
    assembly box therefore keeps a scale of 1.0, so every point size requested
    here is the point size on the page.

    Speed sits above effective diffusivity because it is the component that
    discriminates the strains, and because D_eff = v^2 tau / 2 makes the lower
    row a consequence of the upper one.  Both rows plot the per-unit mean of a
    natural logarithm, which is the aggregation the panel D decomposition uses:
    the top row plots mean ln speed, printed in um/s, and the bottom row plots
    mean ln D_eff, printed as log10.  The ratio of the two groups' geometric
    means is therefore the annotated D ratio exactly, and the square of the
    speed-row group ratio is the panel D speed^2 ratio exactly.
    """
    spec = PANEL_SPECS[panel]
    first, second = spec["phenotypes"]
    box = panel_box_mm(FIGURE_ID, panel)
    width = box[0] - AC_LEFT_MM - AC_RIGHT_MARGIN_MM
    fig = plt.figure(figsize=panel_figsize(FIGURE_ID, panel))
    diffusivity_ax = _mm_axes(fig, box, (AC_LEFT_MM, AC_BOTTOM_MM, width, AC_ROW_HEIGHT_MM))
    speed_ax = _mm_axes(
        fig,
        box,
        (AC_LEFT_MM, AC_BOTTOM_MM + AC_ROW_HEIGHT_MM + AC_ROW_GAP_MM, width, AC_ROW_HEIGHT_MM),
    )
    positions = {"agarose": (0.0, 1.0), "liquid": (2.5, 3.5)}
    _paired_unit_row(speed_ax, panel, units, "mean_log10_speed", positions)
    _paired_unit_row(diffusivity_ax, panel, units, "mean_log10_diffusivity", positions)
    diffusivity_ax.axhline(0, color=REFERENCE_COLOR, lw=0.7, ls="--", zorder=1)

    for ax in (speed_ax, diffusivity_ax):
        ax.set_xlim(-0.7, 4.2)
    speed_ax.set_ylim(*SPEED_YLIM_LOG10)
    speed_ax.set_yticks(
        [np.log10(value) for value in SPEED_TICKS_UM_S],
        [f"{value:g}" for value in SPEED_TICKS_UM_S],
    )
    speed_ax.set_ylabel(SPEED_AXIS_LABEL, linespacing=1.1)
    speed_ax.set_xticks([0.0, 1.0, 2.5, 3.5], ["", "", "", ""])
    diffusivity_ax.set_ylim(*DIFFUSIVITY_YLIM_LOG10)
    diffusivity_ax.set_yticks([0, 1, 2])
    diffusivity_ax.set_ylabel(DIFFUSIVITY_AXIS_LABEL, linespacing=1.1)
    diffusivity_ax.set_xticks([0.0, 1.0, 2.5, 3.5], [first, second, first, second])

    # Each header sits above the row it describes, in the margin the layout
    # reserves for it, so neither header eats into the plotted range.  The
    # medium header names the fill convention where the convention is first
    # used, rather than in a key the reader meets further down the page.
    for medium in MEDIA:
        left, right = positions[medium]
        row = ratios.loc[medium]
        speed_ax.text(
            (left + right) / 2.0,
            1.02,
            f"{medium.capitalize()} ({'open' if medium == 'liquid' else 'filled'})\n"
            f"{int(row.n_paired_units)} units",
            transform=speed_ax.get_xaxis_transform(),
            ha="center",
            va="bottom",
            fontsize=TICK_FONT_PT,
            linespacing=1.15,
            clip_on=False,
        )
        # The D ratio header is pinned a point above the diffusivity axes, not
        # centred in the gap, so it reads as the header of the row below it.
        diffusivity_ax.annotate(
            f"D ratio {row.D_ratio:.2f}\n({row.D_ratio_ci95_low:.2f}-{row.D_ratio_ci95_high:.2f})",
            xy=((left + right) / 2.0, 1.0),
            xycoords=diffusivity_ax.get_xaxis_transform(),
            xytext=(0, -5.0),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=TICK_FONT_PT,
            linespacing=1.15,
            annotation_clip=False,
        )
    # The reference line is named in the key, not inside the axes: panel C puts
    # unit means against the line at both ends, so no in-axes label is free of a
    # marker.  What the D ratio divides is stated in the figure legend.
    fig.text(
        0.5,
        0.6 / box[1],
        "violin: kernel density of unit means\ndashed line: D_eff = 1",
        ha="center",
        va="bottom",
        fontsize=TICK_FONT_PT,
        linespacing=1.15,
    )
    return save_figure(fig, BUILD_PANELS / f"{panel}/Figure_7{panel}")


def _paired_unit_means(
    units: pd.DataFrame, medium: str, column: str = "mean_log10_diffusivity"
) -> pd.DataFrame:
    """Return one row per paired unit with a column per phenotype, for one medium."""
    return (
        units[units.medium == medium]
        .pivot(index="metadata_key", columns="phenotype", values=column)
        .dropna()
        .sort_index()
    )


def panels_a_to_c(panel: str, *, check_only: bool = False) -> dict[str, object]:
    direct = load_direct_tracks(panel)
    spec = PANEL_SPECS[panel]
    unit_counts = direct.groupby("medium").metadata_key.nunique().to_dict()
    track_counts = direct.groupby(["medium", "phenotype"], as_index=False).size().rename(columns={"size": "n_trajectories"})
    # The panel D decomposition averages ln D_eff within a unit before it takes
    # the paired contrast.  The plotted quantity must be that same average, or
    # the markers and the annotated ratio would be different statistics.
    direct["ln_diffusivity"] = np.log(pd.to_numeric(direct.diffcoeff_cve_mean, errors="raise"))
    direct["ln_speed"] = np.log(direct.speed_um_s)
    unit_summary = direct.groupby(["metadata_key", "medium", "phenotype"], as_index=False).agg(
        median_speed_um_s=("speed_um_s", "median"),
        median_log10_diffusivity=("log10_diffusivity", "median"),
        mean_ln_speed=("ln_speed", "mean"),
        mean_ln_diffusivity=("ln_diffusivity", "mean"),
        n_trajectories=("speed_um_s", "size"),
    )
    unit_summary["mean_log10_diffusivity"] = unit_summary.mean_ln_diffusivity / np.log(10.0)
    unit_summary["mean_log10_speed"] = unit_summary.mean_ln_speed / np.log(10.0)
    # The plotted speed is the per-unit geometric mean, which is what a log10
    # speed axis reads back in um/s.
    unit_summary["geometric_mean_speed_um_s"] = np.exp(unit_summary.mean_ln_speed)
    unit_summary = unit_summary.drop(columns=["mean_ln_diffusivity", "mean_ln_speed"])
    if check_only:
        return {"unit_counts": unit_counts, "track_rows": len(direct)}
    summary, _ = decomposition_tables()
    ratios = summary[summary.panel == panel].set_index("medium")
    numerator, denominator = spec["contrast"]
    residuals = {}
    speed_residuals = {}
    for medium in MEDIA:
        wide = _paired_unit_means(unit_summary, medium)
        # The geometric mean of a group of plotted log10 values is 10 ** mean,
        # so the ratio of the two groups' geometric means is this difference.
        plotted_ratio = float(10.0 ** (wide[numerator].mean() - wide[denominator].mean()))
        annotated = float(ratios.loc[medium, "D_ratio"])
        residuals[medium] = abs(plotted_ratio / annotated - 1.0)
        assert residuals[medium] < 1e-12, (panel, medium, plotted_ratio, annotated)
        # The speed row must close on panel D the same way: the square of the
        # ratio of the two plotted groups' geometric mean speeds is the
        # component the decomposition calls speed^2.
        speed_wide = _paired_unit_means(unit_summary, medium, "mean_log10_speed")
        plotted_speed_squared = float(
            10.0 ** (2.0 * (speed_wide[numerator].mean() - speed_wide[denominator].mean()))
        )
        component = float(ratios.loc[medium, "speed_squared_ratio"])
        speed_residuals[medium] = abs(plotted_speed_squared / component - 1.0)
        assert speed_residuals[medium] < 1e-12, (panel, medium, plotted_speed_squared, component)
    _write_table(direct[["metadata_key", "date_iso_meta", "medium", "strain_1", "strain_2", "strain", "phenotype", "speed_um_s", "log10_diffusivity", "diffcoeff_cve_mean"]], panel, f"Figure_7{panel}_direct_pair_trajectories.csv.gz")
    _write_table(unit_summary, panel, f"Figure_7{panel}_paired_unit_summaries.csv")
    _write_table(track_counts, panel, f"Figure_7{panel}_counts.csv", statistics=True)
    _paired_unit_panel(panel, unit_summary, ratios)
    return {
        "unit_counts": unit_counts,
        "track_rows": len(direct),
        "max_geometric_mean_residual": float(max(residuals.values())),
        "max_speed_squared_residual": float(max(speed_residuals.values())),
    }


def bootstrap_decomposition(contrasts: pd.DataFrame, rng: np.random.Generator) -> dict[str, float]:
    values = contrasts[["delta_ln_D", "delta_two_ln_speed", "delta_ln_tau"]].to_numpy(dtype=float)
    n = len(values)
    samples = values[rng.integers(0, n, size=(BOOTSTRAP_ITERATIONS, n))].mean(axis=1)
    row: dict[str, float] = {}
    names = ["D_ratio", "speed_squared_ratio", "tau_ratio"]
    for index, name in enumerate(names):
        estimate = float(np.exp(values[:, index].mean()))
        low, high = np.exp(np.quantile(samples[:, index], [0.025, 0.975]))
        row[name] = estimate
        row[f"{name}_ci95_low"] = float(low)
        row[f"{name}_ci95_high"] = float(high)
    mean_log = values.mean(axis=0)
    row["speed_squared_log_share"] = float(mean_log[1] / mean_log[0])
    row["tau_log_share"] = float(mean_log[2] / mean_log[0])
    row["closure_error"] = float(mean_log[0] - mean_log[1] - mean_log[2])
    return row


@lru_cache(maxsize=1)
def decomposition_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return the paired log-contrast summary and the per-unit contrasts.

    The bootstrap draws from one generator seeded at ``BOOTSTRAP_SEED`` and
    walks the panels in the order A, B, C with agarose before liquid.  Panels
    A-C annotate the D ratio computed here and panel D plots its two
    components, so the whole figure must share this single deterministic pass.

    Example:
        >>> summary, contrasts = decomposition_tables()
        >>> len(summary)
        6
    """
    all_contrasts = []
    results = []
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    for panel, spec in PANEL_SPECS.items():
        direct = load_direct_tracks(panel)
        direct["ln_D"] = np.log(direct.diffcoeff_cve_mean)
        direct["two_ln_speed"] = 2 * np.log(direct.meanspeed)
        direct["ln_tau"] = direct.ln_D - direct.two_ln_speed + np.log(2.0)
        assert np.allclose(direct.ln_D, direct.two_ln_speed + direct.ln_tau - np.log(2.0), rtol=0, atol=1e-12)
        units = direct.groupby(["metadata_key", "medium", "phenotype"], as_index=False).agg(ln_D=("ln_D", "mean"), two_ln_speed=("two_ln_speed", "mean"), ln_tau=("ln_tau", "mean"))
        numerator, denominator = spec["contrast"]
        wide = units.pivot(index=["metadata_key", "medium"], columns="phenotype", values=["ln_D", "two_ln_speed", "ln_tau"])
        for medium in MEDIA:
            one = wide.xs(medium, level="medium")
            contrasts = pd.DataFrame({
                "metadata_key": one.index,
                "panel": panel,
                "comparison": f"{numerator}/{denominator}",
                "medium": medium,
                "delta_ln_D": one["ln_D", numerator] - one["ln_D", denominator],
                "delta_two_ln_speed": one["two_ln_speed", numerator] - one["two_ln_speed", denominator],
                "delta_ln_tau": one["ln_tau", numerator] - one["ln_tau", denominator],
            }).reset_index(drop=True)
            contrasts["closure_error"] = contrasts.delta_ln_D - contrasts.delta_two_ln_speed - contrasts.delta_ln_tau
            assert contrasts.closure_error.abs().max() < 1e-12
            row = {"panel": panel, "comparison": f"{numerator}/{denominator}", "medium": medium, "n_paired_units": len(contrasts), **bootstrap_decomposition(contrasts, rng)}
            results.append(row)
            all_contrasts.append(contrasts)
    summary = pd.DataFrame(results)
    contrasts = pd.concat(all_contrasts, ignore_index=True)
    expected_counts = {("A", "agarose"): 18, ("A", "liquid"): 16, ("B", "agarose"): 18, ("B", "liquid"): 18, ("C", "agarose"): 18, ("C", "liquid"): 16}
    assert {(row.panel, row.medium): row.n_paired_units for row in summary.itertuples()} == expected_counts
    return summary, contrasts


def panel_d(*, check_only: bool = False) -> dict[str, object]:
    summary, contrasts = decomposition_tables()
    max_closure_error = float(contrasts.closure_error.abs().max())
    if check_only:
        return {"rows": len(summary), "max_closure_error": max_closure_error}
    _write_table(contrasts, "D", "Figure_7D_unit_log_contrasts.csv")
    _write_table(summary, "D", "Figure_7D_effective_diffusivity_decomposition.csv", statistics=True)

    # Rendered at the 173 x 56 mm assembly strip so the assembly scale stays 1.0.
    box = panel_box_mm(FIGURE_ID, "D")
    fig = plt.figure(figsize=panel_figsize(FIGURE_ID, "D"))
    axes_width = (box[0] - D_LEFT_MM - D_RIGHT_MARGIN_MM - 2 * D_GAP_MM) / 3.0
    axes_height = box[1] - D_BOTTOM_MM - D_TOP_MARGIN_MM
    axes = [
        _mm_axes(
            fig,
            box,
            (D_LEFT_MM + index * (axes_width + D_GAP_MM), D_BOTTOM_MM, axes_width, axes_height),
        )
        for index in range(3)
    ]
    # Each row is a bar from the reference at 1 to the estimate, so a reader
    # reads the effect as a length.  On a log axis the two component lengths add
    # to the product length, which is why the product row returns here: without
    # it the reader has to multiply two numbers in the head.
    rows = [
        (2, "speed_squared_ratio", COMPONENT_INK, 0.24, 0.15, 0.7),
        (1, "tau_ratio", COMPONENT_INK, 0.24, 0.15, 0.7),
        (0, "D_ratio", COMPONENT_INK, 0.34, 0.20, 0.9),
    ]
    for ax, (panel, spec) in zip(axes, PANEL_SPECS.items(), strict=True):
        sub = summary[summary.panel == panel]
        for y, component, fill, height, spread, edge_width in rows:
            edge_ink = PRODUCT_INK if component == "D_ratio" else fill
            for medium in MEDIA:
                row = sub[sub.medium == medium].iloc[0]
                x = float(row[component])
                low = float(row[f"{component}_ci95_low"])
                high = float(row[f"{component}_ci95_high"])
                position = y + (-spread if medium == "agarose" else spread)
                open_mark = medium == "liquid"
                ax.barh(
                    position,
                    x - 1.0,
                    left=1.0,
                    height=height,
                    color=BACKGROUND_COLOR if open_mark else fill,
                    edgecolor=edge_ink,
                    linewidth=edge_width,
                    zorder=2,
                )
                ax.errorbar(
                    x,
                    position,
                    xerr=[[x - low], [high - x]],
                    fmt="none",
                    ecolor=SUMMARY_INK,
                    elinewidth=0.7,
                    capsize=1.6,
                    capthick=0.7,
                    zorder=3,
                )
                point_edge, point_edge_width = marker_edge(SUMMARY_INK)
                ax.plot(
                    x,
                    position,
                    marker=MEDIUM_MARKERS[medium],
                    ls="none",
                    ms=np.sqrt(POINT_MARKER_SIZE),
                    markerfacecolor=BACKGROUND_COLOR if open_mark else SUMMARY_INK,
                    markeredgecolor=SUMMARY_INK if open_mark else point_edge,
                    markeredgewidth=0.5 if open_mark else point_edge_width,
                    zorder=4,
                )
                # Panel B carries the smallest effects, so its bars are honestly
                # short.  The estimate is therefore printed outward of its own
                # interval, where no bar can reach it.
                ax.annotate(
                    f"{x:.2f}",
                    xy=(high if x >= 1.0 else low, position),
                    xytext=(2.5 if x >= 1.0 else -2.5, 0),
                    textcoords="offset points",
                    ha="left" if x >= 1.0 else "right",
                    va="center",
                    fontsize=TICK_FONT_PT,
                    color=TEXT_COLOR,
                    annotation_clip=False,
                    zorder=5,
                )
        # The rule separates the two measured-and-derived components above from
        # the product below, as in a written multiplication.
        ax.axhline(0.5, color=REFERENCE_COLOR, lw=0.5, zorder=1)
        ax.axvline(1, color=REFERENCE_COLOR, lw=0.7, ls="--", zorder=1)
        ax.set_xscale("log")
        ax.set_xlim(*D_XLIM)
        ax.set_ylim(-0.55, 2.55)
        ax.set_title(spec["title"])
        units = {row.medium: row.n_paired_units for row in sub.itertuples()}
        ax.set_xlabel(
            f"Ratio ({spec['contrast'][0]}/{spec['contrast'][1]})\n"
            f"{units['agarose']} agarose, {units['liquid']} liquid paired units",
            fontsize=TICK_FONT_PT,
            linespacing=1.2,
        )
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_xticks(list(D_XTICKS))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _position: f"{value:g}"))
        ax.set_yticks([0, 1, 2], ["D_eff\n(product)", "τ = 2D/v²\n(derived)", "speed²\n(measured)"])
        ax.tick_params(axis="y", length=0)
        if ax is not axes[0]:
            ax.set_yticklabels([])
    # The product row is the one the reader should leave with, so its name is
    # the only bold text in the strip.
    axes[0].get_yticklabels()[0].set_fontweight("bold")
    point_edge, point_edge_width = marker_edge(SUMMARY_INK)
    fig.legend(
        handles=[
            Line2D(
                [0], [0], marker=MEDIUM_MARKERS["agarose"], color=SUMMARY_INK,
                markerfacecolor=SUMMARY_INK, markeredgecolor=point_edge,
                markeredgewidth=point_edge_width, lw=0, label="agarose",
            ),
            Line2D(
                [0], [0], marker=MEDIUM_MARKERS["liquid"], color=SUMMARY_INK,
                markerfacecolor=BACKGROUND_COLOR, markeredgecolor=SUMMARY_INK,
                markeredgewidth=0.5, lw=0, label="liquid",
            ),
        ],
        loc="upper left",
        # Clear of the assembler's panel letter, which sits in the top-left
        # corner of the strip, and aligned with the left edge of the axes.
        bbox_to_anchor=(D_LEFT_MM / box[0], 0.998),
        ncol=2,
        frameon=False,
        handletextpad=0.4,
        columnspacing=1.4,
        borderpad=0.0,
        borderaxespad=0.0,
    )
    fig.text(
        0.5,
        0.6 / box[1],
        "D_eff = speed² × τ / 2, so on this log axis the two component bars add to the D_eff bar",
        ha="center",
        va="bottom",
        fontsize=TICK_FONT_PT,
    )
    save_figure(fig, BUILD_PANELS / "D/Figure_7D")
    return {"rows": len(summary), "max_closure_error": max_closure_error}


def _draw_discrete_counts(ax: plt.Axes, cells: pd.DataFrame, repeats: pd.DataFrame, order: list[str], axis_max: int) -> int:
    """Draw one integer-count distribution per phenotype, Figure 1 style.

    Hook count is an integer, so a kernel density smears the zero class and
    prints scalloped edges.  This geometry is the ``discrete_count`` recipe of
    ``analyses/figure_01/plotting.py``: one mark per observed integer whose
    half-width follows the square root of its frequency, individual dots where
    a count is carried by 12 cells or fewer, grey markers for the independent
    day replicates, and a black bar at the mean of the replicate means.

    Returns the number of cells that fall above the clipped hook axis.
    """
    off_scale = 0
    for index, phenotype in enumerate(order):
        subset = cells[cells.plot_label == phenotype]
        table = subset.groupby("hook_count", as_index=False).size().rename(columns={"size": "frequency"})
        max_frequency = max(1.0, float(table.frequency.max()))
        color = style_for(phenotype)["color"]
        for row in table.itertuples(index=False):
            value = float(row.hook_count)
            frequency = float(row.frequency)
            half_width = 0.04 + 0.24 * np.sqrt(frequency / max_frequency)
            if value > axis_max:
                off_scale += int(frequency)
                continue
            if frequency <= 12:
                xs = np.linspace(index - half_width, index + half_width, int(frequency))
                cell_edge, cell_edge_width = marker_edge(color)
                ax.scatter(
                    xs,
                    np.full(len(xs), value),
                    s=DENSITY_MARKER_SIZE,
                    color=color,
                    alpha=0.25,
                    edgecolor=cell_edge,
                    linewidth=cell_edge_width,
                )
            else:
                ax.hlines(value, index - half_width, index + half_width, color=color, alpha=0.72, linewidth=1.15)

        replicate_means = pd.to_numeric(
            repeats.loc[repeats.plot_label == phenotype, "hook_count_replicate_mean"], errors="raise"
        ).to_numpy(dtype=float)
        assert len(replicate_means) == 6, (phenotype, len(replicate_means))
        replicate_edge, replicate_edge_width = marker_edge(REFERENCE_COLOR)
        ax.scatter(
            index + np.linspace(-0.22, 0.22, len(replicate_means)),
            replicate_means,
            s=POINT_MARKER_SIZE,
            color=REFERENCE_COLOR,
            edgecolor=replicate_edge,
            linewidth=replicate_edge_width,
            zorder=4,
        )
        mean = float(np.mean(replicate_means))
        deviation = float(np.std(replicate_means, ddof=1))
        ax.hlines(mean, index - 0.32, index + 0.32, color=SUMMARY_INK, linewidth=0.9, zorder=3)
        ax.text(
            index,
            axis_max + 0.4,
            f"{mean:.2f}±{deviation:.2f}\nN={len(subset):,}",
            ha="center",
            va="bottom",
            linespacing=1.05,
            fontsize=ANNOTATION_FONT_PT,
        )
    return off_scale


def hook_panel(panel: str, *, check_only: bool = False) -> dict[str, object]:
    cells = checked_csv("hook_count_per_cell.csv", HOOK_CELL_SHA)
    repeats = checked_csv("hook_count_repeat_means.csv", HOOK_REPEAT_SHA)
    legacy = HOOK_MAP[panel]
    cells = cells[cells.collapsed_panel_label == legacy].copy()
    cells["included_in_violin_display"] = cells.included_in_violin_display.astype(str).str.lower().eq("true")
    # The shipped display flag caps the hook axis; the constant must agree with
    # it so the panel and the processed table describe the same clip.
    assert (cells.included_in_violin_display == (cells.hook_count <= HOOK_AXIS_CAP)).all()
    repeats = repeats[repeats.collapsed_panel_label == legacy].copy()
    order = cells.collapsed_pair_title.iloc[0].split(" vs ")
    counts = cells.groupby("plot_label").size().to_dict()
    repeat_counts = repeats.groupby("plot_label").collapsed_repeat_id.nunique().to_dict()
    assert set(repeat_counts.values()) == {6}
    expected = {"E": {"WT": 2931, "PproA": 3524}, "F": {"WT": 4018, "PproB": 4918}, "G": {"PproA": 7904, "PproB": 6494}}[panel]
    assert counts == expected
    audit = cells.groupby("plot_label", as_index=False).agg(n_cells=("hook_count", "size"), mean_hooks=("hook_count", "mean"), median_hooks=("hook_count", "median"), q1=("hook_count", lambda x: x.quantile(.25)), q3=("hook_count", lambda x: x.quantile(.75)), n_day_repeats=("collapsed_repeat_id", "nunique"))
    axis_max = min(HOOK_AXIS_CAP, int(cells.hook_count.max()))
    audit["n_cells_above_axis_cap"] = [int((cells.loc[cells.plot_label == label, "hook_count"] > axis_max).sum()) for label in audit.plot_label]
    audit["hook_axis_cap"] = axis_max
    audit["mean_of_day_repeat_means"] = [float(repeats.loc[repeats.plot_label == label, "hook_count_replicate_mean"].mean()) for label in audit.plot_label]
    if check_only:
        return {"cell_counts": counts, "repeat_counts": repeat_counts}
    _write_table(cells[["collapsed_repeat_id", "plot_label", "hook_count", "source_file", "roi_id", "cell_index"]], panel, f"Figure_7{panel}_cell_points.csv")
    _write_table(repeats, panel, f"Figure_7{panel}_day_repeat_means.csv")
    _write_table(audit, panel, f"Figure_7{panel}_numeric_audit.csv", statistics=True)

    # Rendered at the 55 x 56 mm assembly box so the assembly scale stays 1.0.
    fig, ax = plt.subplots(figsize=panel_figsize(FIGURE_ID, panel), constrained_layout=True)
    fig.get_layout_engine().set(w_pad=0.012, h_pad=0.012, wspace=0.0, hspace=0.0)
    # Panel E tops out at 15 hooks, so an axis fixed at the shared cap would
    # leave a third of the panel blank.  Each panel clips at its own maximum,
    # never above the shared cap.
    off_scale = _draw_discrete_counts(ax, cells, repeats, order, axis_max)
    ax.set_xticks(range(len(order)), order)
    ax.tick_params(axis="both", pad=1.5)
    ax.set_xlabel("")
    ax.set_ylabel("Hooks per cell", labelpad=1.5)
    ax.set_title(cells.collapsed_pair_title.iloc[0])
    ax.set_xlim(-0.6, len(order) - 0.4)
    # The annotation block sits above the clipped axis, so the upper limit adds
    # room for two lines of 6 pt text.
    ax.set_ylim(-0.7, axis_max + max(3.2, 0.22 * axis_max))
    # Hook counts are integers, so the axis must not offer fractional ticks.
    ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6, steps=[1, 2, 2.5, 5, 10]))
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.5, alpha=0.8)
    ax.set_axisbelow(True)
    frequency_label = "Cell-count frequency"
    if off_scale:
        frequency_label = f"Cell-count frequency ({off_scale} cells above {axis_max})"
    fig.legend(
        handles=[
            # The frequency mark stands for a concept, not for one strain, so it
            # takes the neutral key swatch rather than borrowing a strain hue.
            Line2D([], [], color=KEY_SWATCH, linewidth=1.2, label=frequency_label),
            Line2D(
                [], [], marker="o", linestyle="none", color=REFERENCE_COLOR,
                markersize=np.sqrt(POINT_MARKER_SIZE),
                label="Independent day replicate mean",
            ),
            Line2D([], [], color=SUMMARY_INK, linewidth=1.2, label="Mean of replicate means"),
        ],
        frameon=False,
        loc="outside lower center",
        ncols=1,
        handlelength=1.2,
        handletextpad=0.5,
        labelspacing=0.2,
        borderpad=0.0,
        borderaxespad=0.0,
    )
    save_figure(fig, BUILD_PANELS / f"{panel}/Figure_7{panel}")
    return {"cell_counts": counts, "repeat_counts": repeat_counts, "cells_above_axis_cap": off_scale}


def _panel_limitations(panel: str) -> list[str]:
    """Return the limitations that apply to one panel on top of the shared pair."""
    if panel in "ABC":
        return [
            "Each marker is the per-unit mean of a natural logarithm over that unit's trajectories -- ln speed on the upper row, ln D_eff on the lower one -- so a unit contributes one value regardless of how many trajectories it carries.",
            "The annotated D ratio is the paired bootstrap estimate from the panel D decomposition table, not a test.",
        ]
    if panel == "D":
        return [
            "Tau is derived exactly as 2*D_eff/v^2 and is a persistence-equivalent timescale, not an independent measurement.",
            "The three rows are not independent: the product row is the exact product of the two component rows, printed so the reader does not have to multiply.",
        ]
    return [
        f"The hook axis is clipped at {HOOK_AXIS_CAP} hooks per cell; the panel key names the cells above the clip and the numeric audit counts them.",
        "The inferential unit is the independent day replicate; the six replicate means and their mean are the plotted summary, not the per-cell frequencies.",
    ]


def write_provenance(results: dict[str, object]) -> None:
    inputs = []
    for path in [
        Path(__file__),
        INPUT_DIR / "direct_pair_track_measurements.csv.gz",
        INPUT_DIR / "paired_experimental_unit_measurements.csv",
        INPUT_DIR / "hook_count_per_cell.csv",
        INPUT_DIR / "hook_count_repeat_means.csv",
    ]:
        inputs.append({"relative_path": path.relative_to(PROJECT).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    outputs = []
    paths = [*BUILD_PANELS.rglob("Figure_7*.*"), *BUILD_SOURCE.rglob("*"), *BUILD_STATS.rglob("*")]
    for path in sorted(item for item in paths if item.is_file()):
        outputs.append({"relative_path": path.relative_to(PROJECT).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    document = {
        "schema_version": "1.0.0",
        "figure_id": "Figure_7_revision",
        "generated_at_utc": datetime(2026, 8, 12, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        "command": [".venv/bin/python", "analyses/figure_07_revision/build_figure_07_revision.py"],
        "backend": "Python 3.12",
        "inputs": inputs,
        "software": {
            "python": platform.python_version(),
            "matplotlib": matplotlib.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "random_seeds": {"paired_unit_bootstrap": BOOTSTRAP_SEED},
        "parameters": {
            "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
            "paired_unit_statistic": "per-unit mean of ln speed, displayed in um/s, above per-unit mean of ln D_eff, displayed as log10",
            "ratio_axis_limits": list(D_XLIM),
            "hook_axis_cap": HOOK_AXIS_CAP,
            "hook_count_geometry": "discrete_count, matching analyses/figure_01 panels C, D and H",
            # hdr_levels stays in this module for the supplementary contour
            # figure; Figure 7 itself no longer draws probability contours.
            "contour_probability_mass": list(CONTOUR_MASSES),
            "direct_pair_filter": "metadata keys from reciprocal-label paired-unit tables",
        },
        "results": results,
        "outputs": outputs,
        "interpretation_limit": "The plotted tau is derived exactly as 2*D_eff/v^2 and is not an independent directional-persistence measurement.",
    }
    (Path(__file__).parent / "provenance.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    for panel, result in results.items():
        panel_inputs = [INPUT_DIR / "direct_pair_track_measurements.csv.gz", INPUT_DIR / "paired_experimental_unit_measurements.csv"] if panel in "ABCD" else [INPUT_DIR / "hook_count_per_cell.csv", INPUT_DIR / "hook_count_repeat_means.csv"]
        panel_doc = {
            "schema_version": "1.0.0",
            "panel_id": f"F7_{panel}",
            "status": "partial_reproduction",
            "generated_at_utc": document["generated_at_utc"],
            "command": [".venv/bin/python", "analyses/figure_07_revision/build_figure_07_revision.py", "--panel", panel],
            "backend": document["backend"],
            "inputs": [{"relative_path": path.relative_to(PROJECT).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in [Path(__file__), *panel_inputs]],
            "outputs": [item for item in outputs if f"/Figure_7/{panel}/" in item["relative_path"] or f"Figure_7{panel}_" in item["relative_path"]],
            "software": document["software"],
            # Panels A-C annotate the bootstrap D ratio and its CI, so they
            # depend on the same seed as panel D.
            "random_seeds": document["random_seeds"] if panel in "ABCD" else {},
            "parameters": document["parameters"],
            "results": result,
            "limitations": [
                "The canonical run starts from migrated direct-pair track and paired-unit tables, not raw tracking acquisitions.",
                "The revised panel has not yet passed visual acceptance against the July reference.",
            ]
            + _panel_limitations(panel),
            "interpretation_limit": document["interpretation_limit"] if panel == "D" else "",
        }
        metadata = Path(__file__).parent / f"panel_{panel.lower()}/metadata"
        metadata.mkdir(parents=True, exist_ok=True)
        (metadata / "provenance.json").write_text(json.dumps(panel_doc, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", choices=list("ABCDEFG") + ["all"], default="all")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    apply_publication_style()
    builders = {"A": lambda **kw: panels_a_to_c("A", **kw), "B": lambda **kw: panels_a_to_c("B", **kw), "C": lambda **kw: panels_a_to_c("C", **kw), "D": panel_d, "E": lambda **kw: hook_panel("E", **kw), "F": lambda **kw: hook_panel("F", **kw), "G": lambda **kw: hook_panel("G", **kw)}
    selected = list(builders) if args.panel == "all" else [args.panel]
    results = {panel: builders[panel](check_only=args.check) for panel in selected}
    if not args.check:
        write_provenance(results)
    print(json.dumps(results, indent=2, default=float))


if __name__ == "__main__":
    main()
