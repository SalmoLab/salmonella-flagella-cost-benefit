#!/usr/bin/env python3
"""Regenerate Supplementary Figure 4 from the collaborator's final simulator."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.patches import Circle
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar

PROJECT = Path(__file__).resolve().parents[2]
UPSTREAM = PROJECT / "models/motility_simulation/upstream"

#: Project-local corrected dynamics, the same module Figure 5D and 5E use.  The
#: vendored upstream stays immutable provenance; the corrections live beside it
#: and are documented in models/motility_simulation/corrected/README.md.
CORRECTED_MODEL = PROJECT / "models/motility_simulation/corrected"

sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(UPSTREAM / "src"))
sys.path.insert(0, str(CORRECTED_MODEL / "src"))

sys.path.insert(0, str(PROJECT / "analyses/motility_adopted_parameters"))
sys.path.insert(0, str(PROJECT / "analyses/figure_05_revision"))

import salmonella_motility_corrected as simulation  # noqa: E402
from derive_adopted_parameters import adopted_parameter_table_path  # noqa: E402
from salmonella_motility_corrected import load_parameter_table  # noqa: E402

# These maps must depict the same dynamics as Figure 5D and 5E, so the time step
# and the visual box scale come from the Figure 5 builder instead of being
# restated here.
from build import SIMULATION_DT_S, VISUAL_BOX_SCALE  # noqa: E402
from flagella_repro.theme import (  # noqa: E402
    KEY_SWATCH,
    PALETTE,
    POINT_MARKER_SIZE,
    TICK_FONT_PT,
    apply_publication_style,
    get_strain_style,
    marker_edge,
    panel_figsize,
    save_figure,
)

apply_publication_style()
# Panel-specific salt keeps this figure's SVG element ids stable across rebuilds.
matplotlib.rcParams["svg.hashsalt"] = "flagella-supplementary-05-updated-96ca0e7"

FIGURE_ID = "Supplementary_Figure_4"
NEUTRAL: dict[str, str] = PALETTE["neutral"]
# Simulated phenotypes map onto the manuscript strains that carry the palette.
STRAIN_IDS = {"PproA": "EM9661", "WT": "TH9677", "PproB": "EM9660"}

# The panels run on parameters calibrated in this repository.  The delivered
# table stays declared as an input so the record shows what calibration started
# from.
#
# Adopted 13 August 2026: one canonical table gives every phenotype-by-medium row
# the same turn width, 1.2468 rad, derived from the 57 deg mean turn angle of
# Taute et al. 2015 (Nat Commun 6:8776, PMID 26522289), and scales the agarose
# stall probability with flagella number at the strength Grognot et al. 2023
# measured (PNAS 120:e2301873120, PMID 37579142).  Figure 5D and 5E read the same
# table, so both figures depict the same simulation.
DELIVERED_PARAMETERS = UPSTREAM / "data/motility_summary_parameters.csv"
PARAMETERS = adopted_parameter_table_path()
CALIBRATION_SCRIPTS = (
    PROJECT / "analyses/motility_parameter_calibration/calibrate.py",
    PROJECT / "analyses/motility_turn_angle_comparison/calibrate_global_turn_angle.py",
    PROJECT / "analyses/motility_stall_parameter_comparison/common.py",
    PROJECT / "analyses/motility_adopted_parameters/derive_adopted_parameters.py",
)
SIMULATION_CONFIG = UPSTREAM / "data/config.yml"
UPSTREAM_RECORD = UPSTREAM / "UPSTREAM_SOURCE.md"
UPSTREAM_COMMIT = "96ca0e741c8c4990b1cfa59b2daafee59d74cb7b"
SOURCE_DIR = PROJECT / "data/source_data/supplementary_04"
PANEL_ROOT = PROJECT / "analyses/supplementary_04"

# Exact seeds assigned by upstream run_simulations() when all delivered rows are loaded.
# The manuscript retains its established ordering: liquid A-C, agarose D-F.
# A trajectory map needs a spatial reference.  A scale bar gives it, and axes do
# not suit this panel: the map carries no measured quantity on either axis, and
# two tick bands plus their labels would take page area from the tracks in all
# six panels.  A bar states the same distance in one mark.
#
# The bar is 20 um, about one seventh of the 148 um domain width.  It prints
# 9.6 mm long in the 84 x 53 mm assembly slot, which reads at arm's length and
# still leaves the lower right corner mostly free.  The bar sits opposite the
# symbol key, in the panel's own text colour, over a background-coloured patch
# that keeps it legible where a track runs beneath it.
SCALE_BAR_UM = 20.0
SCALE_BAR_THICKNESS_UM = 1.4

PANEL_MAP = {
    "A": ("PproA", "liquid", 24),
    "B": ("WT", "liquid", 106),
    "C": ("PproB", "liquid", 65),
    "D": ("PproA", "agarose", 17),
    "E": ("WT", "agarose", 99),
    "F": ("PproB", "agarose", 58),
}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact(path: Path, rows: int | None = None) -> dict[str, object]:
    item: dict[str, object] = {
        "relative_path": path.relative_to(PROJECT).as_posix(),
        "sha256": _sha(path),
        "bytes": path.stat().st_size,
    }
    if rows is not None:
        item["rows"] = rows
    return item


def _load_config() -> dict:
    """Return the upstream config with the Figure 5 time step applied.

    The upstream ``config.yml`` declares dt = 0.05 s and is immutable
    provenance.  Figure 5D and 5E integrate at the refined, converged step, so
    these maps do too; otherwise the two figures would show different dynamics.

    The domain is the published 148 x 96 um box, ``VISUAL_BOX_SCALE = 1``.  These
    maps show; they do not measure.  A small field is what keeps individual
    tracks legible, and no number is read off them.  Figure 5D and 5E report
    numbers and therefore run in a box large enough that the reflecting walls do
    not compress the strain ratios.  The methods state the separation.
    """
    with SIMULATION_CONFIG.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    config["simulation"]["dt_s"] = float(SIMULATION_DT_S)
    # Name the stalled-cell translational noise scale that upstream left as a
    # bare literal in the loop.  The value, 0.20, is unchanged, so the maps are
    # unchanged; the constant now reaches the provenance record.
    config["noise"]["stall_translational_scale"] = float(simulation.STALL_TRANSLATIONAL_SCALE)
    return simulation.scaled_config(config, VISUAL_BOX_SCALE)


def _trajectory_table(result: dict, strain: str, medium: str, seed: int, dt: float) -> pd.DataFrame:
    history = result["history"]
    states = result["state_history"]
    n_steps, n_cells = states.shape
    step = np.repeat(np.arange(n_steps), n_cells)
    cell_id = np.tile(np.arange(n_cells), n_steps)
    return pd.DataFrame(
        {
            "phenotype": strain,
            "medium": medium,
            "seed": seed,
            "cell_id": cell_id,
            "step": step,
            "time_s": step * dt,
            "x_um": history[:, :, 0].reshape(-1),
            "y_um": history[:, :, 1].reshape(-1),
            "state": states.reshape(-1),
            "is_motile": result["is_motile"][cell_id].astype(bool),
        }
    )


def _obstacle_table(result: dict, strain: str, medium: str, seed: int) -> pd.DataFrame:
    obstacles = result["obstacles"]
    if obstacles is None:
        return pd.DataFrame(
            columns=["phenotype", "medium", "seed", "obstacle_index", "x_um", "y_um", "radius_um"]
        )
    return pd.DataFrame(
        {
            "phenotype": strain,
            "medium": medium,
            "seed": seed,
            "obstacle_index": np.arange(obstacles.n_obstacles),
            "x_um": obstacles.x_um,
            "y_um": obstacles.y_um,
            "radius_um": obstacles.r_um,
        }
    )


def _plot(result: dict, strain: str, medium: str, panel: str, stem: Path, config: dict) -> None:
    """Draw one trajectory map at the exact size of its assembly slot.

    The panel renders at ``panel_figsize`` so the assembler magnifies it by one.
    A point declared here is therefore a point on the printed page.
    """
    history = result["history"]
    states = result["state_history"]
    is_motile = result["is_motile"]
    state_stalled = int(config["states"]["stalled"])
    state_nonmotile = int(config["states"]["non_motile"])
    track_color = get_strain_style(STRAIN_IDS[strain])["color"]

    fig, ax = plt.subplots(figsize=panel_figsize(FIGURE_ID, panel))
    ax.set_facecolor(NEUTRAL["background"])
    obstacles = result["obstacles"]
    if obstacles is not None:
        for x_um, y_um, r_um in zip(obstacles.x_um, obstacles.y_um, obstacles.r_um, strict=True):
            ax.add_patch(Circle((x_um, y_um), r_um, fc=NEUTRAL["grid"], ec="none", zorder=0))

    track_edge, track_edge_width = marker_edge(track_color)
    for cell in range(history.shape[1]):
        # The manuscript promoter colours are lighter than the upstream
        # literals, so the tracks carry a little more alpha to stay legible.
        alpha = 0.45 if is_motile[cell] else 0.18
        width = 0.75 if is_motile[cell] else 0.5
        ax.plot(history[:, cell, 0], history[:, cell, 1], color=track_color, alpha=alpha, lw=width)
        final_state = int(states[-1, cell])
        # A non-motile cell used to be drawn in a neutral grey fill, which was
        # indistinguishable from the WT track colour. It now takes an unfilled
        # marker, so it separates from every strain colour rather than from
        # just some of them.
        if final_state == state_nonmotile:
            ax.scatter(
                history[-1, cell, 0],
                history[-1, cell, 1],
                s=POINT_MARKER_SIZE,
                facecolor="none",
                edgecolor=KEY_SWATCH,
                linewidths=0.5,
                marker="o",
                zorder=3,
            )
            continue
        ax.scatter(
            history[-1, cell, 0],
            history[-1, cell, 1],
            s=POINT_MARKER_SIZE,
            color=track_color,
            marker="s" if final_state == state_stalled else "o",
            edgecolor=track_edge,
            linewidths=track_edge_width,
            alpha=0.95,
            zorder=3,
        )

    # A key maps each symbol to a short name and stays in the panel. The
    # simulation-parameter readout is prose and moved to the figure legend.
    ax.legend(
        handles=[
            Line2D(
                [],
                [],
                lw=0,
                marker="o",
                markersize=np.sqrt(POINT_MARKER_SIZE),
                color=track_color,
                markeredgewidth=0,
                label="run end",
            ),
            Line2D(
                [],
                [],
                lw=0,
                marker="s",
                markersize=np.sqrt(POINT_MARKER_SIZE),
                color=track_color,
                markeredgewidth=0,
                label="stalled",
            ),
            Line2D(
                [],
                [],
                lw=0,
                marker="o",
                markersize=np.sqrt(POINT_MARKER_SIZE),
                markerfacecolor="none",
                markeredgecolor=KEY_SWATCH,
                markeredgewidth=0.5,
                label="non-motile",
            ),
        ],
        loc="upper left",
        ncols=3,
        frameon=True,
        framealpha=0.85,
        edgecolor="none",
        facecolor=NEUTRAL["background"],
        fontsize=TICK_FONT_PT,
        handlelength=1.0,
        handletextpad=0.35,
        columnspacing=0.9,
        borderpad=0.25,
        borderaxespad=0.2,
    )
    ax.set(
        xlim=(0, float(config["simulation"]["box_width_um"])),
        ylim=(0, float(config["simulation"]["box_height_um"])),
        xticks=[],
        yticks=[],
    )
    # The domain is 148 x 96 um.  Equal aspect with adjustable="box" shrinks the
    # axes to that ratio and centres it, so the map never stretches.
    ax.set_aspect("equal", adjustable="box")
    # The map has no ticks, so the scale bar is the only spatial reference.
    scale_bar = AnchoredSizeBar(
        ax.transData,
        SCALE_BAR_UM,
        f"{SCALE_BAR_UM:.0f} µm",
        loc="lower right",
        pad=0.3,
        borderpad=0.4,
        sep=1.5,
        frameon=True,
        fill_bar=True,
        color=NEUTRAL["text"],
        size_vertical=SCALE_BAR_THICKNESS_UM,
        fontproperties=FontProperties(size=TICK_FONT_PT),
    )
    scale_bar.patch.set(facecolor=NEUTRAL["background"], edgecolor="none", alpha=0.85)
    ax.add_artist(scale_bar)
    # The map shows the spatial search pattern, which is a model output. Speed
    # and turning are calibrated inputs, so the title says so.
    ax.set_title(
        "liquid — calibrated speed and turning"
        if medium == "liquid"
        else "agarose-like mesh — calibrated speed and turning"
    )
    ax.set_ylabel(strain, rotation=0, ha="right", va="center", labelpad=6)
    # The shared style hides the top and right spines.  This panel is a spatial
    # map, so all four spines are needed to draw the simulation box.
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.65)
        spine.set_edgecolor(NEUTRAL["text"])
    # Fixed margins, because save_figure writes the full canvas.  The left band
    # holds the phenotype label and the top band holds the medium title.
    fig.subplots_adjust(left=0.140, right=0.986, top=0.908, bottom=0.022)

    save_figure(fig, stem)


def build(panel: str) -> None:
    config = _load_config()
    table = load_parameter_table(PARAMETERS)
    strain, medium, seed = PANEL_MAP[panel]
    params = table[(strain, medium)]
    obstacle_seed = seed + 300 if medium == "agarose" else None
    obstacles = (
        simulation.make_obstacle_field(config, seed=obstacle_seed)
        if obstacle_seed is not None
        else None
    )
    result = simulation.simulate_population(config, params, obstacles, seed)

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    trajectory = _trajectory_table(
        result, strain, medium, seed, float(config["simulation"]["dt_s"])
    )
    obstacle_table = _obstacle_table(result, strain, medium, seed)
    source = SOURCE_DIR / f"S4_{panel}_simulated_trajectories.csv.gz"
    obstacles_path = SOURCE_DIR / f"S4_{panel}_obstacles.csv"
    trajectory.to_csv(source, index=False, compression={"method": "gzip", "mtime": 0})
    obstacle_table.to_csv(obstacles_path, index=False)

    build_dir = PROJECT / f"build/panels/{FIGURE_ID}/{panel}"
    build_dir.mkdir(parents=True, exist_ok=True)
    graphics = [build_dir / f"S4_{panel}.{suffix}" for suffix in ("png", "svg", "pdf")]
    _plot(result, strain, medium, panel, build_dir / f"S4_{panel}", config)

    panel_dir = PANEL_ROOT / f"panel_{panel.lower()}"
    config_path = panel_dir / "config/panel.json"
    wrapper_path = panel_dir / "scripts/reproduce.py"
    upstream_code = sorted((UPSTREAM / "src/salmonella_motility_simulation").glob("*.py"))
    inputs = [
        _artifact(Path(__file__).resolve()),
        _artifact(config_path),
        _artifact(wrapper_path),
        _artifact(PARAMETERS, len(pd.read_csv(PARAMETERS))),
        _artifact(DELIVERED_PARAMETERS, len(pd.read_csv(DELIVERED_PARAMETERS))),
        *[_artifact(path) for path in CALIBRATION_SCRIPTS],
        _artifact(SIMULATION_CONFIG),
        _artifact(UPSTREAM_RECORD),
        _artifact(UPSTREAM / "CHECKSUMS.sha256"),
        *[_artifact(path) for path in upstream_code],
    ]
    provenance = {
        "schema_version": "1.0.0",
        "panel_id": f"S4_{panel}",
        "status": "partial_reproduction",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "analyses/supplementary_04/build_s4.py",
            "--panel",
            panel,
        ],
        "inputs": inputs,
        "outputs": [
            _artifact(source, len(trajectory)),
            _artifact(obstacles_path, len(obstacle_table)),
            *[_artifact(path) for path in graphics],
        ],
        "software": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "matplotlib": matplotlib.__version__,
            "numpy": np.__version__,
            "pyyaml": yaml.__version__,
            "upstream_commit": UPSTREAM_COMMIT,
        },
        "parameters": {
            "model": "collaborator single-cell run/reorientation/non-motile simulation",
            "phenotype": strain,
            "medium": medium,
            **config["simulation"],
            "declared_config_dt_s": 0.05,
            "obstacle_config": config["obstacles"],
            "noise_config": config["noise"],
            "motility_parameters": params.__dict__,
            "scale_bar_um": SCALE_BAR_UM,
        },
        "random_seeds": {
            "panel_seed": seed,
            "starting_position_seed": seed + 1,
            "obstacle_seed": obstacle_seed,
        },
        "limitations": [
            (
                "The model illustrates the experimental findings. It does not predict them "
                "and is not a mechanistically complete or fitted biophysical model."
            ),
            (
                "Run speed, motile fraction and persistence time are calibrated model inputs, "
                "so these maps do not predict the measured speed or diffusivity ordering."
            ),
            (
                "The turning parameters were calibrated in this repository against our "
                "paired-unit measurements. They were not supplied by the collaborator."
            ),
            (
                "The delivered table already set run speed and motile fraction from these "
                "same measurements; only the turning parameters were uncalibrated."
            ),
            (
                "The turn width is one global value, 1.2468 rad, for all six rows. It matches "
                "the 57 deg mean turn angle of Taute et al. 2015 (n = 8058 turns, E. coli "
                "AW405) through sigma = radians(57) / sqrt(2 / pi). Taute et al. measured in "
                "three dimensions and in E. coli; this simulator is two-dimensional and the "
                "strains are S. Typhimurium. The mapping matches the mean turn magnitude "
                "only. A zero-mean Gaussian cannot reproduce the measured forward-skewed "
                "turn-angle shape."
            ),
            (
                "The agarose stall probability is a per-contact-event probability: it is "
                "drawn once, on the step where a cell first overlaps an obstacle it was not "
                "already touching. It falls with mean flagella number as N^-0.704, "
                "normalised so its mean over the three strains is unchanged. The exponent "
                "sets the ratio between the least and the most flagellated strain to the "
                "1.7 +/- 0.2 stall-frequency ratio of Grognot et al. 2023 (Vibrio "
                "alginolyticus, 0.25 % agar). That study varied a second flagellar system, "
                "not the flagella count, so the mapping onto our hook numbers is an "
                "assumption. Only the ratio is anchored."
            ),
            (
                "The mean stall duration is one nominal value, 0.949 s, in all three agarose "
                "rows. Grognot et al. found the duration effect significant only at 0.16 % "
                "agar, not at the 0.25 % that matches our condition."
            ),
            (
                "The spatial search pattern, obstacle trapping and the stall duty cycle "
                "remain model outputs that no measurement supplies."
            ),
            (
                "Reorientation is instantaneous. The persistence relation the turning "
                "parameters are fitted through carries no duration term, so a "
                "non-advancing reorientation dwell would simulate a different model from "
                "the fitted one. The heading kick is applied at the transition and the cell "
                "keeps swimming, so no track shows a stationary reorientation pause."
            ),
            (
                "These maps keep the published 148 x 96 um domain with reflecting walls, "
                "because a small field is what makes individual tracks legible. They show a "
                "spatial pattern and report no number. Figure 5D and 5E measure, so they run "
                "in a box enlarged twelvefold in each direction, where the walls no longer "
                "compress the strain ratios. The reflecting walls of these maps shorten the "
                "faster strains more than the slower ones; the maps must not be read as a "
                "quantitative comparison of spread."
            ),
            (
                f"The maps integrate at dt = {SIMULATION_DT_S} s, not at the dt = 0.05 s "
                f"declared in the upstream config.yml. Figure 5D and 5E use the same "
                f"refined step, so both figures depict the same simulation. Under the "
                f"corrected dynamics a 100-seed convergence check accepts every step it "
                f"tests, from 0.000625 s to 0.05 s: the largest group deviation is 4.0 %, "
                f"and 2.0 % at the step used here. The upstream config file is immutable "
                f"provenance and was not edited; the builder overrides the value. See "
                f"analyses/figure_05_revision/README.md."
            ),
            (
                "Contour path length is not plotted anywhere, because it does not converge "
                "under time-step refinement. Figure 5D and 5E report net displacement "
                "instead. These maps show a spatial pattern, not a scalar, so the rejection "
                "does not change what they draw."
            ),
            (
                "The delivered parameters are experimentally informed summaries; raw "
                "trajectory-to-parameter fitting inputs were not included."
            ),
            (
                "WT_slow is present in the collaborator package but excluded because "
                "it is not a current manuscript panel."
            ),
            (
                "The frozen 9 July visual remains historical; this panel intentionally "
                "reflects the updated 12 August model source."
            ),
        ],
    }
    rendered = json.dumps(provenance, indent=2) + "\n"
    (panel_dir / "metadata/provenance.json").write_text(rendered, encoding="utf-8")
    # The central audit tree is keyed by figure number, not by the historical
    # directory name, so it matches tools/sync_revision_provenance.py.
    central = PROJECT / "metadata/provenance/supplementary_04" / f"S4_{panel}.json"
    central.parent.mkdir(parents=True, exist_ok=True)
    central.write_text(rendered, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", choices=list("ABCDEF") + ["all"], default="all")
    args = parser.parse_args()
    for panel in list("ABCDEF") if args.panel == "all" else [args.panel]:
        build(panel)


if __name__ == "__main__":
    main()
