#!/usr/bin/env python3
"""Compare seven ways of distributing the two agarose stall parameters between strains.

``stall_probability`` and ``stall_mean_duration_s`` differ per strain in agarose
and neither has a source.  The durations fall with flagella number, which matches
the hypothesis that more flagella free a trapped cell sooner.  The probabilities
are not monotone in flagella number: WT carries the highest value.

Each variant keeps the arithmetic mean of the three current values, so the grid
tests how the effect is **distributed** between strains, not how large it is.
Variant F replaces the duration with the only published agar dwell time.

    A  baseline           per-strain probability, per-strain duration
    B  global, global     both at the mean of the three current values
    C  global p, t ~ 1/N  duration inversely proportional to mean hook number
    D  global p, t ~ 1/sqrt(N)
    E  p ~ 1/N, t ~ 1/N
    F  global p, t = 2.07 s   Datta et al. 2025, 0.25 % agar
    G  p ~ N^-0.70, global t  Grognot et al. 2023 stall-frequency strength

Setup:
    PYTHONPATH=$PWD/src MPLBACKEND=Agg .venv/bin/python \\
        analyses/motility_stall_parameter_comparison/compare_stall_variants.py

Runtime is about 12 min on seven cores for the 2100 simulations.  Results are
cached per variant and keyed by the parameter-table checksum.  Pass ``--force``
to rerun.
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
    DATTA_MEAN_DWELL_S,
    DT_S,
    GROGNOT_STALL_FREQUENCY_RATIO,
    GROGNOT_STALL_FREQUENCY_RATIO_SD,
    OUTPUT,
    PHENOTYPES,
    PROJECT,
    REFERENCE_PHENOTYPE,
    SEEDS,
    bootstrap_draws,
    cached_condition,
    grognot_exponent,
    seed_vectors,
    variant_table_path,
    variants,
)

RECORD = Path(__file__).resolve().parent / "metadata/variant_comparison.json"
BASELINE = "A_baseline"
OBSERVABLE = "predicted_mean_net_displacement_um"
STRAIN_COLORS = {"PproA": "#D55E00", "WT": "#7A7A7A", "PproB": "#0072B2"}


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


def displacement_table(runs: pd.DataFrame) -> pd.DataFrame:
    """Return the mean net displacement per variant and strain, paired on seeds.

    Two intervals are reported and they answer different questions.  The seed
    interval is the 2.5th to 97.5th percentile of the 100 seed means and shows
    how much one seed can differ from another.  The bootstrap interval is on the
    mean itself.  The paired difference from the baseline uses the same seed
    resample for both variants, so the seed-to-seed variation cancels.
    """
    vectors, seeds = seed_vectors(runs, OBSERVABLE)
    draws = bootstrap_draws(len(seeds))
    rows: list[dict[str, object]] = []
    for variant in [v.key for v in variants()]:
        for phenotype in PHENOTYPES:
            values = vectors[(variant, phenotype)]
            base = vectors[(BASELINE, phenotype)]
            boot = values[draws].mean(axis=1)
            boot_difference = boot - base[draws].mean(axis=1)
            rows.append(
                {
                    "variant": variant,
                    "phenotype": phenotype,
                    "n_seeds": len(seeds),
                    "mean_um": float(values.mean()),
                    "boot_ci_low_um": float(np.quantile(boot, 0.025)),
                    "boot_ci_high_um": float(np.quantile(boot, 0.975)),
                    "seed_p2_5_um": float(np.quantile(values, 0.025)),
                    "seed_p97_5_um": float(np.quantile(values, 0.975)),
                    "paired_difference_from_baseline_um": float((values - base).mean()),
                    "paired_difference_ci_low_um": float(np.quantile(boot_difference, 0.025)),
                    "paired_difference_ci_high_um": float(np.quantile(boot_difference, 0.975)),
                    "relative_change_from_baseline": float(values.mean() / base.mean() - 1.0),
                }
            )
    return pd.DataFrame(rows)


def ratio_table(runs: pd.DataFrame) -> pd.DataFrame:
    """Return the strain ratios and their shift away from the baseline.

    The confidence interval is on the **difference** between the variant ratio
    and the baseline ratio, computed from one shared seed resample, so it is a
    paired interval.
    """
    vectors, seeds = seed_vectors(runs, OBSERVABLE)
    draws = bootstrap_draws(len(seeds))

    def boot_ratio(variant: str, phenotype: str) -> np.ndarray:
        numerator = vectors[(variant, phenotype)][draws].mean(axis=1)
        denominator = vectors[(variant, REFERENCE_PHENOTYPE)][draws].mean(axis=1)
        return numerator / denominator

    def observed_ratio(variant: str, phenotype: str) -> float:
        return float(
            vectors[(variant, phenotype)].mean() / vectors[(variant, REFERENCE_PHENOTYPE)].mean()
        )

    rows: list[dict[str, object]] = []
    for variant in [v.key for v in variants()]:
        for phenotype in PHENOTYPES:
            if phenotype == REFERENCE_PHENOTYPE:
                continue
            boot = boot_ratio(variant, phenotype)
            shift = boot - boot_ratio(BASELINE, phenotype)
            rows.append(
                {
                    "variant": variant,
                    "ratio": f"{phenotype}/{REFERENCE_PHENOTYPE}",
                    "value": observed_ratio(variant, phenotype),
                    "ci_low": float(np.quantile(boot, 0.025)),
                    "ci_high": float(np.quantile(boot, 0.975)),
                    "shift_from_baseline": observed_ratio(variant, phenotype)
                    - observed_ratio(BASELINE, phenotype),
                    "shift_ci_low": float(np.quantile(shift, 0.025)),
                    "shift_ci_high": float(np.quantile(shift, 0.975)),
                    "shift_excludes_zero": bool(
                        np.quantile(shift, 0.025) > 0.0 or np.quantile(shift, 0.975) < 0.0
                    ),
                }
            )
    return pd.DataFrame(rows)


def ordering_table(runs: pd.DataFrame) -> pd.DataFrame:
    """Return whether PproA < WT < PproB survives in each variant.

    Both steps of the ordering are tested with the same paired seed resample.
    "Resolved" means the bootstrap interval on the pairwise difference excludes
    zero, so the step is not explained by seed noise alone.
    """
    vectors, seeds = seed_vectors(runs, OBSERVABLE)
    draws = bootstrap_draws(len(seeds))
    rows: list[dict[str, object]] = []
    for variant in [v.key for v in variants()]:
        means = {p: float(vectors[(variant, p)].mean()) for p in PHENOTYPES}
        row: dict[str, object] = {
            "variant": variant,
            "mean_PproA_um": means["PproA"],
            "mean_WT_um": means["WT"],
            "mean_PproB_um": means["PproB"],
            "ordering_holds": bool(means["PproA"] < means["WT"] < means["PproB"]),
        }
        for high, low in (("WT", "PproA"), ("PproB", "WT")):
            difference = vectors[(variant, high)] - vectors[(variant, low)]
            boot = vectors[(variant, high)][draws].mean(axis=1) - vectors[(variant, low)][
                draws
            ].mean(axis=1)
            label = f"{high}_minus_{low}"
            row[f"{label}_um"] = float(difference.mean())
            row[f"{label}_ci_low"] = float(np.quantile(boot, 0.025))
            row[f"{label}_ci_high"] = float(np.quantile(boot, 0.975))
            row[f"{label}_resolved"] = bool(np.quantile(boot, 0.025) > 0.0)
        row["ordering_resolved"] = bool(
            row["WT_minus_PproA_resolved"] and row["PproB_minus_WT_resolved"]
        )
        rows.append(row)
    return pd.DataFrame(rows)


def stall_diagnostic_table(runs: pd.DataFrame) -> pd.DataFrame:
    """Return stall occupancy and stall entry rate per variant and strain.

    **Neither column converges with the time step.**  The simulator draws against
    ``stall_probability`` once per time step in which the proposed step overlaps
    a disk, so halving the step roughly doubles the number of draws per contact.
    Both columns are diagnostics at ``dt = 0.0025`` s.  They must never be
    reported as a converged model output, and they must never be compared with a
    published fraction of time spent stalling.
    """
    rows: list[dict[str, object]] = []
    for (variant, phenotype), part in runs.groupby(["variant", "phenotype"]):
        row: dict[str, object] = {"variant": variant, "phenotype": phenotype, "dt_s": DT_S}
        for column in ("stall_occupancy", "stall_entry_rate_per_swim_s"):
            values = part[column].to_numpy(dtype=float)
            row[f"{column}_mean"] = float(np.nanmean(values))
            row[f"{column}_p2_5"] = float(np.nanquantile(values, 0.025))
            row[f"{column}_p97_5"] = float(np.nanquantile(values, 0.975))
        rows.append(row)
    order = {name: index for index, name in enumerate(PHENOTYPES)}
    frame = pd.DataFrame(rows)
    frame["converges_with_time_step"] = False
    return frame.sort_values(["variant", "phenotype"], key=lambda c: c.map(order).fillna(c))


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------


def diagnostic_style() -> None:
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


def _short(key: str) -> str:
    return key.split("_")[0]


def parameter_figure(parameters: pd.DataFrame) -> None:
    """Draw the two stall parameters of every variant against flagella number."""
    figure, axes = plt.subplots(1, 2, figsize=(8.6, 3.6), constrained_layout=True)
    keys = [v.key for v in variants()]
    for axis, column, label in zip(
        axes,
        ("stall_probability", "stall_mean_duration_s"),
        ("Stall probability per overlapping step", "Mean stall duration (s)"),
        strict=True,
    ):
        for offset, key in enumerate(keys):
            part = parameters[parameters.variant == key]
            for _, item in part.iterrows():
                axis.scatter(
                    offset,
                    item[column],
                    s=34,
                    color=STRAIN_COLORS[item.phenotype],
                    zorder=3,
                    linewidths=0,
                )
        axis.set(
            xticks=range(len(keys)),
            xticklabels=[_short(k) for k in keys],
            ylabel=label,
            xlabel="Variant",
        )
        axis.grid(axis="y", lw=0.3, alpha=0.4)
    handles = [
        plt.Line2D([], [], color=color, lw=0, marker="o", markersize=5, label=name)
        for name, color in STRAIN_COLORS.items()
    ]
    figure.legend(handles=handles, loc="outside lower center", ncols=3, frameon=False, fontsize=8)
    figure.suptitle(
        "The two unsourced agarose stall parameters under each variant.\n"
        "Every variant keeps the arithmetic mean of the three current values.",
        fontsize=9,
    )
    save(figure, "stall_parameter_grid")


def displacement_figure(runs: pd.DataFrame, displacement: pd.DataFrame) -> None:
    """Draw the mean net displacement of every variant, with the baseline marked."""
    vectors, _ = seed_vectors(runs, OBSERVABLE)
    keys = [v.key for v in variants()]
    figure, axis = plt.subplots(figsize=(8.6, 4.2), constrained_layout=True)
    for offset, key in enumerate(keys):
        for index, phenotype in enumerate(PHENOTYPES):
            values = vectors[(key, phenotype)]
            x = offset + (index - 1) * 0.26
            axis.scatter(
                np.full(len(values), x),
                values,
                s=2.5,
                color=STRAIN_COLORS[phenotype],
                alpha=0.22,
                linewidths=0,
            )
            row = displacement.query("variant == @key and phenotype == @phenotype").iloc[0]
            axis.errorbar(
                x,
                row.mean_um,
                yerr=[[row.mean_um - row.boot_ci_low_um], [row.boot_ci_high_um - row.mean_um]],
                fmt="o",
                ms=4,
                color="black",
                lw=1.0,
                zorder=4,
            )
    for phenotype in PHENOTYPES:
        base = displacement.query("variant == @BASELINE and phenotype == @phenotype").iloc[0]
        axis.axhline(base.mean_um, color=STRAIN_COLORS[phenotype], ls=":", lw=0.8)
    axis.set(
        xticks=range(len(keys)),
        xticklabels=[_short(k) for k in keys],
        xlabel="Variant",
        ylabel="Mean net displacement per seed (µm)",
    )
    handles = [
        plt.Line2D([], [], color=color, lw=0, marker="o", markersize=5, label=name)
        for name, color in STRAIN_COLORS.items()
    ]
    figure.legend(handles=handles, loc="outside lower center", ncols=3, frameon=False, fontsize=8)
    figure.suptitle(
        f"Agarose net displacement, 100 shared seeds, 26 cells, 20 s, dt = {DT_S} s.\n"
        "Dotted lines mark the baseline mean. Bars are bootstrap intervals on the mean.",
        fontsize=9,
    )
    save(figure, "variant_net_displacement")


def ratio_figure(ratios: pd.DataFrame) -> None:
    """Draw each variant's strain ratio and its paired shift from the baseline."""
    keys = [v.key for v in variants()]
    figure, axes = plt.subplots(1, 2, figsize=(8.6, 3.8), constrained_layout=True)
    for axis, name in zip(axes, ("WT/PproA", "PproB/PproA"), strict=True):
        part = ratios.query("ratio == @name").set_index("variant").loc[keys]
        axis.errorbar(
            range(len(keys)),
            part.value,
            yerr=[part.value - part.ci_low, part.ci_high - part.value],
            fmt="o",
            ms=4,
            color="black",
            lw=1.0,
        )
        axis.axhline(float(part.loc[BASELINE, "value"]), color="grey", ls=":", lw=0.9)
        axis.axhline(1.0, color="grey", lw=0.5)
        axis.set(
            xticks=range(len(keys)),
            xticklabels=[_short(k) for k in keys],
            xlabel="Variant",
            ylabel=f"{name} net displacement ratio",
            title=name,
        )
    figure.suptitle(
        "Strain ratios in agarose. Dotted line is the baseline ratio; "
        "bars are bootstrap intervals on the ratio.",
        fontsize=9,
    )
    save(figure, "variant_strain_ratios")


def stall_figure(stalls: pd.DataFrame) -> None:
    """Draw the two stall diagnostics, labelled as non-converged."""
    keys = [v.key for v in variants()]
    figure, axes = plt.subplots(1, 2, figsize=(8.6, 3.8), constrained_layout=True)
    for axis, column, label in zip(
        axes,
        ("stall_occupancy_mean", "stall_entry_rate_per_swim_s_mean"),
        ("Fraction of motile-cell time steps stalled", "Stall entries per second of swimming"),
        strict=True,
    ):
        for offset, key in enumerate(keys):
            for phenotype in PHENOTYPES:
                match = (stalls.variant == key) & (stalls.phenotype == phenotype)
                value = float(stalls.loc[match, column].iloc[0])
                axis.scatter(
                    offset, value, s=34, color=STRAIN_COLORS[phenotype], zorder=3, linewidths=0
                )
        axis.set(
            xticks=range(len(keys)),
            xticklabels=[_short(k) for k in keys],
            xlabel="Variant",
            ylabel=label,
        )
        axis.grid(axis="y", lw=0.3, alpha=0.4)
    handles = [
        plt.Line2D([], [], color=color, lw=0, marker="o", markersize=5, label=name)
        for name, color in STRAIN_COLORS.items()
    ]
    figure.legend(handles=handles, loc="outside lower center", ncols=3, frameon=False, fontsize=8)
    figure.suptitle(
        f"Stall diagnostics at dt = {DT_S} s. Neither quantity converges with the time step:\n"
        "the stall draw is made once per time step of obstacle overlap.\n"
        "Do not report either as a model output.",
        fontsize=9,
    )
    save(figure, "variant_stall_diagnostics")


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
    probability, duration = common.current_stall_values()
    record = {
        "schema_version": "1.0.0",
        "record_type": "model_variant_comparison",
        "record_id": "motility_stall_parameter_comparison",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "analyses/motility_stall_parameter_comparison/compare_stall_variants.py",
        ],
        "inputs": [
            artifact(Path(__file__).resolve()),
            artifact(Path(__file__).resolve().parent / "common.py"),
            artifact(common.BASE_TABLE),
            artifact(common.HOOK_COUNTS),
            artifact(common.MEASURED),
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
            "variants": [
                {
                    "key": v.key,
                    "label": v.label,
                    "description": v.description,
                    "probability_exponent": (
                        grognot_exponent()
                        if v.key == "G_grognot_probability"
                        else v.probability_exponent
                    ),
                    "duration_exponent": v.duration_exponent,
                    "duration_override_s": v.duration_override_s,
                }
                for v in variants()
            ],
            "normalisation": (
                "Every scaled column is renormalised so its arithmetic mean over the three "
                "strains equals the mean of the three current values."
            ),
            "current_stall_probability": probability,
            "current_stall_mean_duration_s": duration,
            "current_mean_stall_probability": float(np.mean(list(probability.values()))),
            "current_mean_stall_duration_s": float(np.mean(list(duration.values()))),
            "mean_hooks_per_cell": common.mean_hooks(),
            "grognot_exponent": grognot_exponent(),
            "grognot_stall_frequency_ratio": GROGNOT_STALL_FREQUENCY_RATIO,
            "grognot_stall_frequency_ratio_sd": GROGNOT_STALL_FREQUENCY_RATIO_SD,
            "datta_mean_dwell_s": DATTA_MEAN_DWELL_S,
            "dt_s": DT_S,
            "observable": "mean net displacement per seed (um)",
            "reference_phenotype": REFERENCE_PHENOTYPE,
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "seed_plan_check": seed_plan,
        },
        "random_seeds": {
            "population": f"{SEEDS[0]}-{SEEDS[-1]}",
            "starting_positions": "population seed + 1",
            "agarose_obstacles": "population seed + 300",
            "bootstrap": common.BOOTSTRAP_SEED,
        },
        "limitations": [
            (
                "Neither stall parameter has a source. The grid tests how an unsourced "
                "effect is distributed between strains; it cannot make the effect sourced."
            ),
            (
                "Stall occupancy and stall entry rate are evaluated per time step of "
                "obstacle overlap and do not converge with the time step. They are "
                "diagnostics at dt = 0.0025 s, never model outputs."
            ),
            (
                "Grognot et al. 2023 measured a second flagellar system in Vibrio "
                "alginolyticus, not a flagella count in Salmonella. Mapping their 1.7-fold "
                "stall-frequency ratio onto our hook numbers is an assumption made here."
            ),
            (
                "Datta et al. 2025 measured Pseudomonas putida in 0.25 % agar and report a "
                "power-law dwell time. The model draws an exponential stall time, so the "
                "anchor fixes the mean and nothing else."
            ),
            (
                "All variants share the seed set and therefore the starting positions, the "
                "motile mask and the obstacle field. They do not share the later random "
                "draws. The pairing removes the initial-condition variance, not all "
                "stochastic variation."
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
    parser.add_argument("--processes", type=int, default=None)
    args = parser.parse_args()

    diagnostic_style()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    seed_plan = common.check_seed_plan_matches_manuscript()

    parameters = common.variant_parameter_summary()
    parameters.to_csv(OUTPUT / "variant_parameters.csv", index=False)

    frames = []
    for variant in variants():
        path = variant_table_path(variant)
        frames.append(
            cached_condition(
                variant.key,
                path,
                "agarose",
                True,
                force=args.force,
                processes=args.processes,
            ).assign(variant=variant.key, condition=variant.key)
        )
    runs = pd.concat(frames, ignore_index=True)
    runs.to_csv(OUTPUT / "variant_runs.csv", index=False)

    displacement = displacement_table(runs)
    displacement.to_csv(OUTPUT / "variant_net_displacement.csv", index=False)
    ratios = ratio_table(runs)
    ratios.to_csv(OUTPUT / "variant_strain_ratios.csv", index=False)
    ordering = ordering_table(runs)
    ordering.to_csv(OUTPUT / "variant_ordering.csv", index=False)
    stalls = stall_diagnostic_table(runs)
    stalls.to_csv(OUTPUT / "variant_stall_diagnostics.csv", index=False)

    if not args.skip_figures:
        parameter_figure(parameters)
        displacement_figure(runs, displacement)
        ratio_figure(ratios)
        stall_figure(stalls)

    outputs = sorted(path for path in OUTPUT.iterdir() if path.is_file())
    write_record(outputs, seed_plan)

    with pd.option_context("display.width", 240, "display.precision", 4):
        print("\n== variant parameters (agarose) ==")
        print(parameters.to_string(index=False))
        print("\n== net displacement ==")
        print(
            displacement[
                [
                    "variant",
                    "phenotype",
                    "mean_um",
                    "seed_p2_5_um",
                    "seed_p97_5_um",
                    "paired_difference_from_baseline_um",
                    "paired_difference_ci_low_um",
                    "paired_difference_ci_high_um",
                ]
            ].to_string(index=False)
        )
        print("\n== strain ratios ==")
        print(ratios.to_string(index=False))
        print("\n== ordering PproA < WT < PproB ==")
        print(
            ordering[
                [
                    "variant",
                    "mean_PproA_um",
                    "mean_WT_um",
                    "mean_PproB_um",
                    "ordering_holds",
                    "ordering_resolved",
                ]
            ].to_string(index=False)
        )
        print(f"\n== stall diagnostics at dt = {DT_S} s, not converged ==")
        print(
            stalls[
                [
                    "variant",
                    "phenotype",
                    "stall_occupancy_mean",
                    "stall_entry_rate_per_swim_s_mean",
                ]
            ].to_string(index=False)
        )
    print(f"\noutputs: {OUTPUT.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
