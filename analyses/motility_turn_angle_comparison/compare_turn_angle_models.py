#!/usr/bin/env python3
"""Compare the current per-strain turn angle against one global, literature-anchored turn angle.

The two models differ in exactly one input column, ``turn_angle_sd_rad``:

* **current** - six per-strain values with no source, calibrated by
  ``analyses/motility_parameter_calibration/calibrate.py``.
* **global** - one value for all rows, 1.2468 rad, anchored to a published mean
  turn angle of 57 deg, calibrated by ``calibrate_global_turn_angle.py``.

Both tables close the persistence time on the same measured tau, so the
comparison isolates how that persistence is delivered: as continuous heading
wander, or as discrete turns.

What this script writes, all under ``build/diagnostics/turn_angle_comparison``:

* the per-seed net displacement of both models over the same 100 seeds,
* a parameter table naming D_r, lambda, tau and the tumble share under each,
* a paired net-displacement comparison with bootstrap intervals,
* the PproB/PproA and WT/PproA ratios under each model,
* trajectory maps and single-cell tracks of the same seeds under both models.

Nothing here is a manuscript panel.  It is a decision aid.

Setup:
    PYTHONPATH=$PWD/src MPLBACKEND=Agg .venv/bin/python \
        analyses/motility_turn_angle_comparison/compare_turn_angle_models.py

Runtime is about 12 min on one core for the 1200 simulations.  Results are
cached per model and keyed by the checksum of the parameter table, so a rerun
without a parameter change costs seconds.  Pass ``--force`` to rerun anyway.

Complexity is O(models * seeds * steps * cells).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT / "models/motility_simulation/upstream/src"))
sys.path.insert(0, str(PROJECT / "analyses/motility_parameter_calibration"))
sys.path.insert(0, str(PROJECT / "analyses/figure_05_revision"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from calibrate import calibrated_table_path, model_tau  # noqa: E402
from calibrate_global_turn_angle import (  # noqa: E402
    GLOBAL_TURN_ANGLE_SD_RAD,
    TAUTE_MEAN_TURN_ANGLE_DEG,
    TAUTE_TURN_COUNT,
    global_turn_angle_table_path,
    turn_angle_diagnostics,
)
from salmonella_motility_simulation import simulation  # noqa: E402
from salmonella_motility_simulation.__main__ import load_parameter_table  # noqa: E402

import build as figure_05  # noqa: E402
from flagella_repro.theme import PALETTE, get_strain_style  # noqa: E402

OUTPUT = PROJECT / "build/diagnostics/turn_angle_comparison"
RECORD = Path(__file__).resolve().parent / "metadata/comparison.json"

PHENOTYPES = figure_05.PHENOTYPES
MEDIA = figure_05.MEDIA
STRAIN_IDS = figure_05.STRAIN_IDS
OBSERVABLE = figure_05.OBSERVABLE_COLUMN
DT_S = figure_05.SIMULATION_DT_S
SEEDS = list(figure_05.SEEDS)

MODELS = ("current", "global")
MODEL_LABELS = {
    "current": "Current model\nper-strain turn angle",
    "global": "Global-angle model\n$\\sigma$ = 1.247 rad (57° mean turn)",
}

#: Reference phenotype for the reported net-displacement ratios.
REFERENCE_PHENOTYPE = "PproA"

#: Seed used for every trajectory figure, and the bootstrap seed.  Both are
#: explicit so the figures and the intervals are reproducible.
TRAJECTORY_SEED = 1000
BOOTSTRAP_SEED = 20260813
BOOTSTRAP_DRAWS = 10_000

#: Seconds of track shown in the single-cell zoom.  The full 20 s track fills
#: the box and hides the turn structure, which is what this comparison is about.
ZOOM_DURATION_S = 3.0

INK = PALETTE["neutral"]["text"]
GRID = PALETTE["neutral"]["technical"]
PAPER = PALETTE["neutral"]["background"]


def model_table_path(model: str) -> Path:
    """Return the parameter table for one model, deriving it if it is missing."""
    if model == "current":
        return calibrated_table_path()
    if model == "global":
        return global_turn_angle_table_path()
    raise ValueError(f"unknown model: {model!r}")


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


def seed_summary(model: str, force: bool = False) -> pd.DataFrame:
    """Return one mean net displacement per seed for one model.

    The cache is keyed by the checksum of the parameter table, the time step and
    the observable, so a recalibration invalidates a stale run instead of being
    silently reused.
    """
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / f"seed_summary_{model}.csv"
    fingerprint = OUTPUT / f"seed_summary_{model}.sha256"
    table = model_table_path(model)
    digest = hashlib.sha256(
        table.read_bytes() + repr(float(DT_S)).encode("utf-8") + OBSERVABLE.encode("utf-8")
    ).hexdigest()
    stale = not fingerprint.exists() or fingerprint.read_text(encoding="utf-8").strip() != digest
    if path.exists() and not force and not stale:
        return pd.read_csv(path)
    frame = figure_05.active_particle_seed_summary(parameters_path=table)
    frame.insert(0, "model", model)
    frame.to_csv(path, index=False)
    fingerprint.write_text(digest + "\n", encoding="utf-8")
    return frame


def run_tracks(model: str, phenotype: str, medium: str, seed: int) -> dict:
    """Return one full simulation result, for the trajectory figures.

    Both models start from identical initial conditions at a given seed: the
    heading draw, the motile mask, the starting positions and the obstacle field
    all precede any parameter that differs between the two tables.
    """
    parameters = load_parameter_table(model_table_path(model))
    config = figure_05.simulation_config()
    obstacles = None
    if medium == "agarose":
        obstacles = simulation.make_obstacle_field(config, seed=seed + 300)
    return simulation.simulate_population(config, parameters[(phenotype, medium)], obstacles, seed)


# ---------------------------------------------------------------------------
# Parameter comparison
# ---------------------------------------------------------------------------


def parameter_comparison() -> pd.DataFrame:
    """Return the calibrated turning parameters of both models, side by side.

    Two derived quantities carry the mechanism:

    * ``tumble_share`` is ``lambda * k / (D_r + lambda * k)`` with
      ``k = 1 - exp(-sigma^2 / 2)``.  It is the fraction of the persistence
      decay rate delivered by discrete turns rather than continuous wander.
    * ``reorient_duty_cycle`` is ``d / (1 / lambda + d)``, the fraction of time
      a motile cell spends in the non-swimming reorientation state.
    """
    audit = PROJECT / "data/processed/motility_parameter_calibration/calibration_audit.csv"
    if not audit.exists():
        calibrated_table_path(force=True)
    measured = pd.read_csv(audit)[["phenotype", "medium", "measured_tau_s", "n_units"]]
    rows: list[dict[str, object]] = []
    for model in MODELS:
        table = pd.read_csv(model_table_path(model))
        for item in table.itertuples(index=False):
            sigma = float(item.turn_angle_sd_rad)
            d_r = float(item.rotational_diffusion_rad2_s)
            rate = float(item.reorientation_rate_s)
            duration = float(item.reorientation_duration_s)
            efficiency = 1.0 - math.exp(-(sigma**2) / 2.0)
            rows.append(
                {
                    "model": model,
                    "phenotype": item.phenotype,
                    "medium": item.medium,
                    "turn_angle_sd_rad": sigma,
                    "mean_abs_turn_deg": math.degrees(sigma * math.sqrt(2.0 / math.pi)),
                    "rotational_diffusion_rad2_s": d_r,
                    "reorientation_rate_s": rate,
                    "turn_efficiency": efficiency,
                    "tumble_share": rate * efficiency / (d_r + rate * efficiency),
                    "reorient_duty_cycle": duration / (1.0 / rate + duration),
                    "mean_run_interval_s": 1.0 / rate,
                    "mean_run_length_um": float(item.run_speed_um_s) / rate,
                    "model_tau_s": model_tau(d_r, rate, sigma),
                    "run_speed_um_s": float(item.run_speed_um_s),
                    "motile_fraction": float(item.motile_fraction),
                }
            )
    frame = pd.DataFrame(rows).merge(measured, on=["phenotype", "medium"], how="left")
    frame["tau_closure_residual_s"] = frame.model_tau_s - frame.measured_tau_s
    order = {name: index for index, name in enumerate(PHENOTYPES)}
    frame = frame.sort_values(
        ["medium", "phenotype", "model"], key=lambda col: col.map(order).fillna(col)
    )
    return frame.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Paired bootstrap over seeds
# ---------------------------------------------------------------------------


GroupVectors = dict[tuple[str, str, str], np.ndarray]


def _seed_matrix(seed_data: pd.DataFrame) -> tuple[GroupVectors, list[int]]:
    """Return per-group seed vectors aligned on a common, sorted seed list."""
    seeds = sorted(seed_data.seed.unique())
    vectors: dict[tuple[str, str, str], np.ndarray] = {}
    for key, part in seed_data.groupby(["model", "phenotype", "medium"]):
        part = part.set_index("seed").reindex(seeds)
        if part[OBSERVABLE].isna().any():
            raise ValueError(f"Group {key} is missing a seed.")
        vectors[key] = part[OBSERVABLE].to_numpy(dtype=float)
    return vectors, seeds


def paired_bootstrap(seed_data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return the net-displacement and ratio comparisons with bootstrap intervals.

    The bootstrap resamples the seed index, not the group, so a single resample
    is applied to every group of both models at once.  The two models share the
    seed set and therefore share the initial conditions, so the paired
    difference removes the seed-to-seed variation that both models see.
    """
    vectors, seeds = _seed_matrix(seed_data)
    n_seeds = len(seeds)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.integers(0, n_seeds, size=(BOOTSTRAP_DRAWS, n_seeds))

    def resampled_means(key: tuple[str, str, str]) -> np.ndarray:
        return vectors[key][draws].mean(axis=1)

    displacement_rows: list[dict[str, object]] = []
    ratio_rows: list[dict[str, object]] = []
    boot_means = {key: resampled_means(key) for key in vectors}

    for medium in MEDIA:
        for phenotype in PHENOTYPES:
            current = vectors[("current", phenotype, medium)]
            variant = vectors[("global", phenotype, medium)]
            difference = variant - current
            boot_difference = (
                boot_means[("global", phenotype, medium)]
                - boot_means[("current", phenotype, medium)]
            )
            boot_relative = boot_difference / boot_means[("current", phenotype, medium)]
            row: dict[str, object] = {
                "phenotype": phenotype,
                "medium": medium,
                "n_seeds": n_seeds,
                "current_mean_um": float(current.mean()),
                "current_boot_ci_low_um": float(
                    np.quantile(boot_means[("current", phenotype, medium)], 0.025)
                ),
                "current_boot_ci_high_um": float(
                    np.quantile(boot_means[("current", phenotype, medium)], 0.975)
                ),
                "current_seed_p2_5_um": float(np.quantile(current, 0.025)),
                "current_seed_p97_5_um": float(np.quantile(current, 0.975)),
                "global_mean_um": float(variant.mean()),
                "global_boot_ci_low_um": float(
                    np.quantile(boot_means[("global", phenotype, medium)], 0.025)
                ),
                "global_boot_ci_high_um": float(
                    np.quantile(boot_means[("global", phenotype, medium)], 0.975)
                ),
                "global_seed_p2_5_um": float(np.quantile(variant, 0.025)),
                "global_seed_p97_5_um": float(np.quantile(variant, 0.975)),
                "paired_difference_um": float(difference.mean()),
                "paired_difference_ci_low_um": float(np.quantile(boot_difference, 0.025)),
                "paired_difference_ci_high_um": float(np.quantile(boot_difference, 0.975)),
                "relative_change": float(variant.mean() / current.mean() - 1.0),
                "relative_change_ci_low": float(np.quantile(boot_relative, 0.025)),
                "relative_change_ci_high": float(np.quantile(boot_relative, 0.975)),
            }
            displacement_rows.append(row)

        reference = {model: boot_means[(model, REFERENCE_PHENOTYPE, medium)] for model in MODELS}
        reference_observed = {
            model: vectors[(model, REFERENCE_PHENOTYPE, medium)].mean() for model in MODELS
        }
        for phenotype in PHENOTYPES:
            if phenotype == REFERENCE_PHENOTYPE:
                continue
            entry: dict[str, object] = {
                "ratio": f"{phenotype}/{REFERENCE_PHENOTYPE}",
                "medium": medium,
                "n_seeds": n_seeds,
            }
            boot_ratio: dict[str, np.ndarray] = {}
            for model in MODELS:
                boot_ratio[model] = boot_means[(model, phenotype, medium)] / reference[model]
                observed = vectors[(model, phenotype, medium)].mean() / reference_observed[model]
                entry[f"{model}_ratio"] = float(observed)
                entry[f"{model}_ci_low"] = float(np.quantile(boot_ratio[model], 0.025))
                entry[f"{model}_ci_high"] = float(np.quantile(boot_ratio[model], 0.975))
            shift = boot_ratio["global"] - boot_ratio["current"]
            entry["ratio_shift"] = float(entry["global_ratio"]) - float(entry["current_ratio"])
            entry["ratio_shift_ci_low"] = float(np.quantile(shift, 0.025))
            entry["ratio_shift_ci_high"] = float(np.quantile(shift, 0.975))
            ratio_rows.append(entry)

    return pd.DataFrame(displacement_rows), pd.DataFrame(ratio_rows)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------


def _diagnostic_style() -> None:
    """Apply a plain, readable style.

    The manuscript theme is deliberately not applied.  These are decision aids,
    not panels, and they must not be mistaken for figure output.
    """
    plt.rcParams.update(
        {
            "figure.facecolor": PAPER,
            "axes.facecolor": PAPER,
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "text.color": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "font.size": 8,
            "axes.titlesize": 8,
            "savefig.bbox": "tight",
        }
    )


def _save(figure: plt.Figure, stem: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for suffix in (".png", ".pdf"):
        figure.savefig(OUTPUT / f"{stem}{suffix}", dpi=200)
    plt.close(figure)


def trajectory_map(medium: str, seed: int = TRAJECTORY_SEED) -> None:
    """Draw all 26 tracks of one seed under both models, phenotype by phenotype."""
    figure, axes = plt.subplots(
        len(PHENOTYPES), len(MODELS), figsize=(9.0, 8.4), constrained_layout=True
    )
    for row, phenotype in enumerate(PHENOTYPES):
        color = get_strain_style(STRAIN_IDS[phenotype])["color"]
        for column, model in enumerate(MODELS):
            axis = axes[row, column]
            result = run_tracks(model, phenotype, medium, seed)
            history = result["history"]
            obstacles = result["obstacles"]
            if obstacles is not None:
                for x, y, radius in zip(
                    obstacles.x_um, obstacles.y_um, obstacles.r_um, strict=True
                ):
                    axis.add_patch(
                        plt.Circle((x, y), radius, facecolor=GRID, edgecolor="none", alpha=0.55)
                    )
            motile = result["is_motile"]
            for cell in range(history.shape[1]):
                axis.plot(
                    history[:, cell, 0],
                    history[:, cell, 1],
                    lw=0.45,
                    color=color if motile[cell] else GRID,
                    alpha=0.85 if motile[cell] else 0.5,
                )
            axis.scatter(history[0, :, 0], history[0, :, 1], s=4, color=INK, zorder=3, linewidths=0)
            axis.set(
                xlim=(0, result["box_width_um"]),
                ylim=(0, result["box_height_um"]),
                xticks=[],
                yticks=[],
            )
            axis.set_aspect("equal")
            if row == 0:
                axis.set_title(MODEL_LABELS[model])
            if column == 0:
                axis.set_ylabel(phenotype, fontsize=9)
    duration_s = float(figure_05.simulation_config()["simulation"]["track_duration_s"])
    figure.suptitle(
        f"{medium.capitalize()} — same seed ({seed}), same starting positions, "
        f"26 cells, {duration_s:.0f} s, dt = {DT_S} s\n"
        "Dark dots mark the start of each track; grey tracks are non-motile cells",
        fontsize=9,
    )
    _save(figure, f"trajectories_{medium}")


def single_cell_tracks(medium: str = "liquid", seed: int = TRAJECTORY_SEED) -> None:
    """Draw one motile cell per phenotype under both models, start-centred.

    The same cell index is used for both models.  The motile mask is drawn
    before any differing parameter is read, so the two panels of a row follow
    the same cell from the same starting heading.
    """
    steps = int(round(ZOOM_DURATION_S / DT_S)) + 1
    config = figure_05.simulation_config()
    state_run = int(config["states"]["run"])
    state_reorient = int(config["states"]["reorient"])
    figure, axes = plt.subplots(
        len(PHENOTYPES), len(MODELS), figsize=(8.4, 9.4), constrained_layout=True
    )
    for row, phenotype in enumerate(PHENOTYPES):
        color = get_strain_style(STRAIN_IDS[phenotype])["color"]
        results = {model: run_tracks(model, phenotype, medium, seed) for model in MODELS}
        motile = results["current"]["is_motile"]
        cell = int(np.argmax(motile))
        span = 0.0
        for model in MODELS:
            track = results[model]["history"][:steps, cell, :]
            span = max(span, float(np.abs(track - track[0]).max()))
        for column, model in enumerate(MODELS):
            axis = axes[row, column]
            track = results[model]["history"][:steps, cell, :]
            track = track - track[0]
            states = results[model]["state_history"][:steps, cell]
            # A turn is applied at the step where the cell leaves the reorient
            # state.  Marking those points shows how much of the reorientation
            # arrives as a discrete event rather than as continuous wander.
            turns = np.flatnonzero((states[:-1] == state_reorient) & (states[1:] == state_run)) + 1
            axis.plot(track[:, 0], track[:, 1], lw=0.7, color=color, zorder=2)
            axis.scatter(
                track[turns, 0],
                track[turns, 1],
                s=9,
                facecolor="none",
                edgecolor=INK,
                linewidths=0.5,
                zorder=3,
            )
            axis.scatter([0], [0], s=18, color=INK, zorder=4, linewidths=0)
            limit = span * 1.08 + 1.0
            axis.set(xlim=(-limit, limit), ylim=(-limit, limit))
            axis.set_aspect("equal")
            axis.axhline(0, color=GRID, lw=0.4, zorder=0)
            axis.axvline(0, color=GRID, lw=0.4, zorder=0)
            axis.annotate(
                f"{len(turns)} turns",
                xy=(0.03, 0.96),
                xycoords="axes fraction",
                va="top",
                fontsize=7.5,
            )
            if row == 0:
                axis.set_title(MODEL_LABELS[model])
            if column == 0:
                axis.set_ylabel(f"{phenotype}\ny (µm)", fontsize=9)
            if row == len(PHENOTYPES) - 1:
                axis.set_xlabel("x (µm)")
    figure.legend(
        handles=[
            Line2D([], [], color=INK, lw=0, marker="o", markersize=5, label="Track start"),
            Line2D(
                [],
                [],
                color=INK,
                lw=0,
                marker="o",
                markersize=5,
                markerfacecolor="none",
                label="Discrete turn",
            ),
        ],
        loc="outside lower center",
        ncols=2,
        frameon=False,
        fontsize=8,
    )
    figure.suptitle(
        f"One motile cell, first {ZOOM_DURATION_S:.0f} s in {medium}, seed {seed}\n"
        "Same cell, same starting heading; only the turn-angle model differs",
        fontsize=9,
    )
    _save(figure, f"single_cell_tracks_{medium}")


def paired_displacement_figure(seed_data: pd.DataFrame, comparison: pd.DataFrame) -> None:
    """Plot each seed as a line from the current model to the global-angle model."""
    figure, axes = plt.subplots(1, len(MEDIA), figsize=(8.0, 4.2), constrained_layout=True)
    vectors, _ = _seed_matrix(seed_data)
    for axis, medium in zip(axes, MEDIA, strict=True):
        for offset, phenotype in enumerate(PHENOTYPES):
            color = get_strain_style(STRAIN_IDS[phenotype])["color"]
            current = vectors[("current", phenotype, medium)]
            variant = vectors[("global", phenotype, medium)]
            x_left = offset * 3.0
            x_right = x_left + 1.0
            for a, b in zip(current, variant, strict=True):
                axis.plot([x_left, x_right], [a, b], color=color, lw=0.3, alpha=0.25)
            axis.scatter(
                [x_left, x_right],
                [current.mean(), variant.mean()],
                s=34,
                color=INK,
                zorder=4,
                linewidths=0,
            )
            row = comparison.query("phenotype == @phenotype and medium == @medium").iloc[0]
            axis.annotate(
                f"{row.relative_change:+.1%}",
                xy=((x_left + x_right) / 2.0, max(current.mean(), variant.mean())),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                fontsize=8,
            )
        axis.set(
            xticks=[offset * 3.0 + 0.5 for offset in range(len(PHENOTYPES))],
            xticklabels=PHENOTYPES,
            ylabel="Mean net displacement per seed (µm)",
            title=medium.capitalize(),
        )
    figure.legend(
        handles=[
            Line2D([], [], color=INK, lw=0, marker="o", markersize=6, label="Group mean"),
            Line2D([], [], color=GRID, lw=1.0, label="One seed, current → global"),
        ],
        loc="outside lower center",
        ncols=2,
        frameon=False,
        fontsize=8,
    )
    figure.suptitle(
        "Paired net displacement, 100 shared seeds. Left point of each pair is the "
        "current model,\nright point the global-angle model.",
        fontsize=9,
    )
    _save(figure, "net_displacement_paired")


# ---------------------------------------------------------------------------
# Record and entry point
# ---------------------------------------------------------------------------


def _artifact(path: Path) -> dict[str, object]:
    item: dict[str, object] = {
        "relative_path": path.relative_to(PROJECT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }
    if path.suffix == ".csv":
        item["rows"] = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
    return item


def write_record(outputs: list[Path], parameters: pd.DataFrame) -> None:
    diagnostics = turn_angle_diagnostics()
    record = {
        "schema_version": "1.0.0",
        "record_type": "model_variant_comparison",
        "record_id": "motility_turn_angle_comparison",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "analyses/motility_turn_angle_comparison/compare_turn_angle_models.py",
        ],
        "inputs": [
            _artifact(Path(__file__).resolve()),
            _artifact(Path(__file__).resolve().parent / "calibrate_global_turn_angle.py"),
            _artifact(PROJECT / "analyses/motility_parameter_calibration/calibrate.py"),
            _artifact(PROJECT / "analyses/figure_05_revision/build.py"),
            _artifact(model_table_path("current")),
            _artifact(model_table_path("global")),
            _artifact(
                PROJECT / "models/motility_simulation/upstream/src"
                "/salmonella_motility_simulation/simulation.py"
            ),
            _artifact(PROJECT / "models/motility_simulation/upstream/data/config.yml"),
        ],
        "outputs": [_artifact(path) for path in outputs if path.exists()],
        "software": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "matplotlib": plt.matplotlib.__version__,
        },
        "parameters": {
            "models": list(MODELS),
            "global_turn_angle_sd_rad": GLOBAL_TURN_ANGLE_SD_RAD,
            "anchor_mean_turn_angle_deg": TAUTE_MEAN_TURN_ANGLE_DEG,
            "anchor_turn_count": TAUTE_TURN_COUNT,
            "turn_angle_diagnostics": diagnostics,
            "dt_s": DT_S,
            "track_duration_s": 20.0,
            "cells_per_seed": 26,
            "observable": "mean net displacement per seed (um)",
            "reference_phenotype": REFERENCE_PHENOTYPE,
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "max_tau_closure_residual_s": float(parameters.tau_closure_residual_s.abs().max()),
        },
        "random_seeds": {
            "population": f"{SEEDS[0]}-{SEEDS[-1]}",
            "starting_positions": "population seed + 1",
            "agarose_obstacles": "population seed + 300",
            "bootstrap": BOOTSTRAP_SEED,
            "trajectory_figures": TRAJECTORY_SEED,
        },
        "limitations": [
            (
                "Both models take run speed, motile fraction and persistence time as "
                "calibrated inputs. Neither predicts them."
            ),
            (
                "The two models share the seed set and therefore the starting positions, the "
                "motile mask and the obstacle field. They do not share the later random "
                "draws, because the parameters differ. The pairing removes the initial-"
                "condition variance, not all stochastic variation."
            ),
            (
                "Intervals quantify stochastic model-seed variation, not biological sampling "
                "uncertainty."
            ),
            "Nothing written by this script is a manuscript panel.",
        ],
    }
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Rerun the simulations.")
    parser.add_argument("--skip-figures", action="store_true")
    args = parser.parse_args()

    _diagnostic_style()
    OUTPUT.mkdir(parents=True, exist_ok=True)

    parameters = parameter_comparison()
    parameters.to_csv(OUTPUT / "parameter_comparison.csv", index=False)

    frames = [seed_summary(model, force=args.force) for model in MODELS]
    seed_data = pd.concat(frames, ignore_index=True)
    seed_data.to_csv(OUTPUT / "seed_summary_both_models.csv", index=False)

    displacement, ratios = paired_bootstrap(seed_data)
    displacement.to_csv(OUTPUT / "net_displacement_comparison.csv", index=False)
    ratios.to_csv(OUTPUT / "ratio_comparison.csv", index=False)

    if not args.skip_figures:
        for medium in MEDIA:
            trajectory_map(medium)
            single_cell_tracks(medium)
        paired_displacement_figure(seed_data, displacement)

    outputs = sorted(path for path in OUTPUT.iterdir() if path.is_file())
    write_record(outputs, parameters)

    with pd.option_context("display.width", 240, "display.precision", 4):
        print("\n== calibrated turning parameters ==")
        print(
            parameters[
                [
                    "medium",
                    "phenotype",
                    "model",
                    "turn_angle_sd_rad",
                    "rotational_diffusion_rad2_s",
                    "reorientation_rate_s",
                    "tumble_share",
                    "reorient_duty_cycle",
                    "model_tau_s",
                    "measured_tau_s",
                ]
            ].to_string(index=False)
        )
        print("\n== net displacement, paired over 100 seeds ==")
        print(
            displacement[
                [
                    "medium",
                    "phenotype",
                    "current_mean_um",
                    "global_mean_um",
                    "paired_difference_um",
                    "paired_difference_ci_low_um",
                    "paired_difference_ci_high_um",
                    "relative_change",
                ]
            ].to_string(index=False)
        )
        print("\n== net-displacement ratios ==")
        print(ratios.to_string(index=False))
    worst = float(parameters.tau_closure_residual_s.abs().max())
    print(f"\nmax |model tau - measured tau|: {worst:.3e} s")
    print(f"outputs: {OUTPUT.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
