"""
Coarse-grained 2D single-cell motility simulation for different strains and environments.

Model summary
-------------
- A fixed fraction of cells are permanently non-motile and diffuse weakly.
- Motile cells alternate between:
  1. run mode: ballistic motion with rotational diffusion
  2. reorientation mode: short pause / weakly diffusive phase followed by a turn
- In agarose, static circular obstacles introduce explicit contact interactions:
  cells are projected to the obstacle surface and then either slide tangentially
  or pause transiently with a phenotype-specific stall probability.

The model is intentionally simple, interpretable, and directly parameterized by
observed or pre-estimated summary quantities. It is illustrative rather than
mechanistically complete.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml
from salmonella_motility_simulation import classes
from salmonella_motility_simulation import io_utils
from salmonella_motility_simulation import simulation
from salmonella_motility_simulation import plotting
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# CSV loading and validation
# ---------------------------------------------------------------------------


def load_parameter_table(
    csv_path: Path,
) -> dict[tuple[str, str], classes.MotilityParameters]:
    """Load and validate phenotype-by-medium simulation parameters."""
    df = pd.read_csv(csv_path)
    required = {
        "phenotype",
        "medium",
        "color",
        "motile_fraction",
        "run_speed_um_s",
        "rotational_diffusion_rad2_s",
        "reorientation_rate_s",
        "reorientation_duration_s",
        "turn_angle_sd_rad",
        "passive_diffusion_um2_s",
        "stall_probability",
        "stall_mean_duration_s",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {csv_path}: {sorted(missing)}")

    table: dict[tuple[str, str], classes.MotilityParameters] = {}
    for row in df.to_dict(orient="records"):
        key = (str(row["phenotype"]), str(row["medium"]))
        table[key] = classes.MotilityParameters(
            phenotype=str(row["phenotype"]),
            medium=str(row["medium"]),
            color=str(row["color"]),
            motile_fraction=float(np.clip(row["motile_fraction"], 0.0, 1.0)),
            run_speed_um_s=float(max(row["run_speed_um_s"], 0.0)),
            rotational_diffusion_rad2_s=float(
                max(row["rotational_diffusion_rad2_s"], 0.0)
            ),
            reorientation_rate_s=float(max(row["reorientation_rate_s"], 0.0)),
            reorientation_duration_s=float(
                max(row["reorientation_duration_s"], 1.0e-6)
            ),
            turn_angle_sd_rad=float(max(row["turn_angle_sd_rad"], 1.0e-6)),
            passive_diffusion_um2_s=float(max(row["passive_diffusion_um2_s"], 0.0)),
            stall_probability=float(np.clip(row["stall_probability"], 0.0, 1.0)),
            stall_mean_duration_s=float(max(row["stall_mean_duration_s"], 1.0e-6)),
        )
    return table


# ---------------------------------------------------------------------------
# Configuration and main function
# ---------------------------------------------------------------------------


def parse_args(default_input, default_output) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a six-panel single-cell bacterial motility figure."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input,
        help="Input CSV with phenotype-by-medium motility parameters.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help="Prefix for all output files, such as TSV, JSON, and rendered PNG images.",
    )
    parser.add_argument(
        "--from-tsv-prefix",
        type=Path,
        default=None,
        help="Load panel data from existing '<prefix>_tracks.tsv', '<prefix>_obstacles.tsv', and '<prefix>_meta.json' instead of simulating.",
    )

    return parser.parse_args()


def run_simulations(
    table: dict[tuple[str, str], classes.MotilityParameters], config: dict[str, Any]
) -> list[dict[str, Any]]:
    """Run all phenotype-medium simulations and return panel-wise results."""

    phenotypes = sorted(set(k[0] for k in table.keys()))
    media = sorted(set(k[1] for k in table.keys()))
    base_seed: int = config["simulation"].get("base_seed", 42)
    panel_results: list[dict[str, Any]] = []

    for row, phenotype in enumerate(phenotypes):
        for col, medium in enumerate(media):
            params = table[(phenotype, medium)]
            panel_seed = base_seed + row * 41 + col * 7
            obstacles = (
                None
                if medium == "liquid"
                else simulation.make_obstacle_field(
                    config=config,
                    seed=panel_seed + 300,
                )
            )
            sim = simulation.simulate_population(
                config=config,
                params=params,
                obstacles=obstacles,
                seed=panel_seed,
            )
            panel_results.append(
                {
                    "phenotype": phenotype,
                    "medium": medium,
                    "seed": panel_seed,
                    "dt_s": config["simulation"]["dt_s"],
                    "duration_s": config["simulation"]["track_duration_s"],
                    "sim": sim,
                }
            )

    return panel_results


def main() -> None:

    # set up paths, load config
    workdir = Path(__file__).resolve().parent.parent.parent
    default_input = workdir / "data" / "motility_summary_parameters.csv"
    default_output = workdir / "output" / "ppro"
    config_yaml = workdir / "data" / "config.yml"

    with open(config_yaml) as _f:
        config = yaml.safe_load(_f)

    # argument parsing (including number and type of simulations)
    args = parse_args(default_input, default_output)
    if args.from_tsv_prefix is not None:
        panel_results = io_utils.load_bundle_tsv(args.from_tsv_prefix)
        print(
            f"Loaded {len(panel_results)} phenotype-medium panels from {args.from_tsv_prefix}"
        )
    else:
        table = load_parameter_table(args.input)
        panel_results = run_simulations(
            table=table,
            config=config,
        )
        print(f"Simulated {len(panel_results)} phenotype-medium panels")

        out_files = io_utils.save_bundle_tsv(panel_results, args.output)
        print(f"Saved TSV tracks to {out_files['tracks']}")
        print(f"Saved TSV obstacles to {out_files['obstacles']}")
        print(f"Saved metadata JSON to {out_files['meta']}")

    for panel in panel_results:
        sim = panel["sim"]
        n_cells_panel = int(sim["history"].shape[1])
        n_steps_panel = int(sim["history"].shape[0])
        n_obstacles = 0 if sim["obstacles"] is None else sim["obstacles"].n_obstacles
        print(
            f"  - {panel['phenotype']} / {panel['medium']}: cells={n_cells_panel}, steps={n_steps_panel}, obstacles={n_obstacles}, seed={panel['seed']}"
        )

    # Plotting
    plotting.plot_figure(config, panel_results, args.output)
    plotting.plot_summary(panel_results, args.output)
    html_path = plotting.plot_figure_html(config, panel_results, args.output)
    print(f"Saved interactive HTML to {html_path}")


if __name__ == "__main__":
    main()
