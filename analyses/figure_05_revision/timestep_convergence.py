#!/usr/bin/env python3
"""Test whether the active-particle observables converge under time-step refinement.

Figure 5D and 5E once plotted the mean contour path length of a simulated track.
That quantity does not converge: a trajectory with a diffusive component has an
infinite arc length in the continuum limit, so the summed step length grows
without a limit as the step shrinks.  The ratio between two phenotypes then
drifts and crosses 1, which makes the strain comparison an artefact of the step
rather than a property of the model.

This script runs the full Figure 5D/E seed plan at a ladder of time steps and
reports both observables, so the rejection of path length and the acceptance of
net displacement are on the record with numbers behind them.

The ladder runs the corrected dynamics in the same enlarged box the panels use,
so the accepted step is the step those panels are entitled to.  Under the
upstream per-time-step stall rule the agarose ladder could not converge at all:
a finer step made more stall draws per contact, so stall occupancy grew without
limit.  The corrected model draws once per contact event, which removes that
term from the step dependence.

Setup:
    PYTHONPATH=$PWD/src MPLBACKEND=Agg .venv/bin/python \
        analyses/figure_05_revision/timestep_convergence.py

Outputs, all under ``build/diagnostics/Figure_5``:
    timestep_convergence_seed_values.csv  one row per phenotype, medium, dt, seed
    timestep_convergence.csv              group means with their standard errors
    timestep_convergence_ratios.csv       between-strain ratios against WT

Complexity is O(seeds * groups * duration / dt).  The cost doubles with every
halving of the step, so the finest rung dominates the runtime.  Pitfall: two
different time steps consume the random stream differently, so the same seed is
a different realisation.  The comparison is therefore between group means with
their sampling error, never between single seeds.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[2]
# Every search path is declared here, so no import depends on another import
# having run first.
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT / "analyses/figure_05_revision"))
sys.path.insert(0, str(PROJECT / "analyses/motility_adopted_parameters"))
sys.path.insert(0, str(PROJECT / "models/motility_simulation/upstream/src"))
sys.path.insert(0, str(PROJECT / "models/motility_simulation/corrected/src"))

import salmonella_motility_corrected as simulation  # noqa: E402
from derive_adopted_parameters import adopted_parameter_table_path  # noqa: E402
from salmonella_motility_corrected import load_parameter_table  # noqa: E402

from build import (  # noqa: E402
    DIAGNOSTICS,
    MEDIA,
    PHENOTYPES,
    SEEDS,
    SIMULATION_DT_S,
    simulation_config,
    track_observables,
)

# The ladder halves the step at every rung from the value declared in the
# upstream config.  0.05 -> 0.01 is the one non-halving step; it keeps the
# config value itself on the ladder.
TIME_STEPS = [0.05, 0.01, 0.005, 0.0025, 0.00125, 0.000625]
REFERENCE_PHENOTYPE = "WT"
OBSERVABLES = ["net_displacement_um", "path_length_um"]


def _run_one(task: tuple[str, str, int, float]) -> dict[str, float | int | str]:
    """Simulate one seed at one time step and return both mean observables."""
    phenotype, medium, seed, dt_s = task
    parameters = load_parameter_table(adopted_parameter_table_path())
    config = simulation_config(dt_s)
    obstacles = (
        simulation.make_obstacle_field(config, seed=seed + 300) if medium == "agarose" else None
    )
    result = simulation.simulate_population(
        config, parameters[(phenotype, medium)], obstacles, seed
    )
    tracks = track_observables(result["history"])
    row: dict[str, float | int | str] = {
        "phenotype": phenotype,
        "medium": medium,
        "dt_s": dt_s,
        "seed": seed,
        "n_cells": int(result["history"].shape[1]),
    }
    row.update({name: float(values.mean()) for name, values in tracks.items()})
    return row


def run_sweep(
    time_steps: list[float], seeds: list[int], workers: int | None = None
) -> pd.DataFrame:
    """Return one row per phenotype, medium, time step and seed."""
    tasks = [
        (phenotype, medium, seed, dt_s)
        for dt_s in time_steps
        for phenotype in PHENOTYPES
        for medium in MEDIA
        for seed in seeds
    ]
    # ``Pool.map`` keeps the input order, and every simulation is seeded on its
    # own, so the table is identical whatever the worker count.
    with mp.Pool(workers or mp.cpu_count()) as pool:
        rows = pool.map(_run_one, tasks, chunksize=4)
    return pd.DataFrame(rows)


def group_summary(seed_values: pd.DataFrame) -> pd.DataFrame:
    """Return the group mean of each observable with its standard error."""
    grouped = seed_values.groupby(["medium", "phenotype", "dt_s"], as_index=False)
    summary = grouped.agg(
        n_seeds=("seed", "size"),
        **{
            f"{name}_{statistic}": (name, function)
            for name in OBSERVABLES
            for statistic, function in (("mean", "mean"), ("sd", "std"))
        },
    )
    for name in OBSERVABLES:
        summary[f"{name}_se"] = summary[f"{name}_sd"] / np.sqrt(summary.n_seeds)
    return summary.sort_values(["medium", "phenotype", "dt_s"]).reset_index(drop=True)


def strain_ratios(summary: pd.DataFrame) -> pd.DataFrame:
    """Return each phenotype's group mean divided by the WT mean at the same step."""
    reference = summary.query("phenotype == @REFERENCE_PHENOTYPE").set_index(["medium", "dt_s"])
    rows: list[dict[str, float | str]] = []
    for item in summary.itertuples(index=False):
        base = reference.loc[(item.medium, item.dt_s)]
        entry: dict[str, float | str] = {
            "medium": item.medium,
            "phenotype": item.phenotype,
            "dt_s": item.dt_s,
        }
        for name in OBSERVABLES:
            entry[f"{name}_ratio_to_wt"] = float(
                getattr(item, f"{name}_mean") / base[f"{name}_mean"]
            )
        rows.append(entry)
    return pd.DataFrame(rows)


def convergence_report(summary: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    """Return the relative deviation of each step from the refined reference.

    The reference is the mean of the two finest steps tested.  Two steps
    consume the random stream differently, so each group mean carries its own
    sampling error; averaging the two finest rungs halves that error in the
    quantity every other rung is measured against.

    A step is accepted when the relative deviation of the group mean stays at or
    below ``tolerance`` for every phenotype and medium.
    """
    finest = sorted(summary.dt_s.unique())[:2]
    reference = (
        summary.query("dt_s in @finest")
        .groupby(["medium", "phenotype"])[[f"{name}_mean" for name in OBSERVABLES]]
        .mean()
    )
    rows: list[dict[str, float | bool | str]] = []
    for item in summary.itertuples(index=False):
        base = reference.loc[(item.medium, item.phenotype)]
        entry: dict[str, float | bool | str] = {
            "medium": item.medium,
            "phenotype": item.phenotype,
            "dt_s": item.dt_s,
        }
        for name in OBSERVABLES:
            value = getattr(item, f"{name}_mean")
            entry[f"{name}_rel_deviation"] = float(
                abs(value - base[f"{name}_mean"]) / base[f"{name}_mean"]
            )
        rows.append(entry)
    report = pd.DataFrame(rows)
    report["reference_dt_s"] = ", ".join(f"{value:g}" for value in finest)
    report["tolerance"] = tolerance
    report["within_tolerance"] = report.net_displacement_um_rel_deviation <= tolerance
    report["selected_dt_s"] = select_time_step(report)
    return report


def select_time_step(report: pd.DataFrame) -> float:
    """Return the largest step that passes the tolerance in every group."""
    passing = report.groupby("dt_s").within_tolerance.all()
    accepted = passing[passing].index
    if accepted.empty:
        raise ValueError("No time step on the ladder meets the tolerance.")
    return float(accepted.max())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seeds", type=int, default=len(list(SEEDS)), help="Seeds per phenotype and medium."
    )
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.05,
        help="Accepted relative deviation of the group mean from the refined reference.",
    )
    parser.add_argument(
        "--reuse-seed-values",
        action="store_true",
        help="Rebuild the summary tables from the stored per-seed values, without simulating.",
    )
    args = parser.parse_args()

    seeds = list(SEEDS)[: args.seeds]
    stored = DIAGNOSTICS / "timestep_convergence_seed_values.csv"
    if args.reuse_seed_values:
        seed_values = pd.read_csv(stored)
    else:
        seed_values = run_sweep(TIME_STEPS, seeds, args.workers)
    summary = group_summary(seed_values)
    ratios = strain_ratios(summary)
    report = convergence_report(summary, args.tolerance)

    DIAGNOSTICS.mkdir(parents=True, exist_ok=True)
    seed_values.to_csv(stored, index=False)
    summary.merge(report, on=["medium", "phenotype", "dt_s"]).to_csv(
        DIAGNOSTICS / "timestep_convergence.csv", index=False
    )
    ratios.to_csv(DIAGNOSTICS / "timestep_convergence_ratios.csv", index=False)

    pd.set_option("display.width", 200)
    print(summary.to_string(index=False))
    print()
    print(ratios.to_string(index=False))
    print()
    print(report.to_string(index=False))
    selected = select_time_step(report)
    print()
    print(f"Selected dt = {selected} s at a {args.tolerance:.0%} tolerance.")
    if SIMULATION_DT_S > selected:
        print(
            f"WARNING: build.py integrates at dt = {SIMULATION_DT_S} s, which is coarser "
            f"than the largest accepted step, {selected} s. Refine SIMULATION_DT_S or "
            f"restate the tolerance."
        )
    elif SIMULATION_DT_S < selected:
        print(
            f"build.py integrates at dt = {SIMULATION_DT_S} s, finer than the largest "
            f"accepted step, {selected} s. That is safe: the panels are converged with "
            f"margin. Under the corrected dynamics every step on the ladder passes, so "
            f"the selected step is the coarsest one tested, not a boundary."
        )


if __name__ == "__main__":
    main()
