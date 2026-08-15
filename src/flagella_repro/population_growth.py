from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from flagella_repro.theme import (
    DENSITY_MARKER_SIZE,
    KEY_SWATCH,
    PALETTE,
    PALETTE_PATH,
    POINT_MARKER_SIZE,
    SUMMARY_INK,
    TICK_FONT_PT,
    apply_publication_style,
    get_strain_style,
    marker_edge,
    panel_figsize,
    save_figure,
)

# Guide and grid inks come from the shared palette, so no panel carries a colour
# literal of its own.
REFERENCE_INK: str = PALETTE["neutral"]["reference"]
GRID_INK: str = PALETTE["neutral"]["grid"]
# Half-widths of the two data layers.  The curve cloud is wider than the day
# means, so the marks that carry the statistics stay readable on top of it.
CURVE_CLOUD_HALF_WIDTH = 0.28
DAY_MEAN_HALF_WIDTH = 0.12
CURVE_CLOUD_ALPHA = 0.35


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact(root: Path, path: Path, *, rows: int | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {
        "relative_path": path.relative_to(root).as_posix(),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }
    if rows is not None:
        item["rows"] = rows
    return item


def _benjamini_hochberg(values: np.ndarray) -> np.ndarray:
    output = np.full(values.shape, np.nan, dtype=float)
    finite_mask = np.isfinite(values)
    finite = values[finite_mask]
    if not finite.size:
        return output
    order = np.argsort(finite)
    ranked = finite[order]
    adjusted = ranked * finite.size / np.arange(1, finite.size + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    restored = np.empty_like(adjusted)
    restored[order] = np.clip(adjusted, 0, 1)
    output[finite_mask] = restored
    return output


def _bootstrap_ci(values: np.ndarray, *, seed: int, draws: int) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 1:
        return float(values[0]), float(values[0])
    rng = np.random.default_rng(seed)
    boot = rng.choice(values, size=(draws, values.size), replace=True).mean(axis=1)
    low, high = np.quantile(boot, [0.025, 0.975])
    return float(low), float(high)


def _t_ci(values: np.ndarray) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 2:
        return math.nan, math.nan
    interval = stats.t.interval(
        0.95,
        df=values.size - 1,
        loc=float(values.mean()),
        scale=float(stats.sem(values)),
    )
    return float(interval[0]), float(interval[1])


def _prepare(input_table: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    curves = pd.read_csv(input_table, low_memory=False)
    if config["value_column"] == "mu_from_growth_rate_k":
        curves["growth_rate_1_h"] = pd.to_numeric(
            curves["growth_rate_k"], errors="coerce"
        ) * 60
    else:
        curves["growth_rate_1_h"] = pd.to_numeric(
            curves[config["value_column"]], errors="coerce"
        )
    curves = curves[
        curves["strain"].astype(str).isin(config["strain_order"])
        & np.isfinite(curves["growth_rate_1_h"])
    ].copy()
    group_columns = ["experiment_day", "strain"]
    if "date" in curves:
        group_columns.insert(0, "date")
    days = (
        curves.groupby(group_columns, as_index=False)
        .agg(growth_rate_1_h=("growth_rate_1_h", "mean"), n_technical=("growth_rate_1_h", "size"))
    )
    reference = str(config["reference_strain"])
    reference_by_day = days.loc[
        days["strain"].astype(str) == reference,
        ["experiment_day", "growth_rate_1_h"],
    ].rename(columns={"growth_rate_1_h": "reference_growth_rate_1_h"})
    if reference_by_day["experiment_day"].duplicated().any():
        raise ValueError("reference strain has more than one mean per experiment day")
    if len(reference_by_day) != days["experiment_day"].nunique():
        raise ValueError("reference strain is missing from one or more experiment days")
    days = days.merge(reference_by_day, on="experiment_day", validate="many_to_one")
    days["relative_growth_rate"] = (
        days["growth_rate_1_h"] / days["reference_growth_rate_1_h"]
    )
    curves = curves.merge(reference_by_day, on="experiment_day", validate="many_to_one")
    curves["relative_growth_rate"] = (
        curves["growth_rate_1_h"] / curves["reference_growth_rate_1_h"]
    )
    return curves, days


def _summaries(days: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    seed = int(config["bootstrap_seed"])
    for index, strain in enumerate(config["strain_order"]):
        values = days.loc[
            days["strain"].astype(str) == strain, "relative_growth_rate"
        ].to_numpy()
        low, high = _bootstrap_ci(
            values,
            seed=seed + index,
            draws=int(config["bootstrap_draws"]),
        )
        rows.append(
            {
                "strain": strain,
                "mean_relative_growth_rate": float(np.mean(values)),
                "ci95_low": low,
                "ci95_high": high,
                "n_biological_replicates": int(values.size),
            }
        )
    return pd.DataFrame(rows)


def _paired_statistics(days: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    reference = str(config["reference_strain"])
    ref = days[days["strain"].astype(str) == reference][
        ["experiment_day", "relative_growth_rate"]
    ].rename(columns={"relative_growth_rate": "reference_relative_growth_rate"})
    rows: list[dict[str, Any]] = []
    for strain in config["strain_order"]:
        if strain == reference:
            continue
        current = days[days["strain"].astype(str) == strain][
            ["experiment_day", "relative_growth_rate"]
        ].rename(columns={"relative_growth_rate": "condition_relative_growth_rate"})
        paired = ref.merge(current, on="experiment_day", how="inner").dropna()
        if len(paired) >= 2:
            result = stats.ttest_rel(
                paired["condition_relative_growth_rate"],
                paired["reference_relative_growth_rate"],
            )
            p_value = float(result.pvalue)
        else:
            p_value = math.nan
        difference = (
            paired["condition_relative_growth_rate"]
            - paired["reference_relative_growth_rate"]
        )
        ci_low, ci_high = _t_ci(difference.to_numpy(dtype=float))
        rows.append(
            {
                "reference_strain": reference,
                "strain": strain,
                "n_biological_pairs": len(paired),
                "effect_metric": "paired difference in growth rate relative to same-day reference",
                "mean_paired_difference": float(difference.mean()),
                "ci95_low": ci_low,
                "ci95_high": ci_high,
                "p_value_paired_t": p_value,
            }
        )
    table = pd.DataFrame(rows)
    table["q_value_bh"] = _benjamini_hochberg(
        table["p_value_paired_t"].to_numpy(dtype=float)
    )
    return table


def _plot(
    curves: pd.DataFrame,
    days: pd.DataFrame,
    summaries: pd.DataFrame,
    config: dict[str, Any],
    output_stem: Path,
) -> None:
    apply_publication_style()
    order = list(config["strain_order"])
    positions = {strain: index for index, strain in enumerate(order)}
    colors = {strain: get_strain_style(strain)["color"] for strain in order}
    # The panel is drawn at the exact size of its slot in the figure assembly,
    # so the assembler scales it by 1.0 and a requested point size is the same
    # point size on the printed page.
    figure_id = f"Figure_{int(config['figure_number'])}"
    figure, axis = plt.subplots(
        figsize=panel_figsize(figure_id, str(config["panel_label"])),
        constrained_layout=True,
    )

    # Three layers, the same three every panel of this collection uses.  Every
    # condition, the reference included, is drawn the same way: each individual
    # growth curve divided by its own day's reference mean is the descriptive
    # cloud, the day means are the marks that carry the statistics, and the
    # mean with its bootstrap interval is the summary.  The reference therefore
    # scatters around 1.0 like every other condition instead of collapsing onto
    # the guide line.
    jitter_seed = int(config["bootstrap_seed"])
    for index, strain in enumerate(order):
        fill = colors[strain]
        edge, edge_width = marker_edge(fill)
        style = get_strain_style(strain)

        cloud = curves.loc[curves["strain"].astype(str) == strain].sort_values(
            ["experiment_day", "curve_id"]
        )
        rng = np.random.default_rng(jitter_seed + index)
        cloud_offsets = rng.uniform(-CURVE_CLOUD_HALF_WIDTH, CURVE_CLOUD_HALF_WIDTH, len(cloud))
        axis.scatter(
            index + cloud_offsets,
            cloud["relative_growth_rate"],
            s=DENSITY_MARKER_SIZE,
            alpha=CURVE_CLOUD_ALPHA,
            color=fill,
            marker=style["marker"],
            edgecolors=edge,
            linewidths=edge_width,
            zorder=2,
        )

        replicate = days.loc[days["strain"].astype(str) == strain].sort_values(
            "experiment_day"
        )
        day_offsets = np.linspace(-DAY_MEAN_HALF_WIDTH, DAY_MEAN_HALF_WIDTH, len(replicate))
        axis.scatter(
            index + day_offsets,
            replicate["relative_growth_rate"],
            s=POINT_MARKER_SIZE,
            color=fill,
            marker=style["marker"],
            edgecolors=edge,
            linewidths=edge_width,
            zorder=3,
        )

    summary_edge, summary_edge_width = marker_edge(SUMMARY_INK)
    for row in summaries.itertuples(index=False):
        x = positions[row.strain]
        axis.errorbar(
            x,
            row.mean_relative_growth_rate,
            yerr=[
                [row.mean_relative_growth_rate - row.ci95_low],
                [row.ci95_high - row.mean_relative_growth_rate],
            ],
            marker="D",
            markersize=np.sqrt(POINT_MARKER_SIZE),
            markerfacecolor=SUMMARY_INK,
            markeredgecolor=summary_edge,
            markeredgewidth=summary_edge_width,
            color=SUMMARY_INK,
            capsize=2,
            linewidth=0.8,
            zorder=4,
        )

    rotation = float(config.get("x_label_rotation", 45))
    axis.set_xticks(range(len(order)), [config["labels"][item] for item in order])
    axis.tick_params(axis="x", labelrotation=rotation)
    # A tilted label hangs from its right end so it points at its own tick; an
    # upright label sits centred under it.
    alignment = "right" if rotation else "center"
    for tick in axis.get_xticklabels():
        tick.set_horizontalalignment(alignment)
    axis.axhline(1.0, color=REFERENCE_INK, linewidth=0.65, linestyle=(0, (3, 2)), zorder=0)
    axis.set_ylabel("Growth rate relative to\nsame-day reference")
    axis.set_xlabel(config.get("x_axis_label", ""))
    if config.get("y_limits"):
        axis.set_ylim(config["y_limits"])
    axis.grid(axis="y", color=GRID_INK, linewidth=0.4, alpha=0.6)
    axis.spines[["top", "right"]].set_visible(False)
    # The key names the sampling unit of each layer, so nobody reads the many
    # curves as the sample size.  It sits under the axes because the panel is
    # only 55 mm wide and would otherwise lose data area.
    figure.legend(
        handles=[
            Line2D(
                [], [], linestyle="none", marker="o",
                markersize=np.sqrt(DENSITY_MARKER_SIZE), color=KEY_SWATCH,
                markeredgewidth=0, label="One growth curve (descriptive)",
            ),
            Line2D(
                [], [], linestyle="none", marker="o",
                markersize=np.sqrt(POINT_MARKER_SIZE), color=KEY_SWATCH,
                markeredgewidth=0, label="Independent experiment day",
            ),
            Line2D(
                [], [], linestyle="none", marker="D",
                markersize=np.sqrt(POINT_MARKER_SIZE), color=SUMMARY_INK,
                markeredgewidth=0, label="Mean ± 95% CI",
            ),
        ],
        frameon=False,
        loc="outside lower center",
        ncols=1,
        fontsize=TICK_FONT_PT,
        handlelength=1.2,
        handletextpad=0.5,
        labelspacing=0.25,
        borderpad=0.0,
        borderaxespad=0.0,
    )
    save_figure(figure, output_stem)


def reproduce_population_panel(config_path: Path) -> None:
    config_path = config_path.resolve(strict=True)
    root = config_path.parents[4]
    config = json.loads(config_path.read_text(encoding="utf-8"))
    panel_id = config["panel_id"]
    input_table = root / config["input_table"]
    curves, days = _prepare(input_table, config)
    summaries = _summaries(days, config)
    statistics = _paired_statistics(days, config)

    figure_name = f"Figure_{int(config['figure_number'])}"
    panel_label = str(config["panel_label"])
    source_dir = root / "build" / "source_data" / figure_name / panel_label
    source_dir.mkdir(parents=True, exist_ok=True)
    source_table = source_dir / f"{panel_id}_source_data.csv"
    statistics_dir = root / "build" / "statistics" / figure_name / panel_label
    statistics_dir.mkdir(parents=True, exist_ok=True)
    statistics_table = statistics_dir / f"{panel_id}_statistics.csv"
    source_columns = [
        "plot_component",
        "date",
        "experiment_day",
        "strain",
        "tech_rep",
        "curve_id",
        "growth_rate_1_h",
        "reference_growth_rate_1_h",
        "relative_growth_rate",
        "ci95_low",
        "ci95_high",
        "n_technical",
        "n_biological_replicates",
    ]
    technical = curves.assign(
        plot_component="technical_curve",
        ci95_low=np.nan,
        ci95_high=np.nan,
        n_technical=1,
        n_biological_replicates=np.nan,
    ).reindex(columns=source_columns)
    biological = days.assign(
        plot_component="biological_replicate_mean",
        tech_rep="",
        curve_id="",
        ci95_low=np.nan,
        ci95_high=np.nan,
        n_biological_replicates=np.nan,
    ).reindex(columns=source_columns)
    summary = summaries.rename(
        columns={"mean_relative_growth_rate": "relative_growth_rate"}
    ).assign(
        plot_component="summary_mean",
        date="",
        experiment_day="",
        tech_rep="",
        curve_id="",
        n_technical=np.nan,
        growth_rate_1_h=np.nan,
        reference_growth_rate_1_h=np.nan,
    ).reindex(columns=source_columns)
    source_rows = pd.concat([technical, biological, summary], ignore_index=True)
    source_rows.to_csv(source_table, index=False)
    statistics.to_csv(statistics_table, index=False)

    output_stem = root / "build" / "panels" / figure_name / panel_label / panel_id
    _plot(curves, days, summaries, config, output_stem)
    output_paths = [output_stem.with_suffix(ext) for ext in (".svg", ".pdf", ".png")]
    provenance = {
        "schema_version": "1.0.0",
        "panel_id": panel_id,
        "status": "partial_reproduction",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [sys.executable.rsplit("/", 1)[-1], config["entry_script"]],
        "inputs": [
            _artifact(root, config_path),
            _artifact(root, Path(__file__).resolve()),
            _artifact(root, root / config["entry_script"]),
            _artifact(root, root / "src/flagella_repro/theme.py"),
            _artifact(root, PALETTE_PATH),
            _artifact(root, input_table, rows=len(curves)),
        ],
        "outputs": [
            _artifact(root, source_table, rows=len(source_rows)),
            _artifact(root, statistics_table, rows=len(statistics)),
            *[_artifact(root, path) for path in output_paths],
        ],
        "software": {
            "python": ".".join(map(str, sys.version_info[:3])),
            "matplotlib": matplotlib.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "parameters": {
            "biological_unit": "experiment_day",
            "technical_unit": "plate-reader curve",
            "normalization": (
                "every observation, reference included, divided by the same-day "
                "reference-strain mean"
            ),
            "curve_points_role": "descriptive within-day distribution",
            "statistical_test": "paired two-sided t-test by experiment day on normalized effect",
            "inferential_unit": "experiment_day",
            "multiple_testing": "Benjamini-Hochberg within panel",
            "bootstrap_draws": config["bootstrap_draws"],
        },
        "random_seeds": {
            "bootstrap": config["bootstrap_seed"],
            "curve_cloud_jitter": config["bootstrap_seed"],
        },
        "limitations": [
            "The canonical run starts from migrated fitted growth-rate tables, "
            "not raw plate-reader workbooks.",
            "The July multi-panel placement and crop have not yet passed visual regression.",
        ],
    }
    provenance_path = (
        root / config["analysis_dir"] / config["panel_dir"] / "metadata" / "provenance.json"
    )
    provenance_text = json.dumps(provenance, indent=2, sort_keys=True) + "\n"
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(provenance_text, encoding="utf-8")
