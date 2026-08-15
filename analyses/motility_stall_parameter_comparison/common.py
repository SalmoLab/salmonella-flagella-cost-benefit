#!/usr/bin/env python3
"""Shared machinery for the stall-parameter comparison.

Two parameters of the active-particle simulation differ per strain in agarose
and have no source: ``stall_probability`` and ``stall_mean_duration_s``.  This
module builds parameter-table variants that redistribute those two numbers
between the strains, runs the manuscript seed plan on each variant, and returns
one row per simulation.

Nothing here writes a manuscript panel.  Every output is a decision aid under
``build/diagnostics/stall_parameter_comparison``.

The baseline is the adopted global-turn-angle table derived by
``analyses/motility_turn_angle_comparison/calibrate_global_turn_angle.py``.  It
is read, never written.  The upstream simulator and its ``config.yml`` are read,
never modified.

Setup:
    PYTHONPATH=$PWD/src .venv/bin/python \\
        analyses/motility_stall_parameter_comparison/compare_stall_variants.py

Complexity is O(variants * strains * seeds * steps * cells).  One simulation at
``dt = 0.0025`` s takes about 1.6 s, so a variant of 100 seeds and 3 strains
takes about 8 min on one core and about 1.5 min on seven.
"""

from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT = Path(__file__).resolve().parents[2]
UPSTREAM = PROJECT / "models/motility_simulation/upstream"

#: The adopted parameter table.  Read only.
BASE_TABLE = (
    PROJECT
    / "data/processed/motility_turn_angle_comparison"
    / "motility_summary_parameters_global_turn_angle.csv"
)
#: Per-cell hook counts, the source of the mean flagella number per strain.
HOOK_COUNTS = PROJECT / "data/processed/figure_07_revision/hook_count_per_cell.csv"
#: Paired experimental units, the source of the measured speed, tau and D_eff.
MEASURED = PROJECT / "data/processed/figure_07_revision/paired_experimental_unit_measurements.csv"

OUTPUT = PROJECT / "build/diagnostics/stall_parameter_comparison"
TABLES = OUTPUT / "parameter_tables"

# The manuscript seed plan.  These four values are duplicated from
# analyses/figure_05_revision/build.py deliberately: that file is being edited
# by another workstream, and this comparison must not depend on its import
# surface.  They are asserted against the built seed summary in
# check_seed_plan_matches_manuscript().
PHENOTYPES = ("PproA", "WT", "PproB")
SEEDS = tuple(range(1000, 1100))
DT_S = 0.0025
N_CELLS = 26

#: Reference strain for the reported net-displacement ratios.
REFERENCE_PHENOTYPE = "PproA"

BOOTSTRAP_SEED = 20260813
BOOTSTRAP_DRAWS = 10_000

#: Lag used for the effective-diffusivity diagnostic, in seconds.  Long compared
#: with the persistence time (0.06 - 0.11 s), short enough that the root mean
#: square displacement stays well inside the 148 x 96 um box.
MSD_LAG_S = 2.0

#: Mean dwell time in 0.25 % agar, *Pseudomonas putida*, Datta et al. 2025,
#: Sci Rep 15:20320, doi 10.1038/s41598-025-02741-1, PMID 40579453.  Used as the
#: only literature anchor available for a stall duration.
DATTA_MEAN_DWELL_S = 2.07

#: Ratio by which lateral flagella lower the stall frequency in 0.25 % agar,
#: *Vibrio alginolyticus*, Grognot et al. 2023, PNAS 120:e2301873120,
#: doi 10.1073/pnas.2301873120, PMID 37579142.  Quoted as 1.7 +/- 0.2 (mean +/- SD).
GROGNOT_STALL_FREQUENCY_RATIO = 1.7
GROGNOT_STALL_FREQUENCY_RATIO_SD = 0.2


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def mean_hooks() -> dict[str, float]:
    """Return the mean hook count per cell for each strain.

    Read from the per-cell hook table rather than typed in, so a change in the
    hook data propagates into every flagella-number scaling.

    Example:
        >>> round(mean_hooks()["PproA"], 2)
        2.09
    """
    frame = pd.read_csv(HOOK_COUNTS, usecols=["assigned_alias", "hook_count"])
    means = frame.groupby("assigned_alias").hook_count.mean()
    return {phenotype: float(means[phenotype]) for phenotype in PHENOTYPES}


@lru_cache(maxsize=1)
def base_table() -> pd.DataFrame:
    """Return the adopted parameter table."""
    return pd.read_csv(BASE_TABLE)


@lru_cache(maxsize=1)
def measured_summary() -> pd.DataFrame:
    """Return the measured speed, persistence time and diffusivity per group.

    ``tau`` in the measurement table is derived as ``2 * D_eff / v^2`` by
    ``analyses/figure_07_revision/build_figure_07_revision.py``.  It is therefore
    not an independent measurement of directional persistence: the measured
    ``D_eff`` and the measured speed determine it exactly.  That identity is the
    whole point of the double-counting check, so both columns are carried here.
    """
    units = pd.read_csv(MEASURED)
    rows: list[dict[str, object]] = []
    for medium, part in units.groupby("medium"):
        for phenotype in PHENOTYPES:
            speed = float(part[f"speed_med_{phenotype}"].mean())
            tau = float(part[f"tau_{phenotype}"].mean())
            rows.append(
                {
                    "phenotype": phenotype,
                    "medium": str(medium),
                    "n_units": int(part[f"tau_{phenotype}"].notna().sum()),
                    "measured_speed_um_s": speed,
                    "measured_tau_s": tau,
                    "measured_diffusivity_um2_s": float(part[f"diff_med_{phenotype}"].mean()),
                    "implied_diffusivity_um2_s": speed * speed * tau / 2.0,
                    "measured_motile_fraction": float(part[f"swim_frac_{phenotype}"].mean()),
                }
            )
    return pd.DataFrame(rows)


@lru_cache(maxsize=1)
def simulation_config_template() -> dict:
    """Return the frozen upstream config with the manuscript time step applied."""
    config = yaml.safe_load((UPSTREAM / "data/config.yml").read_text(encoding="utf-8"))
    if int(config["simulation"]["n_cells"]) != N_CELLS:
        raise ValueError("The seed-summary contract requires 26 cells per simulation.")
    config["simulation"]["dt_s"] = float(DT_S)
    return config


# ---------------------------------------------------------------------------
# Variant construction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Variant:
    """One parameter-table variant of the two stall parameters.

    ``probability_exponent`` and ``duration_exponent`` are the exponents ``a`` in
    ``x_s ∝ N_s^-a``.  ``a = 0`` gives one global value.  Every scaled column is
    renormalised so its arithmetic mean over the three strains equals the mean of
    the three current values, so a variant changes how the effect is distributed
    between strains, not its overall size.
    """

    key: str
    label: str
    description: str
    probability_exponent: float | None = None
    duration_exponent: float | None = None
    #: Set to keep the delivered per-strain columns untouched (the baseline).
    keep_delivered: bool = False
    #: Set to override the global duration with a fixed value, in seconds.
    duration_override_s: float | None = None


def _normalised(values: dict[str, float], exponent: float, target_mean: float) -> dict[str, float]:
    """Return ``N^-exponent`` weights rescaled to a given arithmetic mean.

    Example:
        >>> out = _normalised({"a": 1.0, "b": 3.0}, 1.0, 2.0)
        >>> round((out["a"] + out["b"]) / 2, 6), round(out["a"] / out["b"], 6)
        (2.0, 3.0)
    """
    hooks = mean_hooks()
    weights = {name: hooks[name] ** (-exponent) for name in values}
    scale = target_mean / (sum(weights.values()) / len(weights))
    return {name: weight * scale for name, weight in weights.items()}


def current_stall_values() -> tuple[dict[str, float], dict[str, float]]:
    """Return the current per-strain agarose stall probability and duration."""
    agarose = base_table().query("medium == 'agarose'").set_index("phenotype")
    probability = {name: float(agarose.loc[name, "stall_probability"]) for name in PHENOTYPES}
    duration = {name: float(agarose.loc[name, "stall_mean_duration_s"]) for name in PHENOTYPES}
    return probability, duration


def grognot_exponent() -> float:
    """Return the flagella-number exponent that reproduces Grognot's 1.7-fold ratio.

    Grognot et al. 2023 report that lateral flagella lower the stall frequency by
    a factor 1.7 +/- 0.2 in 0.25 % agar.  Mapping that onto our strains means
    setting the ratio between the least and the most flagellated strain to 1.7:

        a = ln(1.7) / ln(N_PproB / N_PproA)

    This is an assumption, not a measurement.  Grognot's contrast is a second
    flagellar system, not a flagella count, so the mapping onto our hook numbers
    is a choice made here.
    """
    hooks = mean_hooks()
    span = hooks["PproB"] / hooks["PproA"]
    return math.log(GROGNOT_STALL_FREQUENCY_RATIO) / math.log(span)


def variants() -> list[Variant]:
    """Return the comparison grid, baseline first."""
    return [
        Variant(
            "A_baseline",
            "A baseline",
            "Current table: per-strain probability, per-strain duration. Neither has a source.",
            keep_delivered=True,
        ),
        Variant(
            "B_global_global",
            "B global p, global t",
            "Both parameters set to the mean of the three current values.",
            probability_exponent=0.0,
            duration_exponent=0.0,
        ),
        Variant(
            "C_global_p_duration_inv_n",
            "C global p, t ~ 1/N",
            "Global probability; duration inversely proportional to mean hook number.",
            probability_exponent=0.0,
            duration_exponent=1.0,
        ),
        Variant(
            "D_global_p_duration_inv_sqrt_n",
            "D global p, t ~ 1/sqrt(N)",
            "Global probability; duration inversely proportional to the square root of N.",
            probability_exponent=0.0,
            duration_exponent=0.5,
        ),
        Variant(
            "E_both_inv_n",
            "E p ~ 1/N, t ~ 1/N",
            "Both parameters inversely proportional to mean hook number.",
            probability_exponent=1.0,
            duration_exponent=1.0,
        ),
        Variant(
            "F_literature_duration",
            "F global p, t = 2.07 s",
            (
                "Global probability (no source exists); duration set to the mean dwell "
                "time in 0.25 % agar of Datta et al. 2025."
            ),
            probability_exponent=0.0,
            duration_exponent=0.0,
            duration_override_s=DATTA_MEAN_DWELL_S,
        ),
        Variant(
            "G_grognot_probability",
            "G p ~ N^-0.70, global t",
            (
                "Probability scaled with flagella number at the strength Grognot et al. "
                "2023 measured for the stall frequency; duration global."
            ),
            probability_exponent=None,  # filled by variant_table() from grognot_exponent()
            duration_exponent=0.0,
        ),
    ]


def variant_table(variant: Variant) -> pd.DataFrame:
    """Return the full parameter table for one variant.

    Only the two stall columns of the three agarose rows can change.  The liquid
    rows are untouched; their ``stall_probability`` is zero, so their
    ``stall_mean_duration_s`` never fires.
    """
    table = base_table().copy()
    if variant.keep_delivered:
        return table

    probability, duration = current_stall_values()
    mean_probability = float(np.mean(list(probability.values())))
    mean_duration = float(np.mean(list(duration.values())))

    exponent_p = variant.probability_exponent
    if variant.key == "G_grognot_probability":
        exponent_p = grognot_exponent()
    if exponent_p is None:
        raise ValueError(f"variant {variant.key} has no probability exponent")
    new_probability = _normalised(probability, exponent_p, mean_probability)

    if variant.duration_override_s is not None:
        new_duration = dict.fromkeys(PHENOTYPES, float(variant.duration_override_s))
    else:
        if variant.duration_exponent is None:
            raise ValueError(f"variant {variant.key} has no duration exponent")
        new_duration = _normalised(duration, variant.duration_exponent, mean_duration)

    mask = table.medium == "agarose"
    table.loc[mask, "stall_probability"] = table.loc[mask, "phenotype"].map(new_probability)
    table.loc[mask, "stall_mean_duration_s"] = table.loc[mask, "phenotype"].map(new_duration)
    if table.stall_probability.isna().any() or table.stall_mean_duration_s.isna().any():
        raise ValueError("A phenotype in the base table has no variant value.")
    return table


def variant_table_path(variant: Variant) -> Path:
    """Write the variant table to disk and return its path."""
    TABLES.mkdir(parents=True, exist_ok=True)
    path = TABLES / f"{variant.key}.csv"
    variant_table(variant).to_csv(path, index=False)
    return path


def variant_parameter_summary() -> pd.DataFrame:
    """Return the two stall columns of every variant, agarose only."""
    hooks = mean_hooks()
    rows: list[dict[str, object]] = []
    for variant in variants():
        table = variant_table(variant).query("medium == 'agarose'").set_index("phenotype")
        for phenotype in PHENOTYPES:
            rows.append(
                {
                    "variant": variant.key,
                    "label": variant.label,
                    "phenotype": phenotype,
                    "mean_hooks": hooks[phenotype],
                    "stall_probability": float(table.loc[phenotype, "stall_probability"]),
                    "stall_mean_duration_s": float(table.loc[phenotype, "stall_mean_duration_s"]),
                }
            )
    frame = pd.DataFrame(rows)
    frame["probability_x_duration_s"] = frame.stall_probability * frame.stall_mean_duration_s
    return frame


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


def _import_simulator():
    """Import the frozen upstream simulator without touching sys.path globally."""
    import sys

    path = str(UPSTREAM / "src")
    if path not in sys.path:
        sys.path.insert(0, path)
    from salmonella_motility_simulation import simulation  # noqa: PLC0415
    from salmonella_motility_simulation.__main__ import (  # noqa: PLC0415
        load_parameter_table,
    )

    return simulation, load_parameter_table


def track_metrics(result: dict, config: dict) -> dict[str, float]:
    """Return the observables of one simulated population.

    Three families of number come out of one run.

    * ``net_displacement`` - the manuscript observable, the straight-line
      distance from the first to the last position, averaged over all 26 cells.
    * ``diffusivity`` - estimated from the mean squared displacement over
      non-overlapping lags of ``MSD_LAG_S``, motile cells only, as
      ``MSD / (4 * lag)``.  The lag is long compared with the persistence time
      and short compared with the box crossing time.
    * ``stall_occupancy`` and ``stall_entry_rate_per_s`` - diagnostics of the
      stall state.  Occupancy is the fraction of motile-cell time steps spent
      stalled.  **It does not converge with the time step**, because the stall
      draw is made once per time step of obstacle overlap, so a smaller step
      makes more draws.  Report it only at a stated ``dt``.
    """
    history = result["history"]
    states = result["state_history"]
    motile = result["is_motile"]
    state_stalled = int(config["states"]["stalled"])
    dt_s = float(config["simulation"]["dt_s"])

    displacement = np.linalg.norm(history[-1] - history[0], axis=1)
    metrics: dict[str, float] = {
        "predicted_mean_net_displacement_um": float(displacement.mean()),
        "predicted_median_net_displacement_um": float(np.median(displacement)),
        "motile_mean_net_displacement_um": float(displacement[motile].mean())
        if motile.any()
        else float("nan"),
        "realized_motile_fraction": float(motile.mean()),
    }

    lag_steps = int(round(MSD_LAG_S / dt_s))
    n_steps = history.shape[0] - 1
    origins = np.arange(0, n_steps - lag_steps + 1, lag_steps)
    if len(origins) and motile.any():
        jumps = history[origins + lag_steps][:, motile, :] - history[origins][:, motile, :]
        msd = float((jumps**2).sum(axis=2).mean())
    else:
        msd = float("nan")
    metrics["msd_lag_um2"] = msd
    metrics["diffusivity_estimate_um2_s"] = msd / (4.0 * MSD_LAG_S)

    if motile.any():
        motile_states = states[1:, motile]
        stalled = motile_states == state_stalled
        metrics["stall_occupancy"] = float(stalled.mean())
        entries = int(np.count_nonzero(stalled[1:] & ~stalled[:-1]))
        entries += int(np.count_nonzero(stalled[0]))
        swimming_steps = int(np.count_nonzero(~stalled))
        swimming_time_s = swimming_steps * dt_s
        metrics["stall_entries"] = float(entries)
        metrics["stall_entry_rate_per_swim_s"] = (
            entries / swimming_time_s if swimming_time_s > 0 else float("nan")
        )
    else:
        metrics["stall_occupancy"] = float("nan")
        metrics["stall_entries"] = float("nan")
        metrics["stall_entry_rate_per_swim_s"] = float("nan")
    return metrics


def _run_one(job: tuple[str, str, str, int, bool]) -> dict[str, object]:
    """Run one simulation.  Top level so multiprocessing can pickle it."""
    table_path, phenotype, medium, seed, with_obstacles = job
    simulation, load_parameter_table = _import_simulator()
    parameters = load_parameter_table(Path(table_path))
    config = simulation_config_template()
    obstacles = None
    obstacle_seed = None
    if with_obstacles:
        obstacle_seed = int(seed) + 300
        obstacles = simulation.make_obstacle_field(config, seed=obstacle_seed)
    result = simulation.simulate_population(
        config, parameters[(phenotype, medium)], obstacles, int(seed)
    )
    row: dict[str, object] = {
        "phenotype": phenotype,
        "medium": medium,
        "seed": int(seed),
        "dt_s": float(config["simulation"]["dt_s"]),
        "obstacles": bool(with_obstacles),
        "obstacle_seed": obstacle_seed,
        "n_cells": int(result["history"].shape[1]),
    }
    row.update(track_metrics(result, config))
    return row


def run_condition(
    table_path: Path,
    medium: str,
    with_obstacles: bool,
    processes: int | None = None,
) -> pd.DataFrame:
    """Run the three strains over all seeds for one parameter table."""
    jobs = [
        (str(table_path), phenotype, medium, seed, with_obstacles)
        for phenotype in PHENOTYPES
        for seed in SEEDS
    ]
    workers = processes or max(1, (os.cpu_count() or 2) - 1)
    if workers == 1:
        rows = [_run_one(job) for job in jobs]
    else:
        with Pool(workers) as pool:
            rows = pool.map(_run_one, jobs, chunksize=4)
    return pd.DataFrame(rows)


def cached_condition(
    name: str,
    table_path: Path,
    medium: str,
    with_obstacles: bool,
    force: bool = False,
    processes: int | None = None,
) -> pd.DataFrame:
    """Return one condition's per-seed rows, running it only when the cache is stale.

    The cache key is the checksum of the parameter table, the medium, the
    obstacle switch, the time step and the version of the metric code.  A change
    in any of them invalidates the cache instead of being silently reused.
    """
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / f"runs_{name}.csv"
    fingerprint = OUTPUT / f"runs_{name}.sha256"
    digest = hashlib.sha256(
        Path(table_path).read_bytes()
        + medium.encode("utf-8")
        + repr(with_obstacles).encode("utf-8")
        + repr(float(DT_S)).encode("utf-8")
        + repr(float(MSD_LAG_S)).encode("utf-8")
        + b"metrics-v1"
    ).hexdigest()
    stale = not fingerprint.exists() or fingerprint.read_text(encoding="utf-8").strip() != digest
    if path.exists() and not force and not stale:
        return pd.read_csv(path)
    frame = run_condition(Path(table_path), medium, with_obstacles, processes=processes)
    frame.insert(0, "condition", name)
    frame.to_csv(path, index=False)
    fingerprint.write_text(digest + "\n", encoding="utf-8")
    return frame


# ---------------------------------------------------------------------------
# Paired bootstrap over seeds
# ---------------------------------------------------------------------------


def seed_vectors(
    runs: pd.DataFrame, column: str
) -> tuple[dict[tuple[str, str], np.ndarray], list[int]]:
    """Return one value per seed for every (condition, phenotype), on a shared seed list."""
    seeds = sorted(runs.seed.unique())
    vectors: dict[tuple[str, str], np.ndarray] = {}
    for (condition, phenotype), part in runs.groupby(["condition", "phenotype"]):
        aligned = part.set_index("seed").reindex(seeds)
        if aligned[column].isna().any():
            raise ValueError(f"{condition}/{phenotype} is missing a seed.")
        vectors[(str(condition), str(phenotype))] = aligned[column].to_numpy(dtype=float)
    return vectors, seeds


def bootstrap_draws(n_seeds: int) -> np.ndarray:
    """Return the shared resample index.

    One resample of the seed index is applied to every condition and strain at
    once, so the pairing and the strain ratios survive the resampling.
    """
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    return rng.integers(0, n_seeds, size=(BOOTSTRAP_DRAWS, n_seeds))


def check_seed_plan_matches_manuscript() -> dict[str, object]:
    """Assert that this comparison uses the same seed plan as the built figure.

    The built seed summary of Figure 5 is read, not rebuilt, so this check costs
    nothing and cannot disturb the figure.
    """
    built = PROJECT / "data/processed/figure_05_revision/active_particle_100_seed_summary.csv"
    if not built.exists():
        return {"checked": False, "reason": "built seed summary not present"}
    frame = pd.read_csv(built)
    agarose = frame.query("medium == 'agarose'")
    report = {
        "checked": True,
        "seeds_match": sorted(agarose.seed.unique()) == list(SEEDS),
        "dt_match": bool(np.allclose(agarose.dt_s.unique(), DT_S)),
        "cells_match": bool((agarose.n_cells == N_CELLS).all()),
        "phenotypes_match": set(agarose.phenotype.unique()) == set(PHENOTYPES),
        "obstacle_seed_rule_match": bool((agarose.obstacle_seed == agarose.seed + 300).all()),
    }
    if not all(value for key, value in report.items() if key.endswith("_match")):
        raise AssertionError(f"Seed plan does not match the built figure: {report}")
    return report
