#!/usr/bin/env python3
"""Build two candidate designs for Figure 7 panels A-C and assemble both full figures.

Historical record.  A coauthor asked for a fair test of two replacements for the
pairwise enrichment maps: overlapping contours, or paired plots of the
experimental units.  Both candidates are drawn here at the same 55 x 54 mm
assembly box, with the same theme, so the comparison is about the design and not
about the size.

The PI reviewed both at final size and chose the paired-unit design.  It is now
the canonical A-C design in ``build_figure_07_revision.py``, where the plotted
per-unit statistic is the mean of ln D_eff rather than the median used here.
This script still runs against the canonical tables and is kept only so the
comparison stays reproducible.

This script is read-only with respect to the canonical build.  It reads the
canonical tables, imports helpers from
``analyses/figure_07_revision/build_figure_07_revision.py`` without changing it,
and writes only under ``build/diagnostics/Figure_7_candidates``.

Run:
    PYTHONPATH=$PWD/src MPLBACKEND=Agg .venv/bin/python \
        analyses/figure_07_revision/build_candidates.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))

from flagella_repro.figure_qa import svg_metrics  # noqa: E402
from flagella_repro.theme import (  # noqa: E402
    BASE_FONT_PT,
    MINIMUM_ON_PAGE_FONT_PT,
    PALETTE,
    TICK_FONT_PT,
    apply_publication_style,
    panel_box_mm,
    panel_figsize,
    save_figure,
)

FIGURE_ID = "Figure_7"
CANDIDATE_ROOT = PROJECT / "build/diagnostics/Figure_7_candidates"
CANONICAL_BUILDER = PROJECT / "analyses/figure_07_revision/build_figure_07_revision.py"
CANONICAL_ASSEMBLY = PROJECT / "config/assembly_figure_07.yaml"
DECOMPOSITION = (
    PROJECT / "build/statistics/Figure_7/D/Figure_7D_effective_diffusivity_decomposition.csv"
)
UNIT_SUMMARY_ROOT = PROJECT / "build/source_data/Figure_7"

REFERENCE_COLOR = PALETTE["neutral"]["reference"]
TECHNICAL_COLOR = PALETTE["neutral"]["technical"]
TEXT_COLOR = PALETTE["neutral"]["text"]

# Two levels, not three.  At 55 mm the middle 80 % ring of the canonical panel
# adds a third closed curve per phenotype without adding information: the reader
# only needs the core and the extent.  See the module docstring of the report.
CANDIDATE_MASSES = (0.50, 0.95)
MEDIA = ("agarose", "liquid")


def _load_canonical():
    """Import the canonical builder as a module without modifying or running it."""
    spec = importlib.util.spec_from_file_location("figure_07_revision_canonical", CANONICAL_BUILDER)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import {CANONICAL_BUILDER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CANONICAL = _load_canonical()
PANEL_SPECS = CANONICAL.PANEL_SPECS
style_for = CANONICAL.style_for
load_direct_tracks = CANONICAL.load_direct_tracks
hdr_levels = CANONICAL.hdr_levels


def load_unit_medians(panel: str) -> pd.DataFrame:
    """Return the canonical per-unit medians for one panel, with the counts checked."""
    spec = PANEL_SPECS[panel]
    path = UNIT_SUMMARY_ROOT / panel / f"Figure_7{panel}_paired_unit_summaries.csv"
    frame = pd.read_csv(path)
    counts = frame.groupby("medium").metadata_key.nunique().to_dict()
    if counts != spec["expected"]:
        raise AssertionError(f"panel {panel} paired-unit counts {counts} != {spec['expected']}")
    if set(frame.phenotype) != set(spec["phenotypes"]):
        raise AssertionError(f"panel {panel} phenotypes {set(frame.phenotype)}")
    return frame


def load_ratios(panel: str) -> pd.DataFrame:
    """Return the already-bootstrapped paired D_eff ratios for one panel."""
    frame = pd.read_csv(DECOMPOSITION)
    frame = frame[frame.panel == panel]
    spec = PANEL_SPECS[panel]
    expected = f"{spec['contrast'][0]}/{spec['contrast'][1]}"
    if set(frame.comparison) != {expected}:
        raise AssertionError(f"panel {panel} comparison {set(frame.comparison)} != {expected}")
    counts = {row.medium: row.n_paired_units for row in frame.itertuples()}
    if counts != spec["expected"]:
        raise AssertionError(f"panel {panel} ratio counts {counts} != {spec['expected']}")
    return frame.set_index("medium")


def contour_candidate(panel: str, direct: pd.DataFrame) -> list[Path]:
    """Draw the overlapping-contour candidate at the printed panel size.

    The readability fix is a difference in kind, not only in shade: the first
    phenotype of the pair is a filled translucent band, the second is an
    outline.  Panels B and C put two neighbouring reds against each other, and
    a fill against a line stays separable where two line colours do not.
    """
    spec = PANEL_SPECS[panel]
    filled, outlined = spec["phenotypes"]
    fig, axes = plt.subplots(
        2,
        1,
        figsize=panel_figsize(FIGURE_ID, panel),
        sharex=True,
        sharey=True,
        constrained_layout=True,
    )
    fill_color = style_for(filled)["color"]
    line_color = style_for(outlined)["color"]
    for ax, medium in zip(axes, MEDIA, strict=True):
        medium_data = direct[direct.medium == medium]
        for phenotype in spec["phenotypes"]:
            one = medium_data[medium_data.phenotype == phenotype]
            xx, yy, density, levels = hdr_levels(
                one.speed_um_s.to_numpy(),
                one.log10_diffusivity.to_numpy(),
                masses=CANDIDATE_MASSES,
            )
            outer, inner = levels
            if not outer < inner < density.max():
                raise AssertionError(f"panel {panel} {medium} {phenotype} degenerate levels")
            if phenotype == filled:
                ax.contourf(
                    xx,
                    yy,
                    density,
                    levels=[outer, inner, float(density.max())],
                    colors=[to_rgba(fill_color, 0.22), to_rgba(fill_color, 0.50)],
                    zorder=1,
                )
            else:
                ax.contour(
                    xx,
                    yy,
                    density,
                    levels=[outer, inner],
                    colors=[line_color],
                    linewidths=[0.55, 1.1],
                    zorder=2,
                )
        ax.axhline(0, color=REFERENCE_COLOR, lw=0.7, ls="--", zorder=3)
        ax.set_xlim(3, 60)
        # The density grid stops at -1.3, so the strip below the reference line
        # holds the counts without touching a contour.
        ax.set_ylim(-1.7, 3.0)
        ax.set_xticks([10, 20, 30, 40, 50, 60])
        ax.set_yticks([-1, 0, 1, 2, 3])
        ax.text(
            0.03,
            0.96,
            medium.capitalize(),
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=TICK_FONT_PT,
            zorder=4,
        )
        ax.text(
            0.97,
            0.02,
            f"{medium_data.metadata_key.nunique()} paired units\n"
            f"{len(medium_data):,} trajectories",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=TICK_FONT_PT,
            linespacing=1.05,
            zorder=4,
        )
    axes[1].set_xlabel("Swimming speed (µm/s)")
    fig.supylabel("log10 effective diffusivity,\nD_eff (µm²/s)", fontsize=BASE_FONT_PT)
    fig.supxlabel("50 % and 95 % probability contours", fontsize=TICK_FONT_PT)
    handles = [
        Patch(facecolor=to_rgba(fill_color, 0.50), edgecolor="none", label=filled),
        Line2D([0], [0], color=line_color, lw=1.1, label=outlined),
        Line2D([0], [0], color=REFERENCE_COLOR, lw=0.7, ls="--", label="D_eff = 1"),
    ]
    fig.legend(
        handles=handles,
        loc="outside upper center",
        ncol=3,
        frameon=False,
        handlelength=1.5,
        handletextpad=0.4,
        columnspacing=1.1,
        borderpad=0.0,
    )
    return save_figure(fig, CANDIDATE_ROOT / f"contour/{panel}/Figure_7{panel}")


def paired_candidate(panel: str, units: pd.DataFrame, ratios: pd.DataFrame) -> list[Path]:
    """Draw the paired-unit candidate at the printed panel size.

    One marker per paired experimental unit, joined to its partner measured in
    the same metadata_key.  The panel shows D_eff only; speed and the derived
    timescale stay in panel D.
    """
    spec = PANEL_SPECS[panel]
    first, second = spec["phenotypes"]
    numerator, denominator = spec["contrast"]
    fig, ax = plt.subplots(figsize=panel_figsize(FIGURE_ID, panel), constrained_layout=True)
    positions = {"agarose": (0.0, 1.0), "liquid": (2.5, 3.5)}
    for medium in MEDIA:
        left, right = positions[medium]
        sub = units[units.medium == medium]
        wide = sub.pivot(
            index="metadata_key", columns="phenotype", values="median_log10_diffusivity"
        ).dropna()
        wide = wide.sort_index()
        if len(wide) != spec["expected"][medium]:
            raise AssertionError(f"panel {panel} {medium} has {len(wide)} paired units")
        # One horizontal offset per unit, used for both phenotypes, so every
        # joining line starts and ends on its own two markers.
        offsets = np.linspace(-0.11, 0.11, len(wide))
        for phenotype, position in zip((first, second), (left, right), strict=True):
            parts = ax.violinplot(
                [wide[phenotype].to_numpy()], positions=[position], widths=0.80, showextrema=False
            )
            body = parts["bodies"][0]
            body.set_facecolor(style_for(phenotype)["color"])
            body.set_edgecolor("none")
            body.set_alpha(0.28)
            body.set_zorder(0)
        for offset, (_, row) in zip(offsets, wide.iterrows(), strict=True):
            ax.plot(
                [left + offset, right + offset],
                [row[first], row[second]],
                color=TECHNICAL_COLOR,
                lw=0.35,
                zorder=1,
            )
        for phenotype, position in zip((first, second), (left, right), strict=True):
            ax.scatter(
                position + offsets,
                wide[phenotype].to_numpy(),
                s=6.0,
                color=style_for(phenotype)["color"],
                edgecolor=TEXT_COLOR,
                lw=0.2,
                zorder=2,
            )
        row = ratios.loc[medium]
        ax.text(
            (left + right) / 2.0,
            2.98,
            f"{medium.capitalize()}, {int(row.n_paired_units)} units\n"
            f"D ratio {row.D_ratio:.2f}\n"
            f"({row.D_ratio_ci95_low:.2f}-{row.D_ratio_ci95_high:.2f})",
            ha="center",
            va="top",
            fontsize=TICK_FONT_PT,
            linespacing=1.15,
            zorder=4,
        )
    ax.axhline(0, color=REFERENCE_COLOR, lw=0.7, ls="--", zorder=1)
    ax.set_xlim(-0.7, 4.2)
    ax.set_ylim(-0.45, 3.05)
    ax.set_xticks([0.0, 1.0, 2.5, 3.5], [first, second, first, second])
    ax.set_yticks([0, 1, 2])
    ax.set_ylabel("Unit median log10 D_eff (µm²/s)")
    # The reference line is named in the key, not inside the axes: panel C puts
    # unit medians against the line at both ends, so no in-axes label is free of
    # a marker.
    fig.supxlabel(
        f"D ratio = {numerator}/{denominator}, 95 % CI in brackets\n"
        "violin: kernel density of unit medians\n"
        "dashed line: D_eff = 1",
        fontsize=TICK_FONT_PT,
        linespacing=1.15,
    )
    return save_figure(fig, CANDIDATE_ROOT / f"paired/{panel}/Figure_7{panel}")


def write_assembly(candidate: str) -> Path:
    """Copy the canonical assembly config, repointing A-C and the output stem."""
    config = yaml.safe_load(CANONICAL_ASSEMBLY.read_text(encoding="utf-8"))
    directory = CANDIDATE_ROOT / candidate
    directory.mkdir(parents=True, exist_ok=True)
    for panel in config["panels"]:
        label = panel.get("label")
        if label in PANEL_SPECS:
            source = directory / f"{label}/Figure_7{label}.svg"
            panel["source"] = source.relative_to(PROJECT).as_posix()
    stem = directory / f"Figure_7_candidate_{candidate}"
    config["output_stem"] = stem.relative_to(PROJECT).as_posix()
    path = directory / "assembly.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path


def assemble(candidate: str) -> Path:
    """Assemble the full figure for one candidate and rasterize it with rsvg-convert."""
    config = write_assembly(candidate)
    subprocess.run(
        [
            str(PROJECT / ".venv/bin/python"),
            str(PROJECT / "analyses/assembly/assemble_svg.py"),
            "--root",
            str(PROJECT),
            "--config",
            str(config),
        ],
        check=True,
        capture_output=True,
    )
    svg = CANDIDATE_ROOT / candidate / f"Figure_7_candidate_{candidate}.svg"
    png = svg.with_suffix(".png")
    # The Python CairoSVG binding is broken on this arm64 interpreter, so the
    # rsvg-convert binary does the rasterization.
    subprocess.run(
        ["rsvg-convert", "-d", "300", "-p", "300", "-f", "png", "-o", str(png), str(svg)],
        check=True,
        capture_output=True,
    )
    return png


def qa(candidate: str) -> list[dict[str, object]]:
    """Report the minimum on-page font size of every candidate panel SVG."""
    box_mm = panel_box_mm(FIGURE_ID, "A")
    rows = []
    for panel in PANEL_SPECS:
        path = CANDIDATE_ROOT / candidate / f"{panel}/Figure_7{panel}.svg"
        metrics = svg_metrics(path, box_mm=box_mm)
        effective = metrics["minimum_effective_font_pt"]
        rows.append(
            {
                "candidate": candidate,
                "panel": panel,
                "minimum_effective_font_pt": effective,
                "contains_significance_star_text": metrics["contains_significance_star_text"],
                "editable_text_nodes": metrics["editable_text_nodes"],
            }
        )
        if effective is None or float(effective) < MINIMUM_ON_PAGE_FONT_PT - 1e-6:
            raise AssertionError(f"{path} prints text at {effective} pt")
        if metrics["contains_significance_star_text"]:
            raise AssertionError(f"{path} contains significance-star text")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=["contour", "paired", "both"], default="both")
    args = parser.parse_args()
    apply_publication_style()
    candidates = ["contour", "paired"] if args.candidate == "both" else [args.candidate]
    report: dict[str, object] = {"panels": {}, "qa": [], "figures": {}}
    for panel in PANEL_SPECS:
        record: dict[str, object] = {}
        if "contour" in candidates:
            direct = load_direct_tracks(panel)
            contour_candidate(panel, direct)
            record["trajectories"] = int(len(direct))
        if "paired" in candidates:
            units = load_unit_medians(panel)
            ratios = load_ratios(panel)
            paired_candidate(panel, units, ratios)
            record["paired_units"] = {
                medium: int(ratios.loc[medium, "n_paired_units"]) for medium in MEDIA
            }
            record["D_ratio"] = {
                medium: float(ratios.loc[medium, "D_ratio"]) for medium in MEDIA
            }
        report["panels"][panel] = record
    for candidate in candidates:
        report["qa"].extend(qa(candidate))
        report["figures"][candidate] = assemble(candidate).relative_to(PROJECT).as_posix()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
