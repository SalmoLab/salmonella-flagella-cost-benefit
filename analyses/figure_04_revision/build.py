#!/usr/bin/env python3
"""Build revised Figure 4 panels and associated proteome-allocation analyses."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator
from scipy.stats import linregress, t

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))
# The sector-override table sits beside this builder and is also read by
# analyses/collaborator_science/build_panels.py, so both figures share it.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sector_overrides import (  # noqa: E402
    OVERRIDE_TABLE,
    apply_sector_overrides,
    load_sector_overrides,
)

from flagella_repro.theme import (  # noqa: E402
    BASE_FONT_PT,
    DENSITY_MARKER_SIZE,
    KEY_SWATCH,
    MINIMUM_ON_PAGE_FONT_PT,
    PALETTE,
    POINT_MARKER_SIZE,
    SEGMENT_SEPARATOR_COLOR,
    SEGMENT_SEPARATOR_WIDTH,
    SUMMARY_INK,
    apply_publication_style,
    get_sector_color,
    get_strain_style,
    marker_edge,
    panel_figsize,
    save_figure,
)

PROTEOMICS = PROJECT / "data/external/promoter_series_proteomics"
MODEL_RESULTS = PROJECT / "data/external/cell_economy_results"
SCHEMATIC = PROJECT / "assets/schematics/salmonella_model.svg"
PROCESSED = PROJECT / "data/processed/figure_04_revision"
SOURCE = PROJECT / "data/source_data/figure_04_revision"
BUILD_SOURCE = PROJECT / "build/source_data/Figure_4"
STATISTICS = PROJECT / "build/statistics/Figure_4"
OUTPUT = PROJECT / "build/panels/Figure_4"
# Diagnostics stay outside build/panels. That tree holds registered manuscript
# panels only, so a diagnostic there inflates every panel count and QA sweep.
DIAGNOSTICS = PROJECT / "build/diagnostics/Figure_4"
ANALYSIS_ROOT = PROJECT / "analyses/figure_04_revision"

SECTORS = ["Oth", "Rib", "Cbn", "Aab", "Etc", "Lpb", "Fla", "Tra"]
# Panel B and the A1 regression both read flagellar allocation as the predictor,
# so the flagellar sector is never also a response.
RESPONSE_SECTORS = [sector for sector in SECTORS if sector != "Fla"]
STRAINS = ["ΔflhDC", "Ppro1-flhDC", "PproA-flhDC", "WT", "PproB-flhDC", "PproD-flhDC"]
CHEMOTAXIS_GENES = frozenset({"cheA", "cheW", "tsr", "tar"})
STRUCTURAL_GENES = frozenset(
    {
        "fliC",
        "fljB",
        "fliD",
        "flgK",
        "flgL",
        "flgE",
        "flgB",
        "flgC",
        "flgF",
        "flgG",
        "flgH",
        "flgI",
        "fliE",
        "fliF",
        "fliG",
        "fliM",
        "fliN",
        "motA",
        "motB",
    }
)
LABEL_THRESHOLD = 0.15
# A share of a sector bar says nothing on its own: a protein reaches a large
# share of a nearly empty bar while carrying almost no protein.  Every label
# therefore also has to carry at least this much of the measured proteome.
# 6.0e-4 is 0.06% of total protein mass.  It is the smallest round value that
# excludes the two flat housekeeping proteins the delivery mis-assigned to the
# flagellar sector (RpoD 4.7e-4, RbsB 5.2e-4) and keeps every protein the share
# rule names on genuine grounds (smallest retained: PtsI 7.1e-4).
ABSOLUTE_FLOOR = 6.0e-4
# The share rule alone cannot name Tsr: it is the second flagellar protein of
# the series and rises 150-fold, but FliC takes so much of the bar that Tsr
# stays near 12%.  A sector's most abundant proteins are therefore named as
# well.  The rank is capped because sector subtotals span a factor of 30: one
# absolute floor that admits Tsr in the flagellar sector would admit all ten
# ribosomal proteins, which no sub-axes of panel C can carry.
ABUNDANCE_LEADER_RANK = 3

# Every panel is drawn at the physical size of its slot in config/assembly_figure_04.yaml,
# so a point size requested here is the point size that reaches the printed page.  Dense
# secondary text (legends, gene labels, the strain ticks of panel C) sits on the theme's
# legibility floor; nothing is allowed below it.  No panel uses mathtext, because
# matplotlib draws a mathtext exponent at 0.7 of its label size and would fall through
# that floor.
DENSE_FONT_PT = MINIMUM_ON_PAGE_FONT_PT
STRAIN_TICKS = ["Δ", "P1", "PA", "WT", "PB", "PD"]
# Panel C reserves the right part of each axes for external protein labels.  The bars
# occupy 0..5, the leader lines start at PANEL_C_LABEL_X, and the axes end at
# PANEL_C_X_LIMIT, so the gutter is part of the data range and constrained_layout can
# account for it.
PANEL_C_LABEL_X = 5.7
PANEL_C_X_LIMIT = 7.4
# A leader line points at the strain where its segment is thickest as drawn.
# Several strains often draw the same thickness, and the leader of the leftmost
# of them crosses the whole axes.  Any strain that draws at least this share of
# the thickest segment is an equally good target, so the rightmost of them is
# taken and the leader stays short.
PANEL_C_ANCHOR_TOLERANCE = 0.8
OVERRIDE_NOTE = (
    "Sector assignment follows the delivered KEGG mapping except for the proteins listed "
    "in analyses/figure_04_revision/config/protein_sector_overrides.csv, which records one "
    "reason per protein."
)
EXPORT_NOTE = (
    "Proteomics begins from the collaborator protein-level export rather than raw MS files."
)


def _ensure_dirs() -> None:
    for path in (PROCESSED, SOURCE, BUILD_SOURCE, STATISTICS, OUTPUT, DIAGNOSTICS):
        path.mkdir(parents=True, exist_ok=True)


def write_source(table: pd.DataFrame, panel: str, filename: str) -> None:
    """Write tracked canonical data and the matching organized build copy."""
    tracked = SOURCE / panel / filename
    built = BUILD_SOURCE / panel / filename
    tracked.parent.mkdir(parents=True, exist_ok=True)
    built.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(tracked, index=False)
    table.to_csv(built, index=False)


def write_diagnostic_source(table: pd.DataFrame, filename: str) -> None:
    """Write a diagnostic table under build/diagnostics, not the Source Data tree."""
    path = DIAGNOSTICS / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)


def panel_stem(label: str) -> Path:
    return OUTPUT / label / f"Figure_4_{label}"


def _artifact(path: Path) -> dict[str, object]:
    result: dict[str, object] = {
        "relative_path": path.relative_to(PROJECT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }
    if path.suffix == ".csv":
        result["rows"] = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
    return result


def write_provenance(labels: list[str]) -> None:
    """Write panel-local provenance ready for central-registry integration."""
    model_inputs = sorted((MODEL_RESULTS / "c_limitation").glob("steady_state_flag_*.csv"))
    # Every measured panel is summed from the protein-level export through the
    # documented sector overrides, so both files are inputs of all of them.
    measured = [
        PROTEOMICS / "sector_mass_fractions.tsv",
        PROTEOMICS / "protein_massfrac_annotated.csv",
        OVERRIDE_TABLE,
    ]
    panel_inputs = {
        "A": [SCHEMATIC],
        "B": [*measured, *model_inputs],
        "C": measured,
        "D": measured,
        "E": model_inputs,
        "F": [
            *measured,
            PROTEOMICS / "population_growth_mutants.csv",
            *model_inputs,
        ],
    }
    limitations = {
        "A": [
            "Exact editable collaborator SVG is preserved; local Cairo preview export "
            "is unavailable.",
            "Schematic text prints at 2.65-4.54 pt, below the 6 pt floor. The asset "
            "declares 7, 9 and 12 px in a 360x240 pt viewBox and its artwork fills "
            "335x230 pt of it. The 48x55 mm slot scales the asset by 0.133, which is "
            "set by width. A 6 pt body text needs a slot about 64 mm wide. Enlarging "
            "the slot or editing collaborator content are both outside this panel.",
        ],
        "B": [EXPORT_NOTE, OVERRIDE_NOTE],
        "C": [EXPORT_NOTE, OVERRIDE_NOTE],
        "D": [EXPORT_NOTE, OVERRIDE_NOTE],
        "E": [
            "Panel is regenerated from supplied solver result tables; the exact IPOPT "
            "runtime is unavailable locally."
        ],
        "F": [
            "Model curve begins from supplied solver results; experimental growth and "
            "proteomics batches are not paired at replicate level.",
            OVERRIDE_NOTE,
        ],
    }
    for label in labels:
        panel_root = ANALYSIS_ROOT / f"panel_{label.lower()}"
        wrapper = panel_root / "scripts/reproduce.py"
        config = panel_root / "config/panel.json"
        outputs = sorted((OUTPUT / label).glob(f"Figure_4_{label}.*"))
        outputs.extend(sorted((BUILD_SOURCE / label).glob("*.csv")))
        if label == "B":
            outputs.extend(sorted((STATISTICS / "B").glob("*.csv")))
        document = {
            "schema_version": "1.0.0",
            "panel_id": f"F4_{label}",
            "status": "partial_reproduction",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "command": [
                ".venv/bin/python3.12",
                wrapper.relative_to(PROJECT).as_posix(),
            ],
            "inputs": [
                _artifact(Path(__file__).resolve()),
                _artifact(wrapper),
                _artifact(config),
                *map(_artifact, panel_inputs[label]),
            ],
            "outputs": [_artifact(path) for path in outputs],
            "software": {
                "python": platform.python_version(),
                "pandas": pd.__version__,
                "numpy": np.__version__,
                "matplotlib": plt.matplotlib.__version__,
            },
            "parameters": {
                "overlay_reference": "delta from experimental ΔflhDC and model 0%",
                "protein_label_relative_threshold": LABEL_THRESHOLD,
                "protein_label_absolute_floor": ABSOLUTE_FLOOR,
                "protein_label_abundance_leader_rank": ABUNDANCE_LEADER_RANK,
                "sector_overrides": {
                    str(row.uniprot_id): (
                        f"{row.delivered_sector_short} to {row.override_sector_short}"
                    )
                    for row in load_sector_overrides().itertuples()
                },
                "a1_inferential_unit": "six condition means",
            },
            "random_seeds": {},
            "limitations": limitations[label],
        }
        metadata = panel_root / "metadata/provenance.json"
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def mass_table() -> pd.DataFrame:
    """Return sector mass fractions with the documented sector overrides applied.

    The delivered sector table is the exact per-sample sum of the delivered
    protein table, so the sector totals are re-summed from the overridden
    protein table instead of being patched.  Every other column of the delivery
    is kept, and a delivery whose sector totals stop matching its own protein
    table raises.
    """
    frame = pd.read_csv(PROTEOMICS / "sector_mass_fractions.tsv", sep="\t")
    frame = frame.dropna(subset=["sector_short", "replicate"]).copy()
    frame["replicate"] = frame.replicate.astype(int)
    keys = ["mutant", "replicate", "sector_short"]
    delivered = _sector_totals(pd.read_csv(PROTEOMICS / "protein_massfrac_annotated.csv"))
    check = frame.merge(delivered, on=keys, suffixes=("", "_summed"))
    if len(check) != len(frame) or not np.allclose(check.mass_fraction, check.mass_fraction_summed):
        raise ValueError("delivered sector totals are not the sum of the delivered protein table")
    overridden = _sector_totals(protein_table())
    updated = frame.drop(columns="mass_fraction").merge(overridden, on=keys, how="left")
    if updated.mass_fraction.isna().any():
        raise ValueError("a sector lost every protein under the documented overrides")
    return updated


def _sector_totals(proteins: pd.DataFrame) -> pd.DataFrame:
    """Sum a protein-level table into one mass fraction per sample and sector."""
    totals = proteins.groupby(
        ["mutant", "replicate", "sector_short"], as_index=False
    ).mass_fraction.sum()
    totals["replicate"] = totals.replicate.astype(int)
    return totals


def protein_table() -> pd.DataFrame:
    """Return the delivered protein-level export with the sector overrides applied."""
    delivered = pd.read_csv(PROTEOMICS / "protein_massfrac_annotated.csv", low_memory=False)
    return apply_sector_overrides(delivered)


def growth_table() -> pd.DataFrame:
    raw = pd.read_csv(PROTEOMICS / "population_growth_mutants.csv")
    raw = raw[["strain", "experiment_day", "doubling_time_min"]].dropna()
    per_experiment = raw.groupby(
        ["strain", "experiment_day"], as_index=False
    ).doubling_time_min.mean()
    per_experiment["growth_rate_1h"] = 60 * math.log(2) / per_experiment["doubling_time_min"]
    mapping = {
        "EM9662": "Ppro1-flhDC",
        "EM9661": "PproA-flhDC",
        "TH9677": "WT",
        "EM9660": "PproB-flhDC",
        "EM8513": "PproD-flhDC",
    }
    per_experiment["mutant"] = per_experiment.strain.map(mapping)
    return per_experiment.dropna(subset=["mutant"])


def model_sector_table() -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for path in sorted((MODEL_RESULTS / "c_limitation").glob("steady_state_flag_*.csv")):
        frame = pd.read_csv(path)
        selected = frame.loc[np.isclose(frame["cex"], 1.0)].copy()
        if len(selected) != 1:
            raise ValueError(f"Expected one cex=1.0 row in {path}, found {len(selected)}")
        selected["flagella"] = float(path.stem.rsplit("_", 1)[1])
        rows.append(selected)
    wide = pd.concat(rows, ignore_index=True).sort_values("flagella")
    long = wide.melt(
        id_vars=["flagella", "mu"],
        value_vars=[f"a_{sector.lower()}" for sector in SECTORS],
        var_name="sector_column",
        value_name="mass_fraction",
    )
    long["sector_short"] = long.sector_column.str.removeprefix("a_").str.capitalize()
    return long.drop(columns="sector_column")


def benjamini_hochberg(p_values: pd.Series) -> pd.Series:
    values = p_values.to_numpy(float)
    order = np.argsort(values)
    ranked = values[order]
    adjusted = np.minimum.accumulate((ranked * len(values) / np.arange(1, len(values) + 1))[::-1])[
        ::-1
    ]
    result = np.empty_like(adjusted)
    result[order] = np.minimum(adjusted, 1.0)
    return pd.Series(result, index=p_values.index)


def analyse_a1() -> pd.DataFrame:
    """Regress condition-level sector means on flagellar mass fraction."""
    mass = mass_table()
    wide = mass.pivot(index=["mutant", "replicate"], columns="sector_short", values="mass_fraction")
    means = wide.groupby("mutant").mean().reindex(STRAINS)
    rows: list[dict[str, float | int | str]] = []
    for sector in RESPONSE_SECTORS:
        fit = linregress(means["Fla"], means[sector])
        critical = float(t.ppf(0.975, len(means) - 2))
        rows.append(
            {
                "sector_short": sector,
                "predictor": "condition_mean_flagellar_mass_fraction",
                "slope": fit.slope,
                "slope_ci95_low": fit.slope - critical * fit.stderr,
                "slope_ci95_high": fit.slope + critical * fit.stderr,
                "p_value": fit.pvalue,
                "r_squared": fit.rvalue**2,
                "n_condition_means": len(means),
                "biological_replicates_per_condition": 4,
            }
        )
    result = pd.DataFrame(rows)
    result["p_bh"] = benjamini_hochberg(result.p_value)
    result["multiple_testing_family"] = "seven non-Fla sectors; Fla is the predictor"
    return result


def analyse_a5() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare summed chemotaxis and structural flagellar-protein allocation."""
    frame = protein_table().query("sector_short == 'Fla'").copy()
    frame["protein_group"] = np.select(
        [
            frame.gene_name_short.isin(CHEMOTAXIS_GENES),
            frame.gene_name_short.isin(STRUCTURAL_GENES),
        ],
        ["chemotaxis", "structural"],
        default="other_flagellar_sector",
    )
    grouped = (
        frame.groupby(["mutant", "replicate", "protein_group"], as_index=False)
        .mass_fraction.sum()
        .pivot(index=["mutant", "replicate"], columns="protein_group", values="mass_fraction")
        .reset_index()
    )
    means = grouped.groupby("mutant", as_index=False)[["chemotaxis", "structural"]].mean()
    means = means.set_index("mutant").reindex(STRAINS).reset_index()
    fit = linregress(np.log10(means.structural), np.log10(means.chemotaxis))
    critical = float(t.ppf(0.975, len(means) - 2))
    summary = pd.DataFrame(
        [
            {
                "comparison": "log10 chemotaxis allocation ~ log10 structural allocation",
                "chemotaxis_genes": ";".join(sorted(CHEMOTAXIS_GENES)),
                "structural_genes": ";".join(sorted(STRUCTURAL_GENES)),
                "slope": fit.slope,
                "slope_ci95_low": fit.slope - critical * fit.stderr,
                "slope_ci95_high": fit.slope + critical * fit.stderr,
                "p_value_slope_equals_zero": fit.pvalue,
                "p_value_slope_equals_one": 2
                * t.sf(abs((fit.slope - 1) / fit.stderr), len(means) - 2),
                "r_squared": fit.rvalue**2,
                "n_condition_means": len(means),
                "interpretation_boundary": (
                    "Descriptive protein-allocation comparison only; does not test "
                    "chemotactic function."
                ),
            }
        ]
    )
    return grouped, summary


def top10_table() -> pd.DataFrame:
    proteins = protein_table()
    grouped = proteins.groupby(
        ["uniprot_id", "gene_name_short", "sector_short", "mutant"],
        dropna=False,
        as_index=False,
    ).mass_fraction.mean()
    totals = grouped.groupby(["sector_short", "uniprot_id"], as_index=False).mass_fraction.sum()
    keep = (
        totals.sort_values(["sector_short", "mass_fraction"], ascending=[True, False])
        .groupby("sector_short")
        .head(10)
    )
    selected = grouped.merge(
        keep[["sector_short", "uniprot_id"]], on=["sector_short", "uniprot_id"]
    )
    subtotal = selected.groupby(["sector_short", "mutant"]).mass_fraction.transform("sum")
    selected["fraction_of_top10_subtotal"] = selected.mass_fraction / subtotal
    return selected


def label_audit(top10: pd.DataFrame) -> pd.DataFrame:
    """Decide which proteins panel C names, and record why for every candidate.

    A protein is named when it carries at least ``ABSOLUTE_FLOOR`` of the
    measured proteome in some condition and, in addition, either reaches
    ``LABEL_THRESHOLD`` of its sector's top-10 subtotal in a condition where it
    also clears the floor, or ranks among the ``ABUNDANCE_LEADER_RANK`` most
    abundant proteins of its sector.  FliC is named regardless.
    """
    rows = top10.assign(
        above_floor=top10.mass_fraction.ge(ABSOLUTE_FLOOR),
        share_and_floor=top10.fraction_of_top10_subtotal.ge(LABEL_THRESHOLD)
        & top10.mass_fraction.ge(ABSOLUTE_FLOOR),
    )
    audit = (
        rows.groupby(["sector_short", "gene_name_short"], as_index=False)
        .agg(
            max_fraction_of_top10_subtotal=("fraction_of_top10_subtotal", "max"),
            max_mass_fraction=("mass_fraction", "max"),
            above_absolute_floor=("above_floor", "any"),
            share_rule=("share_and_floor", "any"),
        )
        .copy()
    )
    audit["abundance_rank_in_sector"] = (
        audit.groupby("sector_short").max_mass_fraction.rank(ascending=False, method="min")
    ).astype(int)
    audit["leader_rule"] = audit.above_absolute_floor & audit.abundance_rank_in_sector.le(
        ABUNDANCE_LEADER_RANK
    )
    audit["always_keep"] = audit.gene_name_short.eq("fliC")
    audit["selected"] = audit.always_keep | audit.share_rule | audit.leader_rule
    audit["relative_threshold"] = LABEL_THRESHOLD
    audit["absolute_floor"] = ABSOLUTE_FLOOR
    audit["abundance_leader_rank"] = ABUNDANCE_LEADER_RANK
    audit["reason"] = [_label_reason(row) for row in audit.itertuples()]
    return audit.sort_values(
        ["sector_short", "selected", "max_mass_fraction"],
        ascending=[True, False, False],
    )


def _label_reason(row: object) -> str:
    """Return the one-line audit reason for a label decision."""
    if row.always_keep:  # type: ignore[attr-defined]
        return "always retain FliC"
    reasons = []
    if row.share_rule:  # type: ignore[attr-defined]
        reasons.append("share of sector subtotal above the relative threshold")
    if row.leader_rule:  # type: ignore[attr-defined]
        reasons.append("among the most abundant proteins of its sector")
    if reasons:
        return "; ".join(reasons)
    if not row.above_absolute_floor:  # type: ignore[attr-defined]
        if row.max_fraction_of_top10_subtotal >= LABEL_THRESHOLD:  # type: ignore[attr-defined]
            return "large share of a nearly empty bar; below the absolute floor"
        return "below the absolute floor"
    return "below the relative threshold and outside the abundance leaders"


def _strain_color(strain: str) -> str:
    canonical_id = {
        "ΔflhDC": "EM16223",
        "Ppro1-flhDC": "EM9662",
        "PproA-flhDC": "EM9661",
        "WT": "TH9677",
        "PproB-flhDC": "EM9660",
        "PproD-flhDC": "EM8513",
    }[strain]
    return get_strain_style(canonical_id)["color"]


def _repel_positions(
    values: list[float], minimum_gap: float, lower: float, upper: float
) -> list[float]:
    if not values:
        return []
    order = np.argsort(values)
    placed = np.asarray(values, float)[order]
    placed[0] = max(placed[0], lower)
    for idx in range(1, len(placed)):
        placed[idx] = max(placed[idx], placed[idx - 1] + minimum_gap)
    overflow = placed[-1] - upper
    if overflow > 0:
        placed -= overflow
        for idx in range(len(placed) - 2, -1, -1):
            placed[idx] = min(placed[idx], placed[idx + 1] - minimum_gap)
    inverse = np.empty_like(order)
    inverse[order] = np.arange(len(order))
    return placed[inverse].tolist()


def _leader_anchor(
    label: str, values: np.ndarray, base: np.ndarray, ymax: float
) -> tuple[str, float, float]:
    """Return where a label's leader line should touch its stacked segment.

    The target is the strain whose segment is thickest as drawn, that is as a
    share of the axes height rather than as a share of its own bar.  A protein
    that is flat across the series draws the same thickness everywhere, and the
    leftmost such strain would drag its leader across the whole axes.  Any
    strain within ``PANEL_C_ANCHOR_TOLERANCE`` of the thickest one is therefore
    an equally good target and the rightmost of them wins.

    Example:
        >>> _leader_anchor("x", np.array([1.0, 1.0]), np.zeros(2), 2.0)[1]
        1.0
    """
    thickness = values / ymax
    candidates = np.flatnonzero(thickness >= PANEL_C_ANCHOR_TOLERANCE * thickness.max())
    index = int(candidates[-1])
    return (label, float(index), float(base[index] + values[index] / 2))


def _compact_y_axis(ax: plt.Axes, nbins: int = 3) -> None:
    """Thin the y ticks so a narrow panel spends its width on data.

    The tick values are unchanged.  A scientific-notation multiplier is not used:
    matplotlib draws its exponent through mathtext at 0.7 of the surrounding size,
    which falls below the theme's on-page legibility floor.
    """
    # Dropping the 2.5 step keeps every tick label short, which widens the data area.
    ax.yaxis.set_major_locator(MaxNLocator(nbins=nbins, steps=[1, 2, 5, 10]))


def write_analysis_tables() -> dict[str, pd.DataFrame]:
    _ensure_dirs()
    a1 = analyse_a1()
    a5_replicates, a5_summary = analyse_a5()
    top10 = top10_table()
    labels = label_audit(top10)
    model = model_sector_table()
    tables = {
        "A1_sector_regressions": a1,
        "A5_chemotaxis_structural_replicates": a5_replicates,
        "A5_chemotaxis_scaling": a5_summary,
        "protein_label_audit": labels,
        "model_sector_allocations": model,
    }
    for name, table in tables.items():
        table.to_csv(PROCESSED / f"{name}.csv", index=False)
    (STATISTICS / "B").mkdir(parents=True, exist_ok=True)
    a1.to_csv(STATISTICS / "B/A1_sector_regressions.csv", index=False)
    (STATISTICS / "A5").mkdir(parents=True, exist_ok=True)
    a5_replicates.to_csv(STATISTICS / "A5/chemotaxis_structural_replicates.csv", index=False)
    a5_summary.to_csv(STATISTICS / "A5/chemotaxis_scaling.csv", index=False)
    return tables


def panel_a() -> None:
    """Preserve the collaborator's fully editable schematic as panel A."""
    destination = panel_stem("A").with_suffix(".svg")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SCHEMATIC, destination)
    asset = pd.DataFrame(
        [
            {
                "role": "editable_model_schematic",
                "asset": "assets/schematics/salmonella_model.svg",
                "sha256": "996e3be8ca7df8bb87c03857fb38e7815f7f8f0ce641fccd47b93673186319f4",
                "upstream_commit": "c5e534de7e2102d330356ecb6e78f6346f3cc14a",
                "formats": "editable SVG; PDF/PNG preview blocked by local ARM64 Cairo mismatch",
            }
        ]
    )
    write_source(asset, "A", "schematic_asset.csv")


def overlay_data(relative: bool) -> pd.DataFrame:
    mass = mass_table()
    exp_reference = mass.query("mutant == 'ΔflhDC'").groupby("sector_short").mass_fraction.mean()
    fla_reference = float(exp_reference["Fla"])
    experiment = mass.copy()
    experiment["x_flagella"] = experiment.mass_fraction.where(experiment.sector_short.eq("Fla"))
    x_by_sample = (
        experiment.query("sector_short == 'Fla'").set_index(["mutant", "replicate"]).mass_fraction
    )
    experiment["x_flagella"] = [
        x_by_sample[(row.mutant, row.replicate)] for row in experiment.itertuples()
    ]
    experiment["series"] = "experiment"
    experiment["value"] = experiment.mass_fraction
    model = model_sector_table().rename(
        columns={"flagella": "x_flagella", "mass_fraction": "value"}
    )
    model["mutant"] = "model"
    model["replicate"] = np.nan
    model["series"] = "model"
    if relative:
        experiment["value"] -= experiment.sector_short.map(exp_reference)
        experiment["x_flagella"] -= fla_reference
        model_reference = model.query("x_flagella == 0").set_index("sector_short").value
        model["value"] -= model.sector_short.map(model_reference)
    return pd.concat(
        [
            experiment[["mutant", "replicate", "sector_short", "x_flagella", "value", "series"]],
            model[["mutant", "replicate", "sector_short", "x_flagella", "value", "series"]],
        ],
        ignore_index=True,
    )


def _scatter_strain(ax: plt.Axes, x: object, y: object, strain: str, *, summary: bool) -> None:
    """Draw one strain's replicate cloud or its condition mean.

    Both marks use the strain's own colour, the shared marker sizes and the
    shared edge policy, so no panel invents a rim of its own.
    """
    fill = _strain_color(strain)
    edge_color, edge_width = marker_edge(fill)
    ax.scatter(
        x,
        y,
        s=POINT_MARKER_SIZE if summary else DENSITY_MARKER_SIZE,
        marker="D" if summary else "o",
        color=fill,
        alpha=1.0 if summary else 0.55,
        edgecolor=edge_color,
        linewidth=edge_width,
        zorder=4 if summary else 3,
    )


def _plot_model_line(
    ax: plt.Axes,
    x_values: object,
    y_values: object,
    flagella: object,
    measured_max: float,
) -> None:
    """Draw the model prediction, dashed where no strain reached that far.

    The model is solved to 5% flagellar allocation, but the promoter series only
    reaches about 3.3%.  ``flagella`` is the model's flagellar allocation for
    each point and ``measured_max`` the largest measured one, both in the same
    units; ``x_values`` and ``y_values`` are the drawn coordinates.  The two
    parts share an interpolated boundary point, so the line has no gap.
    """
    x = np.asarray(x_values, float)
    y = np.asarray(y_values, float)
    allocation = np.asarray(flagella, float)
    order = np.argsort(allocation)
    x, y, allocation = x[order], y[order], allocation[order]
    boundary = float(np.clip(measured_max, allocation.min(), allocation.max()))
    edge = (float(np.interp(boundary, allocation, x)), float(np.interp(boundary, allocation, y)))
    inside = allocation <= boundary
    outside = allocation >= boundary
    ax.plot(
        np.append(x[inside], edge[0]),
        np.append(y[inside], edge[1]),
        color=SUMMARY_INK,
        lw=0.9,
    )
    ax.plot(
        np.insert(x[outside], 0, edge[0]),
        np.insert(y[outside], 0, edge[1]),
        color=SUMMARY_INK,
        lw=0.9,
        ls=(0, (2.2, 1.4)),
    )


def _overlay_handles() -> list[plt.Line2D]:
    """Return the shared key of panel B: two model lines, two marks, six strains."""
    handles = [
        plt.Line2D([], [], color=SUMMARY_INK, lw=0.9, label="model"),
        plt.Line2D(
            [], [], color=SUMMARY_INK, lw=0.9, ls=(0, (2.2, 1.4)), label="model, beyond data"
        ),
        plt.Line2D(
            [],
            [],
            marker="o",
            ls="",
            ms=math.sqrt(DENSITY_MARKER_SIZE),
            color=KEY_SWATCH,
            label="replicate",
        ),
        plt.Line2D(
            [],
            [],
            marker="D",
            ls="",
            ms=math.sqrt(POINT_MARKER_SIZE),
            color=KEY_SWATCH,
            label="condition mean",
        ),
    ]
    handles.extend(
        plt.Line2D(
            [],
            [],
            marker="D",
            ls="",
            ms=math.sqrt(POINT_MARKER_SIZE),
            color=_strain_color(strain),
            label=strain,
        )
        for strain in STRAINS
    )
    return handles


def _plot_overlay(data: pd.DataFrame, target: Path, relative: bool) -> None:
    # The flagellar sub-axes was the identity line: flagellar allocation is the
    # x variable, so it plotted itself, and the model imposed a_Fla == a_fla.
    # It is dropped, and the freed cell of the 2x4 grid now carries the key.
    fig, axes = plt.subplots(2, 4, figsize=panel_figsize("Figure_4", "B"), constrained_layout=True)
    flat = axes.ravel()
    measured_max = float(data.query("series == 'experiment'").x_flagella.max())
    for ax, sector in zip(flat, RESPONSE_SECTORS, strict=False):
        part = data.query("sector_short == @sector")
        model = part.query("series == 'model'").sort_values("x_flagella")
        exp = part.query("series == 'experiment'")
        _plot_model_line(
            ax, model.x_flagella * 100, model.value, model.x_flagella, measured_max
        )
        for strain in STRAINS:
            points = exp.query("mutant == @strain")
            _scatter_strain(ax, points.x_flagella * 100, points.value, strain, summary=False)
            _scatter_strain(
                ax,
                points.x_flagella.mean() * 100,
                points.value.mean(),
                strain,
                summary=True,
            )
        if relative:
            ax.axhline(0, color=PALETTE["neutral"]["reference"], lw=0.5, zorder=0)
        ax.set_title(sector, pad=2.0)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=3))
        _compact_y_axis(ax)
    # One shared pair of axis titles replaces seven repeats, so the width goes to data.
    fig.supxlabel("Flagellar allocation (%)", fontsize=BASE_FONT_PT)
    fig.supylabel("Change from reference" if relative else "Mass fraction", fontsize=BASE_FONT_PT)
    key_axes = flat[len(RESPONSE_SECTORS)]
    key_axes.axis("off")
    key_axes.legend(
        handles=_overlay_handles(),
        loc="center",
        frameon=False,
        fontsize=DENSE_FONT_PT,
        handlelength=1.1,
        handletextpad=0.4,
        labelspacing=0.35,
        borderpad=0.0,
    )
    save_figure(fig, target)
    plt.close(fig)


def panel_b_and_raw_diagnostic() -> None:
    delta = overlay_data(relative=True)
    raw = overlay_data(relative=False)
    write_source(delta, "B", "delta_overlay.csv")
    write_diagnostic_source(raw, "raw_overlay.csv")
    _plot_overlay(delta, panel_stem("B"), relative=True)
    _plot_overlay(raw, DIAGNOSTICS / "diagnostic_raw_overlay", relative=False)


def panel_c() -> None:
    data = top10_table()
    audit = label_audit(data)
    selected = set(
        map(tuple, audit.loc[audit.selected, ["sector_short", "gene_name_short"]].to_numpy())
    )
    # Four rows of two keep every sector wide enough for six strain ticks and an
    # external label gutter.  All eight sectors share one strain axis, so only the
    # bottom row repeats the tick labels.
    fig, axes = plt.subplots(
        4,
        2,
        figsize=panel_figsize("Figure_4", "C"),
        constrained_layout=True,
        sharex=True,
    )
    for ax, sector in zip(axes.ravel(), SECTORS, strict=True):
        part = data.query("sector_short == @sector")
        bottom = np.zeros(len(STRAINS))
        segments: list[tuple[str, np.ndarray, np.ndarray]] = []
        protein_order = (
            part.groupby(["uniprot_id", "gene_name_short"], as_index=False)
            .mass_fraction.sum()
            .sort_values("mass_fraction", ascending=False)
        )
        shades = np.linspace(0.58, 1.0, len(protein_order))
        for shade, protein in zip(shades, protein_order.itertuples(), strict=True):
            protein_rows = part.query("uniprot_id == @protein.uniprot_id").set_index("mutant")
            values = protein_rows.mass_fraction.reindex(STRAINS, fill_value=0).to_numpy()
            color = get_sector_color(sector)
            ax.bar(
                np.arange(len(STRAINS)),
                values,
                bottom=bottom,
                width=0.82,
                color=color,
                alpha=float(shade),
                edgecolor=SEGMENT_SEPARATOR_COLOR,
                linewidth=SEGMENT_SEPARATOR_WIDTH,
            )
            if (sector, protein.gene_name_short) in selected:
                segments.append((str(protein.gene_name_short), values.copy(), bottom.copy()))
            bottom += values
        ymax = max(bottom) * 1.08 if max(bottom) else 1
        anchors = [_leader_anchor(label, values, base, ymax) for label, values, base in segments]
        # One label line is DENSE_FONT_PT high; each axes is about 11 mm tall, so a
        # 22% minimum gap keeps repelled labels apart at the printed size.
        label_y = _repel_positions(
            [item[2] for item in anchors], ymax * 0.22, 0.10 * ymax, 0.90 * ymax
        )
        for (label, x_anchor, y_anchor), y_text in zip(anchors, label_y, strict=True):
            ax.annotate(
                label,
                xy=(x_anchor, y_anchor),
                xytext=(PANEL_C_LABEL_X, y_text),
                textcoords="data",
                ha="left",
                va="center",
                fontsize=DENSE_FONT_PT,
                arrowprops={
                    "arrowstyle": "-",
                    "color": PALETTE["neutral"]["reference"],
                    "lw": 0.35,
                    "shrinkA": 1.0,
                    "shrinkB": 0.5,
                },
                annotation_clip=False,
            )
        ax.set_xlim(-0.7, PANEL_C_X_LIMIT)
        ax.set_ylim(0, ymax)
        ax.set_title(sector, pad=1.5)
        ax.set_xticks(np.arange(len(STRAINS)), STRAIN_TICKS)
        # Six strain ticks share a narrow axis, so they use the dense-text size.
        ax.tick_params(axis="x", labelsize=DENSE_FONT_PT, pad=1.5)
        _compact_y_axis(ax)
    fig.supylabel("Top-10 mass fraction", fontsize=BASE_FONT_PT)
    write_source(data, "C", "top10_proteins.csv")
    write_source(audit, "C", "label_audit.csv")
    save_figure(fig, panel_stem("C"))
    plt.close(fig)


def panel_d() -> None:
    """Draw the measured mean sector composition, one stacked bar per strain.

    This is the measured counterpart of panel E.  Both panels use the same sector
    colours, the same bar width and the same key, so the reader compares the
    measurement against the model at one glance.
    """
    data = mass_table().groupby(["mutant", "sector_short"], as_index=False).mass_fraction.mean()
    pivot = data.pivot(index="mutant", columns="sector_short", values="mass_fraction").reindex(
        STRAINS
    )
    fig, ax = plt.subplots(figsize=panel_figsize("Figure_4", "D"), constrained_layout=True)
    bottom = np.zeros(len(pivot))
    for sector in SECTORS:
        values = pivot[sector].to_numpy()
        ax.bar(
            np.arange(len(pivot)),
            values,
            bottom=bottom,
            width=0.76,
            color=get_sector_color(sector),
            label=sector,
            edgecolor=SEGMENT_SEPARATOR_COLOR,
            linewidth=SEGMENT_SEPARATOR_WIDTH,
        )
        bottom += values
    ax.set(ylabel="Measured protein allocation", ylim=(0, 1.02))
    # Six strain ticks share one axis, so they use the same short names as panel C.
    ax.set_xticks(np.arange(len(pivot)), STRAIN_TICKS)
    ax.tick_params(axis="x", labelsize=DENSE_FONT_PT, pad=1.5)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    # The sector key sits above the axes, as in panel E.
    fig.legend(
        loc="outside upper center",
        ncol=4,
        frameon=False,
        fontsize=DENSE_FONT_PT,
        handlelength=1.0,
        handleheight=0.8,
        handletextpad=0.4,
        columnspacing=1.0,
        labelspacing=0.35,
        borderpad=0.0,
    )
    write_source(data, "D", "measured_sector_composition.csv")
    save_figure(fig, panel_stem("D"))
    plt.close(fig)


def panel_e() -> None:
    """Draw the modelled sector composition across the flagellar allocation."""
    data = model_sector_table()
    pivot = data.pivot(
        index="flagella", columns="sector_short", values="mass_fraction"
    ).sort_index()
    fig, ax = plt.subplots(figsize=panel_figsize("Figure_4", "E"), constrained_layout=True)
    bottom = np.zeros(len(pivot))
    for sector in SECTORS:
        values = pivot[sector].to_numpy()
        ax.bar(
            pivot.index * 100,
            values,
            bottom=bottom,
            width=0.76,
            color=get_sector_color(sector),
            label=sector,
            edgecolor=SEGMENT_SEPARATOR_COLOR,
            linewidth=SEGMENT_SEPARATOR_WIDTH,
        )
        bottom += values
    ax.set(xlabel="Flagellar allocation (%)", ylabel="Model protein allocation", ylim=(0, 1.02))
    ax.set_xticks(pivot.index * 100)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    # The sector key sits above the axes, as in panel D.
    fig.legend(
        loc="outside upper center",
        ncol=4,
        frameon=False,
        fontsize=DENSE_FONT_PT,
        handlelength=1.0,
        handleheight=0.8,
        handletextpad=0.4,
        columnspacing=1.0,
        labelspacing=0.35,
        borderpad=0.0,
    )
    write_source(data, "E", "model_sector_allocation.csv")
    save_figure(fig, panel_stem("E"))
    plt.close(fig)


def panel_f() -> None:
    mass = mass_table()
    growth = growth_table()
    sector_reps = mass.query("sector_short in ['Rib', 'Fla']")
    sector_means = sector_reps.groupby(
        ["mutant", "sector_short"], as_index=False
    ).mass_fraction.mean()
    growth_reps = growth[["mutant", "experiment_day", "growth_rate_1h"]]
    exp = sector_means.merge(growth_reps, on="mutant")
    model = model_sector_table().query("sector_short in ['Rib', 'Fla']")
    # The two sectors stack so that both share one growth-rate axis and the reader
    # reads them against the same scale.  The data and the reference definitions
    # are unchanged.
    fig, axes = plt.subplots(2, 1, figsize=panel_figsize("Figure_4", "F"), constrained_layout=True)
    # Both sub-axes are drawn against the same predictor as panel B, so the same
    # measured limit decides where the model line becomes extrapolation.
    measured_flagella = float(exp.query("sector_short == 'Fla'").mass_fraction.max())
    for ax, sector in zip(axes, ["Rib", "Fla"], strict=True):
        model_part = model.query("sector_short == @sector").sort_values("flagella")
        _plot_model_line(
            ax,
            model_part.mass_fraction,
            model_part.mu,
            model_part.flagella,
            measured_flagella,
        )
        for strain in STRAINS[1:]:
            part = exp.query("sector_short == @sector and mutant == @strain")
            _scatter_strain(ax, part.mass_fraction, part.growth_rate_1h, strain, summary=False)
            _scatter_strain(
                ax,
                part.mass_fraction.mean(),
                part.growth_rate_1h.mean(),
                strain,
                summary=True,
            )
        # The x label names the sector, so a separate title would only repeat it.
        ax.set_xlabel(f"{sector} mass fraction")
        ax.xaxis.set_major_locator(MaxNLocator(nbins=3, steps=[1, 2, 5, 10]))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4, steps=[1, 2, 5, 10]))
    # The unit is written in plain text: mathtext would draw the exponent at 0.7 of
    # the label size, below the theme's on-page legibility floor.
    fig.supylabel("Growth rate (1/h)", fontsize=BASE_FONT_PT)
    handles = [
        plt.Line2D([], [], color=SUMMARY_INK, lw=0.9, label="model"),
        plt.Line2D(
            [], [], color=SUMMARY_INK, lw=0.9, ls=(0, (2.2, 1.4)), label="model, beyond data"
        ),
        plt.Line2D(
            [],
            [],
            marker="o",
            ls="",
            ms=math.sqrt(DENSITY_MARKER_SIZE),
            color=KEY_SWATCH,
            label="experiment day",
        ),
        plt.Line2D(
            [],
            [],
            marker="D",
            ls="",
            ms=math.sqrt(POINT_MARKER_SIZE),
            color=KEY_SWATCH,
            label="strain mean",
        ),
    ]
    handles.extend(
        plt.Line2D(
            [],
            [],
            marker="D",
            ls="",
            ms=math.sqrt(POINT_MARKER_SIZE),
            color=_strain_color(strain),
            label=strain,
        )
        for strain in STRAINS[1:]
    )
    fig.legend(
        handles=handles,
        loc="outside upper center",
        ncol=3,
        frameon=False,
        fontsize=DENSE_FONT_PT,
        handlelength=1.1,
        handletextpad=0.4,
        columnspacing=1.0,
        labelspacing=0.3,
        borderpad=0.0,
    )
    source = pd.concat(
        [
            exp.assign(series="experiment"),
            model.rename(columns={"mass_fraction": "mass_fraction", "mu": "growth_rate_1h"}).assign(
                mutant="model", experiment_day=np.nan, series="model"
            ),
        ],
        ignore_index=True,
    )
    write_source(source, "F", "growth_allocation.csv")
    save_figure(fig, panel_stem("F"))
    plt.close(fig)


def build_selected(labels: list[str]) -> None:
    apply_publication_style()
    _ensure_dirs()
    write_analysis_tables()
    builders = {
        "A": panel_a,
        "B": panel_b_and_raw_diagnostic,
        "C": panel_c,
        "D": panel_d,
        "E": panel_e,
        "F": panel_f,
    }
    for label in labels:
        builders[label]()
    write_provenance(labels)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Build all revised Figure 4 outputs")
    parser.add_argument("--panel", choices=list("ABCDEF"))
    args = parser.parse_args()
    if args.all == bool(args.panel):
        parser.error("Pass exactly one of --all or --panel A-F.")
    build_selected(list("ABCDEF") if args.all else [args.panel])


if __name__ == "__main__":
    main()
