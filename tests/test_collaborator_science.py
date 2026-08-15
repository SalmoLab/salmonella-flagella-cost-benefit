from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[1]


def test_promoter_proteomics_invariants() -> None:
    external = ROOT / "data/external/promoter_series_proteomics"
    raw = pd.read_csv(external / "maxLFQ_protein_intensity_data.csv")
    annotated = pd.read_csv(external / "protein_massfrac_annotated.csv", low_memory=False)
    sectors = pd.read_csv(external / "sector_mass_fractions.tsv", sep="\t")

    accessions = raw["PG.ProteinGroups"].str.split(";").explode()
    assert accessions.nunique() == 2751
    assert raw["R.Condition"].nunique() == 6
    assert raw[["R.Condition", "R.Replicate"]].drop_duplicates().shape[0] == 24

    group_annotation = annotated.groupby("uniprot_id", as_index=False).first()
    annotated_accessions = group_annotation["sector"].notna().sum()
    assert annotated_accessions == 1306
    expanded_groups = raw[["PG.ProteinGroups"]].drop_duplicates()
    annotated_ids = set(group_annotation.loc[group_annotation.sector.notna(), "uniprot_id"])
    annotated_groups = expanded_groups["PG.ProteinGroups"].apply(
        lambda value: any(item in annotated_ids for item in value.split(";"))
    )
    assert int(annotated_groups.sum()) == 1304

    sums = sectors.groupby(["mutant", "replicate"]).mass_fraction.sum()
    np.testing.assert_allclose(sums, 1.0, atol=1e-10)
    means = sectors.groupby(["mutant", "sector_short"]).mass_fraction.mean().unstack()
    assert np.isclose(means.loc["PproD-flhDC", "Fla"], 0.033911, atol=1e-6)
    assert means[["Fla", "Rib"]].corr().iloc[0, 1] < -0.98


def test_static_model_headline_penalties() -> None:
    root = ROOT / "data/external/cell_economy_results/rotation"
    values = {}
    for name in [
        "steady_state_flag_0.00_ATP.csv",
        "steady_state_flag_0.05_ATP.csv",
        "steady_state_flag_0.05_no_ATP.csv",
    ]:
        frame = pd.read_csv(root / name)
        values[name] = float(frame.loc[np.isclose(frame.cex, 1.0), "mu"].iloc[0])
    baseline = values["steady_state_flag_0.00_ATP.csv"]
    rotation = (baseline - values["steady_state_flag_0.05_ATP.csv"]) / baseline * 100
    no_rotation = (baseline - values["steady_state_flag_0.05_no_ATP.csv"]) / baseline * 100
    assert np.isclose(rotation, 8.391678, atol=1e-6)
    assert np.isclose(no_rotation, 7.362563, atol=1e-6)


def test_gradient_model_unique_three_percent_optimum() -> None:
    """The gradient model has one optimum, at 3 % flagellar allocation.

    The claim was Figure 3G in July and is Figure 5C today; see the F5_C row of
    docs/revision_2026-08-12/figure_numbers.csv. This reads the live registered
    table. It read the superseded copy under data/source_data/f3_g/ until
    15 August 2026, which no build step wrote, so a change in the model would
    not have reached this guard.
    """
    data = pd.read_csv(ROOT / "build/source_data/Figure_5/C/relative_biomass.csv")
    expected = np.array([0.235017, 0.586146, 0.931448, 1.0, 0.958478, 0.863218])
    np.testing.assert_allclose(data.relative_biomass, expected, atol=1e-6)
    assert float(data.loc[data.relative_biomass.idxmax(), "flagella"]) == 0.03
    assert int((data.relative_biomass == data.relative_biomass.max()).sum()) == 1


def test_updated_s4_source_identity_and_seeds() -> None:
    """The simulated-track panels became Supplementary Figure 4 on 12 August 2026.

    The analysis directory was renamed to ``supplementary_04`` on 15 August 2026
    to match. The seeds are unchanged across both moves, which is what this pins.
    """
    expected = {
        "S4_A": 24,
        "S4_B": 106,
        "S4_C": 65,
        "S4_D": 17,
        "S4_E": 99,
        "S4_F": 58,
    }
    for panel_id, seed in expected.items():
        table = pd.read_csv(
            ROOT / f"data/source_data/supplementary_04/{panel_id}_simulated_trajectories.csv.gz"
        )
        assert set(table.seed) == {seed}
        assert table.cell_id.nunique() == 26
        assert np.isclose(table.time_s.max(), 20.0)
