"""Build revised Figure 3A, D and E from declared inputs."""

from __future__ import annotations

import hashlib
import json
import math
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
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

COLLECTION_ROOT = Path(__file__).resolve().parents[3]
FIGURE_ID = "Figure_3"
MODEL_RESULTS = COLLECTION_ROOT / "data/external/cell_economy_results/rotation"
EXPERIMENTAL_GROWTH = COLLECTION_ROOT / "data/processed/figure_02/F2_E/per_curve.csv"

# Colour carries one meaning in this figure: it names the biological identity of
# a measured point (the strain colours shared with panels B and C) or marks a
# derived value.  Every derived mark - the two model curves in D, the model
# value in E, the experiment mean and its interval - is drawn in SUMMARY_INK.
# Rotation state is never a colour.  It is the line style in D and the category
# position in E, so no hue has to mean "rotating" in one panel and "non-rotating"
# in the next.
MODEL_MARKER = "s"
ROTATION_LINESTYLE = {"rotating": "solid", "non-rotating": (0, (3.2, 1.8))}
# ``POINT_MARKER_SIZE`` is a scatter area in points squared.  A line marker and
# an errorbar marker take a diameter, so the contract size converts here once.
MARKER_DIAMETER_PT = math.sqrt(POINT_MARKER_SIZE)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact(path: Path, rows: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "relative_path": path.relative_to(COLLECTION_ROOT).as_posix(),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }
    if rows is not None:
        result["rows"] = rows
    return result


def _paths(panel_id: str) -> tuple[Path, Path, Path]:
    label = panel_id.split("_")[1]
    panel = COLLECTION_ROOT / "build/panels/Figure_3" / label
    source = COLLECTION_ROOT / "build/source_data/Figure_3" / label
    statistics = COLLECTION_ROOT / "build/statistics/Figure_3" / label
    for path in (panel, source, statistics):
        path.mkdir(parents=True, exist_ok=True)
    return panel, source, statistics


def _steady_table() -> tuple[pd.DataFrame, list[Path]]:
    rows: list[pd.DataFrame] = []
    inputs = sorted(MODEL_RESULTS.glob("steady_state_flag_*.csv"))
    if len(inputs) != 12:
        raise RuntimeError(f"expected 12 rotation-model result tables, found {len(inputs)}")
    for path in inputs:
        frame = pd.read_csv(path)
        selected = frame.loc[np.isclose(frame["cex"], 1.0)].copy()
        if selected.empty:
            raise RuntimeError(f"no cex=1.0 steady-state row in {path}")
        flagella = float(path.stem.split("flag_")[1].split("_")[0])
        selected = selected.tail(1)
        selected["flagella_mass_fraction"] = flagella
        selected["rotation_state"] = (
            "non-rotating" if "no_ATP" in path.stem else "rotating"
        )
        rows.append(selected)
    output = pd.concat(rows, ignore_index=True)[
        ["flagella_mass_fraction", "rotation_state", "mu"]
    ].rename(columns={"mu": "growth_rate_1_h"})
    output = output.sort_values(["rotation_state", "flagella_mass_fraction"]).reset_index(drop=True)
    return output, inputs


def _t_interval(values: np.ndarray) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if len(values) < 2:
        return math.nan, math.nan
    low, high = stats.t.interval(
        0.95, len(values) - 1, loc=float(values.mean()), scale=float(stats.sem(values))
    )
    return float(low), float(high)


def _bh(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values)
    ranked = values[order]
    adjusted = np.minimum.accumulate(
        (ranked * len(ranked) / np.arange(1, len(ranked) + 1))[::-1]
    )[::-1]
    restored = np.empty_like(adjusted)
    restored[order] = np.minimum(adjusted, 1.0)
    return restored


def _build_placeholder() -> tuple[pd.DataFrame, pd.DataFrame, plt.Figure, list[Path], str]:
    status = pd.DataFrame(
        [
            {
                "panel_id": "F3_A",
                "status": "blocked_asset",
                "missing_artifact": "editable assembly-mutant schematic",
                "scientific_values_plotted": 0,
            }
        ]
    )
    # The placeholder occupies its assembly box exactly, so the assembler scales
    # it by 1.0 and the notice prints at the theme tick size.
    figure, axis = plt.subplots(
        figsize=panel_figsize(FIGURE_ID, "A"), constrained_layout=True
    )
    axis.add_patch(
        plt.Rectangle(
            (0.02, 0.02),
            0.96,
            0.96,
            transform=axis.transAxes,
            fill=False,
            hatch="///",
            edgecolor=KEY_SWATCH,
            linewidth=0.8,
        )
    )
    axis.text(
        0.5,
        0.5,
        "ASSEMBLY-MUTANT\nSCHEMATIC\n\neditable source\nnot supplied",
        ha="center",
        va="center",
        color=PALETTE["neutral"]["text"],
        fontsize=TICK_FONT_PT,
        linespacing=1.5,
        transform=axis.transAxes,
        bbox={
            "facecolor": PALETTE["neutral"]["background"],
            "edgecolor": "none",
            "pad": 3.0,
        },
    )
    axis.set_axis_off()
    return status, pd.DataFrame(), figure, [], "blocked_asset"


def _build_model_curve() -> tuple[pd.DataFrame, pd.DataFrame, plt.Figure, list[Path], str]:
    data, inputs = _steady_table()
    figure, axis = plt.subplots(
        figsize=panel_figsize(FIGURE_ID, "D"), constrained_layout=True
    )
    # Both curves are model output, so both carry the summary ink.  The dash
    # pattern, not a hue, separates the two rotation states.
    edge_color, edge_width = marker_edge(SUMMARY_INK)
    labels = {"rotating": "Rotating", "non-rotating": "Non-rotating"}
    for state in ("rotating", "non-rotating"):
        part = data.loc[data["rotation_state"] == state]
        axis.plot(
            part["flagella_mass_fraction"] * 100,
            part["growth_rate_1_h"],
            color=SUMMARY_INK,
            linestyle=ROTATION_LINESTYLE[state],
            marker=MODEL_MARKER,
            markersize=MARKER_DIAMETER_PT,
            markerfacecolor=SUMMARY_INK,
            markeredgecolor=edge_color,
            markeredgewidth=edge_width,
            label=labels[state],
        )
    axis.set_xlabel("Flagellar protein mass fraction (%)")
    # A mathtext superscript prints at 0.7 of the theme size, which falls below
    # the six-point floor.  The plain unit keeps every glyph at the theme size.
    axis.set_ylabel("Modelled growth rate (1/h)")
    axis.legend(frameon=False, handletextpad=0.4, borderaxespad=0.2)
    axis.set_xlim(-0.2, 5.2)
    axis.grid(axis="y", color=PALETTE["neutral"]["grid"], linewidth=0.4, alpha=0.6)
    baseline = float(data.loc[data["flagella_mass_fraction"] == 0, "growth_rate_1_h"].max())
    stats_rows = []
    for state in ("rotating", "non-rotating"):
        value = float(
            data.loc[
                (data["rotation_state"] == state)
                & np.isclose(data["flagella_mass_fraction"], 0.05),
                "growth_rate_1_h",
            ].iloc[0]
        )
        stats_rows.append(
            {
                "rotation_state": state,
                "flagella_mass_fraction": 0.05,
                "growth_rate_1_h": value,
                "baseline_growth_rate_1_h": baseline,
                "growth_penalty_percent": (baseline - value) / baseline * 100,
                "uncertainty": "not available; deterministic model output",
            }
        )
    return data, pd.DataFrame(stats_rows), figure, inputs, "partial_reproduction"


def _experimental_penalties() -> pd.DataFrame:
    raw = pd.read_csv(EXPERIMENTAL_GROWTH)
    raw["growth_rate_1_h"] = pd.to_numeric(raw["growth_rate_k"], errors="coerce") * 60
    days = (
        raw.groupby(["experiment_day", "strain"], as_index=False)
        .agg(growth_rate_1_h=("growth_rate_1_h", "mean"), n_technical=("growth_rate_1_h", "size"))
    )
    reference = days.loc[
        days["strain"] == "EM16223", ["experiment_day", "growth_rate_1_h"]
    ].rename(columns={"growth_rate_1_h": "reference_growth_rate_1_h"})
    comparisons = {"Rotating flagella": "TH5861", "Non-rotating flagella": "EM16224"}
    rows = []
    for label, strain in comparisons.items():
        current = days.loc[
            days["strain"] == strain, ["experiment_day", "growth_rate_1_h", "n_technical"]
        ].merge(reference, on="experiment_day", validate="one_to_one")
        current["comparison"] = label
        current["strain"] = strain
        current["growth_penalty_percent"] = (
            (current["reference_growth_rate_1_h"] - current["growth_rate_1_h"])
            / current["reference_growth_rate_1_h"]
            * 100
        )
        rows.append(current)
    return pd.concat(rows, ignore_index=True)


def _build_penalty_comparison() -> tuple[pd.DataFrame, pd.DataFrame, plt.Figure, list[Path], str]:
    experimental = _experimental_penalties()
    model, model_inputs = _steady_table()
    baseline = float(model.loc[model["flagella_mass_fraction"] == 0, "growth_rate_1_h"].max())
    model_rows = []
    for comparison, state in (
        ("Rotating flagella", "rotating"),
        ("Non-rotating flagella", "non-rotating"),
    ):
        value = float(
            model.loc[
                (model["rotation_state"] == state)
                & np.isclose(model["flagella_mass_fraction"], 0.05),
                "growth_rate_1_h",
            ].iloc[0]
        )
        model_rows.append(
            {
                "plot_component": "model_value",
                "comparison": comparison,
                "experiment_day": "",
                "strain": "model_5_percent",
                "growth_penalty_percent": (baseline - value) / baseline * 100,
                "ci95_low": np.nan,
                "ci95_high": np.nan,
            }
        )

    stats_rows = []
    source_rows = []
    for comparison, part in experimental.groupby("comparison", sort=False):
        values = part["growth_penalty_percent"].to_numpy(dtype=float)
        mean = float(values.mean())
        low, high = _t_interval(values)
        p_value = float(stats.ttest_1samp(values, 0.0).pvalue)
        stats_rows.append(
            {
                "comparison": comparison,
                "n_biological_pairs": len(values),
                "mean_growth_penalty_percent": mean,
                "ci95_low": low,
                "ci95_high": high,
                "p_value_paired_t": p_value,
                "inferential_unit": "experiment day",
                "test": "two-sided paired t-test versus same-day ΔflhDC reference",
            }
        )
        for row in part.itertuples(index=False):
            source_rows.append(
                {
                    "plot_component": "experimental_day",
                    "comparison": comparison,
                    "experiment_day": row.experiment_day,
                    "strain": row.strain,
                    "growth_penalty_percent": row.growth_penalty_percent,
                    "ci95_low": np.nan,
                    "ci95_high": np.nan,
                }
            )
        source_rows.append(
            {
                "plot_component": "experimental_summary",
                "comparison": comparison,
                "experiment_day": "",
                "strain": "summary",
                "growth_penalty_percent": mean,
                "ci95_low": low,
                "ci95_high": high,
            }
        )
    statistics = pd.DataFrame(stats_rows)
    statistics["q_value_bh"] = _bh(statistics["p_value_paired_t"].to_numpy(dtype=float))
    source = pd.DataFrame([*source_rows, *model_rows])

    figure, axis = plt.subplots(
        figsize=panel_figsize(FIGURE_ID, "E"), constrained_layout=True
    )
    comparisons = ["Rotating flagella", "Non-rotating flagella"]
    experimental_styles = {
        "Rotating flagella": get_strain_style("TH5861"),
        "Non-rotating flagella": get_strain_style("EM16224"),
    }
    for x, comparison in enumerate(comparisons):
        replicate = source.loc[
            (source["comparison"] == comparison)
            & (source["plot_component"] == "experimental_day")
        ]
        offsets = np.linspace(-0.09, 0.09, len(replicate))
        style = experimental_styles[comparison]
        # Each experiment day keeps the colour and the shape its strain carries
        # in panels B and C, so the same genotype reads the same across Figure 3.
        point_edge_color, point_edge_width = marker_edge(style["color"])
        axis.scatter(
            x - 0.10 + offsets,
            replicate["growth_penalty_percent"],
            s=POINT_MARKER_SIZE,
            color=style["color"],
            marker=style["marker"],
            edgecolor=point_edge_color,
            linewidth=point_edge_width,
            label="Experiment days" if x == 0 else None,
            zorder=3,
        )
        summary = source.loc[
            (source["comparison"] == comparison)
            & (source["plot_component"] == "experimental_summary")
        ].iloc[0]
        axis.errorbar(
            x - 0.10,
            summary.growth_penalty_percent,
            yerr=[
                [summary.growth_penalty_percent - summary.ci95_low],
                [summary.ci95_high - summary.growth_penalty_percent],
            ],
            marker="D",
            markersize=MARKER_DIAMETER_PT,
            markerfacecolor=SUMMARY_INK,
            markeredgecolor=SUMMARY_INK,
            color=SUMMARY_INK,
            capsize=2,
            linewidth=0.75,
            label="Experiment mean ± 95% CI" if x == 0 else None,
            zorder=4,
        )
        model_value = float(
            source.loc[
                (source["comparison"] == comparison)
                & (source["plot_component"] == "model_value"),
                "growth_penalty_percent",
            ].iloc[0]
        )
        model_edge_color, model_edge_width = marker_edge(SUMMARY_INK)
        axis.scatter(
            x + 0.16,
            model_value,
            s=POINT_MARKER_SIZE,
            marker=MODEL_MARKER,
            facecolor=SUMMARY_INK,
            edgecolor=model_edge_color,
            linewidth=model_edge_width,
            label="Model (5% mass fraction)" if x == 0 else None,
            zorder=4,
        )
    axis.axhline(0, color=PALETTE["neutral"]["reference"], linewidth=0.65)
    axis.set_xticks(range(2), ["Rotating", "Non-rotating"])
    axis.set_xlim(-0.5, 1.5)
    # Reserve headroom so the three-entry legend never covers a plotted value.
    highest = float(source["growth_penalty_percent"].max())
    axis.set_ylim(-0.7, highest * 1.45)
    axis.set_ylabel("Growth penalty relative to\nflagella-free reference (%)")
    # "Experiment days" names a role, not a strain: the plotted days carry two
    # strain colours and two strain shapes.  A key entry for a role takes the
    # neutral key swatch, so no genotype colour is borrowed for a generic idea.
    axis.legend(
        handles=[
            Line2D(
                [], [], marker="o", linestyle="none", color=KEY_SWATCH,
                markersize=MARKER_DIAMETER_PT,
                label="Experiment days",
            ),
            Line2D(
                [], [], marker="D", linestyle="none",
                markerfacecolor=SUMMARY_INK,
                markeredgecolor=SUMMARY_INK, color=SUMMARY_INK,
                markersize=MARKER_DIAMETER_PT,
                label="Experiment mean ± 95% CI",
            ),
            Line2D(
                [], [], marker=MODEL_MARKER, linestyle="none",
                markerfacecolor=SUMMARY_INK, markeredgecolor=SUMMARY_INK,
                color=SUMMARY_INK, markersize=MARKER_DIAMETER_PT,
                label="Model (5% mass fraction)",
            ),
        ],
        frameon=False,
        loc="upper right",
        handletextpad=0.4,
        borderaxespad=0.2,
        labelspacing=0.35,
    )
    axis.grid(axis="y", color=PALETTE["neutral"]["grid"], linewidth=0.4, alpha=0.6)
    return source, statistics, figure, [EXPERIMENTAL_GROWTH, *model_inputs], "partial_reproduction"


def _write_provenance(
    panel_id: str,
    status: str,
    inputs: list[Path],
    outputs: list[Path],
    rows: dict[Path, int],
) -> None:
    panel_label = panel_id.split("_")[1].lower()
    panel_root = (
        COLLECTION_ROOT
        / "analyses/figure_03_revision"
        / f"panel_{panel_label}"
    )
    path = panel_root / "metadata/provenance.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    provenance = {
        "schema_version": "1.0.0",
        "panel_id": panel_id,
        "status": status,
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "-m",
            f"analyses.figure_03_revision.panel_{panel_label}.scripts.reproduce",
        ],
        "inputs": [
            _artifact(item)
            for item in [
                panel_root / "config/panel.json",
                panel_root / "scripts/reproduce.py",
                COLLECTION_ROOT / "src/flagella_repro/theme.py",
                PALETTE_PATH,
                *inputs,
            ]
        ],
        "outputs": [_artifact(item, rows.get(item)) for item in outputs],
        "software": {
            "python": platform.python_version(),
            "matplotlib": matplotlib.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "parameters": {
            "backend": "Python 3.12",
            "scientific_values_are_in_source_data": True,
            "stars_displayed": False,
        },
        "random_seeds": {},
        "limitations": [
            (
                "The cell-economy curves use fixed collaborator result tables because the exact "
                "local GEKKO solve remains unavailable."
            ),
            "F3_A is deliberately marked blocked and contains no inferred scientific content."
            if panel_id == "F3_A"
            else "No limitation beyond the declared upstream input limitations.",
        ],
    }
    if panel_id == "F3_A":
        provenance["blocker"] = {
            "reason": "Editable assembly-mutant schematic source was not supplied.",
            "required_assets": ["editable assembly-mutant schematic and export recipe"],
        }
    path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")


def build(panel_id: str) -> None:
    apply_publication_style()
    builders = {
        "F3_A": _build_placeholder,
        "F3_D": _build_model_curve,
        "F3_E": _build_penalty_comparison,
    }
    if panel_id not in builders:
        raise KeyError(f"unsupported revised Figure 3 panel: {panel_id}")
    source, statistics, figure, inputs, status = builders[panel_id]()
    panel_dir, source_dir, statistics_dir = _paths(panel_id)
    source_path = source_dir / f"{panel_id}_source_data.csv"
    source.to_csv(source_path, index=False, lineterminator="\n", float_format="%.12g")
    outputs = [source_path]
    rows = {source_path: len(source)}
    if not statistics.empty:
        statistics_path = statistics_dir / f"{panel_id}_statistics.csv"
        statistics.to_csv(
            statistics_path, index=False, lineterminator="\n", float_format="%.12g"
        )
        outputs.append(statistics_path)
        rows[statistics_path] = len(statistics)
    figure_paths = save_figure(figure, panel_dir / panel_id)
    outputs.extend(figure_paths)
    _write_provenance(
        panel_id,
        status,
        [Path(__file__).resolve(), *inputs],
        outputs,
        rows,
    )
    print(f"{panel_id}: {status}; wrote {len(source)} source-data rows")
