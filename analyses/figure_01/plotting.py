"""Deterministic processed-table-to-panel builders for current Figure 1."""

from __future__ import annotations

import hashlib
import itertools
import json
import platform
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
from scipy import stats

from flagella_repro.theme import (
    DENSITY_MARKER_SIZE,
    KEY_SWATCH,
    MINIMUM_ON_PAGE_FONT_PT,
    PALETTE,
    PALETTE_PATH,
    POINT_MARKER_SIZE,
    SUMMARY_INK,
    apply_publication_style,
    get_condition_color,
    get_strain_style,
    marker_edge,
    panel_figsize,
    save_figure,
)

COLLECTION_ROOT = Path(__file__).resolve().parents[2]

# The neutral ink for a mark that carries no strain or condition identity: the
# replicate-mean dots, whose key gives them one generic name, and the Figure 1E
# bubbles, which pool every AnTc level of one strain.  It is a palette entry,
# not a literal, and it is deliberately lighter than ``SUMMARY_INK`` so a
# summary mark still reads as the summary.
NEUTRAL_INK = PALETTE["neutral"]["reference"]
# matplotlib sizes a Line2D key marker by diameter in points and a scatter by
# area in points squared, so a key handle takes the square root of its size.
KEY_POINT_SIZE = float(np.sqrt(POINT_MARKER_SIZE))

# Dense per-column numbers are set at the smallest size the figure QA gate
# accepts.  Every panel now renders at its true assembly size, so this is also
# the printed size.
ANNOTATION_FONT_PT = MINIMUM_ON_PAGE_FONT_PT
# constrained_layout padding shared by every Figure 1 panel, so the panels keep
# identical margins when the assembler places them side by side.
LAYOUT_PAD = 0.012

# The archived Figure 1 tables state the anhydrotetracycline dose in µM and
# name its column ``AnTc_uM``.  That unit is wrong.  Marc Erhardt confirmed on
# 15 August 2026 that the series is ng/mL: anhydrotetracycline is 427.45 g/mol,
# so 0.5 µM would be 214 ng/mL, far above the range a PtetA promoter is induced
# over, and every figure since the July 2026 reference prints ng/mL.
#
# The copies under ``data/processed/`` stay byte-identical to the archived
# bundle, because ``migrate_legacy_tables.py`` verifies them against it by
# sha256.  The correction is therefore applied once, here, as a table enters
# the build.  Only the unit label changes; every number stays as recorded.
LEGACY_INDUCER_UNIT = " µM"
CURRENT_INDUCER_UNIT = " ng/mL"
INDUCER_COLUMN_RENAMES = {"AnTc_uM": "AnTc_ng_per_mL"}


def state_inducer_unit(frame: pd.DataFrame) -> pd.DataFrame:
    """Return the table with the anhydrotetracycline dose stated in ng/mL.

    Both the column name and the condition strings carry the unit, so the
    function rewrites both.  ``AnTc_uM`` becomes ``AnTc_ng_per_mL`` and
    ``Ptet-flhDC 0.5 µM`` becomes ``Ptet-flhDC 0.5 ng/mL``.  Every dose number
    stays as recorded.
    """
    frame = frame.rename(columns=INDUCER_COLUMN_RENAMES)
    for column in frame.columns:
        if frame[column].dtype != object:
            continue
        frame[column] = frame[column].map(
            lambda value: value.replace(LEGACY_INDUCER_UNIT, CURRENT_INDUCER_UNIT)
            if isinstance(value, str)
            else value
        )
    return frame


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_rows(path: Path) -> int:
    with path.open("rb") as handle:
        return max(0, sum(1 for _line in handle) - 1)


def artifact(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "relative_path": path.relative_to(COLLECTION_ROOT).as_posix(),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }
    if path.suffix.lower() == ".csv":
        result["rows"] = csv_rows(path)
    return result


def set_style(panel_id: str) -> None:
    del panel_id
    apply_publication_style()


def resolve_colors(config: dict[str, Any]) -> dict[str, str]:
    """Resolve every plot key to a theme color.

    The configuration stores a semantic key such as ``["antc", "0.25"]``
    instead of a hex literal, so the ordered inducer and promoter ramps stay
    under the control of ``config/palette.yaml``.
    """
    colors: dict[str, str] = {}
    for plot_key, entry in config["color_keys"].items():
        family, value = entry
        if family == "strain":
            colors[plot_key] = get_strain_style(value)["color"]
        else:
            colors[plot_key] = get_condition_color(family, value)
    return colors


def new_panel(figsize: tuple[float, float]) -> tuple[plt.Figure, plt.Axes]:
    """Open a figure that is exactly as large as its slot in the assembly."""
    figure, axis = plt.subplots(figsize=figsize, constrained_layout=True)
    figure.get_layout_engine().set(w_pad=LAYOUT_PAD, h_pad=LAYOUT_PAD, wspace=0.0, hspace=0.0)
    return figure, axis


def add_key(figure: plt.Figure, handles: list[Any]) -> None:
    """Place the plotting key under the axes.

    The panels are 54-84 mm wide.  Inside the axes the key would cover the
    distributions, so it sits below them where it costs only three text lines.
    """
    figure.legend(
        handles=handles,
        frameon=False,
        loc="outside lower center",
        ncols=1,
        handlelength=1.2,
        handletextpad=0.5,
        labelspacing=0.2,
        borderpad=0.0,
        borderaxespad=0.0,
    )


def category_axis(axis: plt.Axes, config: dict[str, Any], tick_labels: list[str]) -> None:
    """Label a categorical x axis compactly.

    The tick labels carry only the varying part of each condition; the unit
    moves into the axis label so seven categories fit across 54 mm.
    """
    axis.set_xticks(range(len(tick_labels)), tick_labels, rotation=config.get("tick_rotation", 0))
    axis.set_xlabel(config["x_label"], labelpad=1.5)
    axis.tick_params(axis="both", pad=1.5)


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    required = {"panel_id", "recipe", "inputs", "output_dir", "command_module"}
    missing = required - set(config)
    if missing:
        raise ValueError(f"missing configuration fields: {sorted(missing)}")
    return config


def input_path(config: dict[str, Any], key: str) -> Path:
    path = COLLECTION_ROOT / config["inputs"][key]
    if not path.is_file():
        raise FileNotFoundError(f"missing input {key}: {path}")
    expected = config.get("expected_rows", {}).get(key)
    if expected is not None and csv_rows(path) != int(expected):
        raise ValueError(f"row-count mismatch for {key}: {csv_rows(path)} != {expected}")
    return path


def benjamini_hochberg(values: np.ndarray) -> np.ndarray:
    output = np.full(values.shape, np.nan, dtype=float)
    finite_mask = np.isfinite(values)
    finite = values[finite_mask]
    if not finite.size:
        return output
    order = np.argsort(finite)
    ranked = finite[order]
    adjusted = ranked * finite.size / np.arange(1, finite.size + 1, dtype=float)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    restored = np.empty_like(adjusted)
    restored[order] = np.clip(adjusted, 0.0, 1.0)
    output[finite_mask] = restored
    return output


def count_statistics(config: dict[str, Any], replicate_means: pd.DataFrame) -> pd.DataFrame:
    key_column = config["category_column"]
    value_column = config["replicate_mean_column"]
    reference = config["reference"]
    order = config["order"]
    reference_values = pd.to_numeric(
        replicate_means.loc[replicate_means[key_column].astype(str) == reference, value_column],
        errors="coerce",
    ).dropna()
    rows = []
    for key in order:
        values = pd.to_numeric(
            replicate_means.loc[replicate_means[key_column].astype(str) == key, value_column],
            errors="coerce",
        ).dropna()
        p_value = np.nan
        ci_low = np.nan
        ci_high = np.nan
        if key != reference and len(reference_values) >= 2 and len(values) >= 2:
            p_value = stats.ttest_ind(values, reference_values, equal_var=False).pvalue
            variance_condition = values.var(ddof=1) / len(values)
            variance_reference = reference_values.var(ddof=1) / len(reference_values)
            standard_error = np.sqrt(variance_condition + variance_reference)
            degrees_freedom = (variance_condition + variance_reference) ** 2 / (
                variance_condition**2 / (len(values) - 1)
                + variance_reference**2 / (len(reference_values) - 1)
            )
            ci_low, ci_high = stats.t.interval(
                0.95,
                degrees_freedom,
                loc=values.mean() - reference_values.mean(),
                scale=standard_error,
            )
        rows.append(
            {
                "reference_key": reference,
                "plot_key": key,
                "n_reference_replicates": len(reference_values),
                "n_condition_replicates": len(values),
                "mean_condition": values.mean(),
                "mean_reference": reference_values.mean(),
                "mean_diff_vs_reference": values.mean() - reference_values.mean(),
                "ci95_low": ci_low,
                "ci95_high": ci_high,
                "p_value_welch_t": p_value,
                "inferential_unit": "independent microscopy replicate",
            }
        )
    result = pd.DataFrame(rows)
    non_reference = result["plot_key"] != reference
    result["q_value_bh_fdr"] = np.nan
    result.loc[non_reference, "q_value_bh_fdr"] = benjamini_hochberg(
        result.loc[non_reference, "p_value_welch_t"].to_numpy(dtype=float)
    )
    result["test"] = "Welch t-test on replicate means vs WT/reference"
    result["multiple_testing_method"] = "Benjamini-Hochberg FDR on non-reference comparisons"
    result["multiple_testing_family"] = f"{reference} vs all non-reference conditions in panel"
    result["multiple_testing_family_members"] = "|".join(key for key in order if key != reference)
    return result


def assert_statistics_match(generated: pd.DataFrame, legacy: pd.DataFrame) -> None:
    generated = generated.set_index("plot_key")
    legacy = legacy.set_index("plot_key")
    if list(generated.index) != list(legacy.index):
        raise ValueError("generated and legacy statistical comparison order differs")
    for column in ("mean_condition", "mean_reference", "p_value_welch_t", "q_value_bh_fdr"):
        left = pd.to_numeric(generated[column], errors="coerce").to_numpy(dtype=float)
        right = pd.to_numeric(legacy[column], errors="coerce").to_numpy(dtype=float)
        if not np.allclose(left, right, rtol=1e-11, atol=1e-12, equal_nan=True):
            raise ValueError(f"generated statistics differ from legacy reference: {column}")


def draw_discrete(
    config: dict[str, Any],
    data: pd.DataFrame,
    reps: pd.DataFrame,
    figsize: tuple[float, float],
) -> plt.Figure:
    key_column = config["category_column"]
    value_column = config["value_column"]
    order = config["order"]
    colors = resolve_colors(config)
    labels = config["labels"]
    count_column = config.get("frequency_column")
    grouped: dict[str, pd.DataFrame] = {}
    for key in order:
        subset = data[data[key_column].astype(str) == key].copy()
        if count_column:
            table = subset.groupby(value_column, as_index=False)[count_column].sum()
            table = table.rename(columns={count_column: "frequency"})
        else:
            table = subset.groupby(value_column, as_index=False).size()
            table = table.rename(columns={"size": "frequency"})
        grouped[key] = table

    maximum = max(float(table[value_column].max()) for table in grouped.values())
    headroom = float(config["annotation_headroom"])
    figure, axis = new_panel(figsize)
    for index, key in enumerate(order):
        table = grouped[key]
        max_frequency = max(1.0, float(table["frequency"].max()))
        total = int(table["frequency"].sum())
        for row in table.itertuples(index=False):
            value = float(getattr(row, value_column))
            frequency = float(row.frequency)
            half_width = 0.04 + 0.24 * np.sqrt(frequency / max_frequency)
            if frequency <= 12:
                xs = np.linspace(index - half_width, index + half_width, int(frequency))
                cell_edge, cell_edge_width = marker_edge(colors[key])
                axis.scatter(
                    xs,
                    np.full(len(xs), value),
                    s=DENSITY_MARKER_SIZE,
                    color=colors[key],
                    alpha=0.25,
                    edgecolor=cell_edge,
                    linewidth=cell_edge_width,
                )
            else:
                axis.hlines(
                    value,
                    index - half_width,
                    index + half_width,
                    color=colors[key],
                    alpha=0.72,
                    linewidth=1.15,
                )

        rep_values = (
            pd.to_numeric(
                reps.loc[reps[key_column].astype(str) == key, config["replicate_mean_column"]],
                errors="coerce",
            )
            .dropna()
            .to_numpy()
        )
        offsets = np.linspace(-0.22, 0.22, len(rep_values)) if len(rep_values) > 1 else [0.0]
        rep_edge, rep_edge_width = marker_edge(NEUTRAL_INK)
        axis.scatter(
            index + np.asarray(offsets),
            rep_values,
            s=POINT_MARKER_SIZE,
            color=NEUTRAL_INK,
            edgecolor=rep_edge,
            linewidth=rep_edge_width,
            zorder=4,
        )
        mean = float(np.mean(rep_values))
        standard_deviation = float(np.std(rep_values, ddof=1)) if len(rep_values) > 1 else 0.0
        axis.hlines(mean, index - 0.32, index + 0.32, color=SUMMARY_INK, linewidth=0.9, zorder=3)
        # Seven conditions share 54 mm, so the per-condition numbers only fit
        # when they are set upright.  The two lines then stack side by side.
        axis.text(
            index,
            maximum + 0.45,
            f"{mean:.2f}±{standard_deviation:.2f}\nN={total}",
            ha="center",
            va="bottom",
            rotation=90,
            linespacing=1.0,
            fontsize=ANNOTATION_FONT_PT,
        )

    category_axis(axis, config, [labels[key] for key in order])
    axis.set_ylabel(config["y_label"], labelpad=1.5)
    axis.set_xlim(-0.55, len(order) - 0.45)
    axis.set_ylim(-0.5, maximum + headroom)
    axis.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6, steps=[1, 2, 2.5, 5, 10]))
    axis.grid(axis="y", linewidth=0.5, alpha=0.8)
    axis.set_axisbelow(True)
    add_key(
        figure,
        [
            # The frequency mark stands for a concept, not for one condition, so
            # its swatch must not borrow a condition or strain colour.
            Line2D([], [], color=KEY_SWATCH, linewidth=1.2, label="Cell-count frequency"),
            Line2D(
                [], [], marker="o", linestyle="none", color=NEUTRAL_INK,
                markersize=KEY_POINT_SIZE, label="Independent replicate mean",
            ),
            Line2D([], [], color=SUMMARY_INK, linewidth=1.2, label="Mean of replicate means"),
        ],
    )
    return figure


def draw_violin(
    config: dict[str, Any],
    cells: pd.DataFrame,
    reps: pd.DataFrame,
    figsize: tuple[float, float],
) -> plt.Figure:
    key_column = config["category_column"]
    value_column = config["value_column"]
    order = config["order"]
    labels = config["labels"]
    colors = resolve_colors(config)
    cells = cells.copy()
    cells["plot_label"] = cells[key_column].map(labels)
    palette = {labels[key]: colors[key] for key in order}
    ordered_labels = [labels[key] for key in order]
    figure, axis = new_panel(figsize)
    sns.violinplot(
        data=cells,
        x="plot_label",
        y=value_column,
        order=ordered_labels,
        hue="plot_label",
        palette=palette,
        cut=0,
        density_norm="width",
        inner=None,
        linewidth=0.8,
        bw_adjust=1.6,
        legend=False,
        ax=axis,
    )
    for collection in axis.collections:
        collection.set_alpha(0.72)
    for index, key in enumerate(order):
        values = (
            pd.to_numeric(
                reps.loc[reps[key_column].astype(str) == key, config["replicate_mean_column"]],
                errors="coerce",
            )
            .dropna()
            .to_numpy()
        )
        offsets = np.linspace(-0.24, 0.24, len(values)) if len(values) > 1 else [0.0]
        rep_edge, rep_edge_width = marker_edge(NEUTRAL_INK)
        axis.scatter(
            index + np.asarray(offsets),
            values,
            s=POINT_MARKER_SIZE,
            color=NEUTRAL_INK,
            edgecolor=rep_edge,
            linewidth=rep_edge_width,
            zorder=4,
        )
        if len(values) >= 2:
            mean = float(np.mean(values))
            low, high = stats.t.interval(
                0.95,
                len(values) - 1,
                loc=mean,
                scale=stats.sem(values),
            )
            summary_edge, summary_edge_width = marker_edge(SUMMARY_INK)
            axis.errorbar(
                index,
                mean,
                yerr=[[mean - low], [high - mean]],
                marker="D",
                markersize=2.6,
                markerfacecolor=SUMMARY_INK,
                markeredgecolor=summary_edge,
                markeredgewidth=summary_edge_width,
                color=SUMMARY_INK,
                capsize=1.4,
                linewidth=0.55,
                zorder=5,
            )
    category_axis(axis, config, ordered_labels)
    axis.set_ylabel(config["y_label"], labelpad=1.5)
    axis.set_xlim(-0.7, len(order) - 0.3)
    # Keep the tip of the tallest violin inside the axes.
    lowest, highest = axis.get_ylim()
    axis.set_ylim(lowest, highest + 0.05 * (highest - lowest))
    axis.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6, steps=[1, 2, 2.5, 5, 10]))
    axis.grid(axis="y", linewidth=0.5, alpha=0.8)
    axis.set_axisbelow(True)
    add_key(
        figure,
        [
            Patch(facecolor=KEY_SWATCH, alpha=0.72, label="Cell distribution"),
            Line2D(
                [], [], marker="o", linestyle="none", color=NEUTRAL_INK,
                markersize=KEY_POINT_SIZE, label="Independent replicate mean",
            ),
            Line2D(
                [], [], marker="D", color=SUMMARY_INK,
                linestyle="none", markersize=3.2, label="Mean ± 95% CI",
            ),
        ],
    )
    return figure


def hook_filament_summary(cells: pd.DataFrame, seed: int) -> pd.DataFrame:
    rho = stats.spearmanr(cells["hook_count"], cells["filament_count"]).statistic
    replicates = sorted(cells["replicate_id"].astype(str).unique())
    bootstrap_values = []
    for selection in itertools.product(range(len(replicates)), repeat=len(replicates)):
        sampled = pd.concat(
            [cells[cells["replicate_id"].astype(str) == replicates[index]] for index in selection],
            ignore_index=True,
        )
        bootstrap_values.append(
            stats.spearmanr(sampled["hook_count"], sampled["filament_count"]).statistic
        )
    low, high = np.percentile(np.asarray(bootstrap_values), [2.5, 97.5])
    return pd.DataFrame(
        [
            {
                "strain_id": "EM8242",
                "n_cells": len(cells),
                "n_replicates": len(replicates),
                "correlation_metric": "spearman_rho",
                "rho": rho,
                "bootstrap_ci95_low": low,
                "bootstrap_ci95_high": high,
                "bootstrap_n": len(bootstrap_values),
                "bootstrap_unit": "replicate_id",
                "bootstrap_method": "exact_enumeration_of_replicate_bootstrap",
                "random_seed": seed,
            }
        ]
    )


def draw_bubbles(
    config: dict[str, Any],
    counts: pd.DataFrame,
    figsize: tuple[float, float],
) -> plt.Figure:
    # Bubble area still scales with the square root of the cell count.  Only
    # the two constants shrink, so that the largest bubble stays inside one
    # count step on a 55 mm panel.  The key uses the identical formula.
    base = float(config["bubble_size_base"])
    scale = float(config["bubble_size_scale"])

    def marker_size(cells: Any) -> Any:
        return base + scale * np.sqrt(cells)

    # One bubble pools every AnTc level of one strain, so it carries no inducer
    # level and no strain identity.  It therefore takes the neutral ink.  The
    # panel previously used the palette's ΔflhDC blue, which named a mutant that
    # does not appear in this Ptet series.
    bubble_edge, bubble_edge_width = marker_edge(NEUTRAL_INK)
    figure, axis = new_panel(figsize)
    axis.scatter(
        counts["hook_count"],
        counts["filament_count"],
        s=marker_size(pd.to_numeric(counts["n_cells"]).to_numpy()),
        color=NEUTRAL_INK,
        edgecolor=bubble_edge,
        linewidth=bubble_edge_width,
        alpha=0.92,
    )
    handles = [
        axis.scatter(
            [],
            [],
            s=marker_size(value),
            color=NEUTRAL_INK,
            edgecolor=bubble_edge,
            linewidth=bubble_edge_width,
        )
        for value in (10, 100, 1000)
    ]
    figure.legend(
        handles,
        ["10", "100", "1000"],
        title="Cells per bubble",
        frameon=False,
        loc="outside lower center",
        ncols=3,
        handlelength=1.0,
        handletextpad=0.4,
        columnspacing=1.0,
        borderpad=0.0,
        borderaxespad=0.0,
    )
    # The widest bubble spans about 0.6 count steps, so the default margin is
    # too small to keep the (0, 0) bubble clear of the spines.
    axis.margins(0.08)
    axis.set_xlabel("Hook count", labelpad=1.5)
    axis.set_ylabel("Filament count", labelpad=1.5)
    axis.tick_params(axis="both", pad=1.5)
    axis.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6, steps=[1, 2, 2.5, 5, 10]))
    axis.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6, steps=[1, 2, 2.5, 5, 10]))
    axis.grid(linewidth=0.5, alpha=0.8)
    axis.set_axisbelow(True)
    return figure


def write_provenance(
    config_path: Path,
    config: dict[str, Any],
    inputs: list[Path],
    outputs: list[Path],
) -> None:
    entry_script = COLLECTION_ROOT / Path(*config["command_module"].split(".")).with_suffix(".py")
    analysis_code = [
        Path(__file__).resolve(),
        entry_script,
        COLLECTION_ROOT / "src/flagella_repro/theme.py",
        PALETTE_PATH,
    ]
    provenance = {
        "schema_version": "1.0.0",
        "panel_id": config["panel_id"],
        "status": "partial_reproduction",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [".venv/bin/python3.12", "-m", config["command_module"]],
        "inputs": [artifact(path) for path in [config_path, *analysis_code, *inputs]],
        "outputs": [artifact(path) for path in outputs],
        "software": {
            "python": platform.python_version(),
            "matplotlib": version("matplotlib"),
            "numpy": version("numpy"),
            "pandas": version("pandas"),
            "scipy": version("scipy"),
            "seaborn": version("seaborn"),
        },
        "parameters": {
            "recipe": config["recipe"],
            "current_panel_labels": True,
            "reproduction_scope": "migrated processed tables to standalone panel",
        },
        "random_seeds": {"bootstrap": config.get("random_seed")},
        "limitations": config["limitations"],
    }
    rendered = json.dumps(provenance, indent=2, ensure_ascii=False) + "\n"
    panel_output = config_path.parents[1] / "metadata" / "provenance.json"
    panel_output.parent.mkdir(parents=True, exist_ok=True)
    panel_output.write_text(rendered, encoding="utf-8")


def render(config_path: Path) -> None:
    config = load_config(config_path)
    set_style(config["panel_id"])
    figure_name = f"Figure_{int(config['figure_number'])}"
    panel_label = str(config["panel_label"])
    # The panel is drawn at the exact size of its slot in the assembly, so the
    # assembler scales it by 1.0 and a requested point size is the same point
    # size on the printed page.
    figsize = panel_figsize(figure_name, panel_label)
    output_dir = COLLECTION_ROOT / "build" / "panels" / figure_name / panel_label
    source_data_dir = COLLECTION_ROOT / "build" / "source_data" / figure_name / panel_label
    source_data_dir.mkdir(parents=True, exist_ok=True)
    inputs: list[Path] = []
    generated_tables: list[Path] = []

    if config["recipe"] in {"discrete_count", "violin_count"}:
        data_key = "histogram_counts" if "histogram_counts" in config["inputs"] else "cell_points"
        data_path = input_path(config, data_key)
        reps_path = input_path(config, "replicate_means")
        legacy_path = input_path(config, "legacy_statistics")
        inputs.extend([data_path, reps_path, legacy_path])
        data = state_inducer_unit(pd.read_csv(data_path, low_memory=False))
        reps = state_inducer_unit(pd.read_csv(reps_path, low_memory=False))
        generated_stats = count_statistics(config, reps)
        assert_statistics_match(
            generated_stats, state_inducer_unit(pd.read_csv(legacy_path))
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        statistics_dir = COLLECTION_ROOT / "build" / "statistics" / figure_name / panel_label
        statistics_dir.mkdir(parents=True, exist_ok=True)
        stats_path = statistics_dir / f"{config['panel_id']}_statistics.csv"
        distribution_path = source_data_dir / f"{config['panel_id']}_distribution.csv"
        replicate_path = source_data_dir / f"{config['panel_id']}_replicate_means.csv"
        data.to_csv(
            distribution_path, index=False, lineterminator="\n", float_format="%.12g"
        )
        reps.to_csv(replicate_path, index=False, lineterminator="\n", float_format="%.12g")
        generated_stats.to_csv(
            stats_path, index=False, lineterminator="\n", float_format="%.12g"
        )
        generated_tables.extend([distribution_path, replicate_path, stats_path])
        if config["recipe"] == "discrete_count":
            figure = draw_discrete(config, data, reps, figsize)
        else:
            figure = draw_violin(config, data, reps, figsize)
    elif config["recipe"] == "hook_filament_bubbles":
        cells_path = input_path(config, "cell_points")
        legacy_counts_path = input_path(config, "legacy_bubble_counts")
        legacy_stats_path = input_path(config, "legacy_statistics")
        inputs.extend([cells_path, legacy_counts_path, legacy_stats_path])
        cells = state_inducer_unit(pd.read_csv(cells_path, low_memory=False))
        counts = (
            cells.groupby(["hook_count", "filament_count"], as_index=False)
            .agg(n_cells=("hook_count", "size"), n_replicates=("replicate_id", "nunique"))
            .sort_values(["hook_count", "filament_count"])
        )
        counts.insert(0, "_plot_component", "panel_scatter_bubble_counts")
        legacy_counts = pd.read_csv(legacy_counts_path)
        pd.testing.assert_frame_equal(
            counts.reset_index(drop=True), legacy_counts, check_dtype=False
        )
        summary = hook_filament_summary(cells, int(config["random_seed"]))
        legacy_summary = pd.read_csv(legacy_stats_path)
        for column in ("rho", "bootstrap_ci95_low", "bootstrap_ci95_high"):
            if not np.allclose(summary[column], legacy_summary[column], rtol=1e-11, atol=1e-12):
                raise ValueError(f"generated hook-filament statistic differs: {column}")
        output_dir.mkdir(parents=True, exist_ok=True)
        statistics_dir = COLLECTION_ROOT / "build" / "statistics" / figure_name / panel_label
        statistics_dir.mkdir(parents=True, exist_ok=True)
        counts_path = source_data_dir / f"{config['panel_id']}_bubble_counts.csv"
        summary_path = statistics_dir / f"{config['panel_id']}_statistics.csv"
        counts.to_csv(counts_path, index=False, lineterminator="\n", float_format="%.12g")
        summary.to_csv(summary_path, index=False, lineterminator="\n", float_format="%.12g")
        generated_tables.extend([counts_path, summary_path])
        figure = draw_bubbles(config, counts, figsize)
    else:
        raise ValueError(f"unsupported recipe: {config['recipe']}")

    figure_paths = save_figure(figure, output_dir / config["panel_id"])
    write_provenance(config_path, config, inputs, [*generated_tables, *figure_paths])
    print(f"reproduced {config['panel_id']} from migrated processed tables")
