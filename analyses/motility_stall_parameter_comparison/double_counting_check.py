#!/usr/bin/env python3
"""Test whether the agarose model represents the mesh more than once.

The measured persistence time comes from cells tracked **in agarose**, so it
already carries the hindering effect of the mesh.  It is also not an independent
measurement: ``analyses/figure_07_revision/build_figure_07_revision.py`` derives
it as ``tau = 2 * D_eff / v^2`` from the measured agarose diffusivity and the
measured agarose speed.  A free run-and-tumble walker carrying the measured
speed and the measured ``tau`` therefore reproduces the measured agarose
diffusivity by construction.

The simulation then imposes that measured ``tau`` **and** adds 58 explicit
obstacles **and** adds stalling.  This script measures how much each addition
takes away, by running the same seeds through a ladder of conditions:

    liquid              measured liquid parameters, no obstacles, no stalls
    agarose_free        measured agarose parameters, no obstacles, no stalls
    agarose_obstacles   plus the 58 obstacles, still no stalls
    agarose_full        plus stalling - the current model

A pure Brownian reference walker carrying the measured diffusivity through the
same box gives the displacement the measurement alone implies.

Setup:
    PYTHONPATH=$PWD/src MPLBACKEND=Agg .venv/bin/python \\
        analyses/motility_stall_parameter_comparison/double_counting_check.py

Runtime is about 5 min on seven cores.  Results are cached per condition and
keyed by the parameter-table checksum.  Pass ``--force`` to rerun.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
from common import (  # noqa: E402
    BOOTSTRAP_DRAWS,
    DT_S,
    MSD_LAG_S,
    OUTPUT,
    PHENOTYPES,
    PROJECT,
    SEEDS,
    TABLES,
    bootstrap_draws,
    cached_condition,
    seed_vectors,
    variant_table,
    variant_table_path,
    variants,
)

RECORD = Path(__file__).resolve().parent / "metadata/double_counting.json"

#: Seed for the Brownian reference walker.
REFERENCE_SEED = 20260814

LADDER = (
    ("liquid", "liquid", False, "Measured liquid parameters, no obstacles, no stalls"),
    ("agarose_free", "agarose", False, "Measured agarose tau only, no obstacles, no stalls"),
    ("agarose_obstacles", "agarose", True, "Agarose tau plus 58 obstacles, no stalls"),
    ("agarose_full", "agarose", True, "Agarose tau plus obstacles plus stalls (current model)"),
)


def no_stall_table_path() -> Path:
    """Write a copy of the adopted table with every stall probability at zero."""
    TABLES.mkdir(parents=True, exist_ok=True)
    table = variant_table(variants()[0]).copy()
    table["stall_probability"] = 0.0
    path = TABLES / "no_stall.csv"
    table.to_csv(path, index=False)
    return path


# ---------------------------------------------------------------------------
# Brownian reference
# ---------------------------------------------------------------------------


def brownian_reference() -> pd.DataFrame:
    """Return what the measured diffusivity implies for a walker in the same box.

    Each strain gets one walker population per seed, with the measured motile
    fraction.  Motile walkers carry the measured effective diffusivity; the rest
    carry the passive diffusivity of the parameter table.  The box and the
    reflecting boundary are those of the simulation, so the comparison with the
    simulated displacement is like for like.

    This is not a claim that the cells are Brownian.  Over 20 s, with a
    persistence time near 0.1 s, a run-and-tumble walker is diffusive, so its
    displacement statistics are set by ``D_eff`` alone.
    """
    config = common.simulation_config_template()
    width = float(config["simulation"]["box_width_um"])
    height = float(config["simulation"]["box_height_um"])
    duration_s = float(config["simulation"]["track_duration_s"])
    n_steps = int(round(duration_s / DT_S))
    passive = float(common.base_table().passive_diffusion_um2_s.iloc[0])
    measured = common.measured_summary().query("medium == 'agarose'").set_index("phenotype")

    rng = np.random.default_rng(REFERENCE_SEED)
    lag_steps = int(round(MSD_LAG_S / DT_S))
    n_cells = int(config["simulation"]["n_cells"])
    n_seeds = len(SEEDS)
    rows: list[dict[str, object]] = []
    for phenotype in PHENOTYPES:
        diffusivity = float(measured.loc[phenotype, "measured_diffusivity_um2_s"])
        motile_fraction = float(measured.loc[phenotype, "measured_motile_fraction"])
        # All seeds advance together, so the 8000 steps run once instead of
        # once per seed.  Every walker keeps its own seed index.
        motile = rng.random((n_seeds, n_cells)) < motile_fraction
        sigma = np.sqrt(2.0 * np.where(motile, diffusivity, passive) * DT_S)
        position = np.stack(
            (
                rng.uniform(0.0, width, (n_seeds, n_cells)),
                rng.uniform(0.0, height, (n_seeds, n_cells)),
            ),
            axis=-1,
        )
        start = position.copy()
        lag_start = position.copy()
        squared_jumps = np.zeros((n_seeds, n_cells))
        n_jumps = 0
        for step in range(1, n_steps + 1):
            position = position + rng.normal(0.0, 1.0, position.shape) * sigma[..., None]
            position[..., 0] = _fold(position[..., 0], width)
            position[..., 1] = _fold(position[..., 1], height)
            if step % lag_steps == 0:
                squared_jumps += ((position - lag_start) ** 2).sum(axis=-1)
                lag_start = position.copy()
                n_jumps += 1
        displacement = np.linalg.norm(position - start, axis=-1)
        mean_squared_jump = squared_jumps / max(n_jumps, 1)
        for index, seed in enumerate(SEEDS):
            mask = motile[index]
            rows.append(
                {
                    "condition": "brownian_reference",
                    "phenotype": phenotype,
                    "medium": "agarose",
                    "seed": int(seed),
                    "predicted_mean_net_displacement_um": float(displacement[index].mean()),
                    "motile_mean_net_displacement_um": float(displacement[index][mask].mean()),
                    "diffusivity_estimate_um2_s": float(
                        mean_squared_jump[index][mask].mean() / (4.0 * MSD_LAG_S)
                    ),
                    "realized_motile_fraction": float(mask.mean()),
                    "stall_occupancy": 0.0,
                    "stall_entry_rate_per_swim_s": 0.0,
                }
            )
    return pd.DataFrame(rows)


def _fold(values: np.ndarray, limit: float) -> np.ndarray:
    """Reflect coordinates into ``[0, limit]``.

    Example:
        >>> [round(v, 6) for v in _fold(np.array([-1.0, 11.0, 5.0]), 10.0)]
        [1.0, 9.0, 5.0]
    """
    folded = np.abs(values)
    folded = np.abs(2.0 * limit - np.mod(folded, 2.0 * limit))
    return np.where(folded > limit, 2.0 * limit - folded, folded)


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


def ladder_summary(runs: pd.DataFrame) -> pd.DataFrame:
    """Return the mean of every observable per condition and strain, with intervals."""
    columns = (
        "predicted_mean_net_displacement_um",
        "motile_mean_net_displacement_um",
        "diffusivity_estimate_um2_s",
        "stall_occupancy",
        "stall_entry_rate_per_swim_s",
    )
    order = {name: index for index, name in enumerate(PHENOTYPES)}
    rows: list[dict[str, object]] = []
    for (condition, phenotype), part in runs.groupby(["condition", "phenotype"]):
        row: dict[str, object] = {
            "condition": condition,
            "phenotype": phenotype,
            "n_seeds": int(len(part)),
        }
        for column in columns:
            if column not in part:
                continue
            values = part[column].to_numpy(dtype=float)
            row[f"{column}_mean"] = float(np.nanmean(values))
            row[f"{column}_p2_5"] = float(np.nanquantile(values, 0.025))
            row[f"{column}_p97_5"] = float(np.nanquantile(values, 0.975))
        rows.append(row)
    frame = pd.DataFrame(rows)
    return frame.sort_values(["condition", "phenotype"], key=lambda c: c.map(order).fillna(c))


def hindrance_table(runs: pd.DataFrame) -> pd.DataFrame:
    """Return what each layer of the agarose model takes away, paired on seeds.

    The reference of every row is ``agarose_free``: the model that carries the
    measured agarose persistence time and nothing else.  A ratio below one means
    the layer hinders the cell beyond what the measurement already contains.
    """
    vectors, seeds = seed_vectors(runs, "predicted_mean_net_displacement_um")
    diffusivity, _ = seed_vectors(runs, "diffusivity_estimate_um2_s")
    draws = bootstrap_draws(len(seeds))
    measured = common.measured_summary().query("medium == 'agarose'").set_index("phenotype")
    rows: list[dict[str, object]] = []
    for condition in ("agarose_free", "agarose_obstacles", "agarose_full", "brownian_reference"):
        for phenotype in PHENOTYPES:
            key = (condition, phenotype)
            reference = ("agarose_free", phenotype)
            if key not in vectors:
                continue
            values = vectors[key]
            base = vectors[reference]
            boot = values[draws].mean(axis=1) / base[draws].mean(axis=1)
            rows.append(
                {
                    "condition": condition,
                    "phenotype": phenotype,
                    "mean_net_displacement_um": float(values.mean()),
                    "ratio_to_agarose_free": float(values.mean() / base.mean()),
                    "ratio_ci_low": float(np.quantile(boot, 0.025)),
                    "ratio_ci_high": float(np.quantile(boot, 0.975)),
                    "diffusivity_estimate_um2_s": float(np.nanmean(diffusivity[key])),
                    "measured_diffusivity_um2_s": float(
                        measured.loc[phenotype, "measured_diffusivity_um2_s"]
                    ),
                    "diffusivity_over_measured": float(
                        np.nanmean(diffusivity[key])
                        / measured.loc[phenotype, "measured_diffusivity_um2_s"]
                    ),
                }
            )
    return pd.DataFrame(rows)


def strain_ratio_table(runs: pd.DataFrame) -> pd.DataFrame:
    """Return the PproB/PproA and WT/PproA displacement ratios in every condition."""
    vectors, seeds = seed_vectors(runs, "predicted_mean_net_displacement_um")
    draws = bootstrap_draws(len(seeds))
    rows: list[dict[str, object]] = []
    for condition in sorted({key[0] for key in vectors}):
        reference = vectors[(condition, "PproA")][draws].mean(axis=1)
        observed_reference = vectors[(condition, "PproA")].mean()
        for phenotype in ("WT", "PproB"):
            boot = vectors[(condition, phenotype)][draws].mean(axis=1) / reference
            rows.append(
                {
                    "condition": condition,
                    "ratio": f"{phenotype}/PproA",
                    "value": float(vectors[(condition, phenotype)].mean() / observed_reference),
                    "ci_low": float(np.quantile(boot, 0.025)),
                    "ci_high": float(np.quantile(boot, 0.975)),
                }
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------


def diagnostic_style() -> None:
    """Apply a plain style, deliberately not the manuscript theme."""
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.size": 8,
            "axes.titlesize": 8,
            "savefig.bbox": "tight",
        }
    )


def save(figure: plt.Figure, stem: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for suffix in (".png", ".pdf"):
        figure.savefig(OUTPUT / f"{stem}{suffix}", dpi=200)
    plt.close(figure)


def ladder_figure(runs: pd.DataFrame, hindrance: pd.DataFrame) -> None:
    """Draw the ladder of agarose conditions against the measured expectation."""
    order = [
        "brownian_reference",
        "agarose_free",
        "agarose_obstacles",
        "agarose_full",
    ]
    names = {
        "brownian_reference": "Measured $D_{eff}$\nsame box",
        "agarose_free": "Model,\nmeasured $\\tau$ only",
        "agarose_obstacles": "+ 58\nobstacles",
        "agarose_full": "+ stalls\n(current model)",
    }
    colors = {"PproA": "#D55E00", "WT": "#7A7A7A", "PproB": "#0072B2"}
    figure, axes = plt.subplots(1, 2, figsize=(9.4, 4.4), constrained_layout=True)

    axis = axes[0]
    vectors, _ = seed_vectors(runs, "predicted_mean_net_displacement_um")
    for offset, condition in enumerate(order):
        for index, phenotype in enumerate(PHENOTYPES):
            values = vectors[(condition, phenotype)]
            x = offset + (index - 1) * 0.24
            axis.scatter(
                np.full(len(values), x),
                values,
                s=3,
                color=colors[phenotype],
                alpha=0.25,
                linewidths=0,
            )
            axis.scatter([x], [values.mean()], s=40, color="black", zorder=4, linewidths=0)
    axis.set(
        xticks=range(len(order)),
        xticklabels=[names[c] for c in order],
        ylabel="Mean net displacement per seed (µm)",
        title="Each agarose layer removes displacement\nthe measurement already contains",
    )
    axis.tick_params(axis="x", labelsize=7)

    axis = axes[1]
    measured = common.measured_summary().query("medium == 'agarose'").set_index("phenotype")
    for phenotype in PHENOTYPES:
        part = hindrance.query("phenotype == @phenotype").set_index("condition")
        values = [float(part.loc[c, "diffusivity_estimate_um2_s"]) for c in order]
        axis.plot(range(len(order)), values, "-o", color=colors[phenotype], label=phenotype, ms=4)
        axis.axhline(
            float(measured.loc[phenotype, "measured_diffusivity_um2_s"]),
            color=colors[phenotype],
            ls=":",
            lw=1.0,
        )
    axis.set(
        xticks=range(len(order)),
        xticklabels=[names[c] for c in order],
        ylabel=f"Effective diffusivity from MSD at {MSD_LAG_S:.0f} s lag (µm²/s)",
        yscale="log",
        title="Dotted lines: measured agarose $D_{eff}$",
    )
    axis.tick_params(axis="x", labelsize=7)
    axis.legend(frameon=False, fontsize=7)
    figure.suptitle(
        "Double-counting check. Same 100 seeds, 26 cells, 20 s, "
        f"dt = {DT_S} s, agarose parameters throughout.",
        fontsize=9,
    )
    save(figure, "double_counting_ladder")


# ---------------------------------------------------------------------------
# Record and entry point
# ---------------------------------------------------------------------------


def artifact(path: Path) -> dict[str, object]:
    item: dict[str, object] = {
        "relative_path": path.relative_to(PROJECT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }
    if path.suffix == ".csv":
        item["rows"] = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
    return item


def write_record(outputs: list[Path], seed_plan: dict[str, object]) -> None:
    record = {
        "schema_version": "1.0.0",
        "record_type": "model_diagnostic",
        "record_id": "motility_stall_double_counting_check",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "analyses/motility_stall_parameter_comparison/double_counting_check.py",
        ],
        "inputs": [
            artifact(Path(__file__).resolve()),
            artifact(Path(__file__).resolve().parent / "common.py"),
            artifact(common.BASE_TABLE),
            artifact(common.MEASURED),
            artifact(common.HOOK_COUNTS),
            artifact(common.UPSTREAM / "src/salmonella_motility_simulation/simulation.py"),
            artifact(common.UPSTREAM / "data/config.yml"),
        ],
        "outputs": [artifact(path) for path in outputs if path.exists()],
        "software": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "matplotlib": plt.matplotlib.__version__,
        },
        "parameters": {
            "ladder": [
                {"condition": name, "medium": medium, "obstacles": obstacles, "note": note}
                for name, medium, obstacles, note in LADDER
            ],
            "dt_s": DT_S,
            "msd_lag_s": MSD_LAG_S,
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "seed_plan_check": seed_plan,
            "measured_tau_definition": (
                "tau = 2 * D_eff / v^2, derived in analyses/figure_07_revision"
            ),
        },
        "random_seeds": {
            "population": f"{SEEDS[0]}-{SEEDS[-1]}",
            "starting_positions": "population seed + 1",
            "agarose_obstacles": "population seed + 300",
            "brownian_reference": REFERENCE_SEED,
        },
        "limitations": [
            (
                "The no-obstacle condition samples starting positions from the whole box, "
                "the obstacle conditions from the free area only. The pairing is on the seed "
                "index, not on identical initial conditions."
            ),
            (
                "The effective diffusivity is estimated at one lag inside a reflecting box. "
                "The box lowers every estimate by the same mechanism, so the comparison "
                "between conditions is fair; the absolute value is a slight underestimate."
            ),
            (
                "Stall occupancy is evaluated per time step of obstacle overlap and does not "
                "converge with the time step. It is a diagnostic at dt = 0.0025 s only."
            ),
            "Nothing written by this script is a manuscript panel.",
        ],
    }
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Rerun the simulations.")
    parser.add_argument("--processes", type=int, default=None)
    args = parser.parse_args()

    diagnostic_style()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    seed_plan = common.check_seed_plan_matches_manuscript()

    baseline = variant_table_path(variants()[0])
    no_stall = no_stall_table_path()
    tables = {
        "liquid": baseline,
        "agarose_free": no_stall,
        "agarose_obstacles": no_stall,
        "agarose_full": baseline,
    }
    frames = []
    for name, medium, obstacles, _ in LADDER:
        frames.append(
            cached_condition(
                f"t0_{name}",
                tables[name],
                medium,
                obstacles,
                force=args.force,
                processes=args.processes,
            ).assign(condition=name)
        )
    frames.append(brownian_reference())
    runs = pd.concat(frames, ignore_index=True)
    runs.to_csv(OUTPUT / "double_counting_runs.csv", index=False)

    summary = ladder_summary(runs)
    summary.to_csv(OUTPUT / "double_counting_summary.csv", index=False)
    agarose_runs = runs[runs.medium == "agarose"]
    hindrance = hindrance_table(agarose_runs)
    hindrance.to_csv(OUTPUT / "double_counting_hindrance.csv", index=False)
    ratios = strain_ratio_table(runs)
    ratios.to_csv(OUTPUT / "double_counting_strain_ratios.csv", index=False)
    measured = common.measured_summary()
    measured.to_csv(OUTPUT / "measured_reference.csv", index=False)
    ladder_figure(agarose_runs, hindrance)

    outputs = sorted(path for path in OUTPUT.iterdir() if path.is_file())
    write_record(outputs, seed_plan)

    with pd.option_context("display.width", 240, "display.precision", 4):
        print("\n== measured reference ==")
        print(measured.to_string(index=False))
        print("\n== ladder, mean over 100 seeds ==")
        print(
            summary[
                [
                    "condition",
                    "phenotype",
                    "predicted_mean_net_displacement_um_mean",
                    "diffusivity_estimate_um2_s_mean",
                    "stall_occupancy_mean",
                    "stall_entry_rate_per_swim_s_mean",
                ]
            ].to_string(index=False)
        )
        print("\n== hindrance relative to the measured-tau-only model ==")
        print(hindrance.to_string(index=False))
        print("\n== strain ratios ==")
        print(ratios.to_string(index=False))
    print(f"\noutputs: {OUTPUT.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
