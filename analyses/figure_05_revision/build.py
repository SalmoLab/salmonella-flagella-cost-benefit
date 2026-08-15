#!/usr/bin/env python3
"""Build revised Figure 5 from gradient and active-particle model outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))

from flagella_repro.theme import (  # noqa: E402
    DENSITY_MARKER_SIZE,
    KEY_SWATCH,
    PALETTE,
    POINT_MARKER_SIZE,
    SUMMARY_INK,
    TICK_FONT_PT,
    apply_publication_style,
    get_condition_color,
    get_strain_style,
    marker_edge,
    panel_figsize,
    save_figure,
)

FIGURE_ID = "Figure_5"
# Neutral inks come from the shared palette so no panel carries its own colour
# literal.  "technical" is the manuscript's neutral shading grey.
GRADIENT_FILL = PALETTE["neutral"]["technical"]
INK = PALETTE["neutral"]["text"]
PAPER = PALETTE["neutral"]["background"]

MODEL_RESULTS = PROJECT / "data/external/cell_economy_results/swimming/8500"
ACTIVE_MODEL = PROJECT / "models/motility_simulation/upstream"
PROCESSED = PROJECT / "data/processed/figure_05_revision"
SOURCE = PROJECT / "data/source_data/figure_05_revision"
BUILD_SOURCE = PROJECT / "build/source_data/Figure_5"
STATISTICS = PROJECT / "build/statistics/Figure_5"
OUTPUT = PROJECT / "build/panels/Figure_5"
ANALYSIS_ROOT = PROJECT / "analyses/figure_05_revision"
# The delivered-parameter run stays available for the collaborator conversation.
# It is a diagnostic, not a panel, so it never reaches build/panels.
DIAGNOSTICS = PROJECT / "build/diagnostics/Figure_5"

#: Project-local corrected dynamics.  The vendored upstream stays immutable
#: provenance; the corrections live beside it and are documented in
#: models/motility_simulation/corrected/README.md.
CORRECTED_MODEL = PROJECT / "models/motility_simulation/corrected"

sys.path.insert(0, str(ACTIVE_MODEL / "src"))
sys.path.insert(0, str(CORRECTED_MODEL / "src"))
sys.path.insert(0, str(PROJECT / "analyses/motility_adopted_parameters"))

import salmonella_motility_corrected as simulation  # noqa: E402
from derive_adopted_parameters import adopted_parameter_table_path  # noqa: E402
from salmonella_motility_corrected import load_parameter_table  # noqa: E402

# Panels D and E run on parameters calibrated in this repository.  The delivered
# table is the fallback only for the diagnostic run.
DELIVERED_PARAMETERS = ACTIVE_MODEL / "data/motility_summary_parameters.csv"

# Adopted 13 August 2026.  One canonical table carries both decisions.  Every
# phenotype-by-medium row gets the same turn width, 1.2468 rad, from the 57 deg
# mean turn angle of Taute et al. 2015 (Nat Commun 6:8776, PMID 26522289).  The
# agarose stall probability falls with flagella number at the strength Grognot
# et al. 2023 measured (PNAS 120:e2301873120, PMID 37579142), and the stall
# duration is one global value.  Both sets of values they replace had no source.
# The table is derived at build time from the frozen delivered table, our
# paired-unit measurements and our per-cell hook counts; no value is written
# here by hand.  See docs/revision_2026-08-12/turn_angle_model_comparison.md and
# docs/revision_2026-08-12/stall_parameter_comparison.md.
CALIBRATION_SCRIPTS = (
    PROJECT / "analyses/motility_parameter_calibration/calibrate.py",
    PROJECT / "analyses/motility_turn_angle_comparison/calibrate_global_turn_angle.py",
    PROJECT / "analyses/motility_stall_parameter_comparison/common.py",
    PROJECT / "analyses/motility_adopted_parameters/derive_adopted_parameters.py",
)

PHENOTYPES = ["PproA", "WT", "PproB"]
MEDIA = ["liquid", "agarose"]
SEEDS = range(1000, 1100)
STRAIN_IDS = {"PproA": "EM9661", "WT": "TH9677", "PproB": "EM9660"}
FLAGELLAR_ALLOCATIONS = [0.005, 0.010, 0.020, 0.030, 0.040, 0.050]

# The non-motile reference a coauthor asked for.  A cell that spends nothing on
# flagella never reaches the substrate, so its growth rate is the baseline that
# every motile allocation is measured against.  The trajectory and its solver
# status come from the A3 continuation run: IPOPT on the public APMonitor
# server with ``remote=True``.  See models/cell_economy/low_allocation_sweep.py.
BASELINE_ALLOCATION = 0.0
LOW_ALLOCATION_STATUS = PROCESSED / "A3_low_allocation_continuation_status.csv"
LOW_ALLOCATION_TRAJECTORIES = PROCESSED / "A3_trajectories"

# Panels D and E plot net displacement, the straight-line distance from the start
# to the end of a track.  Contour path length was rejected: it grows without a
# limit as the time step shrinks, because a trajectory with a diffusive component
# has an infinite arc length in the continuum limit.  Net displacement converges.
# ``timestep_convergence.py`` records the check under build/diagnostics.
OBSERVABLE_COLUMN = "predicted_mean_net_displacement_um"
# The upstream config declares dt = 0.05 s.  At that step the per-step turn
# probability ``reorientation_rate_s * dt`` reaches 0.85 for the fastest-turning
# row, so the run statistics and the net displacement are still far from their
# refined values.  The convergence check picks the largest step that is converged,
# and this override applies it.  The upstream config.yml stays untouched: it is
# immutable provenance.
SIMULATION_DT_S = 0.0025
# Convergence tolerance carried into the legend and the provenance record.
CONVERGENCE_TOLERANCE = 0.05

# Panels D and E measure; Supplementary Figure 4 shows.  The two need different
# domains, so the two are separated here.
#
# The upstream box is 148 x 96 um with reflecting walls.  A wall turns a cell
# back, so it shortens a fast strain more than a slow one and compresses the
# strain ratios these panels report.  The quantitative panels therefore run in a
# box enlarged by this linear factor, where the wall artefact is negligible.
# Supplementary Figure 4 keeps the published box: its trajectory maps need a
# small field to stay legible, and it reports no numbers.
#
# The obstacle count scales with box AREA, so the mesh keeps the number density
# and the area fraction of the published field.  Enlarging the box without
# scaling the count would dilute the mesh and inflate every agarose number.
# ``obstacle_area_fraction`` is recorded per run as the check that it did not.
# The realised fraction is 0.185 in the published box and 0.187 at scale 12.
#
# Scale 12 is where the boundary ladder in
# analyses/motility_domain_boundary_check puts the strain ratios on a plateau:
# every ratio moves by less than 0.6 % between scale 8 and scale 12, against the
# 10 % to 17 % the published box costs them.
QUANTITATIVE_BOX_SCALE = 12
VISUAL_BOX_SCALE = 1


# Panels D and E illustrate the measurements; they do not predict them.  The
# limitations say which quantities are inputs and who calibrated them.
_ACTIVE_LIMITATIONS = [
    (
        "Run speed, motile fraction and persistence time are calibrated model inputs, "
        "so the panel does not predict the measured speed or diffusivity ordering."
    ),
    (
        "The turning parameters were calibrated in this repository against our paired-unit "
        "measurements. They were not supplied by the collaborator."
    ),
    (
        "The delivered table already set run speed and motile fraction from these same "
        "measurements; only the turning parameters were uncalibrated."
    ),
    (
        "The turn width is one global value, 1.2468 rad, for all six rows. It matches the "
        "57 deg mean turn angle of Taute et al. 2015 (n = 8058 turns, E. coli AW405) through "
        "sigma = radians(57) / sqrt(2 / pi). Taute et al. measured in three dimensions and in "
        "E. coli; this simulator is two-dimensional and the strains are S. Typhimurium. The "
        "mapping matches the mean turn magnitude only. A zero-mean Gaussian cannot reproduce "
        "the measured forward-skewed turn-angle shape."
    ),
    (
        "The agarose stall probability is a per-contact-event probability: it is drawn once, "
        "on the step where a cell first overlaps an obstacle it was not already touching. "
        "That is the same kind of quantity Grognot et al. measured, a stall frequency per "
        "contact. It falls with mean flagella number as N^-0.704, normalised so its mean "
        "over the three strains is unchanged. The exponent sets the ratio between the least "
        "and the most flagellated strain to the 1.7 +/- 0.2 stall-frequency ratio of Grognot "
        "et al. 2023 (Vibrio alginolyticus, 0.25 % agar). That study varied a second "
        "flagellar system, not the flagella count, so the mapping onto our hook numbers is "
        "an assumption. Only the ratio is anchored; the absolute probability has no source."
    ),
    (
        "Reorientation is instantaneous. The persistence relation the turning parameters are "
        "fitted through, tau = 1 / (D_theta + lambda * (1 - exp(-sigma^2 / 2))), carries no "
        "duration term, so a non-advancing reorientation dwell would simulate a different "
        "model from the fitted one. reorientation_duration_s is therefore not a parameter of "
        "the model and does not appear in Supplementary Table X. The measured tumble "
        "duration of E. coli, 0.19 s, cannot simply be substituted: it would put cells in a "
        "non-swimming state 49 % to 71 % of the time. A model with a real tumble duration "
        "needs the persistence relation refitted with a duration term."
    ),
    (
        "The mean stall duration is one nominal value, 0.949 s, in all three agarose rows. "
        "Grognot et al. found the duration effect significant only at 0.16 % agar, not at "
        "the 0.25 % that matches our condition, so a per-strain duration is not supported. "
        "Published gel trapping times are longer and power-law distributed; the model draws "
        "an exponential."
    ),
    (
        "Net displacement, obstacle trapping, the stall duty cycle and the spatial search "
        "pattern remain model outputs that no measurement supplies."
    ),
    (
        "The measured agarose persistence time is derived as 2 * D_eff / v^2, so it already "
        "contains the mesh. The model then adds obstacles and stalls on top of it, which "
        "remove a further 17 % to 22 % of the effective diffusivity. The mesh is therefore "
        "counted twice in agarose, once in the calibrated persistence time and once in the "
        "simulated geometry. The panel is not an independent prediction of agarose spreading."
    ),
    (
        "The corrected model reproduces 87 % to 90 % of the measured effective diffusivity "
        "in liquid and 69 % to 76 % in agarose, against 60 % to 61 % and 37 % to 39 % before "
        "the correction. Ratios compare the simulated value with the lag-corrected measured "
        "value. Against the model's own implied diffusivity the corrected liquid runs reach "
        "98 % to 100 %, so in the obstacle-free case the simulation now matches the "
        "calibration it was fitted through. Agarose reaches 78 % to 83 % of implied, and the "
        "remaining gap is the double-counted mesh. Motile cells are ballistic 100 % of the "
        "time in liquid and 86 % to 90 % in agarose; the reorient state is never occupied. "
        "build/diagnostics/effective_diffusivity_check/effective_diffusivity_comparison.csv "
        "holds the comparison."
    ),
    (
        "Contour path length was rejected as the plotted observable because it does not "
        "converge under time-step refinement. A trajectory with a diffusive component has "
        "an infinite arc length in the continuum limit, so the path length grows without a "
        "limit as the step shrinks, and the ratio between two phenotypes drifts across 1. "
        "Net displacement, the straight-line distance from the start to the end of a track, "
        "converges and is reported instead."
    ),
    (
        f"The panels integrate at dt = {SIMULATION_DT_S} s, not at the dt = 0.05 s declared "
        f"in the upstream config.yml. A 100-seed convergence test accepts every step whose "
        f"group mean net displacement stays within {CONVERGENCE_TOLERANCE:.0%} of the mean "
        f"of the two finest steps tested, 0.00125 s and 0.000625 s. Under the corrected "
        f"dynamics every step tested passes: the largest deviation over the six groups is "
        f"2.2 % at 0.000625 s and 0.00125 s, 2.0 % at 0.0025 s, 3.2 % at 0.005 s, 3.9 % at "
        f"0.01 s and 4.0 % at 0.05 s. The panels keep the fine step because it is cheap and "
        f"leaves no doubt, not because a coarser one fails. The upstream config file is "
        f"immutable provenance and was not edited; the builder overrides the value. "
        f"build/diagnostics/Figure_5/timestep_convergence.csv holds the check."
    ),
    (
        "Net displacement no longer depends on the time step. The upstream model drew against "
        "the stall probability at every step of obstacle overlap, so a finer step made more "
        "stall draws per contact and stall occupancy grew without limit. The corrected model "
        "draws once per contact event, which removes that dependence: the PproB agarose group "
        "mean moves by 0.3 % between the two finest steps tested, and the PproB/PproA ratio "
        "stays between 3.29 and 3.50 across the whole ladder from 0.000625 s to 0.05 s with "
        "no trend in the step."
    ),
    ("Intervals quantify stochastic model-seed variation, not biological sampling uncertainty."),
    (
        "The delivered-parameter run is retained as a diagnostic under build/diagnostics and "
        "is not a manuscript panel."
    ),
]


def _ensure_dirs() -> None:
    for path in (PROCESSED, SOURCE, BUILD_SOURCE, STATISTICS, OUTPUT, DIAGNOSTICS):
        path.mkdir(parents=True, exist_ok=True)


def write_source(table: pd.DataFrame, panel: str, filename: str) -> None:
    tracked = SOURCE / panel / filename
    built = BUILD_SOURCE / panel / filename
    tracked.parent.mkdir(parents=True, exist_ok=True)
    built.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(tracked, index=False)
    table.to_csv(built, index=False)


def panel_stem(label: str) -> Path:
    return OUTPUT / label / f"Figure_5_{label}"


def _artifact(path: Path) -> dict[str, object]:
    result: dict[str, object] = {
        "relative_path": path.relative_to(PROJECT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }
    if path.suffix == ".csv":
        result["rows"] = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
    return result


def write_provenance(labels: list[str]) -> None:
    """Write panel-local provenance ready for central-registry integration."""
    dynamic = sorted(MODEL_RESULTS.glob("dynamic_flag_*.csv"))
    active_inputs = [
        ACTIVE_MODEL / "data/config.yml",
        DELIVERED_PARAMETERS,
        adopted_parameter_table_path(),
        *CALIBRATION_SCRIPTS,
        ACTIVE_MODEL / "src/salmonella_motility_simulation/simulation.py",
        # The dynamics these panels actually integrate.  The upstream file above
        # stays declared because the correction is stated against it.
        CORRECTED_MODEL / "src/salmonella_motility_corrected/simulation.py",
        CORRECTED_MODEL / "src/salmonella_motility_corrected/obstacles.py",
        CORRECTED_MODEL / "src/salmonella_motility_corrected/classes.py",
        CORRECTED_MODEL / "src/salmonella_motility_corrected/io.py",
        ANALYSIS_ROOT / "timestep_convergence.py",
    ]
    # The zero-allocation curve is ours, not a delivered table.  Its harness,
    # its solver-status record and the trajectory itself are all declared.
    baseline_inputs = [
        PROJECT / "models/cell_economy/low_allocation_sweep.py",
        LOW_ALLOCATION_STATUS,
        LOW_ALLOCATION_TRAJECTORIES / f"dynamic_flag_{BASELINE_ALLOCATION:.4f}.csv",
    ]
    panel_inputs = {
        "A": [*dynamic, MODEL_RESULTS / "substrate_gradient.csv"],
        "B": [*dynamic, *baseline_inputs],
        "C": dynamic,
        "D": active_inputs,
        "E": active_inputs,
    }
    limitations = {
        "A": [
            "Dynamic trajectories begin from supplied solver result tables because the "
            "exact IPOPT runtime is unavailable locally."
        ],
        "B": [
            "Trajectories at 0.5-5% flagellar allocation are the supplied solver result "
            "tables. The zero-allocation trajectory was solved here with IPOPT on the "
            "public APMonitor server, GEKKO remote=True.",
            "The sweep between 0% and 1% is not drawn. A warm-start continuation with a "
            "multi-start solved every step, but the solved growth rates do not follow one "
            "consistent branch, so the interior is recorded and not plotted. "
            "build/statistics/Figure_5/A3/ holds the record.",
            "The model is coarse-grained. It recovers the trend of a benefit that rises "
            "steeply from zero and then flattens; it does not fix the allocation of the "
            "optimum to the stated precision.",
        ],
        "C": [
            "Dynamic trajectories begin from supplied solver result tables because the "
            "exact IPOPT runtime is unavailable locally."
        ],
        "D": _ACTIVE_LIMITATIONS,
        "E": _ACTIVE_LIMITATIONS,
    }
    for label in labels:
        panel_root = ANALYSIS_ROOT / f"panel_{label.lower()}"
        wrapper = panel_root / "scripts/reproduce.py"
        config = panel_root / "config/panel.json"
        outputs = sorted((OUTPUT / label).glob(f"Figure_5_{label}.*"))
        outputs.extend(sorted((BUILD_SOURCE / label).glob("*.csv")))
        if label in "DE":
            outputs.extend(sorted((STATISTICS / label).glob("*.csv")))
        document = {
            "schema_version": "1.0.0",
            "panel_id": f"F5_{label}",
            "status": "partial_reproduction" if label in "ABC" else "reproduced",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "command": [
                ".venv/bin/python3.12",
                wrapper.relative_to(PROJECT).as_posix(),
            ],
            "inputs": [
                _artifact(Path(__file__).resolve()),
                _artifact(wrapper),
                _artifact(config),
                *map(_artifact, panel_inputs[label]),
            ],
            "outputs": [_artifact(path) for path in outputs],
            "software": {
                "python": platform.python_version(),
                "pandas": pd.__version__,
                "numpy": np.__version__,
                "matplotlib": plt.matplotlib.__version__,
            },
            "parameters": {
                "dynamic_gradient_age_h": 3,
                "dynamic_duration_h": 8,
                "active_model_cells_per_seed": 26,
                "active_model_seed_range": [1000, 1099],
                "active_model_seed_count_per_group": 100,
                "active_model_phenotypes": PHENOTYPES,
                "active_model_observable": "mean net displacement per seed (um)",
                "active_model_dt_s": SIMULATION_DT_S,
                "active_model_config_dt_s": 0.05,
                "active_model_dt_tolerance": CONVERGENCE_TOLERANCE,
                "active_model_box_scale": QUANTITATIVE_BOX_SCALE,
                # The four global noise scales. None has a source, so the record
                # carries them rather than leaving them in a config file.
                "active_model_noise_scales": simulation_config()["noise"],
            },
            "random_seeds": {
                "population": "1000-1099",
                "starting_positions": "population seed + 1",
                "agarose_obstacles": "population seed + 300",
            },
            "limitations": limitations[label],
        }
        metadata = panel_root / "metadata/provenance.json"
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def allocation_colors() -> dict[float, str]:
    """Return the declared allocation ramp, keyed by the numeric allocation."""
    return {
        allocation: get_condition_color("allocation", f"{allocation:g}")
        for allocation in FLAGELLAR_ALLOCATIONS
    }


def _strain_color(phenotype: str) -> str:
    return get_strain_style(STRAIN_IDS[phenotype])["color"]


def baseline_trajectory() -> pd.DataFrame:
    """Return the recorded zero-allocation growth trajectory.

    The panel draws this curve only when the recorded solver status of that
    exact step says ``success``.  No value is interpolated across the sweep and
    no value is invented.  The endpoint of the trajectory is checked against the
    endpoint the status table recorded, so the curve and the status cannot drift
    apart.
    """
    if not LOW_ALLOCATION_STATUS.exists():
        raise FileNotFoundError(
            f"{LOW_ALLOCATION_STATUS} is missing. Run "
            "models/cell_economy/low_allocation_sweep.py --continuation first."
        )
    status = pd.read_csv(LOW_ALLOCATION_STATUS)
    match = status.loc[np.isclose(status.flagellar_allocation, BASELINE_ALLOCATION)]
    if match.empty:
        raise ValueError(f"{LOW_ALLOCATION_STATUS} records no zero-allocation step.")
    row = match.iloc[0]
    if row.status != "success":
        raise ValueError(
            f"The zero-allocation solve is recorded as '{row.status}'. "
            "Figure 5B draws solved values only."
        )
    path = LOW_ALLOCATION_TRAJECTORIES / f"dynamic_flag_{BASELINE_ALLOCATION:.4f}.csv"
    frame = pd.read_csv(path)
    frame = frame.loc[frame.time > 0].copy()
    frame["flagella"] = BASELINE_ALLOCATION
    recorded = float(row.objective_final_growth_rate_1h)
    if not np.isclose(float(frame.iloc[-1].mu), recorded, rtol=1e-9):
        raise ValueError(
            f"{path.name} ends at {frame.iloc[-1].mu} 1/h, but the status table "
            f"records {recorded} 1/h."
        )
    biomass = 1.0
    values: list[float] = []
    for growth_rate in frame.mu:
        biomass += float(growth_rate) * biomass
        values.append(biomass)
    frame["biomass"] = values
    return frame


def swimming_table() -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for path in sorted(MODEL_RESULTS.glob("dynamic_flag_*.csv")):
        frame = pd.read_csv(path)
        frame = frame.loc[frame.time > 0].copy()
        frame["flagella"] = float(path.stem.split("flag_")[1])
        biomass = 1.0
        values: list[float] = []
        for growth_rate in frame.mu:
            biomass += float(growth_rate) * biomass
            values.append(biomass)
        frame["biomass"] = values
        rows.append(frame)
    result = pd.concat(rows, ignore_index=True)
    observed = sorted(result.flagella.unique())
    if not np.allclose(observed, FLAGELLAR_ALLOCATIONS):
        raise ValueError(f"Unexpected dynamic-model allocations: {observed}")
    return result


def seed_plan() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"phenotype": phenotype, "medium": medium, "seed": seed, "n_cells": 26}
            for phenotype in PHENOTYPES
            for medium in MEDIA
            for seed in SEEDS
        ]
    )


def simulation_config(dt_s: float | None = None, box_scale: int | None = None) -> dict:
    """Return the upstream config with the step and the domain overridden.

    The upstream ``config.yml`` is immutable provenance, so every override is
    applied here instead of being written back into that file.  ``box_scale``
    enlarges the box and scales the obstacle count with its area; it defaults to
    the quantitative scale used by Figure 5D and 5E.

    The stalled-cell translational noise scale is written in as well.  Upstream
    kept it as a bare literal inside the integration loop, so it reached no
    config file and no table.  Naming it here does not change its value, 0.20,
    and so does not change any number the panels report; it makes the constant
    visible to the provenance record and to Supplementary Table X.
    """
    config = yaml.safe_load((ACTIVE_MODEL / "data/config.yml").read_text(encoding="utf-8"))
    if int(config["simulation"]["n_cells"]) != 26:
        raise ValueError("The approved seed-summary contract requires 26 cells per simulation.")
    config["simulation"]["dt_s"] = float(SIMULATION_DT_S if dt_s is None else dt_s)
    config["noise"]["stall_translational_scale"] = float(simulation.STALL_TRANSLATIONAL_SCALE)
    return simulation.scaled_config(
        config, QUANTITATIVE_BOX_SCALE if box_scale is None else box_scale
    )


def track_observables(history: np.ndarray) -> dict[str, np.ndarray]:
    """Return per-cell net displacement and contour path length for one run.

    ``history`` has shape ``(steps + 1, cells, 2)`` in micrometres.  Net
    displacement is the straight-line distance from the first to the last
    recorded position.  Path length is the summed step length; it is reported
    only by the convergence diagnostic, because it does not converge.
    """
    steps = np.diff(history, axis=0)
    return {
        "net_displacement_um": np.linalg.norm(history[-1] - history[0], axis=1),
        "path_length_um": np.sqrt((steps**2).sum(axis=2)).sum(axis=0),
    }


def active_particle_seed_summary(
    plan: pd.DataFrame | None = None,
    parameters_path: Path | None = None,
    dt_s: float | None = None,
) -> pd.DataFrame:
    """Run deterministic simulations and return one plotted value per seed.

    ``parameters_path`` defaults to the adopted table, which carries the global
    literature-anchored turn angle and the flagella-scaled stall probability.
    Pass the delivered table to reproduce the collaborator's original run.
    ``dt_s`` defaults to the converged step in ``SIMULATION_DT_S``.
    """
    if plan is None:
        plan = seed_plan()
    if parameters_path is None:
        parameters_path = adopted_parameter_table_path()
    parameters = load_parameter_table(parameters_path)
    config = simulation_config(dt_s)
    rows: list[dict[str, float | int | str]] = []
    for item in plan.itertuples(index=False):
        if item.phenotype not in PHENOTYPES or item.medium not in MEDIA:
            raise ValueError(f"Non-manuscript simulation requested: {item.phenotype}/{item.medium}")
        params = parameters[(item.phenotype, item.medium)]
        obstacles = None
        obstacle_seed: int | None = None
        if item.medium == "agarose":
            obstacle_seed = int(item.seed) + 300
            obstacles = simulation.make_obstacle_field(config, seed=obstacle_seed)
        result = simulation.simulate_population(config, params, obstacles, int(item.seed))
        displacement = track_observables(result["history"])["net_displacement_um"]
        rows.append(
            {
                "phenotype": item.phenotype,
                "medium": item.medium,
                "seed": int(item.seed),
                "dt_s": float(config["simulation"]["dt_s"]),
                "box_width_um": float(config["simulation"]["box_width_um"]),
                "box_height_um": float(config["simulation"]["box_height_um"]),
                "n_obstacles": 0 if obstacles is None else int(obstacles.n_obstacles),
                # The density check: it must match the published field whatever
                # the box size.
                "obstacle_area_fraction": float(result["obstacle_area_fraction"]),
                "contact_events": int(result["contact_events"]),
                "stall_entries": int(result["stall_entries"]),
                "starting_position_seed": int(item.seed) + 1,
                "obstacle_seed": obstacle_seed,
                "n_cells": len(displacement),
                OBSERVABLE_COLUMN: float(displacement.mean()),
                "predicted_median_net_displacement_um": float(np.median(displacement)),
                "predicted_cell_q25_net_displacement_um": float(np.quantile(displacement, 0.25)),
                "predicted_cell_q75_net_displacement_um": float(np.quantile(displacement, 0.75)),
                "realized_motile_fraction": float(result["is_motile"].mean()),
            }
        )
    return pd.DataFrame(rows)


def summarize_seed_predictions(seed_data: pd.DataFrame) -> pd.DataFrame:
    """Summarise the seed-level means per phenotype and medium.

    The summary names its observable and its time step in their own columns, so
    a reader of the statistics table never has to infer either from the figure.
    """
    summary = seed_data.groupby(["phenotype", "medium"], as_index=False).agg(
        seed_mean=(OBSERVABLE_COLUMN, "mean"),
        seed_median=(OBSERVABLE_COLUMN, "median"),
        simulation_interval_2_5=(OBSERVABLE_COLUMN, lambda values: values.quantile(0.025)),
        simulation_interval_97_5=(OBSERVABLE_COLUMN, lambda values: values.quantile(0.975)),
        n_seeds=(OBSERVABLE_COLUMN, "size"),
    )
    summary.insert(2, "observable", "mean net displacement per seed")
    summary.insert(3, "unit", "um")
    if "dt_s" in seed_data.columns:
        summary.insert(4, "dt_s", float(seed_data.dt_s.iloc[0]))
    return summary


def panel_a() -> None:
    swim = swimming_table()
    final = swim.sort_values("time").groupby("flagella", as_index=False).tail(1).copy()
    final["distance_travelled_um"] = 8500 - final.distance
    gradient = pd.read_csv(MODEL_RESULTS / "substrate_gradient.csv")
    gradient["distance_travelled_um"] = 8500 - gradient.dist_um
    colors = allocation_colors()
    fig, ax = plt.subplots(figsize=panel_figsize(FIGURE_ID, "A"), constrained_layout=True)
    secondary = ax.twinx()
    secondary.fill_between(
        gradient.distance_travelled_um,
        0,
        gradient.substrate_mM,
        color=GRADIENT_FILL,
        alpha=0.55,
        linewidth=0,
        zorder=0,
    )
    secondary.set(ylabel="Glucose concentration (mM)", ylim=(0, 5.2))
    secondary.spines["right"].set_visible(True)
    ax.patch.set_alpha(0)
    ax.set_zorder(2)
    for row in final.itertuples():
        fill = colors[row.flagella]
        edge, edge_width = marker_edge(fill)
        ax.hlines(
            row.flagella * 100,
            0,
            row.distance_travelled_um,
            color=fill,
            lw=1.4,
        )
        ax.scatter(
            row.distance_travelled_um,
            row.flagella * 100,
            color=fill,
            s=POINT_MARKER_SIZE,
            edgecolor=edge,
            linewidths=edge_width,
            zorder=3,
        )
    ax.set(
        xlim=(0, 8500),
        ylim=(0.2, 5.3),
        xlabel="Distance travelled after 8 h (µm)",
        ylabel="Flagellar allocation (%)",
        xticks=[0, 2000, 4000, 6000, 8000],
        yticks=[0.5, 1, 2, 3, 4, 5],
        yticklabels=["0.5", "1", "2", "3", "4", "5"],
    )
    # A coauthor asked that every drawn element carry a definition.  The shading,
    # the horizontal segment and the endpoint circle each get one legend entry.
    fig.legend(
        handles=[
            Patch(facecolor=GRADIENT_FILL, alpha=0.55, label="Fixed 3-h glucose gradient"),
            Line2D([], [], color=KEY_SWATCH, lw=1.4, label="Distance travelled by 8 h"),
            Line2D(
                [],
                [],
                color=KEY_SWATCH,
                lw=0,
                marker="o",
                markersize=np.sqrt(POINT_MARKER_SIZE),
                label="Endpoint after 8 h",
            ),
        ],
        loc="outside upper center",
        frameon=False,
        fontsize=TICK_FONT_PT,
        handlelength=1.4,
        handletextpad=0.5,
        labelspacing=0.25,
        borderpad=0.0,
        borderaxespad=0.15,
    )
    write_source(
        final[["flagella", "time", "distance", "distance_travelled_um", "cex", "v_swim", "mu"]],
        "A",
        "distance_endpoints.csv",
    )
    write_source(
        gradient[["distance_travelled_um", "dist_um", "substrate_mM"]],
        "A",
        "glucose_gradient.csv",
    )
    save_figure(fig, panel_stem("A"))
    plt.close(fig)


def non_motile_gain(swim: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    """Return the 8-h gain of every drawn allocation over the non-motile cell.

    A coauthor asked for the model prediction at zero flagellar allocation,
    expressed as the gain relative to a non-motile cell.  Both quantities come
    from solved trajectories: the growth rate at 8 h, and the compounded biomass
    that Figure 5C plots.  Nothing here is fitted or interpolated.
    """
    final = swim.sort_values("time").groupby("flagella", as_index=False).tail(1)
    reference = baseline.iloc[-1]
    rows = [
        {
            "flagellar_allocation": float(row.flagella),
            "flagellar_allocation_percent": float(row.flagella) * 100,
            "growth_rate_8h_1h": float(row.mu),
            "non_motile_growth_rate_8h_1h": float(reference.mu),
            "growth_rate_gain": float(row.mu) / float(reference.mu),
            "final_biomass": float(row.biomass),
            "non_motile_final_biomass": float(reference.biomass),
            "biomass_gain": float(row.biomass) / float(reference.biomass),
        }
        for row in final.itertuples()
    ]
    return pd.DataFrame(rows).sort_values("flagellar_allocation")


def panel_b() -> None:
    swim = swimming_table()
    data = swim[["flagella", "time", "mu"]]
    baseline = baseline_trajectory().sort_values("time")
    colors = allocation_colors()
    # The zero-allocation curve is a reference, not a seventh step of the ramp,
    # so it carries the neutral summary ink and a dashed stroke.
    strokes = {BASELINE_ALLOCATION: SUMMARY_INK, **colors}
    fig, ax = plt.subplots(figsize=panel_figsize(FIGURE_ID, "B"), constrained_layout=True)
    endpoints: list[tuple[float, float]] = []
    ax.plot(
        baseline.time,
        baseline.mu,
        color=SUMMARY_INK,
        lw=1.1,
        linestyle=(0, (2.6, 1.4)),
    )
    for allocation, part in data.groupby("flagella"):
        part = part.sort_values("time")
        ax.plot(part.time, part.mu, color=colors[allocation], lw=1.25)
        last = part.iloc[-1]
        endpoints.append((allocation, float(last.mu)))
    # The dashed curve needs its meaning where it is drawn.  It runs flat along
    # the floor of the panel, so the note sits just above it and crosses nothing.
    # The curve is deliberately kept out of the right-hand label stack: a seventh
    # entry there would push the lowest label off the axes.
    ax.annotate(
        "0%: non-motile",
        xy=(1.05, float(baseline.iloc[1].mu)),
        xytext=(0, 3.0),
        textcoords="offset points",
        color=SUMMARY_INK,
        ha="left",
        va="bottom",
        fontsize=TICK_FONT_PT,
    )
    ax.set(
        xlabel="Time (h)",
        # Plain text, not mathtext: matplotlib draws a superscript at 0.7x the
        # label size, which would print the exponent below the 6 pt page floor.
        ylabel="Growth rate (1/h)",
        xlim=(0, 10.4),
        xticks=[0, 2, 4, 6, 8],
    )
    # Direct labels replace a six-entry legend.  Their minimum spacing is derived
    # from the drawn axes, so the stack never overlaps at the printed size.
    fig.canvas.draw()
    axis_low, axis_high = ax.get_ylim()
    axes_height_pt = ax.get_window_extent().height * 72.0 / fig.dpi
    minimum_gap = (axis_high - axis_low) * (TICK_FONT_PT * 1.4) / axes_height_pt
    order = np.argsort([value for _, value in endpoints])
    label_positions = np.asarray([value for _, value in endpoints], dtype=float)[order]
    for index in range(1, len(label_positions)):
        label_positions[index] = max(
            label_positions[index], label_positions[index - 1] + minimum_gap
        )
    ceiling = axis_high - 0.5 * minimum_gap
    if label_positions[-1] > ceiling:
        label_positions -= label_positions[-1] - ceiling
    inverse = np.empty_like(order)
    inverse[order] = np.arange(len(order))
    label_positions = label_positions[inverse]
    for (allocation, endpoint), label_y in zip(endpoints, label_positions, strict=True):
        ax.annotate(
            f"{allocation * 100:g}%",
            xy=(8.0, endpoint),
            xytext=(8.45, label_y),
            color=strokes[allocation],
            ha="left",
            va="center",
            fontsize=TICK_FONT_PT,
            arrowprops={
                "arrowstyle": "-",
                "color": strokes[allocation],
                "lw": 0.45,
                "shrinkB": 3.0,
            },
        )
    ax.set_ylim(axis_low, axis_high)
    plotted = pd.concat(
        [baseline[["flagella", "time", "mu"]], data], ignore_index=True
    ).sort_values(["flagella", "time"])
    write_source(plotted, "B", "growth_trajectories.csv")
    write_source(non_motile_gain(swim, baseline), "B", "non_motile_gain.csv")
    save_figure(fig, panel_stem("B"))
    plt.close(fig)


def panel_c() -> None:
    swim = swimming_table()
    data = (
        swim.sort_values("time")
        .groupby("flagella", as_index=False)
        .tail(1)[["flagella", "biomass"]]
    )
    data = data.sort_values("flagella")
    data["relative_biomass"] = data.biomass / data.biomass.max()
    colors = allocation_colors()
    fig, ax = plt.subplots(figsize=panel_figsize(FIGURE_ID, "C"), constrained_layout=True)
    ax.plot(data.flagella * 100, data.relative_biomass, color=SUMMARY_INK, lw=0.9, zorder=1)
    for row in data.itertuples():
        fill = colors[row.flagella]
        edge, edge_width = marker_edge(fill)
        ax.scatter(
            row.flagella * 100,
            row.relative_biomass,
            color=fill,
            s=POINT_MARKER_SIZE,
            edgecolor=edge,
            linewidths=edge_width,
            zorder=2,
        )
        # The connecting guide passes close to the two labels on the rising
        # limb, so each value carries a background-coloured halo.
        ax.text(
            row.flagella * 100,
            row.relative_biomass + 0.03,
            f"{row.relative_biomass:.2f}",
            ha="center",
            va="bottom",
            fontsize=TICK_FONT_PT,
            zorder=3,
            path_effects=[path_effects.withStroke(linewidth=1.8, foreground=PAPER)],
        )
    ax.set(
        xlabel="Flagellar allocation (%)",
        ylabel="Relative final biomass",
        xticks=[0.5, 1, 2, 3, 4, 5],
        xticklabels=["0.5", "1", "2", "3", "4", "5"],
        ylim=(0.15, 1.14),
    )
    write_source(data, "C", "relative_biomass.csv")
    save_figure(fig, panel_stem("C"))
    plt.close(fig)


def _plot_active_prediction(seed_data: pd.DataFrame, medium: str, panel: str) -> None:
    part = seed_data.query("medium == @medium").copy()
    summary = summarize_seed_predictions(part)
    fig, ax = plt.subplots(figsize=panel_figsize(FIGURE_ID, panel), constrained_layout=True)
    for x_position, phenotype in enumerate(PHENOTYPES):
        values = part.query("phenotype == @phenotype").sort_values("seed")
        jitter = ((values.seed.to_numpy() * 37) % 101 - 50) / 240
        fill = _strain_color(phenotype)
        point_edge, point_edge_width = marker_edge(fill)
        ax.scatter(
            x_position + jitter,
            values[OBSERVABLE_COLUMN],
            s=DENSITY_MARKER_SIZE,
            alpha=0.36,
            color=fill,
            edgecolor=point_edge,
            linewidths=point_edge_width,
        )
        row = summary.query("phenotype == @phenotype").iloc[0]
        # The interval bar and the median diamond are summary marks, so both
        # carry the summary ink.  Strain identity is already given by the
        # position on the axis and by the colour of the seed cloud.
        ax.vlines(
            x_position,
            row.simulation_interval_2_5,
            row.simulation_interval_97_5,
            color=SUMMARY_INK,
            lw=1.1,
            zorder=4,
        )
        summary_edge, summary_edge_width = marker_edge(SUMMARY_INK)
        ax.scatter(
            x_position,
            row.seed_median,
            marker="D",
            s=POINT_MARKER_SIZE,
            color=SUMMARY_INK,
            edgecolor=summary_edge,
            linewidth=summary_edge_width,
            zorder=5,
        )
    ax.set(
        xticks=np.arange(len(PHENOTYPES)),
        xticklabels=PHENOTYPES,
        xlabel="Phenotype",
        # Net displacement is a model output. Speed, motile fraction and
        # persistence time are calibrated inputs, so the title says so and the
        # axis says "simulated" rather than "predicted".
        ylabel="Simulated mean net displacement (µm)",
        title=(
            "Liquid — calibrated speed and turning"
            if medium == "liquid"
            else "Agarose-like mesh — calibrated speed and turning"
        ),
    )
    # The key maps each symbol to a short name. The sentence that bounds how the
    # intervals may be read lives in the figure legend, not in the panel.
    fig.legend(
        handles=[
            Line2D(
                [],
                [],
                lw=0,
                marker="o",
                markersize=np.sqrt(DENSITY_MARKER_SIZE),
                color=KEY_SWATCH,
                markeredgewidth=0,
                label="One seed mean (26 cells)",
            ),
            Line2D(
                [],
                [],
                lw=0,
                marker="D",
                markersize=np.sqrt(POINT_MARKER_SIZE),
                color=SUMMARY_INK,
                markeredgewidth=0,
                label="Median of 100 seed means",
            ),
            Line2D([], [], color=SUMMARY_INK, lw=1.1, label="2.5–97.5% simulation interval"),
        ],
        loc="outside upper center",
        ncols=2,
        frameon=False,
        alignment="left",
        fontsize=TICK_FONT_PT,
        handlelength=1.4,
        handletextpad=0.5,
        labelspacing=0.25,
        columnspacing=1.2,
        borderpad=0.0,
        borderaxespad=0.15,
    )
    write_source(part, panel, f"{medium}_seed_predictions.csv")
    write_source(summary, panel, f"{medium}_summary.csv")
    statistics_dir = STATISTICS / panel
    statistics_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(statistics_dir / f"{medium}_simulation_interval.csv", index=False)
    save_figure(fig, panel_stem(panel))
    plt.close(fig)


def _cached_seed_summary(
    path: Path, parameters_path: Path, fingerprint: Path, force: bool
) -> pd.DataFrame:
    """Return the seed summary, rerunning whenever an input changed.

    The cache is keyed by the checksum of the parameter table, by the time step
    and by the plotted observable, so a recalibration, a refined step or a
    changed observable invalidates a stale run instead of being silently reused.
    """
    key = b"".join(
        [
            parameters_path.read_bytes(),
            repr(float(SIMULATION_DT_S)).encode("utf-8"),
            repr(int(QUANTITATIVE_BOX_SCALE)).encode("utf-8"),
            OBSERVABLE_COLUMN.encode("utf-8"),
            # The dynamics are part of the cache key, so a change in the
            # corrected model invalidates a stale run instead of being reused.
            (CORRECTED_MODEL / "src/salmonella_motility_corrected/simulation.py").read_bytes(),
        ]
    )
    digest = hashlib.sha256(key).hexdigest()
    stale = not fingerprint.exists() or fingerprint.read_text(encoding="utf-8").strip() != digest
    if path.exists() and not force and not stale:
        return pd.read_csv(path)
    seed_data = active_particle_seed_summary(parameters_path=parameters_path)
    seed_data.to_csv(path, index=False)
    fingerprint.write_text(digest + "\n", encoding="utf-8")
    return seed_data


def delivered_parameter_diagnostic(force: bool = False) -> pd.DataFrame:
    """Run the same seed plan on the delivered table and keep it as a diagnostic.

    The collaborator conversation about the uncalibrated turning parameters is
    still open, so this run stays reproducible. It is written under
    ``build/diagnostics`` and never becomes a panel.
    """
    DIAGNOSTICS.mkdir(parents=True, exist_ok=True)
    seed_data = _cached_seed_summary(
        DIAGNOSTICS / "active_particle_100_seed_summary_delivered_parameters.csv",
        DELIVERED_PARAMETERS,
        DIAGNOSTICS / "active_particle_delivered_parameters.sha256",
        force,
    )
    summary = summarize_seed_predictions(seed_data)
    summary.to_csv(DIAGNOSTICS / "delivered_parameter_summary.csv", index=False)
    return seed_data


def panels_d_e(labels: list[str], force: bool = False) -> None:
    path = PROCESSED / "active_particle_100_seed_summary.csv"
    parameters_path = adopted_parameter_table_path()
    seed_data = _cached_seed_summary(
        path, parameters_path, PROCESSED / "active_particle_parameters.sha256", force
    )
    delivered_parameter_diagnostic(force=force)
    plan = seed_plan()
    plan.to_csv(PROCESSED / "active_particle_seed_plan.csv", index=False)
    if len(seed_data) != 600 or seed_data.groupby(["phenotype", "medium"]).size().ne(100).any():
        raise ValueError(
            "Expected 100 deterministic seeds for each of six phenotype-medium groups."
        )
    if set(seed_data.phenotype) != set(PHENOTYPES):
        raise ValueError("Seed summary includes a non-manuscript phenotype such as WT_slow.")
    if "D" in labels:
        _plot_active_prediction(seed_data, "liquid", "D")
    if "E" in labels:
        _plot_active_prediction(seed_data, "agarose", "E")


def build_selected(labels: list[str], force_simulation: bool = False) -> None:
    apply_publication_style()
    _ensure_dirs()
    builders = {"A": panel_a, "B": panel_b, "C": panel_c}
    for label in labels:
        if label in builders:
            builders[label]()
    active_labels = [label for label in labels if label in "DE"]
    if active_labels:
        panels_d_e(active_labels, force=force_simulation)
    write_provenance(labels)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--panel", choices=list("ABCDE"))
    parser.add_argument("--force-simulation", action="store_true")
    args = parser.parse_args()
    if args.all == bool(args.panel):
        parser.error("Pass exactly one of --all or --panel A-E.")
    build_selected(
        list("ABCDE") if args.all else [args.panel],
        force_simulation=args.force_simulation,
    )


if __name__ == "__main__":
    main()
