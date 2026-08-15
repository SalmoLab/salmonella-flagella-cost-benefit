"""Scientific and reproducibility checks for revised Figures 4 and 5."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
for _module_name in list(sys.modules):
    if _module_name == "flagella_repro" or _module_name.startswith("flagella_repro."):
        del sys.modules[_module_name]


def _load(name: str, relative_path: str):
    path = PROJECT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F4 = _load("revision_figure_04", "analyses/figure_04_revision/build.py")
S2 = _load("collaborator_science_panels", "analyses/collaborator_science/build_panels.py")
F5 = _load("revision_figure_05", "analyses/figure_05_revision/build.py")
A3 = _load("revision_a3_sweep", "models/cell_economy/low_allocation_sweep.py")


def test_editable_schematic_is_exact_immutable_intake_copy() -> None:
    schematic = PROJECT / "assets/schematics/salmonella_model.svg"
    digest = hashlib.sha256(schematic.read_bytes()).hexdigest()
    assert digest == "996e3be8ca7df8bb87c03857fb38e7815f7f8f0ce641fccd47b93673186319f4"
    text = schematic.read_text(encoding="utf-8")
    assert "<text" in text
    assert "<image" not in text


def test_a1_condition_mean_regressions_and_multiple_testing() -> None:
    result = F4.analyse_a1().set_index("sector_short")
    assert set(result.index) == {"Oth", "Rib", "Cbn", "Aab", "Etc", "Lpb", "Tra"}
    assert (result.n_condition_means == 6).all()
    assert (result.biological_replicates_per_condition == 4).all()
    # Sector totals are re-summed through the documented protein-sector
    # overrides, so the slopes differ slightly from the delivered sector table.
    assert result.loc["Rib", "slope"] == pytest.approx(-1.4911711769)
    assert result.loc["Rib", "p_bh"] < 0.002
    for sector in ("Cbn", "Aab", "Tra"):
        assert result.loc[sector, "slope"] > 0
        assert result.loc[sector, "p_bh"] < 0.02
    for sector in ("Oth", "Etc", "Lpb"):
        assert result.loc[sector, "p_bh"] > 0.05


def test_a5_is_predeclared_descriptive_allocation_test() -> None:
    replicates, summary = F4.analyse_a5()
    row = summary.iloc[0]
    assert set(row.chemotaxis_genes.split(";")) == {"cheA", "cheW", "tar", "tsr"}
    assert len(replicates) == 24
    assert replicates.groupby("mutant").size().eq(4).all()
    assert row.slope == pytest.approx(1.1108338561)
    assert row.slope_ci95_low < 1 < row.slope_ci95_high
    assert row.p_value_slope_equals_one > 0.1
    assert "does not test chemotactic function" in row.interpretation_boundary


def test_top10_label_rule_is_auditable() -> None:
    audit = F4.label_audit(F4.top10_table())
    assert len(audit) == 80
    assert int(audit.selected.sum()) == 24
    flic = audit.query("gene_name_short == 'fliC'")
    assert len(flic) == 1 and bool(flic.iloc[0].selected)
    # Every label carries the absolute floor, and every label that is not FliC
    # clears either the relative share rule or the sector abundance rank.
    named = audit.query("selected and gene_name_short != 'fliC'")
    assert (named.max_mass_fraction >= F4.ABSOLUTE_FLOOR).all()
    assert (named.share_rule | named.leader_rule).all()
    assert (audit.relative_threshold == 0.15).all()
    assert (audit.absolute_floor == F4.ABSOLUTE_FLOOR).all()
    assert audit.reason.str.len().gt(0).all()
    # Tsr is the second flagellar protein of the series and is now named; the
    # two proteins the override moves out of the sector are no longer in it.
    flagellar = audit.query("sector_short == 'Fla'")
    assert set(flagellar.query("selected").gene_name_short) == {"fliC", "tsr", "fliO"}
    assert {"rpoD", "rbsB"}.isdisjoint(set(flagellar.gene_name_short))


def test_both_proteomics_figures_read_one_sector_override() -> None:
    overrides = F4.load_sector_overrides()
    assert set(overrides.uniprot_id) == {"P0A2E3", "P0A2C5"}
    assert (overrides.delivered_sector_short == "Fla").all()
    assert overrides.reason.str.len().gt(40).all()
    figure_4 = F4.protein_table()
    supplementary_2 = S2.protein_table()
    for uniprot, sector in zip(overrides.uniprot_id, overrides.override_sector_short, strict=True):
        assert set(figure_4.loc[figure_4.uniprot_id == uniprot, "sector_short"]) == {sector}
        assert set(
            supplementary_2.loc[supplementary_2.uniprot_id == uniprot, "sector_short"]
        ) == {sector}
    # The two builders must resolve every protein to the same sector.
    keys = ["uniprot_id", "sector_short"]
    assert set(map(tuple, figure_4[keys].drop_duplicates().to_numpy())) == set(
        map(tuple, supplementary_2[keys].drop_duplicates().to_numpy())
    )


def test_delta_overlay_exposes_model_experiment_direction_mismatches() -> None:
    data = F4.overlay_data(relative=True)
    model = data.query("series == 'model'")
    reference = model.query("x_flagella == 0").set_index("sector_short").value
    assert np.allclose(reference.reindex(F4.SECTORS), 0)
    experiment = data.query("series == 'experiment'")
    delta_means = experiment.query("mutant == 'ΔflhDC'").groupby("sector_short").value.mean()
    assert np.allclose(delta_means.reindex(F4.SECTORS), 0, atol=1e-15)
    expected_opposite = {
        "Cbn": ("negative", "positive"),
        "Aab": ("negative", "positive"),
        "Etc": ("positive", "negative"),
        "Tra": ("negative", "positive"),
    }
    for sector, (model_direction, experiment_direction) in expected_opposite.items():
        model_at_five_percent = (
            model.loc[model.sector_short.eq(sector)].sort_values("x_flagella").value.iloc[-1]
        )
        pprod = experiment.loc[
            experiment.sector_short.eq(sector) & experiment.mutant.eq("PproD-flhDC"), "value"
        ].mean()
        assert np.sign(model_at_five_percent) == (-1 if model_direction == "negative" else 1)
        assert np.sign(pprod) == (-1 if experiment_direction == "negative" else 1)


def test_gradient_model_reproduces_manuscript_optimum() -> None:
    data = (
        F5.swimming_table()
        .sort_values("time")
        .groupby("flagella", as_index=False)
        .tail(1)
        .sort_values("flagella")
    )
    relative = data.biomass.to_numpy() / data.biomass.max()
    assert np.allclose(data.flagella, F5.FLAGELLAR_ALLOCATIONS)
    assert np.allclose(relative, [0.23501734, 0.58614568, 0.93144755, 1, 0.95847844, 0.86321834])
    assert data.loc[data.biomass.idxmax(), "flagella"] == pytest.approx(0.03)


def test_active_particle_seed_contract_and_determinism() -> None:
    plan = F5.seed_plan()
    assert len(plan) == 600
    assert plan.groupby(["phenotype", "medium"]).size().eq(100).all()
    assert set(plan.phenotype) == {"PproA", "WT", "PproB"}
    assert "WT_slow" not in set(plan.phenotype)
    assert (plan.n_cells == 26).all()
    assert plan.seed.min() == 1000 and plan.seed.max() == 1099

    one_per_group = plan.groupby(["phenotype", "medium"], as_index=False).head(1)
    first = F5.active_particle_seed_summary(one_per_group)
    second = F5.active_particle_seed_summary(one_per_group)
    pd.testing.assert_frame_equal(first, second, check_exact=True)
    assert len(first) == 6 and (first.n_cells == 26).all()


def test_full_active_particle_summary_has_expected_ordering() -> None:
    path = PROJECT / "data/processed/figure_05_revision/active_particle_100_seed_summary.csv"
    if not path.is_file():
        pytest.skip("Run the Figure 5 builder to materialize the 600-seed source-data table.")
    data = pd.read_csv(path)
    summary = F5.summarize_seed_predictions(data)
    assert len(data) == 600
    assert summary.n_seeds.eq(100).all()
    for medium in F5.MEDIA:
        means = summary.loc[summary.medium.eq(medium)].set_index("phenotype").seed_mean
        assert means.PproA < means.WT < means.PproB


def test_a3_low_allocation_sweep_is_explicitly_blocked() -> None:
    plan = A3.sweep_plan()
    assert len(plan) == 21
    assert plan.flagellar_allocation.iloc[0] == 0
    assert plan.flagellar_allocation.iloc[-1] == pytest.approx(0.01)
    assert np.allclose(np.diff(plan.flagellar_allocation), 0.0005)
    assert plan.status.eq("blocked_exact_solver_unavailable").all()
    assert plan.objective_final_growth_rate_1h.isna().all()
    assert plan.final_distance_um.isna().all()


def test_nested_canonical_output_contract() -> None:
    assert F4.panel_stem("A") == PROJECT / "build/panels/Figure_4/A/Figure_4_A"
    assert F5.panel_stem("E") == PROJECT / "build/panels/Figure_5/E/Figure_5_E"
    assert F4.BUILD_SOURCE == PROJECT / "build/source_data/Figure_4"
    assert F5.STATISTICS == PROJECT / "build/statistics/Figure_5"
