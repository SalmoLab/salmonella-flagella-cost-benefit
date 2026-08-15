"""Render a current single-cell panel from its compact migrated table."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy import stats

from flagella_repro.theme import (
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

# The guide ink comes from the shared palette, so this file carries no colour
# literal of its own.
REFERENCE_INK: str = PALETTE["neutral"]["reference"]
VIOLIN_ALPHA = 0.72
VIOLIN_LINE_WIDTH = 0.45
# The two replicate marks sit far enough apart to clear the summary mark that
# lands between them.  At 0.075 they hid behind it whenever the replicates
# agreed, which is exactly when a reader most wants to see both.
REPLICATE_HALF_WIDTH = 0.14
MEAN_BAR_HALF_WIDTH = 0.20


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact(path: Path, root: Path, rows: int | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {
        "relative_path": path.relative_to(root).as_posix(),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }
    if rows is not None:
        item["rows"] = rows
    return item


def style() -> None:
    apply_publication_style()


def violin(ax: plt.Axes, frame: pd.DataFrame, config: dict[str, Any]) -> None:
    order = config["strain_order"]
    palette = {strain: get_strain_style(strain)["color"] for strain in order}
    sns.violinplot(
        data=frame,
        x="strain",
        y=config["value_column"],
        order=order,
        palette=palette,
        hue="strain",
        hue_order=order,
        legend=False,
        cut=0,
        density_norm="width",
        inner=None,
        bw_adjust=1.5,
        linewidth=VIOLIN_LINE_WIDTH,
        saturation=1,
        ax=ax,
    )
    # A violin keeps its outline inside its own colour family: the fill itself,
    # or a darkened version of it when the fill is too light to show an edge.
    # No violin carries a dark rim that competes with the data.
    for collection, strain in zip(ax.collections, order, strict=True):
        collection.set_alpha(VIOLIN_ALPHA)
        fill = palette[strain]
        edge, _width = marker_edge(fill)
        collection.set_edgecolor(fill if edge == "none" else edge)
        collection.set_linewidth(VIOLIN_LINE_WIDTH)


def add_key(fig: plt.Figure, handles: list[Any], ncols: int = 1) -> None:
    """Place the plotting key under the axes.

    The panels are 55-84 mm wide.  Inside the axes the key would cover the
    violins, so it sits below them where it costs only a few text lines.
    """
    fig.legend(
        handles=handles,
        frameon=False,
        loc="outside lower center",
        ncols=ncols,
        fontsize=TICK_FONT_PT,
        handlelength=1.2,
        handletextpad=0.5,
        labelspacing=0.25,
        columnspacing=1.2,
        borderpad=0.0,
        borderaxespad=0.0,
    )


def render_main(
    frame: pd.DataFrame,
    means: pd.DataFrame,
    config: dict[str, Any],
    figsize: tuple[float, float],
) -> tuple[plt.Figure, pd.DataFrame]:
    fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
    violin(ax, frame, config)
    summary = (
        frame.groupby("strain", sort=False)["relative_growth_rate"]
        .agg([("mean", "mean"), ("median", "median"), ("n_cells", "size")])
        .reindex(config["strain_order"])
        .reset_index()
    )
    summary_edge, summary_edge_width = marker_edge(SUMMARY_INK)
    for x_position, strain in enumerate(config["strain_order"]):
        replicate_rows = means.loc[means["strain"] == strain].sort_values("replicate")
        offsets = (
            [-REPLICATE_HALF_WIDTH, REPLICATE_HALF_WIDTH]
            if len(replicate_rows) == 2
            else [0.0] * len(replicate_rows)
        )
        style_for_strain = get_strain_style(strain)
        point_edge, point_edge_width = marker_edge(style_for_strain["color"])
        ax.scatter(
            [x_position + offset for offset in offsets],
            replicate_rows["relative_growth_rate"],
            s=POINT_MARKER_SIZE,
            color=style_for_strain["color"],
            marker=style_for_strain["marker"],
            edgecolor=point_edge,
            linewidth=point_edge_width,
            zorder=6,
            clip_on=False,
        )
        values = replicate_rows["relative_growth_rate"].to_numpy(dtype=float)
        mean = float(np.mean(values))
        if len(values) >= 2:
            standard_error = float(stats.sem(values))
            if np.isclose(standard_error, 0.0):
                low = high = mean
            else:
                low, high = stats.t.interval(
                    0.95,
                    len(values) - 1,
                    loc=mean,
                    scale=standard_error,
                )
            ax.errorbar(
                x_position,
                mean,
                yerr=[[mean - low], [high - mean]],
                marker="D",
                markersize=np.sqrt(POINT_MARKER_SIZE),
                markerfacecolor=SUMMARY_INK,
                markeredgecolor=summary_edge,
                markeredgewidth=summary_edge_width,
                color=SUMMARY_INK,
                capsize=2,
                linewidth=0.7,
                zorder=7,
            )
    ax.set_xticks(range(len(config["strain_labels"])), config["strain_labels"], rotation=28)
    ax.set_xlabel("")
    ax.axhline(1.0, color=REFERENCE_INK, linewidth=0.65, linestyle=(0, (3, 2)), zorder=0)
    ax.set_ylabel(config["y_label"])
    ax.set_ylim(config["y_limits"])
    # The swatch stands for the concept "cell distribution", not for a strain,
    # so it takes the neutral key swatch. Borrowing whichever strain happens to
    # sit last in the order gave the same concept a different colour in every
    # figure.
    add_key(
        fig,
        [
            Patch(
                facecolor=KEY_SWATCH,
                alpha=VIOLIN_ALPHA,
                label="Cell distribution (descriptive)",
            ),
            Line2D(
                [], [], marker="o", linestyle="none", color=KEY_SWATCH,
                markersize=np.sqrt(POINT_MARKER_SIZE), markeredgewidth=0,
                label="Independent replicate mean",
            ),
            Line2D(
                [], [], marker="D", linestyle="none", color=SUMMARY_INK,
                markersize=np.sqrt(POINT_MARKER_SIZE), markeredgewidth=0,
                label="Mean ± 95% CI",
            ),
        ],
    )
    sns.despine(ax=ax)
    return fig, summary


def render_supplement(
    frame: pd.DataFrame,
    means: pd.DataFrame,
    config: dict[str, Any],
    figsize: tuple[float, float],
) -> tuple[plt.Figure, pd.DataFrame]:
    fig, axes = plt.subplots(1, 2, figsize=figsize, sharey=True, constrained_layout=True)
    summaries: list[pd.DataFrame] = []
    value = config["value_column"]
    mean_column = f"mean_{value}"
    for ax, subset, title in zip(
        axes, config["subset_order"], config["subset_titles"], strict=True
    ):
        current = frame.loc[frame["_subset"] == subset]
        violin(ax, current, config)
        summary = (
            current.groupby("strain", sort=False)[value]
            .agg([("mean", "mean"), ("median", "median"), ("n_cells", "size")])
            .reindex(config["strain_order"])
            .reset_index()
        )
        summary.insert(0, "subset", subset)
        summaries.append(summary)
        # The same three layers Figure 2C uses: cells describe the spread, the
        # independent replicate means are the marks a reader may count, and the
        # bar is the mean of those replicate means.  This panel runs no test, so
        # the summary stays a bar rather than an interval.
        subset_means = means.loc[means["_subset"] == subset]
        for x_position, strain in enumerate(config["strain_order"]):
            replicate_rows = subset_means.loc[subset_means["strain"] == strain].sort_values(
                "replicate"
            )
            offsets = (
                [-REPLICATE_HALF_WIDTH, REPLICATE_HALF_WIDTH]
                if len(replicate_rows) == 2
                else [0.0] * len(replicate_rows)
            )
            style_for_strain = get_strain_style(strain)
            point_edge, point_edge_width = marker_edge(style_for_strain["color"])
            ax.scatter(
                [x_position + offset for offset in offsets],
                replicate_rows[mean_column],
                s=POINT_MARKER_SIZE,
                color=style_for_strain["color"],
                marker=style_for_strain["marker"],
                edgecolor=point_edge,
                linewidth=point_edge_width,
                zorder=6,
                clip_on=False,
            )
            ax.hlines(
                float(replicate_rows[mean_column].mean()),
                x_position - MEAN_BAR_HALF_WIDTH,
                x_position + MEAN_BAR_HALF_WIDTH,
                color=SUMMARY_INK,
                lw=1.0,
                zorder=7,
            )
        ax.axhline(1.0, color=REFERENCE_INK, lw=0.7, ls=(0, (3, 2)), zorder=0)
        # Each subplot is only ~40 mm wide.  The lineage class names the
        # subplot; the analysis window is a method statement and lives in the
        # figure legend.
        ax.set_title(title)
        ax.set_xticks(range(len(config["strain_labels"])), config["strain_labels"], rotation=28)
        ax.set_xlabel("")
        ax.set_ylabel(config["y_label"] if ax is axes[0] else "")
        ax.set_ylim(config["y_limits"])
        sns.despine(ax=ax)
    add_key(
        fig,
        [
            Patch(
                facecolor=KEY_SWATCH,
                alpha=VIOLIN_ALPHA,
                label="Cell distribution (descriptive)",
            ),
            Line2D(
                [], [], marker="o", linestyle="none", color=KEY_SWATCH,
                markersize=np.sqrt(POINT_MARKER_SIZE), markeredgewidth=0,
                label="Independent replicate mean",
            ),
            Line2D([], [], color=SUMMARY_INK, lw=1.0, label="Mean of replicate means"),
        ],
        ncols=2,
    )
    return fig, pd.concat(summaries, ignore_index=True)


def effect_statistics(means: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    reference = config["normalization_reference"]
    ref = means.loc[means["strain"] == reference, ["replicate", "relative_growth_rate"]]
    ref = ref.rename(columns={"relative_growth_rate": "reference_relative_growth_rate"})
    rows: list[dict[str, Any]] = []
    for strain in config["strain_order"]:
        if strain == reference:
            continue
        current = means.loc[
            means["strain"] == strain, ["replicate", "relative_growth_rate"]
        ].rename(columns={"relative_growth_rate": "condition_relative_growth_rate"})
        paired = ref.merge(current, on="replicate", validate="one_to_one")
        differences = (
            paired["condition_relative_growth_rate"]
            - paired["reference_relative_growth_rate"]
        ).to_numpy(dtype=float)
        mean = float(np.mean(differences))
        if len(differences) >= 2:
            low, high = stats.t.interval(
                0.95,
                len(differences) - 1,
                loc=mean,
                scale=stats.sem(differences),
            )
            p_value = float(stats.ttest_rel(
                paired["condition_relative_growth_rate"],
                paired["reference_relative_growth_rate"],
            ).pvalue)
        else:
            low = high = p_value = np.nan
        rows.append(
            {
                "reference_strain": reference,
                "strain": strain,
                "n_biological_pairs": len(paired),
                "effect_metric": "paired difference in growth rate relative to replicate reference",
                "mean_paired_difference": mean,
                "ci95_low": low,
                "ci95_high": high,
                "p_value_paired_t": p_value,
                "inferential_unit": "independent mother-machine experiment/replicate",
            }
        )
    output = pd.DataFrame(rows)
    values = output["p_value_paired_t"].to_numpy(dtype=float)
    order = np.argsort(values)
    ranked = values[order]
    adjusted = np.minimum.accumulate(
        (ranked * len(ranked) / np.arange(1, len(ranked) + 1))[::-1]
    )[::-1]
    restored = np.empty_like(adjusted)
    restored[order] = np.minimum(adjusted, 1.0)
    output["q_value_bh"] = restored
    return output


def software_versions() -> dict[str, str]:
    packages = ("matplotlib", "pandas", "pyarrow", "seaborn")
    versions = {name: importlib.metadata.version(name) for name in packages}
    return {"python": platform.python_version(), **versions}


def render(config_path: Path) -> None:
    collection = Path(__file__).resolve().parents[4]
    config = json.loads(config_path.read_text())
    panel_id = config["panel_id"]
    parquet = collection / config["processed_parquet"]
    means_path = collection / config["replicate_means_csv"]
    source_data = collection / config["source_data_csv_gz"]
    inventory = collection / config["migration_inventory"]
    frame = pd.read_parquet(parquet)
    means = pd.read_csv(means_path)
    if len(frame) != config["expected_rows"]:
        raise RuntimeError(f"Expected {config['expected_rows']} rows, found {len(frame)}")

    # Panels with a declared within-replicate reference strain are renormalized
    # here from absolute values; supplement panels whose migrated table is
    # already normalized stay descriptive and plot their stored values.
    reference = config.get("normalization_reference")
    plot_config = dict(config)
    if reference is not None:
        mean_column = f"mean_{config['value_column']}"
        reference_means = means.loc[
            means["strain"] == reference, ["replicate", mean_column]
        ].rename(columns={mean_column: "reference_growth_rate_per_h"})
        if reference_means["replicate"].duplicated().any():
            raise RuntimeError("normalization reference has duplicate replicate identifiers")
        if set(reference_means["replicate"]) != set(means["replicate"]):
            raise RuntimeError(
                "normalization reference is missing one or more replicate identifiers"
            )
        means = means.merge(reference_means, on="replicate", validate="many_to_one")
        means["relative_growth_rate"] = (
            means[mean_column] / means["reference_growth_rate_per_h"]
        )
        frame = frame.merge(reference_means, on="replicate", validate="many_to_one")
        frame["absolute_growth_rate_per_h"] = frame[config["value_column"]]
        frame["relative_growth_rate"] = (
            frame[config["value_column"]] / frame["reference_growth_rate_per_h"]
        )
        plot_config["value_column"] = "relative_growth_rate"

    if "figure_number" in config:
        figure_name = f"Figure_{int(config['figure_number'])}"
        panel_label = str(config["panel_label"])
    else:
        prefix, panel_label = panel_id.split("_", 1)
        figure_name = f"Supplementary_Figure_{int(prefix[1:])}"

    style()
    # The panel is drawn at the exact size of its slot in the figure assembly,
    # so the assembler scales it by 1.0 and a requested point size is the same
    # point size on the printed page.
    figsize = panel_figsize(figure_name, panel_label)
    is_supplement = panel_id.startswith("S")
    if is_supplement:
        fig, summary = render_supplement(frame, means, plot_config, figsize)
    else:
        fig, summary = render_main(frame, means, plot_config, figsize)
    output_dir = collection / "build" / "panels" / figure_name / panel_label
    figures = save_figure(fig, output_dir / panel_id)
    summary_path = output_dir / "summary.csv"
    summary.to_csv(summary_path, index=False, lineterminator="\n", float_format="%.12g")
    normalized_source = (
        collection
        / "build"
        / "source_data"
        / figure_name
        / panel_label
        / f"{panel_id}_source_data.csv.gz"
    )
    normalized_source.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(
        normalized_source,
        index=False,
        compression={"method": "gzip", "mtime": 0},
        float_format="%.12g",
    )
    statistics_path: Path | None = None
    statistics: pd.DataFrame | None = None
    if reference is not None:
        statistics = effect_statistics(means, plot_config)
        statistics_path = (
            collection
            / "build"
            / "statistics"
            / figure_name
            / panel_label
            / f"{panel_id}_statistics.csv"
        )
        statistics_path.parent.mkdir(parents=True, exist_ok=True)
        statistics.to_csv(
            statistics_path, index=False, lineterminator="\n", float_format="%.12g"
        )

    panel_dir = config_path.parents[1]
    wrapper = panel_dir / "scripts" / "plot.py"
    engine = Path(__file__).resolve()
    code_inputs = [engine] if engine == wrapper else [engine, wrapper]
    code_inputs.extend([collection / "src/flagella_repro/theme.py", PALETTE_PATH])
    inputs = [artifact(config_path, collection)]
    inputs.extend(artifact(path, collection) for path in code_inputs)
    inputs.extend(
        [
            artifact(parquet, collection, len(frame)),
            artifact(means_path, collection, len(means)),
            artifact(source_data, collection, len(frame)),
            artifact(inventory, collection),
        ]
    )
    # The migration step creates the every-observation source table. Include it
    # as a canonical panel output as well as a plotting input so release audits
    # can discover the exact data behind every violin directly from provenance.
    outputs = [
        artifact(source_data, collection, len(frame)),
        artifact(normalized_source, collection, len(frame)),
        artifact(summary_path, collection, len(summary)),
    ]
    if statistics_path is not None and statistics is not None:
        outputs.insert(2, artifact(statistics_path, collection, len(statistics)))
    outputs.extend(artifact(path, collection) for path in figures)
    command_module = config.get(
        "command_module",
        ".".join(panel_dir.relative_to(collection).parts) + ".scripts.plot",
    )
    provenance = {
        "schema_version": "1.0.0",
        "panel_id": panel_id,
        "status": "partial_reproduction",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "-m",
            command_module,
        ],
        "inputs": inputs,
        "outputs": outputs,
        "software": software_versions(),
        "parameters": {
            "value_column": config["value_column"],
            "filters": config["filters"],
            "biological_unit": "independent experiment/replicate",
            "cell_points_role": "descriptive distribution",
            "normalization_reference": reference,
            "normalization": (
                "each observation divided by the reference-strain mean from the same "
                "independent replicate"
                if reference is not None
                else "values are plotted as stored in the migrated normalized table"
            ),
            "display_y_limits": config["y_limits"],
            "display_clipping_only": True,
            "inferential_test": (
                "paired two-sided t-test on independent replicate means"
                if reference is not None
                else "none; the panel is descriptive"
            ),
            "migration_command": [
                ".venv/bin/python3.12",
                "-m",
                config.get("migration_module", "not_available_for_revision_alias"),
                "--write",
            ],
        },
        "random_seeds": {"jitter": None, "bootstrap": None},
        "limitations": [
            (
                "The workflow starts from an archived processed per-cell table; raw microscopy, "
                "mother-machine tracking files, and image-to-cell extraction are absent."
            ),
            (
                "The compact table is a checksum-backed extraction because the legacy CSV "
                "exceeds the collection's no-LFS 100 MB policy."
            ),
            (
                "Final multi-panel assembly and pixel-level comparison to the current manuscript "
                "export are not yet implemented."
            ),
        ],
    }
    provenance_path = panel_dir / "metadata" / "provenance.json"
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n")
    print(f"{panel_id}: wrote {len(frame)} plotted cell values to {output_dir}")


if __name__ == "__main__":
    render(Path(__file__).resolve().parents[1] / "config" / "config.json")
