#!/usr/bin/env python3
"""Measure how much the bounded simulation domain compresses the strain ratios.

The question
------------
Figure 5D and 5E once simulated cells inside a 148 x 96 um box with reflecting
walls.  A wall turns a cell back, so it shortens a long track more than a short
one and compresses the strain ratios the panels report.  The methods carried a
number for that compression, "about 12 %", which no script reproduced and which
was measured under a retired model.  This module measures it under the corrected
dynamics and writes the evidence out.

The design
----------
One ladder of box sizes.  At scale ``k`` the box is ``148k x 96k`` um and the
obstacle count scales with the box **area**, ``58 k^2``, so the mesh keeps the
number density, the disk-size distribution and the area fraction of the
published field.  Every other input is unchanged: the same 100 seeds, the same
26 cells, the same 20 s, the same time step and the same parameter table.  Scale
1 is the published box; a larger box moves the walls away, so the ratio measured
at large ``k`` is the ratio of an effectively unbounded medium.

The realised obstacle area fraction is reported at every scale.  That is the
check that the area scaling worked.  If it drifted upward with the box, the mesh
would have been diluted and every agarose number would be inflated.

How the ladder proves it is long enough
---------------------------------------
Every run reports the fraction of cells that ever reach a wall.  The ladder
reports the ratio at every scale and the compression against the largest box, so
the reader sees the plateau instead of trusting an extrapolation.

Setup:
    PYTHONPATH=$PWD/src .venv/bin/python \
        analyses/motility_domain_boundary_check/measure_box_compression.py --workers 8

Outputs, all under ``build/diagnostics/domain_boundary_check``.  Nothing here is
a manuscript panel.

Complexity is O(scales * strains * seeds * steps * cells); the grid obstacle
index holds the per-step cost constant in the box size, so a large box costs no
more per step than the published one.  Pitfall: two box sizes consume the random
stream differently once obstacles are present, so seeds are paired for the
bootstrap but single seeds are not comparable one by one.
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
import yaml

PROJECT = Path(__file__).resolve().parents[2]
UPSTREAM = PROJECT / "models/motility_simulation/upstream"
CORRECTED = PROJECT / "models/motility_simulation/corrected"
sys.path.insert(0, str(PROJECT / "analyses/motility_adopted_parameters"))
sys.path.insert(0, str(CORRECTED / "src"))

import salmonella_motility_corrected as smc  # noqa: E402
from derive_adopted_parameters import adopted_parameter_table_path  # noqa: E402

OUTPUT = PROJECT / "build/diagnostics/domain_boundary_check"
RECORD = Path(__file__).resolve().parent / "metadata/derivation.json"

#: The manuscript seed plan of Figure 5D and 5E.
PHENOTYPES = ("PproA", "WT", "PproB")
MEDIA = ("liquid", "agarose")
SEEDS = tuple(range(1000, 1100))
DT_S = 0.0025
N_CELLS = 26

#: Linear enlargement factors of the box.  1 is the published domain.
BOX_SCALES: tuple[int, ...] = (1, 2, 4, 8, 12)

#: Reference strain of the reported ratios.
REFERENCE_PHENOTYPE = "PproA"

BOOTSTRAP_SEED = 20260814
BOOTSTRAP_DRAWS = 10_000


def base_config() -> dict:
    """Return the frozen upstream config with the manuscript time step applied."""
    config = yaml.safe_load((UPSTREAM / "data/config.yml").read_text(encoding="utf-8"))
    if int(config["simulation"]["n_cells"]) != N_CELLS:
        raise ValueError("The Figure 5 seed plan requires 26 cells per simulation.")
    config["simulation"]["dt_s"] = float(DT_S)
    return config


def _run_one(job: tuple[str, str, str, int, int]) -> dict[str, object]:
    """Run one seed at one box scale.  Top level so multiprocessing can pickle it."""
    table_path, phenotype, medium, seed, scale = job
    parameters = smc.load_parameter_table(Path(table_path))
    config = smc.scaled_config(base_config(), scale)

    obstacles = None
    obstacle_seed = None
    if medium == "agarose":
        obstacle_seed = int(seed) + 300
        obstacles = smc.make_obstacle_field(config, seed=obstacle_seed)

    result = smc.simulate_population(
        config, parameters[(phenotype, medium)], obstacles, int(seed)
    )
    history = result["history"]
    motile = result["is_motile"]
    displacement = np.linalg.norm(history[-1] - history[0], axis=1)

    # A cell counts as wall-touched when it ever reaches within one run step of a
    # wall.  It is the diagnostic of how far the ladder moved the wall away.
    width = float(config["simulation"]["box_width_um"])
    height = float(config["simulation"]["box_height_um"])
    margin = float(parameters[(phenotype, medium)].run_speed_um_s) * DT_S
    touched = (
        (history[..., 0] <= margin)
        | (history[..., 0] >= width - margin)
        | (history[..., 1] <= margin)
        | (history[..., 1] >= height - margin)
    ).any(axis=0)

    return {
        "phenotype": phenotype,
        "medium": medium,
        "box_scale": int(scale),
        "seed": int(seed),
        "obstacle_seed": obstacle_seed,
        "n_obstacles": 0 if obstacles is None else int(obstacles.n_obstacles),
        "obstacle_area_fraction": float(result["obstacle_area_fraction"]),
        "box_width_um": width,
        "box_height_um": height,
        "n_cells": int(history.shape[1]),
        "mean_net_displacement_um": float(displacement.mean()),
        "motile_mean_net_displacement_um": float(displacement[motile].mean())
        if motile.any()
        else float("nan"),
        "wall_touched_fraction": float(touched.mean()),
    }


def run_ladder(scales: tuple[int, ...], seeds: tuple[int, ...], workers: int) -> pd.DataFrame:
    """Return one row per phenotype, medium, box scale and seed."""
    table_path = str(adopted_parameter_table_path())
    jobs = [
        (table_path, phenotype, medium, seed, scale)
        for medium in MEDIA
        for scale in scales
        for phenotype in PHENOTYPES
        for seed in seeds
    ]
    if workers == 1:
        rows = [_run_one(job) for job in jobs]
    else:
        with Pool(workers) as pool:
            rows = pool.map(_run_one, jobs, chunksize=4)
    return pd.DataFrame(rows)


def group_summary(runs: pd.DataFrame) -> pd.DataFrame:
    """Return the group mean net displacement with its standard error."""
    grouped = runs.groupby(["medium", "box_scale", "phenotype"], as_index=False).agg(
        n_seeds=("seed", "size"),
        n_obstacles=("n_obstacles", "first"),
        obstacle_area_fraction=("obstacle_area_fraction", "mean"),
        box_width_um=("box_width_um", "first"),
        box_height_um=("box_height_um", "first"),
        mean_net_displacement_um=("mean_net_displacement_um", "mean"),
        sd_net_displacement_um=("mean_net_displacement_um", "std"),
        wall_touched_fraction=("wall_touched_fraction", "mean"),
    )
    grouped["se_net_displacement_um"] = grouped.sd_net_displacement_um / np.sqrt(grouped.n_seeds)
    return grouped.sort_values(["medium", "box_scale", "phenotype"]).reset_index(drop=True)


def _seed_matrix(runs: pd.DataFrame, medium: str, scale: int) -> tuple[dict[str, np.ndarray], int]:
    part = runs.query("medium == @medium and box_scale == @scale")
    seeds = sorted(part.seed.unique())
    vectors: dict[str, np.ndarray] = {}
    for phenotype in PHENOTYPES:
        aligned = part.query("phenotype == @phenotype").set_index("seed").reindex(seeds)
        if aligned.mean_net_displacement_um.isna().any():
            raise ValueError(f"{medium}/{phenotype}/scale {scale} is missing a seed.")
        vectors[phenotype] = aligned.mean_net_displacement_um.to_numpy(dtype=float)
    return vectors, len(seeds)


def ratio_table(runs: pd.DataFrame) -> pd.DataFrame:
    """Return each strain ratio at each box scale with a paired bootstrap interval."""
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    rows: list[dict[str, object]] = []
    for medium in MEDIA:
        for scale in sorted(runs.query("medium == @medium").box_scale.unique()):
            vectors, n_seeds = _seed_matrix(runs, medium, int(scale))
            draws = rng.integers(0, n_seeds, size=(BOOTSTRAP_DRAWS, n_seeds))
            reference = vectors[REFERENCE_PHENOTYPE]
            reference_draws = reference[draws].mean(axis=1)
            for phenotype in PHENOTYPES:
                if phenotype == REFERENCE_PHENOTYPE:
                    continue
                ratio = float(vectors[phenotype].mean() / reference.mean())
                resampled = vectors[phenotype][draws].mean(axis=1) / reference_draws
                rows.append(
                    {
                        "medium": medium,
                        "box_scale": int(scale),
                        "ratio": f"{phenotype}/{REFERENCE_PHENOTYPE}",
                        "value": ratio,
                        "ci_low": float(np.quantile(resampled, 0.025)),
                        "ci_high": float(np.quantile(resampled, 0.975)),
                    }
                )
    return pd.DataFrame(rows)


def compression_table(runs: pd.DataFrame, ratios: pd.DataFrame, summary: pd.DataFrame):
    """Return the compression of the published box against the unbounded limit.

    ``compression`` is ``1 - published / unbounded``, where ``unbounded`` is the
    ratio in the largest box on the ladder.  A positive value means the published
    box makes the ratio smaller than it would be without walls.  The interval
    comes from a paired bootstrap: one resample of the seed index is applied to
    both box sizes and both strains at once.

    ``plateau_shift`` is the relative change between the two largest boxes.  It
    is the evidence that the largest box is effectively unbounded.
    """
    rng = np.random.default_rng(BOOTSTRAP_SEED + 1)
    rows: list[dict[str, object]] = []
    for medium in MEDIA:
        scales = sorted(runs.query("medium == @medium").box_scale.unique())
        largest, second = int(scales[-1]), int(scales[-2])
        published_vectors, n_seeds = _seed_matrix(runs, medium, 1)
        unbounded_vectors, _ = _seed_matrix(runs, medium, largest)
        draws = rng.integers(0, n_seeds, size=(BOOTSTRAP_DRAWS, n_seeds))
        wall = float(
            summary.query("medium == @medium and box_scale == @largest").wall_touched_fraction.max()
        )
        for phenotype in PHENOTYPES:
            if phenotype == REFERENCE_PHENOTYPE:
                continue
            name = f"{phenotype}/{REFERENCE_PHENOTYPE}"
            published = float(
                published_vectors[phenotype].mean() / published_vectors[REFERENCE_PHENOTYPE].mean()
            )
            unbounded = float(
                unbounded_vectors[phenotype].mean()
                / unbounded_vectors[REFERENCE_PHENOTYPE].mean()
            )
            second_value = float(
                ratios.query(
                    "medium == @medium and box_scale == @second and ratio == @name"
                ).value.iloc[0]
            )
            published_draws = published_vectors[phenotype][draws].mean(axis=1) / published_vectors[
                REFERENCE_PHENOTYPE
            ][draws].mean(axis=1)
            unbounded_draws = unbounded_vectors[phenotype][draws].mean(axis=1) / unbounded_vectors[
                REFERENCE_PHENOTYPE
            ][draws].mean(axis=1)
            resampled = 1.0 - published_draws / unbounded_draws
            rows.append(
                {
                    "medium": medium,
                    "ratio": name,
                    "published_box_value": published,
                    "largest_box_scale": largest,
                    "largest_box_value": unbounded,
                    "second_largest_box_scale": second,
                    "second_largest_box_value": second_value,
                    "plateau_shift": float(1.0 - second_value / unbounded),
                    "wall_touched_fraction_largest_box": wall,
                    "compression": float(1.0 - published / unbounded),
                    "compression_ci_low": float(np.quantile(resampled, 0.025)),
                    "compression_ci_high": float(np.quantile(resampled, 0.975)),
                }
            )
    return pd.DataFrame(rows).sort_values(["medium", "ratio"]).reset_index(drop=True)


def _artifact(path: Path) -> dict[str, object]:
    item: dict[str, object] = {
        "relative_path": path.relative_to(PROJECT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }
    if path.suffix == ".csv":
        item["rows"] = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
    return item


def write_record(compression: pd.DataFrame, summary: pd.DataFrame, outputs: list[Path]) -> None:
    """Write the machine-readable derivation record."""
    headline = compression.query("ratio == 'PproB/PproA'").set_index("medium")
    area = summary.query("medium == 'agarose'").groupby("box_scale").obstacle_area_fraction.mean()
    record = {
        "schema_version": "1.0.0",
        "record_type": "model_diagnostic",
        "record_id": "motility_domain_boundary_check",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "analyses/motility_domain_boundary_check/measure_box_compression.py",
        ],
        "inputs": [
            _artifact(Path(__file__).resolve()),
            _artifact(adopted_parameter_table_path()),
            _artifact(UPSTREAM / "data/config.yml"),
            _artifact(CORRECTED / "src/salmonella_motility_corrected/simulation.py"),
            _artifact(CORRECTED / "src/salmonella_motility_corrected/obstacles.py"),
        ],
        "outputs": [_artifact(path) for path in outputs],
        "software": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "parameters": {
            "box_scales": list(BOX_SCALES),
            "published_box_um": [148.0, 96.0],
            "obstacle_count_rule": "58 * box_scale^2, scaled with box area",
            "obstacle_area_fraction_by_scale": {
                str(scale): float(value) for scale, value in area.items()
            },
            "seeds": [int(min(SEEDS)), int(max(SEEDS))],
            "n_seeds": len(SEEDS),
            "n_cells": N_CELLS,
            "dt_s": DT_S,
            "observable": "mean net displacement per seed (um)",
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "compression_pproB_over_pproA": {
                medium: {
                    "compression": float(headline.loc[medium, "compression"]),
                    "ci": [
                        float(headline.loc[medium, "compression_ci_low"]),
                        float(headline.loc[medium, "compression_ci_high"]),
                    ],
                    "plateau_shift": float(headline.loc[medium, "plateau_shift"]),
                }
                for medium in headline.index
            },
            "wall_touched_fraction_by_scale": {
                f"{row.medium}_scale_{row.box_scale}_{row.phenotype}": row.wall_touched_fraction
                for row in summary.itertuples(index=False)
            },
        },
        "random_seeds": {
            "population": f"{min(SEEDS)}-{max(SEEDS)}",
            "starting_positions": "population seed + 1",
            "agarose_obstacles": "population seed + 300",
            "bootstrap": BOOTSTRAP_SEED,
        },
        "findings": [
            (
                "The reflecting 148 x 96 um domain lowers the strain ratios of net "
                "displacement. The measured compression is reported per medium and per "
                "ratio in domain_box_compression.csv."
            ),
            (
                "The obstacle count scales with box area, so the realised area fraction is "
                "the published one at every box scale. The ladder therefore isolates the "
                "wall rather than mixing it with a change of mesh density."
            ),
        ],
        "limitations": [
            (
                "Cells start uniformly in the box, so a wall-adjacent band stays at risk of a "
                "wall contact. The reported wall-touched fraction in the largest box states "
                "how much of that risk is left, and the plateau shift between the two largest "
                "boxes states what it costs the ratio."
            ),
            (
                "Two box sizes consume the random stream differently once obstacles are "
                "present, so seeds are paired for the bootstrap but single seeds are not "
                "comparable one by one."
            ),
            (
                "The intervals quantify stochastic seed variation, not biological sampling "
                "uncertainty."
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
    parser.add_argument(
        "--reuse-runs",
        action="store_true",
        help="Rebuild the summaries from the stored per-seed rows, without simulating.",
    )
    args = parser.parse_args()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    runs_path = OUTPUT / "domain_box_runs.csv"
    if args.reuse_runs:
        runs = pd.read_csv(runs_path)
    else:
        runs = run_ladder(BOX_SCALES, SEEDS[: args.seeds], args.workers)
        runs.to_csv(runs_path, index=False)

    summary = group_summary(runs)
    ratios = ratio_table(runs)
    compression = compression_table(runs, ratios, summary)

    summary_path = OUTPUT / "domain_box_group_means.csv"
    ratios_path = OUTPUT / "domain_box_strain_ratios.csv"
    compression_path = OUTPUT / "domain_box_compression.csv"
    summary.to_csv(summary_path, index=False)
    ratios.to_csv(ratios_path, index=False)
    compression.to_csv(compression_path, index=False)
    write_record(compression, summary, [runs_path, summary_path, ratios_path, compression_path])

    with pd.option_context("display.width", 240, "display.precision", 4):
        print(summary.to_string(index=False))
        print()
        print(ratios.to_string(index=False))
        print()
        print(compression.to_string(index=False))


if __name__ == "__main__":
    main()
