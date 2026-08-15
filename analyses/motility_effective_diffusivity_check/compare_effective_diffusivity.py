#!/usr/bin/env python3
"""Compare the simulated effective diffusivity with the measured one.

The question
------------
Before the dynamics corrections the model reproduced 56 % to 58 % of the measured
``D_eff`` in liquid and only 35 % to 37 % in agarose.  The diagnosis was a
duty-cycle error: the
parameters are fitted through the persistence relation

    tau = 1 / (D_theta + lambda * (1 - exp(-sigma^2 / 2)))

which has no duration term and so describes a walker that swims the whole time,
while the simulation parked the cell in a non-advancing ``reorient`` state for
``reorientation_duration_s``.  A cell swam only 60 % to 80 % of the time, and the
effective diffusivity of a run-and-tumble walker scales as the square of that
ballistic fraction.

This module measures what the correction bought, per strain and per medium.

What is compared, and against what
----------------------------------
Three reference quantities, because "the measured value" is not one number.

``measured``
    ``diff_med_*`` from the paired experimental units: a per-trajectory
    covariance estimator, averaged over units.  This is the number the
    shortfall statement was made against, so the headline ratio uses it.

``implied``
    ``v^2 tau / 2``, the diffusivity the calibration actually targets.  The
    measured ``tau`` is itself derived as ``2 D_eff / v^2`` per unit, so
    ``implied`` and ``measured`` would agree exactly if the unit means commuted
    with the products.  They do not, so ``implied`` is 85 % to 92 % of
    ``measured``.  That gap is a property of the measurement aggregation, not of
    the model, and it caps what any faithful simulation can return.

``lag-corrected simulated``
    The plain ``MSD / (4 t)`` estimator is biased low at a finite lag.  For a
    persistent random walk ``MSD(t) = 4 D [t - tau (1 - exp(-t / tau))]``, so the
    estimator returns ``D [1 - (tau/t)(1 - exp(-t/tau))]``.  At ``t = 2`` s and
    ``tau`` of 0.06 to 0.14 s that is a 3 % to 7 % underestimate.  Both the raw
    and the corrected simulated value are reported, so no comparison hides an
    estimator artefact.

Setup:
    PYTHONPATH=$PWD/src .venv/bin/python \
        analyses/motility_effective_diffusivity_check/compare_effective_diffusivity.py \
        --workers 8

Outputs go to ``build/diagnostics/effective_diffusivity_check``.  Nothing here is
a manuscript panel.

Complexity is O(models * strains * media * seeds * steps * cells).  Pitfall: the
two models consume the random stream differently, so seeds are not comparable one
by one; only group means are.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from datetime import UTC, datetime
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT = Path(__file__).resolve().parents[2]
UPSTREAM = PROJECT / "models/motility_simulation/upstream"
CORRECTED = PROJECT / "models/motility_simulation/corrected"
for path in (
    PROJECT / "analyses/motility_adopted_parameters",
    PROJECT / "analyses/motility_stall_parameter_comparison",
    PROJECT / "analyses/figure_05_revision",
    CORRECTED / "src",
    UPSTREAM / "src",
):
    sys.path.insert(0, str(path))

import salmonella_motility_corrected as smc  # noqa: E402
from common import MSD_LAG_S, measured_summary  # noqa: E402
from derive_adopted_parameters import (  # noqa: E402
    adopted_parameter_table_path,
    adopted_variant,
)

OUTPUT = PROJECT / "build/diagnostics/effective_diffusivity_check"
RECORD = Path(__file__).resolve().parent / "metadata/derivation.json"

PHENOTYPES = ("PproA", "WT", "PproB")
MEDIA = ("liquid", "agarose")
SEEDS = tuple(range(1000, 1100))
DT_S = 0.0025
N_CELLS = 26

#: "before" is the published configuration the 49 %-58 % statement came from:
#: upstream dynamics in the published 148 x 96 um box.  "after" is what the
#: corrected panels do: corrected dynamics in the enlarged quantitative box.
MODELS = {"before_upstream": 1, "after_corrected": 12}


def base_config(box_scale: int) -> dict:
    """Return the frozen upstream config at one box scale and the panel step."""
    config = yaml.safe_load((UPSTREAM / "data/config.yml").read_text(encoding="utf-8"))
    if int(config["simulation"]["n_cells"]) != N_CELLS:
        raise ValueError("The Figure 5 seed plan requires 26 cells per simulation.")
    config["simulation"]["dt_s"] = float(DT_S)
    return smc.scaled_config(config, box_scale)


def legacy_parameter_table_path() -> Path:
    """Write the adopted table with its retired column restored, and return it.

    The upstream dynamics require ``reorientation_duration_s``.  The adopted
    table no longer carries it, so the "before" arm rebuilds the pre-drop table
    from the same variant record rather than hardcoding a value.
    """
    from common import variant_table  # noqa: PLC0415

    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "legacy_parameters_with_reorientation_duration.csv"
    variant_table(adopted_variant()).to_csv(path, index=False)
    return path


def diffusivity_from_history(
    history: np.ndarray, motile: np.ndarray, dt_s: float
) -> float:
    """Estimate D_eff from the mean squared displacement over non-overlapping lags.

    Motile cells only, ``MSD / (4 * lag)``, exactly the estimator the stall
    comparison uses, so the number is comparable with the earlier record.
    """
    lag_steps = int(round(MSD_LAG_S / dt_s))
    n_steps = history.shape[0] - 1
    origins = np.arange(0, n_steps - lag_steps + 1, lag_steps)
    if not len(origins) or not motile.any():
        return float("nan")
    jumps = history[origins + lag_steps][:, motile, :] - history[origins][:, motile, :]
    return float((jumps**2).sum(axis=2).mean()) / (4.0 * MSD_LAG_S)


def _run_one(job: tuple[str, str, str, str, int, int]) -> dict[str, object]:
    """Run one seed under one model.  Top level so multiprocessing can pickle it."""
    model, table_path, phenotype, medium, seed, box_scale = job
    config = base_config(box_scale)

    if model == "after_corrected":
        parameters = smc.load_parameter_table(Path(table_path))
        params = parameters[(phenotype, medium)]
        obstacles = (
            smc.make_obstacle_field(config, seed=int(seed) + 300) if medium == "agarose" else None
        )
        result = smc.simulate_population(config, params, obstacles, int(seed))
    else:
        from salmonella_motility_simulation import simulation  # noqa: PLC0415
        from salmonella_motility_simulation.__main__ import (  # noqa: PLC0415
            load_parameter_table,
        )

        parameters = load_parameter_table(Path(table_path))
        params = parameters[(phenotype, medium)]
        obstacles = (
            simulation.make_obstacle_field(config, seed=int(seed) + 300)
            if medium == "agarose"
            else None
        )
        result = simulation.simulate_population(config, params, obstacles, int(seed))

    history = result["history"]
    motile = result["is_motile"]
    states = result["state_history"]
    reorient_state = int(config["states"]["reorient"])
    stalled_state = int(config["states"]["stalled"])
    motile_states = states[1:, motile]
    return {
        "model": model,
        "phenotype": phenotype,
        "medium": medium,
        "seed": int(seed),
        "box_scale": int(box_scale),
        "simulated_diffusivity_um2_s": diffusivity_from_history(history, motile, DT_S),
        # The duty cycle is the quantity the first correction removes.
        "reorient_occupancy": float((motile_states == reorient_state).mean()),
        "stall_occupancy": float((motile_states == stalled_state).mean()),
        "ballistic_fraction": float(
            ((motile_states != reorient_state) & (motile_states != stalled_state)).mean()
        ),
    }


def run_models(seeds: tuple[int, ...], workers: int) -> pd.DataFrame:
    """Return one row per model, phenotype, medium and seed."""
    adopted = str(adopted_parameter_table_path())
    legacy = str(legacy_parameter_table_path())
    jobs = [
        (
            model,
            adopted if model == "after_corrected" else legacy,
            phenotype,
            medium,
            seed,
            box_scale,
        )
        for model, box_scale in MODELS.items()
        for medium in MEDIA
        for phenotype in PHENOTYPES
        for seed in seeds
    ]
    if workers == 1:
        rows = [_run_one(job) for job in jobs]
    else:
        with Pool(workers) as pool:
            rows = pool.map(_run_one, jobs, chunksize=4)
    return pd.DataFrame(rows)


def model_tau(row: pd.Series) -> float:
    """Return the model persistence time of one parameter row."""
    turn_efficiency = 1.0 - math.exp(-(row.turn_angle_sd_rad**2) / 2.0)
    return 1.0 / (row.rotational_diffusion_rad2_s + row.reorientation_rate_s * turn_efficiency)


def compare(runs: pd.DataFrame) -> pd.DataFrame:
    """Return the simulated and measured diffusivities side by side, with ratios."""
    parameters = pd.read_csv(adopted_parameter_table_path())
    parameters["tau_s"] = parameters.apply(model_tau, axis=1)
    parameters["implied_from_model_um2_s"] = (
        parameters.run_speed_um_s**2 * parameters.tau_s / 2.0
    )
    measured = measured_summary()

    grouped = runs.groupby(["model", "phenotype", "medium"], as_index=False).agg(
        n_seeds=("seed", "size"),
        simulated_diffusivity_um2_s=("simulated_diffusivity_um2_s", "mean"),
        simulated_sd=("simulated_diffusivity_um2_s", "std"),
        reorient_occupancy=("reorient_occupancy", "mean"),
        stall_occupancy=("stall_occupancy", "mean"),
        ballistic_fraction=("ballistic_fraction", "mean"),
    )
    grouped["simulated_se"] = grouped.simulated_sd / np.sqrt(grouped.n_seeds)

    table = grouped.merge(
        measured[
            [
                "phenotype",
                "medium",
                "measured_diffusivity_um2_s",
                "implied_diffusivity_um2_s",
                "measured_tau_s",
            ]
        ],
        on=["phenotype", "medium"],
        how="left",
        validate="m:1",
    ).merge(
        parameters[["phenotype", "medium", "tau_s", "implied_from_model_um2_s"]],
        on=["phenotype", "medium"],
        how="left",
        validate="m:1",
    )

    # Divide out the finite-lag bias of the MSD estimator.
    bias = 1.0 - (table.tau_s / MSD_LAG_S) * (1.0 - np.exp(-MSD_LAG_S / table.tau_s))
    table["msd_lag_bias_factor"] = bias
    table["simulated_lag_corrected_um2_s"] = table.simulated_diffusivity_um2_s / bias

    table["ratio_to_measured"] = (
        table.simulated_diffusivity_um2_s / table.measured_diffusivity_um2_s
    )
    table["ratio_to_measured_lag_corrected"] = (
        table.simulated_lag_corrected_um2_s / table.measured_diffusivity_um2_s
    )
    table["ratio_to_implied"] = table.simulated_diffusivity_um2_s / table.implied_diffusivity_um2_s
    table["ratio_to_implied_lag_corrected"] = (
        table.simulated_lag_corrected_um2_s / table.implied_diffusivity_um2_s
    )
    order = {name: rank for rank, name in enumerate(PHENOTYPES)}
    return table.sort_values(
        ["model", "medium", "phenotype"], key=lambda s: s.map(order).fillna(s)
    ).reset_index(drop=True)


def _artifact(path: Path) -> dict[str, object]:
    item: dict[str, object] = {
        "relative_path": path.relative_to(PROJECT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }
    if path.suffix == ".csv":
        item["rows"] = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
    return item


def write_record(table: pd.DataFrame, outputs: list[Path]) -> None:
    """Write the machine-readable derivation record."""

    def span(model: str, column: str) -> list[float]:
        part = table.query("model == @model")[column]
        return [float(part.min()), float(part.max())]

    record = {
        "schema_version": "1.0.0",
        "record_type": "model_diagnostic",
        "record_id": "motility_effective_diffusivity_check",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "analyses/motility_effective_diffusivity_check/compare_effective_diffusivity.py",
        ],
        "inputs": [
            _artifact(Path(__file__).resolve()),
            _artifact(adopted_parameter_table_path()),
            _artifact(UPSTREAM / "data/config.yml"),
            _artifact(UPSTREAM / "src/salmonella_motility_simulation/simulation.py"),
            _artifact(CORRECTED / "src/salmonella_motility_corrected/simulation.py"),
        ],
        "outputs": [_artifact(path) for path in outputs],
        "software": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "parameters": {
            "models": MODELS,
            "seeds": [int(min(SEEDS)), int(max(SEEDS))],
            "n_seeds": len(SEEDS),
            "n_cells": N_CELLS,
            "dt_s": DT_S,
            "msd_lag_s": MSD_LAG_S,
            "estimator": "MSD over non-overlapping lags / (4 * lag), motile cells only",
            "ratio_to_measured_before": span("before_upstream", "ratio_to_measured"),
            "ratio_to_measured_after": span("after_corrected", "ratio_to_measured"),
            "ratio_to_measured_after_lag_corrected": span(
                "after_corrected", "ratio_to_measured_lag_corrected"
            ),
            "ratio_to_implied_after_lag_corrected": span(
                "after_corrected", "ratio_to_implied_lag_corrected"
            ),
            "ballistic_fraction_before": span("before_upstream", "ballistic_fraction"),
            "ballistic_fraction_after": span("after_corrected", "ballistic_fraction"),
        },
        "random_seeds": {
            "population": f"{min(SEEDS)}-{max(SEEDS)}",
            "starting_positions": "population seed + 1",
            "agarose_obstacles": "population seed + 300",
        },
        "findings": [
            (
                "Removing the non-advancing reorientation dwell raises the ballistic "
                "fraction to 1 in liquid and raises the simulated effective diffusivity "
                "accordingly. The per-strain and per-medium ratios are in "
                "effective_diffusivity_comparison.csv."
            ),
            (
                "The measured tau is itself derived as 2 D_eff / v^2 per unit, so the "
                "diffusivity the calibration targets, v^2 tau / 2, is only 85 % to 92 % of "
                "the mean measured D_eff. That gap is an artefact of averaging units and "
                "caps what any faithful simulation can return."
            ),
        ],
        "limitations": [
            (
                "The measured D_eff comes from a per-trajectory covariance estimator on "
                "experimental tracks; the simulated value comes from a mean squared "
                "displacement at a 2 s lag. The two estimators are not identical, so a "
                "ratio of exactly 1 was never the right target."
            ),
            (
                "The agarose comparison double-counts the mesh. The measured agarose tau "
                "already contains it, and the simulation adds obstacles and stalls on top, "
                "so the agarose ratio is expected to stay below the liquid one."
            ),
            (
                "The two models consume the random stream differently, so seeds are not "
                "comparable one by one; only group means are."
            ),
            "Nothing here is a manuscript panel. No figure, config, theme or palette changes.",
        ],
    }
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--seeds", type=int, default=len(SEEDS))
    parser.add_argument("--reuse-runs", action="store_true")
    args = parser.parse_args()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    runs_path = OUTPUT / "effective_diffusivity_runs.csv"
    if args.reuse_runs:
        runs = pd.read_csv(runs_path)
    else:
        runs = run_models(SEEDS[: args.seeds], args.workers)
        runs.to_csv(runs_path, index=False)

    table = compare(runs)
    table_path = OUTPUT / "effective_diffusivity_comparison.csv"
    table.to_csv(table_path, index=False)
    write_record(table, [runs_path, table_path])

    columns = [
        "model",
        "medium",
        "phenotype",
        "ballistic_fraction",
        "simulated_diffusivity_um2_s",
        "simulated_lag_corrected_um2_s",
        "measured_diffusivity_um2_s",
        "implied_diffusivity_um2_s",
        "ratio_to_measured",
        "ratio_to_measured_lag_corrected",
        "ratio_to_implied_lag_corrected",
    ]
    with pd.option_context("display.width", 260, "display.precision", 3):
        print(table[columns].to_string(index=False))


if __name__ == "__main__":
    main()
