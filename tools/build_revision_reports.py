#!/usr/bin/env python3
"""Build mechanical panel-map, graphical-element, and figure-number reports.

The figure-number register is computed, not typed.  Every row names one source
file and one rule, and the rule runs here.  A number that a source no longer
produces stops the build, so the register cannot drift away from the panels.
"""

# ruff: noqa: E501

from __future__ import annotations

import csv
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "docs" / "revision_2026-08-12"


ELEMENTS = {
    "F1_A": "placeholder box|missing editable schematic; no scientific graphic invented",
    "F1_B": "placeholder box|missing calibrated microscopy; no image invented",
    "F1_C": "frequency mark;cell dot;replicate point;mean bar;count annotation|one observed count, half-width set by the square root of its cell frequency; one cell, drawn where a count carries 12 cells or fewer; independent replicate mean; mean of the replicate means; mean and SD of the replicate means with the cell count",
    "F1_D": "frequency mark;cell dot;replicate point;mean bar;count annotation|one observed count, half-width set by the square root of its cell frequency; one cell, drawn where a count carries 12 cells or fewer; independent replicate mean; mean of the replicate means; mean and SD of the replicate means with the cell count",
    "F1_E": "count bubble;bubble size key|one observed hook and filament count pair, bubble area set by the square root of the cell number; 10, 100 and 1000 cells per bubble",
    "F1_F": "placeholder box|missing editable schematic; no scientific graphic invented",
    "F1_G": "placeholder box|missing calibrated microscopy; no image invented",
    "F1_H": "frequency mark;cell dot;replicate point;mean bar;count annotation|one observed count, half-width set by the square root of its cell frequency; one cell, drawn where a count carries 12 cells or fewer; independent replicate mean; mean of the replicate means; mean and SD of the replicate means with the cell count",
    "F2_A": "curve point;day point;mean and 95% CI;reference line|one growth curve, pale and descriptive; one independent experiment day, normalized to the same-day WT mean, and the unit of every test; black diamond at the mean of the day values with its 95% bootstrap percentile interval; dashed line at 1.0, the same-day reference",
    "F2_B": "curve point;day point;mean and 95% CI;reference line|one growth curve, pale and descriptive; one independent experiment day, normalized to the same-day WT mean, and the unit of every test; black diamond at the mean of the day values with its 95% bootstrap percentile interval; dashed line at 1.0, the same-day reference",
    "F2_C": "cell distribution;replicate point;mean and 95% CI;reference line|violin of the cell values, descriptive, drawn without a box and without a quartile line; one independent mother-machine experiment mean; black diamond at the mean of the replicate means with its 95% t interval; dashed line at 1.0, the Ppro1-flhDC reference",
    "F3_A": "placeholder box|missing editable assembly-mutant schematic",
    "F3_B": "curve point;day point;mean and 95% CI;reference line|one growth curve, pale and descriptive; one independent experiment day, normalized to the same-day WT mean, and the unit of every test; black diamond at the mean of the day values with its 95% bootstrap percentile interval; dashed line at 1.0, the same-day reference",
    "F3_C": "cell distribution;replicate point;mean and 95% CI;reference line|violin of the cell values, descriptive, drawn without a box and without a quartile line; one independent mother-machine experiment mean; black diamond at the mean of the replicate means with its 95% t interval; dashed line at 1.0, the replicate WT reference",
    "F3_D": "solid line|fixed cell-economy prediction for the named rotation condition",
    "F3_E": "day point;experiment mean and 95% CI;model marker;reference line|one experiment day, in the colour and the shape its strain carries in B and C; black diamond at the mean of the day values with its 95% t interval; black square at the single cell-economy value for 5% flagellar mass fraction; solid line at zero penalty, the flagella-free reference",
    "F4_A": "editable schematic elements|cell-economy model species, sectors, fluxes, and constraints",
    "F4_B": "replicate point;condition mean;model line;model line beyond data|one of the four biological proteomics replicates of a strain; diamond at the condition mean, with no dispersion mark drawn; solid cell-economy-model change from the reference, in the summary ink and with no uncertainty band; dashed continuation above 3.34% flagellar allocation, which no strain reaches",
    "F4_C": "stacked segment;segment separator;external label;leader line|protein contribution; thin white line drawn between two stacked segments, which marks the boundary and carries no value; retained protein identity; label association",
    "F4_D": "stacked segment;segment separator|measured mean sector fraction of each strain; thin white line drawn between two stacked segments, which marks the boundary and carries no value",
    "F4_E": "stacked segment;segment separator|modeled sector fraction at each flagellar allocation; thin white line drawn between two stacked segments, which marks the boundary and carries no value",
    "F4_F": "experiment day point;strain mean;model line;model line beyond data|one of the six independent growth-experiment days of a strain, at that strain's single proteomics-derived allocation; diamond at the strain mean; solid cell-economy-model line, not a fit to these points and drawn with no confidence band; dashed continuation past the measured flagellar range",
    "F5_A": "colored line;endpoint;grey area|travelled distance; final distance; fixed glucose profile",
    "F5_B": "colored line|modeled growth trajectory at the stated flagellar allocation",
    "F5_C": "ordered point;connecting line|final normalized biomass; ordering across allocation values",
    "F5_D": "seed point;median;simulation interval|seed-level mean net displacement; median; 2.5–97.5% seed variability",
    "F5_E": "seed point;median;simulation interval|seed-level mean net displacement; median; 2.5–97.5% seed variability",
    "F6_A": "well measurement;day point;mean and 95% CI;reference line|one soft-agar well, pale and descriptive; one independent experiment day, the analysis unit; black diamond at the mean of the day values with its 95% t interval; solid line at 100%, the same-day WT reference",
    "F6_B": "replicate point;mean and 95% CI;reference line|one independent replicate, the analysis unit, carrying a single measurement so no pale layer is drawn; black diamond at the mean of the replicate values with its 95% t interval; solid line at 100%, the WT reference",
    "F6_C": "frequency mark;cell dot;mean bar;count annotation|one observed hook count, half-width set by the square root of its cell frequency; one cell, drawn where a count carries 12 cells or fewer; black bar at the mean of all cells at that plate position; mean and SD over all cells with the cell count",
    "F6_D": "schematic node;workflow arrow;expansion ring;sampling label|a labelled step of the competition workflow, from the two strains to the readout; the order of the steps; a neutral grey ring that marks expansion distance only and carries no strain identity; the four sampled regions R1 to R4",
    "F6_E": "region point;connecting line;SD whisker;strain key;image placeholder|the mean fraction of all cells of one strain in that region carrying the given hook count; the ordering across hook bins within one strain; plus and minus one SD across imaging fields, which are not biological replicates; PproA and PproB; unavailable calibrated region image",
    "F7_A": "unit point;pairing line;unit violin;ratio annotation;reference line|paired experimental unit, plotted as its mean log10 D_eff; the two phenotypes imaged in the same session; kernel density of the unit means; medium, paired-unit count, D ratio and its 95% CI; dashed D_eff = 1",
    "F7_B": "unit point;pairing line;unit violin;ratio annotation;reference line|paired experimental unit, plotted as its mean log10 D_eff; the two phenotypes imaged in the same session; kernel density of the unit means; medium, paired-unit count, D ratio and its 95% CI; dashed D_eff = 1",
    "F7_C": "unit point;pairing line;unit violin;ratio annotation;reference line|paired experimental unit, plotted as its mean log10 D_eff; the two phenotypes imaged in the same session; kernel density of the unit means; medium, paired-unit count, D ratio and its 95% CI; dashed D_eff = 1",
    "F7_D": "component bar;estimate marker;95% interval;estimate label;row rule;reference line;unit count annotation|horizontal bar from the reference ratio of 1 to the estimate, filled for agarose and open for liquid; the point estimate, a circle for agarose and a square for liquid; paired-unit bootstrap percentile interval; the numeric point estimate beside its own interval; thin line that separates the speed² and τ component rows from the D_eff product row; dashed ratio = 1; paired units per medium",
    "F7_E": "frequency mark;cell dot;day point;mean bar;count annotation|one observed hook count, half-width set by the square root of its cell frequency; one cell, drawn where a count carries 12 cells or fewer; independent day-replicate mean; mean of the day-replicate means; mean and SD of the day means with the cell count, and the cells above the clipped axis named in the key",
    "F7_F": "frequency mark;cell dot;day point;mean bar;count annotation|one observed hook count, half-width set by the square root of its cell frequency; one cell, drawn where a count carries 12 cells or fewer; independent day-replicate mean; mean of the day-replicate means; mean and SD of the day means with the cell count, and the cells above the clipped axis named in the key",
    "F7_G": "frequency mark;cell dot;day point;mean bar;count annotation|one observed hook count, half-width set by the square root of its cell frequency; one cell, drawn where a count carries 12 cells or fewer; independent day-replicate mean; mean of the day-replicate means; mean and SD of the day means with the cell count, and the cells above the clipped axis named in the key",
    "S1_A": "cell distribution;replicate point;mean bar;reference line;lineage title|violin of the cell values, descriptive, drawn without a box and without a quartile line; one independent mother-machine experiment mean; black bar at the mean of the two experiment means, with no interval because the panel runs no test; dashed line at 1.0, the Ppro1-flhDC reference; mother-only or non-mother sub-axes",
    "S1_B": "cell distribution;replicate point;mean bar;reference line;lineage title|violin of the cell values, descriptive, drawn without a box and without a quartile line; one independent mother-machine experiment mean; black bar at the mean of the two experiment means, with no interval because the panel runs no test; dashed line at 1.0, the Ppro1-flhDC reference; mother-only or non-mother sub-axes",
    "S2_A": "strain point;gene title;strain key|the mean protein mass fraction of one strain over its four biological proteomics replicates, with no dispersion mark drawn; the gene name of that sub-axes; the six promoter-series strains, in the shared strain colours",
    "S3_A": "unit point;pairing line;unit violin;effect annotation|one paired experimental unit, that is one metadata key in one medium, filled circle for agarose and open square for liquid; joins the two strains of the same paired unit, solid for agarose and dashed for liquid; kernel density of the unit values on the plotted scale, clipped to the observed range; paired-unit median-speed ratio with its 95% bootstrap percentile interval and the unit count, per medium",
    "S3_B": "unit point;pairing line;unit violin;effect annotation|one paired experimental unit, that is one metadata key in one medium, filled circle for agarose and open square for liquid; joins the two strains of the same paired unit, solid for agarose and dashed for liquid; kernel density of the unit values on the plotted scale, clipped to the observed range; paired-unit median-speed ratio with its 95% bootstrap percentile interval and the unit count, per medium",
    "S3_C": "unit point;pairing line;unit violin;effect annotation|one paired experimental unit, that is one metadata key in one medium, filled circle for agarose and open square for liquid; joins the two strains of the same paired unit, solid for agarose and dashed for liquid; kernel density of the unit values on the plotted scale, clipped to the observed range; paired-unit median-speed ratio with its 95% bootstrap percentile interval and the unit count, per medium",
    "S3_D": "unit point;pairing line;unit violin;effect annotation|one paired experimental unit, that is one metadata key in one medium, filled circle for agarose and open square for liquid; joins the two strains of the same paired unit, solid for agarose and dashed for liquid; kernel density of the unit values on the plotted scale, clipped to the observed range; paired-unit swimming-fraction difference with its 95% bootstrap percentile interval and the unit count, per medium",
    "S3_E": "unit point;pairing line;unit violin;effect annotation|one paired experimental unit, that is one metadata key in one medium, filled circle for agarose and open square for liquid; joins the two strains of the same paired unit, solid for agarose and dashed for liquid; kernel density of the unit values on the plotted scale, clipped to the observed range; paired-unit swimming-fraction difference with its 95% bootstrap percentile interval and the unit count, per medium",
    "S3_F": "unit point;pairing line;unit violin;effect annotation|one paired experimental unit, that is one metadata key in one medium, filled circle for agarose and open square for liquid; joins the two strains of the same paired unit, solid for agarose and dashed for liquid; kernel density of the unit values on the plotted scale, clipped to the observed range; paired-unit swimming-fraction difference with its 95% bootstrap percentile interval and the unit count, per medium",
    "S3_G": "unit point;pairing line;unit violin;effect annotation|one paired experimental unit, that is one metadata key in one medium, filled circle for agarose and open square for liquid; joins the two strains of the same paired unit, solid for agarose and dashed for liquid; kernel density of the unit values on the plotted scale, clipped to the observed range; paired-unit directional-persistence ratio with its 95% bootstrap percentile interval and the unit count, per medium",
    "S3_H": "unit point;pairing line;unit violin;effect annotation;medium key|one paired experimental unit, that is one metadata key in one medium, filled circle for agarose and open square for liquid; joins the two strains of the same paired unit, solid for agarose and dashed for liquid; kernel density of the unit values on the plotted scale, clipped to the observed range; paired-unit directional-persistence ratio with its 95% bootstrap percentile interval and the unit count, per medium; the single figure-level key for agarose and liquid, drawn once below this panel",
    "S3_I": "unit point;pairing line;unit violin;effect annotation|one paired experimental unit, that is one metadata key in one medium, filled circle for agarose and open square for liquid; joins the two strains of the same paired unit, solid for agarose and dashed for liquid; kernel density of the unit values on the plotted scale, clipped to the observed range; paired-unit directional-persistence ratio with its 95% bootstrap percentile interval and the unit count, per medium",
    "S4_A": "track line;run end marker;stalled marker;non-motile marker;medium title|the simulated path of one cell in the phenotype colour, fainter and thinner where the cell is non-motile; filled circle at the last position of a cell that ended in a run; filled square at the last position of a stalled cell; open circle at the last position of a non-motile cell; names the medium and states that speed and turning are calibrated inputs",
    "S4_B": "track line;run end marker;stalled marker;non-motile marker;medium title|the simulated path of one cell in the phenotype colour, fainter and thinner where the cell is non-motile; filled circle at the last position of a cell that ended in a run; filled square at the last position of a stalled cell; open circle at the last position of a non-motile cell; names the medium and states that speed and turning are calibrated inputs",
    "S4_C": "track line;run end marker;stalled marker;non-motile marker;medium title|the simulated path of one cell in the phenotype colour, fainter and thinner where the cell is non-motile; filled circle at the last position of a cell that ended in a run; filled square at the last position of a stalled cell; open circle at the last position of a non-motile cell; names the medium and states that speed and turning are calibrated inputs",
    "S4_D": "track line;run end marker;stalled marker;non-motile marker;obstacle disc;medium title|the simulated path of one cell in the phenotype colour, fainter and thinner where the cell is non-motile; filled circle at the last position of a cell that ended in a run; filled square at the last position of a stalled cell; open circle at the last position of a non-motile cell; one grey disc is one agarose-like obstacle; names the medium and states that speed and turning are calibrated inputs",
    "S4_E": "track line;run end marker;stalled marker;non-motile marker;obstacle disc;medium title|the simulated path of one cell in the phenotype colour, fainter and thinner where the cell is non-motile; filled circle at the last position of a cell that ended in a run; filled square at the last position of a stalled cell; open circle at the last position of a non-motile cell; one grey disc is one agarose-like obstacle; names the medium and states that speed and turning are calibrated inputs",
    "S4_F": "track line;run end marker;stalled marker;non-motile marker;obstacle disc;medium title|the simulated path of one cell in the phenotype colour, fainter and thinner where the cell is non-motile; filled circle at the last position of a cell that ended in a run; filled square at the last position of a stalled cell; open circle at the last position of a non-motile cell; one grey disc is one agarose-like obstacle; names the medium and states that speed and turning are calibrated inputs",
    "S5_A": "filled contour band;contour outline;marginal density;centroid marker;centroid connector;reference line;count annotation|50% and 95% probability mass of the first phenotype, pooled over its trajectories; the same two levels of the second phenotype; kernel density of speed above the axes and of log10 D_eff to its right, in the same fill-against-outline convention; the mean of the per-unit centroids of a phenotype, with 95% paired-unit bootstrap whiskers, and the inferential mark of the panel; joins the two centroids of the pair; dashed D_eff = 1; paired experiments and trajectories per phenotype",
    "S5_B": "filled contour band;contour outline;marginal density;centroid marker;centroid connector;reference line;count annotation|50% and 95% probability mass of the first phenotype, pooled over its trajectories; the same two levels of the second phenotype; kernel density of speed above the axes and of log10 D_eff to its right, in the same fill-against-outline convention; the mean of the per-unit centroids of a phenotype, with 95% paired-unit bootstrap whiskers, and the inferential mark of the panel; joins the two centroids of the pair; dashed D_eff = 1; paired experiments and trajectories per phenotype",
    "S5_C": "filled contour band;contour outline;marginal density;centroid marker;centroid connector;reference line;count annotation|50% and 95% probability mass of the first phenotype, pooled over its trajectories; the same two levels of the second phenotype; kernel density of speed above the axes and of log10 D_eff to its right, in the same fill-against-outline convention; the mean of the per-unit centroids of a phenotype, with 95% paired-unit bootstrap whiskers, and the inferential mark of the panel; joins the two centroids of the pair; dashed D_eff = 1; paired experiments and trajectories per phenotype",
}


#: ``config/panels.csv`` carries a compact figure key; the register prints the
#: name the legend uses.
FIGURE_TITLES = {
    "Figure1": "Figure 1",
    "Figure2": "Figure 2",
    "Figure3": "Figure 3",
    "Figure4": "Figure 4",
    "Figure5": "Figure 5",
    "Figure6": "Figure 6",
    "Figure7": "Figure 7",
    "Supplementary1": "Supplementary Figure S1",
    "Supplementary2": "Supplementary Figure S2",
    "Supplementary3": "Supplementary Figure S3",
    "Supplementary4": "Supplementary Figure S4",
    "Supplementary5": "Supplementary Figure S5",
}


@dataclass(frozen=True)
class NumberSpec:
    """One number printed in a figure legend, with the rule that produces it."""

    panel_id: str
    quantity: str
    source: str
    computation: str
    rule: Callable[[], str]


_TABLES: dict[str, pd.DataFrame] = {}


def table(relative: str) -> pd.DataFrame:
    """Read a repository table once and keep it for the other rules."""
    if relative not in _TABLES:
        path = ROOT / relative
        if not path.exists():
            raise FileNotFoundError(
                f"{relative} is missing; build the panels before the reports"
            )
        _TABLES[relative] = pd.read_csv(path)
    return _TABLES[relative]


def provenance(relative: str) -> dict:
    """Read the parameters and the seeds of one panel provenance record."""
    path = ROOT / relative
    if not path.exists():
        raise FileNotFoundError(f"{relative} is missing; build the panel before the reports")
    record = json.loads(path.read_text(encoding="utf-8"))
    return {**record.get("parameters", {}), **record.get("random_seeds", {})}


def literal(relative: str, pattern: str) -> tuple[str, ...]:
    """Read a drawing constant straight out of the builder that applies it."""
    path = ROOT / relative
    if not path.exists():
        raise FileNotFoundError(f"{relative} is missing")
    match = re.search(pattern, path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"{relative} no longer contains the constant {pattern!r}")
    return match.groups()


def one(values: object, quantity: str) -> object:
    """Return the single distinct value of a series, or stop the build."""
    distinct = sorted(set(pd.Series(values).tolist()))
    if len(distinct) != 1:
        raise ValueError(f"{quantity} is not one value across the source rows: {distinct}")
    return distinct[0]


def whole(value: object) -> str:
    return str(int(round(float(value))))


def fixed(value: object, places: int) -> str:
    return f"{float(value):.{places}f}"


def percent(value: object, places: int) -> str:
    return f"{float(value) * 100:.{places}f}%"


# --- exact P and q values ----------------------------------------------------
#
# Coauthor decision 1.6 asks every legend to carry the effect size, the
# confidence interval and the exact P value.  A threshold such as "P < 0.05" is
# never printed.  A Benjamini-Hochberg value is a q value and is labelled q, so
# a corrected value is never called a P value.

#: Below this the number is printed in scientific notation, because two
#: significant figures in decimal notation would run to six leading zeros.
SCIENTIFIC_BELOW = 1e-4


def probability(value: object) -> str:
    """Format one exact P or q value to two significant figures.

    >>> probability(0.005310760745513765)
    '0.0053'
    >>> probability(1.3804792932964242e-05)
    '1.4 × 10^-5'
    """
    import math

    number = float(value)
    if not 0.0 < number <= 1.0:
        raise ValueError(f"{number} is not a probability")
    if number >= SCIENTIFIC_BELOW:
        exponent = math.floor(math.log10(number))
        return f"{number:.{max(0, 1 - exponent)}f}"
    mantissa, exponent_text = f"{number:.1e}".split("e")
    return f"{mantissa} × 10^{int(exponent_text)}"


#: ``config/palette.yaml`` names every plotted strain.  The register prints the
#: label the panel key carries, so a reader can match a value to a mark.
_STRAIN_LABELS: dict[str, str] = {}


def strain_label(key: str) -> str:
    """Return the plotted label of one strain key."""
    if not _STRAIN_LABELS:
        import yaml

        palette = yaml.safe_load((ROOT / "config" / "palette.yaml").read_text(encoding="utf-8"))
        _STRAIN_LABELS.update(
            {name: style["label"] for name, style in palette["strain_styles"].items()}
        )
    return _STRAIN_LABELS.get(key, key)


def comparison_values(
    relative: str, key_column: str, value_column: str, reference: str | None = None
) -> list[tuple[str, float]]:
    """Return one (label, value) pair per comparison row, in table order."""
    rows = table(relative)
    if reference is not None:
        rows = rows[rows[key_column] != reference]
    rows = rows[rows[value_column].notna()]
    return [
        (strain_label(str(row[key_column])), float(row[value_column]))
        for _, row in rows.iterrows()
    ]


def comparison_specs(
    panel_id: str,
    relative: str,
    key_column: str,
    value_column: str,
    quantity: str,
    computation: str,
    reference: str | None = None,
) -> list[NumberSpec]:
    """One register row per comparison, so every printed value is traceable."""
    specs: list[NumberSpec] = []
    for index, (label, _) in enumerate(
        comparison_values(relative, key_column, value_column, reference)
    ):
        specs.append(
            NumberSpec(
                panel_id,
                f"{quantity}, {label}",
                relative,
                computation,
                lambda relative=relative, key_column=key_column, value_column=value_column,
                reference=reference, index=index: probability(
                    comparison_values(relative, key_column, value_column, reference)[index][1]
                ),
            )
        )
    return specs


def q_range_specs(
    panel_id: str,
    relative: str,
    key_column: str,
    value_column: str,
    family: str,
    reference: str | None = None,
) -> list[NumberSpec]:
    """The smallest and the largest corrected value of one testing family."""

    def edge(which: str) -> Callable[[], str]:
        def rule() -> str:
            values = [value for _, value in comparison_values(
                relative, key_column, value_column, reference
            )]
            return probability(min(values) if which == "smallest" else max(values))

        return rule

    return [
        NumberSpec(
            panel_id,
            f"{which} Benjamini-Hochberg q value, {family}",
            relative,
            f"the {which} {value_column} of the panel's correction family",
            edge(which),
        )
        for which in ("smallest", "largest")
    ]


# --- Figure 1 ---------------------------------------------------------------

F1_PLOTTING = "analyses/figure_01/plotting.py"
F6_BUILDER = "analyses/figure_06_revision/build_figure_06_revision.py"
F7_BUILDER = "analyses/figure_07_revision/build_figure_07_revision.py"
DOT_RULE = r"if frequency <= (\d+):"
DOT_COMPUTATION = "the integer in the `if frequency <= N` rule that draws a sparse count as cell dots"


def dot_threshold(builder: str) -> Callable[[], str]:
    return lambda: literal(builder, DOT_RULE)[0]


# --- Figure 2 and Figure 3 --------------------------------------------------

F2_A = "build/source_data/Figure_2/A/F2_A_source_data.csv"
F2_B = "build/source_data/Figure_2/B/F2_B_source_data.csv"
F2_C = "build/source_data/Figure_2/C/F2_C_source_data.csv.gz"
F3_B = "build/source_data/Figure_3/B/F3_B_source_data.csv"
F3_C = "build/source_data/Figure_3/C/F3_C_source_data.csv.gz"
F3_D = "build/source_data/Figure_3/D/F3_D_source_data.csv"


def curves(relative: str) -> pd.DataFrame:
    return table(relative).query("plot_component == 'technical_curve'")


def experiment_days(relative: str) -> str:
    return whole(curves(relative).experiment_day.nunique())


def curves_per_condition_day(relative: str) -> str:
    counts = curves(relative).groupby(["experiment_day", "strain"]).curve_id.nunique()
    return whole(one(counts, "growth curves per condition and day"))


def reference_growth_rate(relative: str, places: int = 3) -> float:
    day_reference = curves(relative).groupby("experiment_day").reference_growth_rate_1_h.first()
    return round(float(day_reference.mean()), places)


def cell_values(relative: str) -> str:
    return whole(len(table(relative)))


def replicates_per_strain(relative: str) -> str:
    counts = table(relative).groupby("strain").replicate.nunique()
    return whole(one(counts, "independent experiments per strain"))


def rotation_penalty(state: str) -> Callable[[], str]:
    def rule() -> str:
        model = table(F3_D)
        rows = model[model.rotation_state == state].set_index("flagella_mass_fraction")
        free = float(rows.growth_rate_1_h.loc[0.00])
        loaded = float(rows.growth_rate_1_h.loc[0.05])
        return percent((free - loaded) / free, 1)

    return rule


# --- Figure 4 ---------------------------------------------------------------

F4_B_OVERLAY = "build/source_data/Figure_4/B/delta_overlay.csv"
F4_C_LABELS = "build/source_data/Figure_4/C/label_audit.csv"
F4_E_MODEL = "build/source_data/Figure_4/E/model_sector_allocation.csv"
F4_F_GROWTH = "build/source_data/Figure_4/F/growth_allocation.csv"


def proteomics_replicates() -> str:
    counts = table(F4_B_OVERLAY).query("series == 'experiment'").groupby("mutant").replicate.nunique()
    return whole(one(counts, "proteomics replicates per strain"))


# --- Figure 5 ---------------------------------------------------------------

F5_C_BIOMASS = "build/source_data/Figure_5/C/relative_biomass.csv"
F5_B_GAIN = "build/source_data/Figure_5/B/non_motile_gain.csv"
F5_B_BASELINE = "build/statistics/Figure_5/A3/low_allocation_continuation_status.csv"


def baseline_step() -> pd.Series:
    """Return the solved zero-allocation step of the low-allocation sweep."""
    sweep = table(F5_B_BASELINE)
    zero = sweep[sweep.flagellar_allocation == 0.0]
    if len(zero) != 1:
        raise ValueError("the sweep records no single zero-allocation step")
    return zero.iloc[0]


def solved_sweep_steps() -> str:
    sweep = table(F5_B_BASELINE)
    failed = sweep[sweep.status != "success"]
    if not failed.empty:
        raise ValueError(f"{len(failed)} sweep steps are not solved; the legend claims all of them")
    return whole(len(sweep))
F5_SEEDS = {
    "F5_D": "build/source_data/Figure_5/D/liquid_seed_predictions.csv",
    "F5_E": "build/source_data/Figure_5/E/agarose_seed_predictions.csv",
}
F5_INTERVALS = {
    "F5_D": "build/statistics/Figure_5/D/liquid_simulation_interval.csv",
    "F5_E": "build/statistics/Figure_5/E/agarose_simulation_interval.csv",
}


def seed_column(panel: str, column: str, rule: Callable[[object], str]) -> Callable[[], str]:
    return lambda: rule(one(table(F5_SEEDS[panel])[column], column))


def seeds_per_phenotype(panel: str) -> Callable[[], str]:
    def rule() -> str:
        counts = table(F5_SEEDS[panel]).groupby("phenotype").seed.nunique()
        return whole(one(counts, "seeds per phenotype"))

    return rule


# --- Figure 6 ---------------------------------------------------------------

F6_A_WELLS = "build/source_data/Figure_6/A/Figure_6A_well_measurements.csv"
F6_B_POINTS = "build/source_data/Figure_6/B/Figure_6B_replicate_points.csv"
F6_C_CELLS = "build/source_data/Figure_6/C/Figure_6C_cell_points.csv"
F6_E_REGIONS = "build/source_data/Figure_6/E/Figure_6E_roi_fraction_mean_sd.csv"


def wt_well_span(edge: str) -> Callable[[], str]:
    def rule() -> str:
        wt = table(F6_A_WELLS).query("condition == 'WT'").motility_value
        return f"{(wt.min() if edge == 'low' else wt.max()):.1f}%"

    return rule


def soft_agar_days(condition: str) -> Callable[[], str]:
    def rule() -> str:
        wells = table(F6_A_WELLS)
        selected = wells.query("condition == 'WT'" if condition == "WT" else "condition != 'WT'")
        counts = selected.groupby("condition").day_repeat_id.nunique()
        return whole(one(counts, f"experiment days for {condition}"))

    return rule


def region_fields() -> str:
    counts = table(F6_E_REGIONS).groupby("region_id").n_rois.first()
    return "/".join(whole(value) for value in counts.sort_index())


# --- Figure 7 and Supplementary Figure 5 ------------------------------------

F7_PAIRS = {
    "F7_A": "build/source_data/Figure_7/A/Figure_7A_paired_unit_summaries.csv",
    "F7_B": "build/source_data/Figure_7/B/Figure_7B_paired_unit_summaries.csv",
    "F7_C": "build/source_data/Figure_7/C/Figure_7C_paired_unit_summaries.csv",
}
F7_DAYS = {
    "F7_E": "build/source_data/Figure_7/E/Figure_7E_day_repeat_means.csv",
    "F7_F": "build/source_data/Figure_7/F/Figure_7F_day_repeat_means.csv",
    "F7_G": "build/source_data/Figure_7/G/Figure_7G_day_repeat_means.csv",
}
S5_AUDITS = {
    "S5_A": "build/statistics/Supplementary_Figure_5/A/S5_A_contour_grid_audit.csv",
    "S5_B": "build/statistics/Supplementary_Figure_5/B/S5_B_contour_grid_audit.csv",
    "S5_C": "build/statistics/Supplementary_Figure_5/C/S5_C_contour_grid_audit.csv",
}
S5_PROVENANCE = {
    "S5_A": "build/provenance/Supplementary_Figure_5/A.json",
    "S5_B": "build/provenance/Supplementary_Figure_5/B.json",
    "S5_C": "build/provenance/Supplementary_Figure_5/C.json",
}


def paired_units(panel: str) -> Callable[[], str]:
    def rule() -> str:
        pairs = table(F7_PAIRS[panel])
        counts = pairs.groupby("medium").metadata_key.nunique()
        return f"{whole(counts['agarose'])}/{whole(counts['liquid'])}"

    return rule


def hook_days(panel: str) -> Callable[[], str]:
    def rule() -> str:
        counts = table(F7_DAYS[panel]).groupby("plot_label").collapsed_repeat_id.nunique()
        return whole(one(counts, "independent day replicates per phenotype"))

    return rule


def s5_paired_experiments(panel: str) -> Callable[[], str]:
    def rule() -> str:
        audit = table(S5_AUDITS[panel]).groupby("medium").n_paired_units
        counts = {medium: one(values, "paired experiments") for medium, values in audit}
        return f"{whole(counts['agarose'])}/{whole(counts['liquid'])}"

    return rule


def s5_trajectories(panel: str, medium: str) -> Callable[[], str]:
    def rule() -> str:
        audit = table(S5_AUDITS[panel])
        ordered = audit[audit.medium == medium].set_index("phenotype").n_trajectories
        pair = sorted(audit.phenotype.unique(), key=lambda name: (name != "WT", name))
        return "/".join(whole(ordered[name]) for name in pair)

    return rule


def contour_masses(panel: str) -> Callable[[], str]:
    def rule() -> str:
        masses = provenance(S5_PROVENANCE[panel])["contour_probability_mass"]
        return " and ".join(percent(mass, 0) for mass in masses)

    return rule


# --- Supplementary Figures 1, 2 and 4 ---------------------------------------

S1_A = "build/source_data/Supplementary_Figure_1/A/S1_A_source_data.csv.gz"
S1_B = "build/source_data/Supplementary_Figure_1/B/S1_B_source_data.csv.gz"
S2_A = "data/source_data/s2_a/S2_A_source_data.csv"
S4_PROVENANCE = {
    letter: f"build/provenance/Supplementary_Figure_4/{letter}.json" for letter in "ABCDEF"
}
ADOPTED = "data/processed/motility_adopted_parameters/motility_summary_parameters_adopted.csv"


def analysis_window(relative: str) -> Callable[[], str]:
    def rule() -> str:
        rows = table(relative)
        start = one(rows._window_start_min, "window start")
        end = one(rows._window_end_min, "window end")
        return f"{whole(start)}-{whole(end)} min"

    return rule


def s4_parameter(letter: str, key: str, places: int) -> Callable[[], str]:
    def rule() -> str:
        record = provenance(S4_PROVENANCE[letter])
        return fixed(record["motility_parameters"][key], places)

    return rule


def s4_seed(letter: str) -> Callable[[], str]:
    return lambda: whole(provenance(S4_PROVENANCE[letter])["panel_seed"])


def adopted_constant(column: str, places: int) -> Callable[[], str]:
    def rule() -> str:
        rows = table(ADOPTED)
        selected = rows if column == "turn_angle_sd_rad" else rows.query("medium == 'agarose'")
        return fixed(one(selected[column], column), places)

    return rule


STALL_AUDIT = "data/processed/motility_adopted_parameters/adopted_stall_parameter_audit.csv"
STALL_COMMON = "analyses/motility_stall_parameter_comparison/common.py"
TURN_CALIBRATION = "analyses/motility_turn_angle_comparison/calibrate_global_turn_angle.py"
DIFFUSIVITY = "build/diagnostics/effective_diffusivity_check/effective_diffusivity_comparison.csv"
CONVERGENCE = "build/diagnostics/Figure_5/timestep_convergence.csv"
CONVERGENCE_RATIOS = "build/diagnostics/Figure_5/timestep_convergence_ratios.csv"


def stall_exponent() -> str:
    """Recover the exponent from the two probabilities it was fitted through."""
    import math

    audit = table(STALL_AUDIT).set_index("phenotype")
    probability = audit.adopted_stall_probability
    hooks = audit.mean_hooks
    exponent = -math.log(probability["PproB"] / probability["PproA"]) / math.log(
        hooks["PproB"] / hooks["PproA"]
    )
    return fixed(exponent, 3)


def diffusivity_span(medium: str, column: str) -> Callable[[], str]:
    def rule() -> str:
        rows = table(DIFFUSIVITY)
        selected = rows[(rows.model == "after_corrected") & (rows.medium == medium)][column]
        return f"{percent(selected.min(), 0)[:-1]}-{percent(selected.max(), 0)}"

    return rule


def convergence_steps() -> pd.DataFrame:
    return table(CONVERGENCE).sort_values("dt_s", ascending=False)


def step_deviations() -> str:
    largest = convergence_steps().groupby("dt_s").net_displacement_um_rel_deviation.max()
    ordered = largest.sort_index(ascending=False)
    return "/".join(percent(value, 2)[:-1] for value in ordered) + "%"


def path_length_span() -> str:
    rows = table(CONVERGENCE)
    wt = rows[(rows.medium == "agarose") & (rows.phenotype == "WT")].set_index("dt_s")
    coarse = wt.path_length_um_mean.loc[wt.index.max()]
    fine = wt.path_length_um_mean.loc[wt.index.min()]
    return f"{whole(coarse)} to {whole(fine)} um"


def path_length_ratio_span() -> str:
    rows = table(CONVERGENCE_RATIOS)
    ppro_a = rows[(rows.medium == "agarose") & (rows.phenotype == "PproA")].set_index("dt_s")
    coarse = ppro_a.path_length_um_ratio_to_wt.loc[ppro_a.index.max()]
    fine = ppro_a.path_length_um_ratio_to_wt.loc[ppro_a.index.min()]
    return f"{fixed(coarse, 2)} to {fixed(fine, 2)}"


def finest_step_change() -> str:
    rows = table(CONVERGENCE)
    ppro_b = rows[(rows.medium == "agarose") & (rows.phenotype == "PproB")].set_index("dt_s")
    steps = sorted(ppro_b.index)[:2]
    finest, next_finest = ppro_b.net_displacement_um_mean.loc[steps[0]], ppro_b.net_displacement_um_mean.loc[steps[1]]
    return percent(abs(next_finest / finest - 1.0), 2)


def step_ratio_series() -> str:
    rows = table(CONVERGENCE_RATIOS)
    agarose = rows[rows.medium == "agarose"].pivot(
        index="dt_s", columns="phenotype", values="net_displacement_um_ratio_to_wt"
    )
    ratios = (agarose["PproB"] / agarose["PproA"]).sort_index(ascending=False)
    return ", ".join(fixed(value, 2) for value in ratios)


def figure_number_specs() -> list[NumberSpec]:
    """List every number a legend prints, with the rule that recomputes it."""
    specs: list[NumberSpec] = []

    # Figure 1
    for panel in ("F1_C", "F1_D", "F1_H"):
        specs.append(
            NumberSpec(panel, "cell-dot threshold", F1_PLOTTING, DOT_COMPUTATION, dot_threshold(F1_PLOTTING))
        )
    specs.append(
        NumberSpec(
            "F1_E",
            "bubble size key, cells per bubble",
            F1_PLOTTING,
            "the three cell numbers in the bubble-key tuple of the hook-versus-filament panel",
            lambda: "/".join(literal(F1_PLOTTING, r"for value in \((\d+), (\d+), (\d+)\)")),
        )
    )

    # Figure 2
    for panel, source in (("F2_A", F2_A), ("F2_B", F2_B)):
        specs += [
            NumberSpec(
                panel,
                "independent days",
                source,
                "distinct experiment_day of the technical-curve rows",
                lambda source=source: experiment_days(source),
            ),
            NumberSpec(
                panel,
                "growth curves per condition and day",
                source,
                "distinct curve_id per experiment_day and strain; the build stops if the count varies",
                lambda source=source: curves_per_condition_day(source),
            ),
            NumberSpec(
                panel,
                "WT reference growth rate",
                source,
                "mean over the six days of reference_growth_rate_1_h, to three decimals",
                lambda source=source: f"{fixed(reference_growth_rate(source), 3)} 1/h",
            ),
        ]
    specs.append(
        NumberSpec(
            "F2_B",
            "between-series difference of the WT reference",
            f"{F2_A}; {F2_B}",
            "the B reference growth rate minus the A reference growth rate, both rounded to three decimals first",
            lambda: f"{fixed(reference_growth_rate(F2_B) - reference_growth_rate(F2_A), 3)} 1/h",
        )
    )
    specs += [
        NumberSpec(
            "F2_C",
            "independent experiments per strain",
            F2_C,
            "distinct replicate per strain",
            lambda: replicates_per_strain(F2_C),
        ),
        NumberSpec(
            "F2_C", "cell values", F2_C, "row count of the cell-level table", lambda: cell_values(F2_C)
        ),
    ]

    # Figure 3
    specs += [
        NumberSpec(
            "F3_B",
            "independent days",
            F3_B,
            "distinct experiment_day of the technical-curve rows",
            lambda: experiment_days(F3_B),
        ),
        NumberSpec(
            "F3_C",
            "independent experiments",
            F3_C,
            "distinct replicate per strain",
            lambda: replicates_per_strain(F3_C),
        ),
        NumberSpec(
            "F3_C", "cell values", F3_C, "row count of the cell-level table", lambda: cell_values(F3_C)
        ),
        NumberSpec(
            "F3_D",
            "rotating penalty at 5%",
            F3_D,
            "one minus the growth rate at 0.05 divided by the growth rate at 0.00, rotating rows",
            rotation_penalty("rotating"),
        ),
        NumberSpec(
            "F3_D",
            "non-rotating penalty at 5%",
            F3_D,
            "one minus the growth rate at 0.05 divided by the growth rate at 0.00, non-rotating rows",
            rotation_penalty("non-rotating"),
        ),
        NumberSpec(
            "F3_E",
            "model flagellar mass fraction",
            F3_D,
            "the largest flagella_mass_fraction the fixed model table carries",
            lambda: percent(table(F3_D).flagella_mass_fraction.max(), 0),
        ),
    ]

    # Figure 4
    for panel in ("F4_B", "F4_C"):
        specs.append(
            NumberSpec(
                panel,
                "proteomics replicates per strain",
                F4_B_OVERLAY,
                "distinct replicate per mutant of the experiment rows",
                proteomics_replicates,
            )
        )
    specs += [
        NumberSpec(
            "F4_B",
            "dashed-line threshold, largest measured flagellar allocation",
            F4_B_OVERLAY,
            "the largest x_flagella of the experiment rows, as a percentage to two decimals",
            lambda: percent(table(F4_B_OVERLAY).query("series == 'experiment'").x_flagella.max(), 2),
        ),
        NumberSpec(
            "F4_B",
            "Oth sector constraint",
            F4_E_MODEL,
            "the single mass_fraction the model holds for the Oth sector at every allocation",
            lambda: fixed(one(table(F4_E_MODEL).query("sector_short == 'Oth'").mass_fraction, "Oth"), 2),
        ),
        NumberSpec(
            "F4_C",
            "protein-label mass floor",
            F4_C_LABELS,
            "the absolute_floor column, as a percentage of total protein mass",
            lambda: percent(one(table(F4_C_LABELS).absolute_floor, "absolute floor"), 2),
        ),
        NumberSpec(
            "F4_C",
            "protein-label share threshold",
            F4_C_LABELS,
            "the relative_threshold column, as a percentage of the displayed sector subtotal",
            lambda: percent(one(table(F4_C_LABELS).relative_threshold, "relative threshold"), 0),
        ),
        NumberSpec(
            "F4_C",
            "abundance-leader rank",
            F4_C_LABELS,
            "the abundance_leader_rank column, the rank that always keeps a protein",
            lambda: whole(one(table(F4_C_LABELS).abundance_leader_rank, "leader rank")),
        ),
        NumberSpec(
            "F4_F",
            "independent growth-experiment days per strain",
            F4_F_GROWTH,
            "distinct experiment_day per mutant of the experiment rows",
            lambda: whole(
                one(
                    table(F4_F_GROWTH)
                    .query("series == 'experiment'")
                    .groupby("mutant")
                    .experiment_day.nunique(),
                    "growth-experiment days per strain",
                )
            ),
        ),
    ]

    # Figure 5
    specs += [
        NumberSpec(
            "F5_A",
            "glucose-profile age",
            "build/provenance/Figure_5/A.json",
            "the dynamic_gradient_age_h parameter of the panel provenance",
            lambda: f"{whole(provenance('build/provenance/Figure_5/A.json')['dynamic_gradient_age_h'])} h",
        ),
        NumberSpec(
            "F5_B",
            "flagellar allocation range of the colored lines",
            F5_B_GAIN,
            "the smallest and the largest flagellar_allocation of the motile family",
            lambda: f"{percent(table(F5_B_GAIN).flagellar_allocation.min(), 1)} to {percent(table(F5_B_GAIN).flagellar_allocation.max(), 0)}",
        ),
        NumberSpec(
            "F5_B",
            "non-motile reference allocation",
            F5_B_BASELINE,
            "the flagellar_allocation of the solved baseline step, which the panel draws dashed",
            lambda: percent(table(F5_B_BASELINE).flagellar_allocation.min(), 0),
        ),
        NumberSpec(
            "F5_B",
            "non-motile growth rate at 8 h",
            F5_B_GAIN,
            "the non_motile_growth_rate_8h_1h column, one value for every allocation",
            lambda: f"{fixed(one(table(F5_B_GAIN).non_motile_growth_rate_8h_1h, 'non-motile rate'), 3)} 1/h",
        ),
        NumberSpec(
            "F5_B",
            "non-motile distance from the source",
            F5_B_BASELINE,
            "the final_distance_um of the zero-allocation step, unchanged from the start",
            lambda: f"{whole(baseline_step()['final_distance_um'])} um",
        ),
        NumberSpec(
            "F5_B",
            "glucose the non-motile cell holds",
            F5_B_BASELINE,
            "the final_substrate_mM of the zero-allocation step",
            lambda: f"{fixed(baseline_step()['final_substrate_mM'], 3)} mM",
        ),
        NumberSpec(
            "F5_B",
            "motile growth-rate range at 8 h",
            F5_B_GAIN,
            "the smallest and the largest growth_rate_8h_1h of the motile family",
            lambda: f"{fixed(table(F5_B_GAIN).growth_rate_8h_1h.min(), 2)}-{fixed(table(F5_B_GAIN).growth_rate_8h_1h.max(), 2)} 1/h",
        ),
        NumberSpec(
            "F5_B",
            "growth-rate gain over the non-motile cell",
            F5_B_GAIN,
            "the smallest and the largest growth_rate_gain, as a percentage above one",
            lambda: f"{percent(table(F5_B_GAIN).growth_rate_gain.min() - 1.0, 0)} to {percent(table(F5_B_GAIN).growth_rate_gain.max() - 1.0, 0)}",
        ),
        NumberSpec(
            "F5_B",
            "compounded biomass gain over the non-motile cell",
            F5_B_GAIN,
            "the smallest and the largest biomass_gain",
            lambda: f"{fixed(table(F5_B_GAIN).biomass_gain.min(), 1)}-fold to {fixed(table(F5_B_GAIN).biomass_gain.max(), 1)}-fold",
        ),
        NumberSpec(
            "F5_B",
            "trajectory duration",
            "build/provenance/Figure_5/B.json",
            "the dynamic_duration_h parameter of the panel provenance",
            lambda: f"{whole(provenance('build/provenance/Figure_5/B.json')['dynamic_duration_h'])} h",
        ),
        NumberSpec(
            "F5_B",
            "solved steps of the 0-1% sweep",
            F5_B_BASELINE,
            "row count of the warm-start continuation status table, all of status success",
            solved_sweep_steps,
        ),
        NumberSpec(
            "F5_C",
            "unique optimum",
            F5_C_BIOMASS,
            "the flagella value that carries the largest relative_biomass",
            lambda: percent(
                table(F5_C_BIOMASS).loc[table(F5_C_BIOMASS).relative_biomass.idxmax(), "flagella"], 0
            ),
        ),
    ]
    for panel in ("F5_D", "F5_E"):
        specs += [
            NumberSpec(
                panel,
                "seeds per phenotype",
                F5_SEEDS[panel],
                "distinct seed per phenotype",
                seeds_per_phenotype(panel),
            ),
            NumberSpec(
                panel,
                "cells per seed",
                F5_SEEDS[panel],
                "the n_cells column, one value for every seed",
                seed_column(panel, "n_cells", whole),
            ),
            NumberSpec(
                panel,
                "domain width and height",
                F5_SEEDS[panel],
                "the box_width_um and box_height_um columns",
                lambda panel=panel: "{} x {} um".format(
                    whole(one(table(F5_SEEDS[panel]).box_width_um, "box width")),
                    whole(one(table(F5_SEEDS[panel]).box_height_um, "box height")),
                ),
            ),
            NumberSpec(
                panel,
                "integration step",
                F5_SEEDS[panel],
                "the dt_s column, one value for every seed",
                lambda panel=panel: f"{fixed(one(table(F5_SEEDS[panel]).dt_s, 'dt'), 4)} s",
            ),
            NumberSpec(
                panel,
                "simulation interval percentiles",
                F5_INTERVALS[panel],
                "the two interval column names of the statistics table",
                lambda panel=panel: "2.5-97.5%"
                if {"simulation_interval_2_5", "simulation_interval_97_5"} <= set(
                    table(F5_INTERVALS[panel]).columns
                )
                else "absent",
            ),
        ]
    specs += [
        NumberSpec(
            "F5_E",
            "obstacle disks",
            F5_SEEDS["F5_E"],
            "the n_obstacles column, one value for every seed",
            seed_column("F5_E", "n_obstacles", whole),
        ),
        NumberSpec(
            "F5_E",
            "realised obstacle area fraction",
            F5_SEEDS["F5_E"],
            "the mean obstacle_area_fraction over the seeds, to three decimals",
            lambda: fixed(table(F5_SEEDS["F5_E"]).obstacle_area_fraction.mean(), 3),
        ),
        NumberSpec(
            "F5_E",
            "reorientation angle spread",
            ADOPTED,
            "the turn_angle_sd_rad column, one value for all six strain-by-medium rows",
            lambda: f"{adopted_constant('turn_angle_sd_rad', 3)()} rad",
        ),
        NumberSpec(
            "F5_E",
            "mean stall duration",
            ADOPTED,
            "the stall_mean_duration_s column of the agarose rows",
            lambda: f"{adopted_constant('stall_mean_duration_s', 3)()} s",
        ),
    ]
    specs += [
        NumberSpec(
            "F5_E",
            "stall-probability exponent",
            STALL_AUDIT,
            "minus the log ratio of the adopted stall probabilities of PproB and PproA, divided by the log ratio of their mean hook numbers",
            stall_exponent,
        ),
        NumberSpec(
            "F5_E",
            "published stall-frequency ratio",
            STALL_COMMON,
            "the GROGNOT_STALL_FREQUENCY_RATIO and GROGNOT_STALL_FREQUENCY_RATIO_SD constants the exponent is anchored to",
            lambda: "{} +/- {}".format(
                literal(STALL_COMMON, r"GROGNOT_STALL_FREQUENCY_RATIO = ([0-9.]+)")[0],
                literal(STALL_COMMON, r"GROGNOT_STALL_FREQUENCY_RATIO_SD = ([0-9.]+)")[0],
            ),
        ),
        NumberSpec(
            "F5_E",
            "anchor mean turn magnitude",
            TURN_CALIBRATION,
            "the TAUTE_MEAN_TURN_ANGLE_DEG constant the angle spread is fitted to",
            lambda: f"{fixed(literal(TURN_CALIBRATION, r'TAUTE_MEAN_TURN_ANGLE_DEG = ([0-9.]+)')[0], 0)} deg",
        ),
        NumberSpec(
            "F5_E",
            "anchor turn count",
            TURN_CALIBRATION,
            "the TAUTE_TURN_COUNT constant, the number of measured turns behind the anchor",
            lambda: literal(TURN_CALIBRATION, r"TAUTE_TURN_COUNT = (\d+)")[0],
        ),
        NumberSpec(
            "F5_D",
            "simulated share of the measured effective diffusivity, liquid",
            DIFFUSIVITY,
            "the smallest and the largest ratio_to_measured_lag_corrected of the liquid rows of the corrected model",
            diffusivity_span("liquid", "ratio_to_measured_lag_corrected"),
        ),
        NumberSpec(
            "F5_E",
            "simulated share of the measured effective diffusivity, agarose-like",
            DIFFUSIVITY,
            "the smallest and the largest ratio_to_measured_lag_corrected of the agarose rows of the corrected model",
            diffusivity_span("agarose", "ratio_to_measured_lag_corrected"),
        ),
        NumberSpec(
            "F5_D",
            "simulated share of the implied v2 tau / 2, liquid",
            DIFFUSIVITY,
            "the smallest and the largest ratio_to_implied_lag_corrected of the liquid rows of the corrected model",
            diffusivity_span("liquid", "ratio_to_implied_lag_corrected"),
        ),
        NumberSpec(
            "F5_E",
            "convergence tolerance",
            CONVERGENCE,
            "the tolerance column of the time-step ladder",
            lambda: percent(one(table(CONVERGENCE).tolerance, "tolerance"), 0),
        ),
        NumberSpec(
            "F5_E",
            "largest group deviation per time step",
            CONVERGENCE,
            "the largest net_displacement_um_rel_deviation over the six strain-by-medium groups, per dt_s, coarsest step first",
            step_deviations,
        ),
        NumberSpec(
            "F5_E",
            "WT agarose-like mean path length, coarsest to finest step",
            CONVERGENCE,
            "path_length_um_mean of the WT agarose rows at the largest and at the smallest dt_s",
            path_length_span,
        ),
        NumberSpec(
            "F5_E",
            "PproA/WT path-length ratio, coarsest to finest step",
            CONVERGENCE_RATIOS,
            "path_length_um_ratio_to_wt of the PproA agarose rows at the largest and at the smallest dt_s",
            path_length_ratio_span,
        ),
        NumberSpec(
            "F5_E",
            "PproB agarose-like group-mean change between the two finest steps",
            CONVERGENCE,
            "the relative change of net_displacement_um_mean of PproB agarose between dt = 0.00125 s and dt = 0.000625 s",
            finest_step_change,
        ),
        NumberSpec(
            "F5_E",
            "PproB/PproA net-displacement ratio per time step",
            CONVERGENCE_RATIOS,
            "net_displacement_um_ratio_to_wt of PproB divided by that of PproA, per dt_s, coarsest step first",
            step_ratio_series,
        ),
        NumberSpec(
            "F5_E",
            "tested time-step ladder",
            CONVERGENCE,
            "the distinct dt_s of the ladder, coarsest step first",
            lambda: ", ".join(
                f"{value:g}" for value in sorted(set(table(CONVERGENCE).dt_s), reverse=True)
            )
            + " s",
        ),
        NumberSpec(
            "F5_E",
            "declared configuration time step",
            S4_PROVENANCE["D"],
            "the declared_config_dt_s parameter the builder overrides",
            lambda: f"{fixed(provenance(S4_PROVENANCE['D'])['declared_config_dt_s'], 2)} s",
        ),
    ]
    for phenotype in ("PproA", "WT", "PproB"):
        specs.append(
            NumberSpec(
                "F5_E",
                f"per-contact stall probability, {phenotype}",
                ADOPTED,
                "the stall_probability column of that agarose row, to three decimals",
                lambda phenotype=phenotype: fixed(
                    table(ADOPTED)
                    .set_index(["medium", "phenotype"])
                    .stall_probability.loc[("agarose", phenotype)],
                    3,
                ),
            )
        )

    # Figure 6
    specs += [
        NumberSpec(
            "F6_A",
            "soft-agar wells",
            F6_A_WELLS,
            "row count of the well table",
            lambda: whole(len(table(F6_A_WELLS))),
        ),
        NumberSpec(
            "F6_A",
            "WT well span, lower edge",
            F6_A_WELLS,
            "the smallest motility_value of the WT wells, to one decimal",
            wt_well_span("low"),
        ),
        NumberSpec(
            "F6_A",
            "WT well span, upper edge",
            F6_A_WELLS,
            "the largest motility_value of the WT wells, to one decimal",
            wt_well_span("high"),
        ),
        NumberSpec(
            "F6_A",
            "experiment days, WT",
            F6_A_WELLS,
            "distinct day_repeat_id of the WT wells",
            soft_agar_days("WT"),
        ),
        NumberSpec(
            "F6_A",
            "experiment days, each AnTc condition",
            F6_A_WELLS,
            "distinct day_repeat_id per non-WT condition",
            soft_agar_days("AnTc"),
        ),
        NumberSpec(
            "F6_B",
            "independent replicates per strain",
            F6_B_POINTS,
            "distinct replicate_id per condition",
            lambda: whole(
                one(table(F6_B_POINTS).groupby("condition").replicate_id.nunique(), "replicates")
            ),
        ),
        NumberSpec(
            "F6_C",
            "cells per radial region",
            F6_C_CELLS,
            "row count per condition of the cell table",
            lambda: whole(one(table(F6_C_CELLS).groupby("condition").size(), "cells per position")),
        ),
        NumberSpec("F6_C", "cell-dot threshold", F6_BUILDER, DOT_COMPUTATION, dot_threshold(F6_BUILDER)),
        NumberSpec(
            "F6_E",
            "imaging fields R1/R2/R3/R4",
            F6_E_REGIONS,
            "the n_rois column, one value per region_id",
            region_fields,
        ),
    ]

    # Figure 7
    for panel in ("F7_A", "F7_B", "F7_C"):
        specs.append(
            NumberSpec(
                panel,
                "paired units agarose/liquid",
                F7_PAIRS[panel],
                "distinct metadata_key per medium",
                paired_units(panel),
            )
        )
    specs += [
        NumberSpec(
            "F7_D",
            "paired-unit bootstrap resamples",
            "build/provenance/Figure_7/D.json",
            "the bootstrap_iterations parameter of the panel provenance",
            lambda: whole(provenance("build/provenance/Figure_7/D.json")["bootstrap_iterations"]),
        ),
        NumberSpec(
            "F7_D",
            "symmetric log axis span",
            "build/provenance/Figure_7/D.json",
            "the ratio_axis_limits parameter, printed as one over the upper bound to the upper bound",
            lambda: "1/{} to {}".format(
                fixed(1.0 / provenance("build/provenance/Figure_7/D.json")["ratio_axis_limits"][0], 1),
                fixed(provenance("build/provenance/Figure_7/D.json")["ratio_axis_limits"][1], 1),
            ),
        ),
    ]
    for panel in ("F7_E", "F7_F", "F7_G"):
        specs += [
            NumberSpec(
                panel,
                "independent days",
                F7_DAYS[panel],
                "distinct collapsed_repeat_id per phenotype",
                hook_days(panel),
            ),
            NumberSpec(panel, "cell-dot threshold", F7_BUILDER, DOT_COMPUTATION, dot_threshold(F7_BUILDER)),
        ]

    # Supplementary Figure 1
    for panel, source in (("S1_A", S1_A), ("S1_B", S1_B)):
        specs += [
            NumberSpec(
                panel, "cell values", source, "row count of the cell-level table", lambda source=source: cell_values(source)
            ),
            NumberSpec(
                panel,
                "pooled stable window",
                source,
                "the _window_start_min and _window_end_min columns",
                analysis_window(source),
            ),
            NumberSpec(
                panel,
                "independent experiments per strain and lineage class",
                source,
                "distinct replicate per strain",
                lambda source=source: replicates_per_strain(source),
            ),
        ]

    # Supplementary Figure 2
    specs += [
        NumberSpec(
            "S2_A",
            "flagellar-sector proteins",
            S2_A,
            "distinct uniprot_id of the plotted matrix",
            lambda: whole(table(S2_A).uniprot_id.nunique()),
        ),
        NumberSpec(
            "S2_A",
            "proteomics replicates per strain",
            F4_B_OVERLAY,
            "distinct replicate per mutant of the experiment rows; the panel plots their mean",
            proteomics_replicates,
        ),
        NumberSpec(
            "S2_A",
            "promoter-series conditions",
            S2_A,
            "distinct mutant of the plotted matrix",
            lambda: whole(table(S2_A).mutant.nunique()),
        ),
    ]

    # Supplementary Figure 4
    S4_PANELS = {
        "S4_A": ("A", "PproA", "liquid"),
        "S4_B": ("B", "WT", "liquid"),
        "S4_C": ("C", "PproB", "liquid"),
        "S4_D": ("D", "PproA", "agarose"),
        "S4_E": ("E", "WT", "agarose"),
        "S4_F": ("F", "PproB", "agarose"),
    }
    for panel, (letter, _, _) in S4_PANELS.items():
        record = S4_PROVENANCE[letter]
        specs += [
            NumberSpec(panel, "motile fraction", record, "the motile_fraction model input of the panel provenance", s4_parameter(letter, "motile_fraction", 2)),
            NumberSpec(panel, "run speed", record, "the run_speed_um_s model input of the panel provenance", lambda letter=letter: f"{s4_parameter(letter, 'run_speed_um_s', 1)()} um/s"),
            NumberSpec(panel, "reorientation rate", record, "the reorientation_rate_s model input of the panel provenance", lambda letter=letter: f"{s4_parameter(letter, 'reorientation_rate_s', 2)()} 1/s"),
            NumberSpec(panel, "stall probability", record, "the stall_probability model input of the panel provenance", s4_parameter(letter, "stall_probability", 2)),
            NumberSpec(panel, "panel seed", record, "the panel_seed entry of the panel provenance", s4_seed(letter)),
        ]
    specs += [
        NumberSpec(
            "S4_A",
            "cells per panel",
            S4_PROVENANCE["A"],
            "the n_cells parameter of the panel provenance",
            lambda: whole(provenance(S4_PROVENANCE["A"])["n_cells"]),
        ),
        NumberSpec(
            "S4_A",
            "simulated time",
            S4_PROVENANCE["A"],
            "the track_duration_s parameter of the panel provenance",
            lambda: f"{whole(provenance(S4_PROVENANCE['A'])['track_duration_s'])} s",
        ),
        NumberSpec(
            "S4_A",
            "integration step",
            S4_PROVENANCE["A"],
            "the dt_s parameter of the panel provenance",
            lambda: f"{fixed(provenance(S4_PROVENANCE['A'])['dt_s'], 4)} s",
        ),
        NumberSpec(
            "S4_A",
            "published domain width and height",
            S4_PROVENANCE["A"],
            "the box_width_um and box_height_um parameters of the panel provenance",
            lambda: "{} x {} um".format(
                whole(provenance(S4_PROVENANCE["A"])["box_width_um"]),
                whole(provenance(S4_PROVENANCE["A"])["box_height_um"]),
            ),
        ),
        NumberSpec(
            "S4_D",
            "obstacle disks per map",
            S4_PROVENANCE["D"],
            "the obstacle_config count parameter of the panel provenance",
            lambda: whole(provenance(S4_PROVENANCE["D"])["obstacle_config"]["count"]),
        ),
        NumberSpec(
            "S4_D",
            "obstacle-field seed offset",
            S4_PROVENANCE["D"],
            "obstacle_seed minus panel_seed of the panel provenance",
            lambda: whole(
                provenance(S4_PROVENANCE["D"])["obstacle_seed"]
                - provenance(S4_PROVENANCE["D"])["panel_seed"]
            ),
        ),
        NumberSpec(
            "S4_A",
            "starting-position seed offset",
            S4_PROVENANCE["A"],
            "starting_position_seed minus panel_seed of the panel provenance",
            lambda: whole(
                provenance(S4_PROVENANCE["A"])["starting_position_seed"]
                - provenance(S4_PROVENANCE["A"])["panel_seed"]
            ),
        ),
        NumberSpec(
            "S4_D",
            "reorientation angle spread",
            ADOPTED,
            "the turn_angle_sd_rad column, one value for all six strain-by-medium rows",
            lambda: f"{adopted_constant('turn_angle_sd_rad', 3)()} rad",
        ),
        NumberSpec(
            "S4_D",
            "mean stall duration",
            ADOPTED,
            "the stall_mean_duration_s column of the agarose rows",
            lambda: f"{adopted_constant('stall_mean_duration_s', 3)()} s",
        ),
    ]

    # Supplementary Figure 5
    for panel in ("S5_A", "S5_B", "S5_C"):
        specs += [
            NumberSpec(
                panel,
                "paired experiments agarose/liquid",
                S5_AUDITS[panel],
                "the n_paired_units column per medium",
                s5_paired_experiments(panel),
            ),
            NumberSpec(
                panel,
                "agarose trajectories per phenotype",
                S5_AUDITS[panel],
                "the n_trajectories column of the agarose rows, first phenotype of the pair first",
                s5_trajectories(panel, "agarose"),
            ),
            NumberSpec(
                panel,
                "liquid trajectories per phenotype",
                S5_AUDITS[panel],
                "the n_trajectories column of the liquid rows, first phenotype of the pair first",
                s5_trajectories(panel, "liquid"),
            ),
            NumberSpec(
                panel,
                "contour probability mass",
                S5_PROVENANCE[panel],
                "the contour_probability_mass parameter of the panel provenance",
                contour_masses(panel),
            ),
            NumberSpec(
                panel,
                "centroid bootstrap resamples",
                S5_PROVENANCE[panel],
                "the bootstrap_iterations parameter of the panel provenance",
                lambda panel=panel: whole(provenance(S5_PROVENANCE[panel])["bootstrap_iterations"]),
            ),
            NumberSpec(
                panel,
                "density-grid padding, kernel bandwidths per axis",
                S5_PROVENANCE[panel],
                "the density_grid_padding_bandwidths parameter of the panel provenance",
                lambda panel=panel: whole(
                    provenance(S5_PROVENANCE[panel])["density_grid_padding_bandwidths"]
                ),
            ),
        ]

    specs += probability_specs()
    return specs


# --- the exact P values the legends print ------------------------------------
#
# A panel earns a P value only where it draws a comparison the argument rests
# on.  A descriptive panel prints no P value and says so instead.  Figure 1C and
# 1D are the titration, which is read as a series and not as six contrasts, so
# they carry only the smallest corrected value of their family, which is what
# stops a reader inferring a per-level difference that the data do not carry.

F1_C_STATS = "build/statistics/Figure_1/C/F1_C_statistics.csv"
F1_D_STATS = "build/statistics/Figure_1/D/F1_D_statistics.csv"
F1_H_STATS = "build/statistics/Figure_1/H/F1_H_statistics.csv"
F2_A_STATS = "build/statistics/Figure_2/A/F2_A_statistics.csv"
F2_B_STATS = "build/statistics/Figure_2/B/F2_B_statistics.csv"
F2_C_STATS = "build/statistics/Figure_2/C/F2_C_statistics.csv"
F3_B_STATS = "build/statistics/Figure_3/B/F3_B_statistics.csv"
F3_C_STATS = "build/statistics/Figure_3/C/F3_C_statistics.csv"
F3_E_STATS = "build/statistics/Figure_3/E/F3_E_statistics.csv"
F4_B_REGRESSIONS = "build/statistics/Figure_4/B/A1_sector_regressions.csv"
F6_B_STATS = "build/statistics/Figure_6/B/Figure_6B_paired_statistics.csv"

WELCH = "the p_value_welch_t column of that comparison row, to two significant figures"
PAIRED_T = "the p_value_paired_t column of that comparison row, to two significant figures"


def smallest_q(relative: str, column: str, family: str, panel_id: str) -> NumberSpec:
    return NumberSpec(
        panel_id,
        f"smallest Benjamini-Hochberg q value, {family}",
        relative,
        f"the smallest {column} of the panel's correction family",
        lambda: probability(table(relative)[column].dropna().min()),
    )


def probability_specs() -> list[NumberSpec]:
    specs: list[NumberSpec] = []

    # Figure 1.  C and D are descriptive; only the corrected floor is printed.
    specs.append(
        smallest_q(F1_C_STATS, "q_value_bh_fdr", "six AnTc levels against WT", "F1_C")
    )
    specs.append(
        smallest_q(F1_D_STATS, "q_value_bh_fdr", "six AnTc levels against WT", "F1_D")
    )
    specs += comparison_specs(
        "F1_H",
        F1_H_STATS,
        "plot_key",
        "p_value_welch_t",
        "exact P value against TH9677",
        WELCH,
    )
    specs += q_range_specs(
        "F1_H", F1_H_STATS, "plot_key", "q_value_bh_fdr", "four Ppro strains against TH9677"
    )

    # Figure 2 and Figure 3.  Every drawn comparison carries its own value.
    for panel, source, family in (
        ("F2_A", F2_A_STATS, "six AnTc levels against the same-day WT"),
        ("F2_B", F2_B_STATS, "four Ppro strains against the same-day WT"),
        ("F2_C", F2_C_STATS, "three Ppro strains against Ppro1-flhDC"),
        ("F3_B", F3_B_STATS, "five assembly mutants against the same-day WT"),
        ("F3_C", F3_C_STATS, "five assembly mutants against the replicate WT"),
    ):
        specs += comparison_specs(
            panel, source, "strain", "p_value_paired_t", "exact P value", PAIRED_T
        )
        specs += q_range_specs(panel, source, "strain", "q_value_bh", family)

    specs += comparison_specs(
        "F3_E",
        F3_E_STATS,
        "comparison",
        "p_value_paired_t",
        "exact P value against the same-day ΔflhDC reference",
        PAIRED_T,
    )
    specs += q_range_specs(
        "F3_E", F3_E_STATS, "comparison", "q_value_bh", "two rotation conditions"
    )

    # Figure 4B.  The panel draws measured sector changes and a model line, not
    # a regression.  Only the ribosomal sector is printed, because the
    # ribosome-flagella trade-off is the claim the figure rests on; the other
    # six sector regressions stay in the registered table, and the legend says
    # so.
    specs += [
        NumberSpec(
            "F4_B",
            "exact P value, ribosomal-sector slope against flagellar allocation",
            F4_B_REGRESSIONS,
            "the p_value of the Rib row, a two-sided test that the slope is zero",
            lambda: probability(
                one(table(F4_B_REGRESSIONS).query("sector_short == 'Rib'").p_value, "Rib P")
            ),
        ),
        NumberSpec(
            "F4_B",
            "Benjamini-Hochberg q value, ribosomal-sector slope",
            F4_B_REGRESSIONS,
            "the p_bh of the Rib row, corrected over the seven non-flagellar sectors",
            lambda: probability(
                one(table(F4_B_REGRESSIONS).query("sector_short == 'Rib'").p_bh, "Rib q")
            ),
        ),
        NumberSpec(
            "F4_B",
            "ribosomal-sector slope with its 95% confidence interval",
            F4_B_REGRESSIONS,
            "the slope, slope_ci95_low and slope_ci95_high of the Rib row",
            lambda: "{} (95% CI {} to {})".format(
                fixed(one(table(F4_B_REGRESSIONS).query("sector_short == 'Rib'").slope, "slope"), 2),
                fixed(
                    one(
                        table(F4_B_REGRESSIONS).query("sector_short == 'Rib'").slope_ci95_low,
                        "slope CI low",
                    ),
                    2,
                ),
                fixed(
                    one(
                        table(F4_B_REGRESSIONS).query("sector_short == 'Rib'").slope_ci95_high,
                        "slope CI high",
                    ),
                    2,
                ),
            ),
        ),
    ]

    # Figure 6B.  The registered table carries no corrected column, so the
    # legend prints P values and says that no correction is registered.
    specs += comparison_specs(
        "F6_B",
        F6_B_STATS,
        "comparison",
        "exact_p_value",
        "exact P value",
        "the exact_p_value column of that comparison row, to two significant figures",
    )
    return specs


def read_panels() -> list[dict[str, str]]:
    with (ROOT / "config" / "panels.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    panels = read_panels()
    panel_map = [
        {
            "panel_id": row["panel_id"],
            "figure_id": row["figure_id"],
            "panel_label": row["panel_label"],
            "title": row["title"],
            "legacy_panel_ids": row["legacy_panel_ids"],
            "status": row["status"],
        }
        for row in panels
    ]
    write_csv(REPORTS / "panel_map_revision_2026-08-12.csv", list(panel_map[0]), panel_map)

    element_rows = []
    for row in panels:
        specification = ELEMENTS.get(row["panel_id"])
        if specification is None:
            # The former fallback wrote "point or line, defined in the panel
            # legend and source-data table" for any panel without an entry.
            # That is a deferral, not a definition, and it outlived the panels
            # it stood for.  A missing entry is now a build error.
            raise KeyError(
                f"{row['panel_id']} has no graphical-element specification; "
                "add one to ELEMENTS after reading the rendered panel"
            )
        elements, definitions = specification.split("|", 1)
        element_items = elements.split(";")
        definition_items = (
            [definitions]
            if len(element_items) == 1
            else definitions.split("; ", len(element_items) - 1)
        )
        if len(definition_items) == 1 and len(element_items) > 1:
            definition_items *= len(element_items)
        for element, definition in zip(element_items, definition_items, strict=True):
            element_rows.append(
                {
                    "panel_id": row["panel_id"],
                    "element": element,
                    "definition_or_action": definition,
                }
            )
    write_csv(REPORTS / "graphical_elements.csv", list(element_rows[0]), element_rows)

    figure_of = {row["panel_id"]: FIGURE_TITLES[row["figure_id"]] for row in panels}
    number_rows = []
    for spec in figure_number_specs():
        if spec.panel_id not in figure_of:
            raise KeyError(f"{spec.panel_id} is not a panel in config/panels.csv")
        number_rows.append(
            {
                "figure": figure_of[spec.panel_id],
                "panel_id": spec.panel_id,
                "quantity": spec.quantity,
                "value": spec.rule(),
                "source_file": spec.source,
                "computation": spec.computation,
            }
        )
    write_csv(REPORTS / "figure_numbers.csv", list(number_rows[0]), number_rows)
    print(f"wrote reports for {len(panels)} panels and {len(number_rows)} recomputed numbers")


if __name__ == "__main__":
    main()
