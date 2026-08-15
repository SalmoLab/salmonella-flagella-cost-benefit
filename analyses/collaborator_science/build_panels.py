#!/usr/bin/env python3
"""Build proteomics and cell-economy panels from the final collaborator delivery."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

# The panel wrappers under analyses/*/scripts/reproduce.py run this file
# directly, without PYTHONPATH.  Put this collection's own src/ first so the
# shared theme always comes from the repository, not from an installed copy.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
# Supplementary Figure 2 and Figure 4 draw the same protein sectors, so both
# read the one documented override table that lives beside the Figure 4 builder.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "figure_04_revision"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from sector_overrides import OVERRIDE_TABLE, apply_sector_overrides

from flagella_repro.theme import (
    PALETTE,
    POINT_MARKER_SIZE,
    SEGMENT_SEPARATOR_COLOR,
    SEGMENT_SEPARATOR_WIDTH,
    TICK_FONT_PT,
    apply_publication_style,
    get_condition_color,
    get_sector_color,
    marker_edge,
    panel_figsize,
    save_figure,
)

apply_publication_style()
# The shared style sets its own hash salt.  This builder keeps the salt it has
# always used, so its SVG element ids stay byte-identical across rebuilds.
matplotlib.rcParams["svg.hashsalt"] = "flagella-collaborator-science-2026-08-12"

PROJECT = Path(__file__).resolve().parents[2]
PROTEOMICS = PROJECT / "data/external/promoter_series_proteomics"
MODEL_RESULTS = PROJECT / "data/external/cell_economy_results"
MODEL_SOURCE = PROJECT / "models/cell_economy/upstream"
SOURCE_ROOT = PROJECT / "data/source_data"
SECTORS = ["Oth", "Rib", "Cbn", "Aab", "Etc", "Lpb", "Fla", "Tra"]
MUTANTS = ["ΔflhDC", "Ppro1-flhDC", "PproA-flhDC", "WT", "PproB-flhDC", "PproD-flhDC"]
# Strain colors come from the shared vocabulary: the deletion and the wild type
# from the mutant family, the promoter series from its light-to-dark ramp.
MUTANT_COLORS = {
    "ΔflhDC": get_condition_color("mutant", "delta_flhDC"),
    "Ppro1-flhDC": get_condition_color("promoter", "Ppro1"),
    "PproA-flhDC": get_condition_color("promoter", "PproA"),
    "WT": get_condition_color("mutant", "WT"),
    "PproB-flhDC": get_condition_color("promoter", "PproB"),
    "PproD-flhDC": get_condition_color("promoter", "PproD"),
}
# The flagella mass-fraction ramp of the model panels has no counterpart in the
# shared vocabulary, so it stays local to this builder.
FLAG_COLORS = dict(
    zip(
        [0.005, 0.01, 0.02, 0.03, 0.04, 0.05],
        ["#7570B3", "#984EA3", "#D62F8A", "#E63B6F", "#ED762F", "#E6AB02"],
        strict=True,
    )
)
# Panels drawn at the exact size of their assembly slot.  The assembler scales
# each panel by min(box / viewBox), so a canvas that already matches the box is
# placed at 1:1 and a declared point size is that point size on the page.
TRUE_PAGE_SIZE_PANELS = {
    "S2_A": ("Supplementary_Figure_2", "A"),
}
PANEL_DIRS = {
    "S2_A": "supplementary_02/panel_a",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def artifact(path: Path, rows: int | None = None) -> dict[str, object]:
    out: dict[str, object] = {
        "relative_path": path.relative_to(PROJECT).as_posix(),
        "sha256": sha(path),
        "bytes": path.stat().st_size,
    }
    if rows is not None:
        out["rows"] = rows
    return out


def style(ax: plt.Axes) -> None:
    ax.grid(True, color=PALETTE["neutral"]["grid"], linewidth=0.5)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color(PALETTE["neutral"]["reference"])
        spine.set_linewidth(matplotlib.rcParams["axes.linewidth"])


def panel_folder(panel_id: str) -> str:
    prefix, label = panel_id.split("_", 1)
    if prefix.startswith("S"):
        return f"Supplementary_Figure_{int(prefix[1:])}/{label}"
    return f"Figure_{int(prefix[1:])}/{label}"


def save(fig: plt.Figure, panel_id: str) -> list[Path]:
    outdir = PROJECT / "build/panels" / panel_folder(panel_id)
    outdir.mkdir(parents=True, exist_ok=True)
    if panel_id in TRUE_PAGE_SIZE_PANELS:
        # These panels already carry the physical size of their assembly box.
        # A tight bounding box would trim that canvas and make the assembler
        # scale the panel again, so the shared writer is used instead.
        return save_figure(fig, outdir / panel_id)
    paths = [outdir / f"{panel_id}.{suffix}" for suffix in ("png", "svg", "pdf")]
    fig.savefig(paths[0], dpi=300, bbox_inches="tight", metadata={"Software": "flagella-repro"})
    fig.savefig(paths[1], bbox_inches="tight", metadata={"Date": None, "Creator": "flagella-repro"})
    fig.savefig(
        paths[2],
        bbox_inches="tight",
        metadata={"CreationDate": None, "ModDate": None, "Creator": "flagella-repro"},
    )
    plt.close(fig)
    return paths


def write_source(panel_id: str, name: str, frame: pd.DataFrame) -> Path:
    path = SOURCE_ROOT / panel_id.lower() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def mass_table() -> pd.DataFrame:
    """Sector mass fractions re-summed through the documented sector overrides.

    The delivered table is the exact per-sample sum of the delivered protein
    table.  Rows that carry no sector, that is the growth-only rows of the two
    reference strains, keep their delivered values.
    """
    frame = pd.read_csv(PROTEOMICS / "sector_mass_fractions.tsv", sep="\t")
    totals = protein_table().groupby(
        ["mutant", "replicate", "sector_short"], as_index=False
    ).mass_fraction.sum()
    totals["replicate"] = totals.replicate.astype(float)
    keys = ["mutant", "replicate", "sector_short"]
    totals = totals.rename(columns={"mass_fraction": "overridden"})
    merged = frame.merge(totals, on=keys, how="left")
    merged["mass_fraction"] = merged.overridden.fillna(merged.mass_fraction)
    return merged.drop(columns="overridden")


def protein_table() -> pd.DataFrame:
    """The delivered protein-level export with the shared sector overrides applied."""
    delivered = pd.read_csv(PROTEOMICS / "protein_massfrac_annotated.csv", low_memory=False)
    return apply_sector_overrides(delivered)


def growth_table() -> pd.DataFrame:
    raw = pd.read_csv(PROTEOMICS / "population_growth_mutants.csv")
    raw = raw[["strain", "experiment_day", "doubling_time_min"]].dropna()
    per_experiment = raw.groupby(
        ["strain", "experiment_day"], as_index=False
    ).doubling_time_min.mean()
    per_experiment["growth_rate_1h"] = 60 * math.log(2) / per_experiment["doubling_time_min"]
    return per_experiment


def steady_table(folder: str = "rotation") -> pd.DataFrame:
    rows = []
    for path in sorted((MODEL_RESULTS / folder).glob("steady_state_flag_*.csv")):
        frame = pd.read_csv(path)
        selected = frame.loc[np.isclose(frame["cex"], 1.0)].copy()
        if selected.empty:
            selected = frame.loc[frame["time"] == frame["time"].max()].tail(1).copy()
        selected["flagella"] = float(path.stem.split("flag_")[1].split("_")[0])
        selected["energy_cost"] = "no_rotation" if "no_ATP" in path.stem else "rotation"
        rows.append(selected)
    return pd.concat(rows, ignore_index=True)


def swimming_table() -> pd.DataFrame:
    rows = []
    for path in sorted((MODEL_RESULTS / "swimming/8500").glob("dynamic_flag_*.csv")):
        frame = pd.read_csv(path)
        frame = frame.loc[frame["time"] > 0].copy()
        frame["flagella"] = float(path.stem.split("flag_")[1])
        biomass = 1.0
        values = []
        for mu in frame["mu"]:
            biomass += float(mu) * biomass
            values.append(biomass)
        frame["biomass"] = values
        rows.append(frame)
    return pd.concat(rows, ignore_index=True)


def panel_f2_g() -> tuple[pd.DataFrame, plt.Figure, list[Path]]:
    data = steady_table("rotation")[["flagella", "energy_cost", "mu"]].sort_values(
        ["energy_cost", "flagella"]
    )
    fig, ax = plt.subplots(figsize=(3.2, 3.0))
    for label, color in [("rotation", "#E7298A"), ("no_rotation", "#F46AA3")]:
        part = data[data.energy_cost == label]
        ax.plot(
            part.flagella, part.mu, "o-", color=color, lw=1.7, ms=4, label=label.replace("_", " ")
        )
    style(ax)
    ax.set(
        xlabel="Flagella mass fraction",
        ylabel="Growth rate (1/h)",
        title="Rotation mutant simulation",
    )
    ax.legend(frameon=False, fontsize=8)
    return (
        data,
        fig,
        [
            MODEL_RESULTS / "rotation" / p.name
            for p in sorted((MODEL_RESULTS / "rotation").glob("*.csv"))
        ],
    )


def panel_f2_h() -> tuple[pd.DataFrame, plt.Figure, list[Path]]:
    model = steady_table("rotation")
    model = model[model.flagella.isin([0.0, 0.05])]
    baseline = float(model.loc[model.flagella == 0, "mu"].max())
    model_rows = [
        (
            "Model",
            "F=5% R+",
            float(model.query("flagella == 0.05 and energy_cost == 'rotation'").mu.iloc[0]),
            0.0,
        ),
        (
            "Model",
            "F=5% R−",
            float(model.query("flagella == 0.05 and energy_cost == 'no_rotation'").mu.iloc[0]),
            0.0,
        ),
        ("Model", "F=0% R−", baseline, 0.0),
    ]
    sector_growth = mass_table()[["mutant", "mean_growth_rate", "sd_growth_rate"]].drop_duplicates()
    exp_rows = []
    for label in ["WT-(fliC ON)", "motB-D33N", "ΔflhDC"]:
        row = sector_growth.loc[sector_growth.mutant == label].iloc[0]
        exp_rows.append(
            ("Experiment", label, float(row.mean_growth_rate), float(row.sd_growth_rate))
        )
    data = pd.DataFrame(exp_rows + model_rows, columns=["type", "condition", "growth_rate", "sd"])
    data["penalty_percent"] = data.groupby("type")["growth_rate"].transform(
        lambda x: (x.max() - x) / x.max() * 100
    )
    fig, axes = plt.subplots(1, 2, figsize=(5.2, 2.8), sharey=True)
    colors = ["#E7298A", "#F46AA3", "#F9B5CE"]
    for ax, kind in zip(axes, ["Experiment", "Model"], strict=True):
        part = data[data.type == kind]
        x = np.arange(len(part))
        ax.bar(x, part.growth_rate, yerr=part.sd, color=colors, edgecolor="white", capsize=2)
        for i, row in enumerate(part.itertuples()):
            ax.text(
                i, 1.96, f"-{row.penalty_percent:.1f}%", ha="center", color="#E7298A", fontsize=7
            )
        ax.set_xticks(x, part.condition, rotation=0)
        ax.set_title(kind)
        style(ax)
    axes[0].set_ylabel("Growth rate (1/h)")
    axes[0].set_ylim(0, 2.05)
    return (
        data,
        fig,
        [
            PROTEOMICS / "population_growth_mutants.csv",
            MODEL_RESULTS / "rotation/steady_state_flag_0.00_ATP.csv",
            MODEL_RESULTS / "rotation/steady_state_flag_0.05_ATP.csv",
            MODEL_RESULTS / "rotation/steady_state_flag_0.05_no_ATP.csv",
        ],
    )


def panel_f3_a() -> tuple[pd.DataFrame, plt.Figure, list[Path]]:
    data = mass_table().groupby(["mutant", "sector_short"], as_index=False).mass_fraction.mean()
    pivot = data.pivot(index="mutant", columns="sector_short", values="mass_fraction").reindex(
        MUTANTS
    )
    fig, ax = plt.subplots(figsize=(4.0, 3.7))
    bottom = np.zeros(len(pivot))
    for sector in SECTORS:
        vals = pivot[sector].to_numpy()
        ax.bar(
            np.arange(len(pivot)),
            vals,
            bottom=bottom,
            color=get_sector_color(sector),
            width=0.9,
            label=sector,
            edgecolor=SEGMENT_SEPARATOR_COLOR,
            linewidth=SEGMENT_SEPARATOR_WIDTH,
        )
        bottom += vals
    style(ax)
    ax.set(
        ylim=(0, 1.04),
        ylabel="Mean mass fraction",
        xticks=np.arange(len(pivot)),
        xticklabels=MUTANTS,
    )
    ax.tick_params(axis="x", rotation=45)
    ax.legend(frameon=False, bbox_to_anchor=(1.02, 0.5), loc="center left", fontsize=8)
    return data, fig, [PROTEOMICS / "sector_mass_fractions.tsv"]


def top10_data() -> pd.DataFrame:
    frame = protein_table()
    grouped = frame.groupby(
        ["uniprot_id", "gene_name_short", "sector_short", "mutant"], dropna=False, as_index=False
    ).mass_fraction.mean()
    sums = grouped.groupby(["sector_short", "uniprot_id"], as_index=False).mass_fraction.sum()
    keep = (
        sums.sort_values(["sector_short", "mass_fraction"], ascending=[True, False])
        .groupby("sector_short")
        .head(10)
    )
    return grouped.merge(
        keep[["sector_short", "uniprot_id"]], on=["sector_short", "uniprot_id"], how="inner"
    )


def panel_f3_b() -> tuple[pd.DataFrame, plt.Figure, list[Path]]:
    data = top10_data()
    fig, axes = plt.subplots(2, 4, figsize=(10, 5.2), squeeze=False)
    for ax, sector in zip(axes.ravel(), SECTORS, strict=True):
        part = data[data.sector_short == sector]
        bottom = np.zeros(len(MUTANTS))
        for _, protein in part.groupby("uniprot_id", sort=False):
            vals = (
                protein.set_index("mutant").mass_fraction.reindex(MUTANTS, fill_value=0).to_numpy()
            )
            ax.bar(
                np.arange(len(MUTANTS)),
                vals,
                bottom=bottom,
                color=get_sector_color(sector),
                alpha=0.78,
                edgecolor=SEGMENT_SEPARATOR_COLOR,
                linewidth=SEGMENT_SEPARATOR_WIDTH,
            )
            for i, (value, base) in enumerate(zip(vals, bottom, strict=True)):
                if value > 0:
                    ax.text(
                        i,
                        base + value / 2,
                        str(protein.gene_name_short.iloc[0]),
                        ha="center",
                        va="center",
                        fontsize=4.5,
                        color="white",
                    )
            bottom += vals
        style(ax)
        ax.set_title(sector)
        ax.set_xticks(np.arange(len(MUTANTS)), MUTANTS, rotation=55, ha="right", fontsize=6)
    fig.supylabel("Mean mass fraction")
    fig.tight_layout()
    return data, fig, [PROTEOMICS / "protein_massfrac_annotated.csv"]


def panel_f3_c() -> tuple[pd.DataFrame, plt.Figure, list[Path]]:
    raw = steady_table("c_limitation")
    columns = [f"a_{s.lower()}" for s in SECTORS]
    data = raw[["flagella", *columns]].copy()
    data = data.rename(columns={f"a_{s.lower()}": s for s in SECTORS}).sort_values("flagella")
    fig, ax = plt.subplots(figsize=(4.0, 3.7))
    bottom = np.zeros(len(data))
    for sector in SECTORS:
        vals = data[sector].to_numpy()
        # ``width`` is in flagella-mass-fraction units and the axis spans 0 to
        # 0.05, so each bar is about 30 pt wide.  The separator reads here as
        # clearly as it does on the strain bars.
        ax.bar(
            data.flagella,
            vals,
            bottom=bottom,
            width=0.008,
            color=get_sector_color(sector),
            edgecolor=SEGMENT_SEPARATOR_COLOR,
            linewidth=SEGMENT_SEPARATOR_WIDTH,
        )
        bottom += vals
    style(ax)
    ax.set(xlabel="Flagella mass fraction (model)", ylabel="Protein allocation", ylim=(0, 1.04))
    return data, fig, sorted((MODEL_RESULTS / "c_limitation").glob("*.csv"))


def growth_by_mutant() -> pd.DataFrame:
    growth = growth_table()
    mapping = {
        "EM9662": "Ppro1-flhDC",
        "EM9661": "PproA-flhDC",
        "TH9677": "WT",
        "EM9660": "PproB-flhDC",
        "EM8513": "PproD-flhDC",
    }
    growth["mutant"] = growth.strain.map(mapping)
    return growth.dropna(subset=["mutant"]).groupby("mutant", as_index=False).growth_rate_1h.mean()


def panel_f3_d() -> tuple[pd.DataFrame, plt.Figure, list[Path]]:
    sectors = mass_table().groupby(["mutant", "sector_short"], as_index=False).mass_fraction.mean()
    data = sectors.merge(growth_by_mutant(), on="mutant").query(
        "sector_short in ['Rib','Fla'] and mutant != 'ΔflhDC'"
    )
    fig, axes = plt.subplots(2, 1, figsize=(3.5, 5.2))
    for ax, sector in zip(axes, ["Rib", "Fla"], strict=True):
        part = data[data.sector_short == sector]
        ax.scatter(part.mass_fraction, part.growth_rate_1h, s=28, color=get_sector_color(sector))
        for row in part.itertuples():
            ax.annotate(
                row.mutant,
                (row.mass_fraction, row.growth_rate_1h),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=7,
                color=get_sector_color(sector),
            )
        style(ax)
        ax.set(xlabel=f"Mean mass fraction {sector}", ylabel="Mean growth rate (1/h)")
    fig.tight_layout()
    return (
        data,
        fig,
        [PROTEOMICS / "sector_mass_fractions.tsv", PROTEOMICS / "population_growth_mutants.csv"],
    )


def panel_f3_e() -> tuple[pd.DataFrame, plt.Figure, list[Path]]:
    swim = swimming_table()
    final = swim.sort_values("time").groupby("flagella").tail(1).copy()
    final["distance_travelled_um"] = 8500 - final.distance
    gradient = pd.read_csv(MODEL_RESULTS / "swimming/8500/substrate_gradient.csv")
    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    for row in final.itertuples():
        ax.hlines(
            row.flagella * 100,
            0,
            row.distance_travelled_um,
            color=FLAG_COLORS[row.flagella],
            lw=1.7,
        )
        ax.plot(
            row.distance_travelled_um,
            row.flagella * 100,
            "o",
            color=FLAG_COLORS[row.flagella],
            ms=4,
        )
    ax.fill_between(8500 - gradient.dist_um, 0, gradient.substrate_mM, color="#BBBBBB", alpha=0.5)
    style(ax)
    ax.set(xlim=(0, 8500), xlabel="Distance travelled (µm)", ylabel="Flagella mass fraction (%)")
    return (
        final[["flagella", "distance_travelled_um", "distance", "cex"]],
        fig,
        sorted((MODEL_RESULTS / "swimming/8500").glob("*.csv")),
    )


def panel_f3_f() -> tuple[pd.DataFrame, plt.Figure, list[Path]]:
    data = swimming_table()[["flagella", "time", "mu"]]
    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    for flagella, part in data.groupby("flagella"):
        ax.plot(part.time, part.mu, color=FLAG_COLORS[flagella], lw=1.7, label=f"{flagella:.3g}")
    style(ax)
    ax.set(xlabel="Time (h)", ylabel="Growth rate (1/h)")
    ax.legend(frameon=False, bbox_to_anchor=(1.02, 0.5), loc="center left", fontsize=7)
    return data, fig, sorted((MODEL_RESULTS / "swimming/8500").glob("dynamic_flag_*.csv"))


def panel_f3_g() -> tuple[pd.DataFrame, plt.Figure, list[Path]]:
    swim = swimming_table()
    data = swim.groupby("flagella").tail(1)[["flagella", "biomass"]].sort_values("flagella")
    data["relative_biomass"] = data.biomass / data.biomass.max()
    fig, ax = plt.subplots(figsize=(3.3, 3.2))
    ax.bar(
        np.arange(len(data)), data.relative_biomass, color=[FLAG_COLORS[x] for x in data.flagella]
    )
    for i, value in enumerate(data.relative_biomass):
        ax.text(i, value + 0.02, f"{value:.2f}", ha="center", fontsize=8)
    style(ax)
    ax.set(
        xticks=np.arange(len(data)),
        xticklabels=[f"{x:.3g}" for x in data.flagella],
        xlabel="Flagella mass fraction",
        ylabel="Relative final biomass",
        ylim=(0, 1.12),
    )
    return data, fig, sorted((MODEL_RESULTS / "swimming/8500").glob("dynamic_flag_*.csv"))


def panel_s2_a() -> tuple[pd.DataFrame, plt.Figure, list[Path]]:
    proteins = protein_table()
    data = (
        proteins[proteins.sector_short == "Fla"]
        .groupby(["uniprot_id", "gene_name_short", "mutant"], as_index=False)
        .mass_fraction.mean()
    )
    order = (
        data.groupby("gene_name_short")
        .mass_fraction.mean()
        .sort_values(ascending=False)
        .index.tolist()
    )
    ncols = 9
    nrows = math.ceil(len(order) / ncols)
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=panel_figsize(*TRUE_PAGE_SIZE_PANELS["S2_A"]),
        sharey=True,
        squeeze=False,
        layout="constrained",
    )
    fig.get_layout_engine().set(w_pad=0.025, h_pad=0.035, wspace=0.012, hspace=0.06)
    ceiling = max(0.008, float(data.mass_fraction.max()) * 1.05)
    # Most genes sit near zero.  A floor at exactly zero draws those marks on
    # top of the bottom spine, so the axis starts one marker radius below it.
    floor = -0.07 * ceiling
    edges = [marker_edge(MUTANT_COLORS[mutant]) for mutant in MUTANTS]
    for ax, gene in zip(axes.ravel(), order, strict=False):
        part = data[data.gene_name_short == gene].set_index("mutant").mass_fraction.reindex(MUTANTS)
        ax.scatter(
            np.arange(len(MUTANTS)),
            part,
            c=[MUTANT_COLORS[m] for m in MUTANTS],
            s=POINT_MARKER_SIZE,
            edgecolors=[edge[0] for edge in edges],
            linewidths=[edge[1] for edge in edges],
            zorder=3,
        )
        ax.set_title(str(gene), fontsize=TICK_FONT_PT, pad=1.5)
        ax.set_xticks([])
        ax.set_xlim(-0.8, len(MUTANTS) - 0.2)
        ax.set_ylim(floor, ceiling)
        ax.set_yticks(np.linspace(0, ceiling, 3))
        ax.tick_params(axis="y", pad=1.0)
        style(ax)
    for ax in axes.ravel()[len(order) :]:
        ax.axis("off")
    fig.supylabel("Protein mass fraction")
    # The strains are the only x information in each cell, so a shared legend
    # replaces the former title, which repeated the figure caption.
    handles = [
        Line2D(
            [],
            [],
            linestyle="none",
            marker="o",
            markersize=math.sqrt(POINT_MARKER_SIZE),
            markerfacecolor=MUTANT_COLORS[mutant],
            markeredgecolor=edge[0],
            markeredgewidth=edge[1],
            label=mutant,
        )
        for mutant, edge in zip(MUTANTS, edges, strict=True)
    ]
    fig.legend(
        handles=handles,
        loc="outside upper center",
        ncol=len(MUTANTS),
        frameon=False,
        handletextpad=0.25,
        columnspacing=1.1,
        borderpad=0.0,
    )
    return data, fig, [PROTEOMICS / "protein_massfrac_annotated.csv", OVERRIDE_TABLE]


# Only S2_A is dispatched. Every other builder in this file is superseded.
#   F3_A drew the measured sector composition of the July Figure 3A.  That panel
#   is now Figure 4D and is built by analyses/figure_04_revision/build.py, so
#   dispatching it here would overwrite the Figure 3A schematic placeholder.
#   S3_A duplicated the lower half of Figure 4F, so Supplementary Figure 3 was
#   withdrawn on 12 August 2026.
#   F3_B to F3_E are now built by analyses/figure_03_revision. They were still
#   dispatched here until 15 August, which was the same hazard already recorded
#   for F3_A: build() writes metadata/provenance/figure_03/<panel>.json, the
#   live central document, so running this file overwrote the revision
#   provenance with the superseded collaborator version.
#   F2_G, F2_H, F3_F and F3_G are not registered panels in config/panels.csv.
# The builder functions stay for reference. They are unreachable.
BUILDERS = {
    "S2_A": panel_s2_a,
}


def build(panel_id: str) -> None:
    data, fig, scientific_inputs = BUILDERS[panel_id]()
    source = write_source(panel_id, f"{panel_id}_source_data.csv", data)
    graphics = save(fig, panel_id)
    panel_root = PROJECT / "analyses" / PANEL_DIRS[panel_id]
    provenance = {
        "schema_version": "1.0.0",
        "panel_id": panel_id,
        "status": "partial_reproduction",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "analyses/collaborator_science/build_panels.py",
            "--panel",
            panel_id,
        ],
        "inputs": [
            artifact(Path(__file__).resolve()),
            artifact(panel_root / "config/panel.json"),
            artifact(panel_root / "scripts/reproduce.py"),
            artifact(MODEL_SOURCE / "UPSTREAM_SOURCE.md"),
            *[artifact(path) for path in scientific_inputs],
        ],
        "outputs": [artifact(source, len(data)), *[artifact(path) for path in graphics]],
        "software": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
            "cell_economy_commit": "c5e534de7e2102d330356ecb6e78f6346f3cc14a",
        },
        "parameters": {
            "backend": "Python 3.12",
            "source_delivery": "2026-08-12",
            "panel": panel_id,
        },
        "random_seeds": {},
        "limitations": [
            (
                "Proteomics panels reproduce from the delivered protein-level export; "
                "raw MS files, FASTA and Spectronaut settings were not supplied."
            ),
            (
                "Model panels reproduce from fixed collaborator result tables. A local "
                "GEKKO 1.3.2 solve was attempted: solver 3 was unavailable and the "
                "APOPT fallback did not find a solution."
            ),
            "The collaborator parameter-sampling log does not record a random seed.",
        ],
    }
    rendered = json.dumps(provenance, indent=2) + "\n"
    (panel_root / "metadata/provenance.json").write_text(rendered, encoding="utf-8")
    central = (
        PROJECT / "metadata/provenance" / PANEL_DIRS[panel_id].split("/")[0] / f"{panel_id}.json"
    )
    central.parent.mkdir(parents=True, exist_ok=True)
    central.write_text(rendered, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", choices=[*BUILDERS, "all"], default="all")
    args = parser.parse_args()
    panels = BUILDERS if args.panel == "all" else [args.panel]
    for panel in panels:
        build(panel)


if __name__ == "__main__":
    main()
