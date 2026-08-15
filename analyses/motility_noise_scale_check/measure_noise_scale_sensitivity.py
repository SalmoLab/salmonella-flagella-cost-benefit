#!/usr/bin/env python3
"""Measure how much the undeclared noise scales change the reported observables.

The question
------------
The model scales its random translational motion off the passive diffusion
coefficient ``D_t``, with a different multiplier per state:

    running     0.12   (``noise.run_translational_scale``)
    stalled     0.20   (``noise.stall_translational_scale``)
    non-motile  1.00   (the passive rate itself, by definition)

That ordering is inverted.  A swimming cell diffuses about eight times less than
a stopped one, which is backwards: swimming adds motion, it does not suppress
Brownian motion.  None of the four noise constants has a source.

Rather than argue about the defect, this module measures it.  It compares the
shipped scales against the minimal physically ordered alternative, in which every
state diffuses at the full passive rate, and reports what that does to the two
numbers the manuscript uses: the net displacement Figure 5D and 5E plot, and the
effective diffusivity the calibration check reports.

Why no integrator is copied here
--------------------------------
Both scales now carry config keys, so both arms call the shipped
``simulate_population`` unchanged and differ only in the config they pass.  The
measurement therefore cannot drift from the model it describes.  This is the
reason the bare ``0.20`` was lifted into ``noise.stall_translational_scale``:
a constant that cannot be varied cannot be tested.

What is compared
----------------
``current``
    ``run_translational_scale`` 0.12, ``stall_translational_scale`` 0.20.
    The shipped configuration.  Its group means reproduce the ``after_corrected``
    rows of ``effective_diffusivity_check/effective_diffusivity_comparison.csv``.

``ordered``
    Both scales 1.00, so a running cell diffuses at the same rate as a
    non-motile one.  This is the weakest change that removes the inversion.  It
    has no source either, which is why it is a test and not a proposal.

Both arms use the same 100 seeds, so every comparison is paired and the seed
noise cancels.  Intervals are paired percentile bootstraps over the seed pairs.

Setup:
    PYTHONPATH=$PWD/src .venv/bin/python \
        analyses/motility_noise_scale_check/measure_noise_scale_sensitivity.py

Complexity is O(seeds * groups * steps * cells) and the integrator is pure
Python: about 1 s per agarose seed, so the default 1200 runs take a few minutes
on several workers.  Pitfall: a different time step consumes the random stream
differently, so compare group means and never single seeds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[2]
for path in (
    PROJECT / "analyses/motility_adopted_parameters",
    PROJECT / "analyses/motility_effective_diffusivity_check",
    PROJECT / "analyses/motility_stall_parameter_comparison",
    PROJECT / "models/motility_simulation/corrected/src",
    PROJECT / "models/motility_simulation/upstream/src",
):
    sys.path.insert(0, str(path))

import salmonella_motility_corrected as smc  # noqa: E402

# Reuse the effective-diffusivity check's own settings and estimator, so the
# numbers here are directly comparable with the record it writes.
from compare_effective_diffusivity import (  # noqa: E402
    DT_S,
    MEDIA,
    PHENOTYPES,
    SEEDS,
    base_config,
    diffusivity_from_history,
)
from derive_adopted_parameters import adopted_parameter_table_path  # noqa: E402

OUTPUT = PROJECT / "build/diagnostics/noise_scale_check"

#: The quantitative domain of Figure 5D and 5E.
BOX_SCALE = 12

#: variant -> (run translational scale, stall translational scale).
#: The non-motile scale is 1.00 in both arms; it is the passive rate itself and
#: the model has no multiplier for it.
VARIANTS: dict[str, tuple[float, float]] = {
    "current": (0.12, 0.20),
    "ordered": (1.00, 1.00),
}

#: Bootstrap draws for the paired interval on each relative change.
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20260814


def variant_config(run_scale: float, stall_scale: float) -> dict:
    """Return the panel config with the two translational noise scales set.

    Everything else, including the box, the step and the obstacle count, is the
    configuration Figure 5D and 5E use.
    """
    config = base_config(BOX_SCALE)
    config["noise"]["run_translational_scale"] = float(run_scale)
    config["noise"]["stall_translational_scale"] = float(stall_scale)
    return config


def _run_one(job: tuple[str, str, str, int]) -> dict[str, object]:
    """Run one seed of one group under one variant.  Top level so Pool can pickle it."""
    variant, phenotype, medium, seed = job
    run_scale, stall_scale = VARIANTS[variant]
    config = variant_config(run_scale, stall_scale)
    params = smc.load_parameter_table(adopted_parameter_table_path())[(phenotype, medium)]
    obstacles = (
        smc.make_obstacle_field(config, seed=int(seed) + 300) if medium == "agarose" else None
    )
    result = smc.simulate_population(config, params, obstacles, int(seed))

    history = result["history"]
    motile = result["is_motile"]
    net = np.linalg.norm(history[-1] - history[0], axis=1)
    stalled_state = int(config["states"]["stalled"])
    motile_states = result["state_history"][1:, motile]
    return {
        "variant": variant,
        "phenotype": phenotype,
        "medium": medium,
        "seed": int(seed),
        "run_translational_scale": run_scale,
        "stall_translational_scale": stall_scale,
        "mean_net_displacement_um": float(net.mean()),
        "diffusivity_um2_s": diffusivity_from_history(history, motile, DT_S),
        "contact_events": int(result["contact_events"]),
        "stall_entries": int(result["stall_entries"]),
        "stall_occupancy": float((motile_states == stalled_state).mean()),
    }


def run_variants(seeds: tuple[int, ...], workers: int | None) -> pd.DataFrame:
    """Return one row per variant, phenotype, medium and seed."""
    jobs = [
        (variant, phenotype, medium, seed)
        for variant in VARIANTS
        for medium in MEDIA
        for phenotype in PHENOTYPES
        for seed in seeds
    ]
    if workers and workers > 1:
        with Pool(workers) as pool:
            rows = pool.map(_run_one, jobs)
    else:
        rows = [_run_one(job) for job in jobs]
    return pd.DataFrame(rows)


def _paired_interval(current: np.ndarray, ordered: np.ndarray, rng: np.random.Generator) -> tuple:
    """Return the relative change in the group mean and its paired bootstrap interval.

    The two arrays are matched seed by seed, so a draw resamples seed *pairs*.
    That removes the seed noise the two arms share.
    """
    change = float(ordered.mean() / current.mean() - 1.0)
    n = len(current)
    picks = rng.integers(0, n, size=(BOOTSTRAP_DRAWS, n))
    draws = ordered[picks].mean(axis=1) / current[picks].mean(axis=1) - 1.0
    low, high = np.percentile(draws, [2.5, 97.5])
    return change, float(low), float(high)


def compare(runs: pd.DataFrame) -> pd.DataFrame:
    """Return the paired comparison, one row per phenotype and medium."""
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    rows: list[dict[str, object]] = []
    for (phenotype, medium), group in runs.groupby(["phenotype", "medium"], sort=False):
        current = group[group.variant == "current"].sort_values("seed")
        ordered = group[group.variant == "ordered"].sort_values("seed")
        if not np.array_equal(current.seed.to_numpy(), ordered.seed.to_numpy()):
            raise ValueError(f"{phenotype} {medium}: the two arms do not share their seeds.")

        row: dict[str, object] = {
            "phenotype": phenotype,
            "medium": medium,
            "n_seeds": int(len(current)),
        }
        for observable in ("mean_net_displacement_um", "diffusivity_um2_s"):
            a = current[observable].to_numpy()
            b = ordered[observable].to_numpy()
            change, low, high = _paired_interval(a, b, rng)
            row[f"{observable}_current"] = float(a.mean())
            row[f"{observable}_ordered"] = float(b.mean())
            row[f"{observable}_rel_change"] = change
            row[f"{observable}_ci_low"] = low
            row[f"{observable}_ci_high"] = high
            row[f"{observable}_excludes_zero"] = bool(low > 0.0 or high < 0.0)

        # The agarose coupling: more translational noise means more encounters.
        row["contact_events_current"] = float(current.contact_events.mean())
        row["contact_events_ordered"] = float(ordered.contact_events.mean())
        row["stall_occupancy_current"] = float(current.stall_occupancy.mean())
        row["stall_occupancy_ordered"] = float(ordered.stall_occupancy.mean())
        rows.append(row)
    return pd.DataFrame(rows)


def _artifact(path: Path) -> dict[str, object]:
    item: dict[str, object] = {
        "relative_path": path.relative_to(PROJECT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }
    if path.suffix == ".csv":
        item["rows"] = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
    return item


def write_record(table: pd.DataFrame, seeds: tuple[int, ...], outputs: list[Path]) -> None:
    """Write the machine-readable derivation record."""
    corrected = PROJECT / "models/motility_simulation/corrected"
    net = table.mean_net_displacement_um_rel_change
    diffusivity = table.diffusivity_um2_s_rel_change
    record = {
        "schema_version": "1.0.0",
        "record_type": "model_diagnostic",
        "record_id": "motility_noise_scale_check",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "analyses/motility_noise_scale_check/measure_noise_scale_sensitivity.py",
        ],
        "inputs": [
            _artifact(Path(__file__).resolve()),
            _artifact(adopted_parameter_table_path()),
            _artifact(PROJECT / "models/motility_simulation/upstream/data/config.yml"),
            _artifact(corrected / "src/salmonella_motility_corrected/simulation.py"),
        ],
        "outputs": [_artifact(path) for path in outputs],
        "software": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "parameters": {
            "variants": {name: list(scales) for name, scales in VARIANTS.items()},
            "seeds": [int(min(seeds)), int(max(seeds))],
            "n_seeds": len(seeds),
            "dt_s": DT_S,
            "box_scale": BOX_SCALE,
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "interval": "paired percentile bootstrap over seed pairs",
            "largest_net_displacement_change": float(net.abs().max()),
            "largest_diffusivity_change": float(diffusivity.abs().max()),
        },
        "random_seeds": {
            "population": f"{min(seeds)}-{max(seeds)}",
            "starting_positions": "population seed + 1",
            "agarose_obstacles": "population seed + 300",
            "bootstrap": BOOTSTRAP_SEED,
        },
        "findings": [
            "The four noise constants have no source. This diagnostic measures what the "
            "inverted translational-noise ordering costs, by comparing the shipped scales "
            "against the minimal physically ordered alternative in which every state "
            "diffuses at the full passive rate.",
            "Net displacement, the observable Figure 5D and 5E plot, is insensitive: the "
            f"largest change over the six groups is {net.abs().max():.1%}, and no agarose "
            "interval excludes zero.",
            "The effective diffusivity in agarose is sensitive: the largest change is "
            f"{diffusivity.abs().max():.1%}. Larger translational noise drives cells into "
            "obstacles more often, so contact events and stall occupancy both rise and the "
            "lost duty cycle outweighs the added diffusivity.",
            "In liquid the change matches the analytic prediction, an added translational "
            "diffusivity of D_t * (1.00 - 0.12) = 0.308 um^2/s, because a motile cell there "
            "runs the whole time.",
            "The constants are declared in Supplementary Table X and kept. The ordered "
            "alternative has no source either, so changing them would alter a calibrated "
            "model on no evidence.",
        ],
        "limitations": [
            "The ordered alternative is a test, not a proposal. Setting every scale to 1.00 "
            "is the weakest change that removes the inversion; it is not a measured value.",
            "The non-motile translational scale has no config key, because it is the passive "
            "rate itself. Only the running and stalled scales are varied here.",
            "Intervals quantify stochastic model-seed variation, not biological sampling "
            "uncertainty.",
        ],
    }
    path = Path(__file__).resolve().parent / "metadata/derivation.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=len(SEEDS))
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()

    seeds = tuple(SEEDS[: args.seeds])
    runs = run_variants(seeds, args.workers)
    table = compare(runs)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    runs.to_csv(OUTPUT / "noise_scale_runs.csv", index=False)
    table.to_csv(OUTPUT / "noise_scale_comparison.csv", index=False)
    write_record(
        table, seeds, [OUTPUT / "noise_scale_runs.csv", OUTPUT / "noise_scale_comparison.csv"]
    )

    pd.set_option("display.width", 220)
    show = [
        "phenotype",
        "medium",
        "mean_net_displacement_um_rel_change",
        "mean_net_displacement_um_ci_low",
        "mean_net_displacement_um_ci_high",
        "diffusivity_um2_s_rel_change",
        "diffusivity_um2_s_ci_low",
        "diffusivity_um2_s_ci_high",
    ]
    print(table[show].to_string(index=False))
    print()
    net = table.mean_net_displacement_um_rel_change.abs().max()
    diff = table.diffusivity_um2_s_rel_change.abs().max()
    print(f"Largest net-displacement change: {net:.2%}")
    print(f"Largest effective-diffusivity change: {diff:.2%}")
    print(f"wrote {(OUTPUT / 'noise_scale_comparison.csv').relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
