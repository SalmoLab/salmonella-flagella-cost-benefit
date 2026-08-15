from __future__ import annotations

import json
from pathlib import Path

import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

from analyses.figure_03_revision.scripts.build_revision import (
    _build_model_curve,
    _experimental_penalties,
)
from flagella_repro.population_growth import _prepare
from flagella_repro.theme import (
    ANTC_COLORS,
    PROMOTER_COLORS,
    SECTOR_COLORS,
    STRAIN_STYLES,
    get_strain_style,
)

ROOT = Path(__file__).resolve().parents[1]


def _config(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def _relative_luminance(color: str) -> float:
    rgb = np.asarray(mcolors.to_rgb(color))
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return float(linear @ np.asarray([0.2126, 0.7152, 0.0722]))


def test_shared_palette_preserves_collaborator_sector_colors() -> None:
    assert SECTOR_COLORS == {
        "Oth": "#B3B3B3",
        "Rib": "#A6761D",
        "Cbn": "#E6AB02",
        "Aab": "#7570B3",
        "Etc": "#66A61E",
        "Lpb": "#1B9E77",
        "Fla": "#E7298A",
        "Tra": "#DF9359",
    }


def test_ordered_condition_ramps_are_monotonic_in_luminance() -> None:
    antc = [_relative_luminance(ANTC_COLORS[key]) for key in ("0", "0.25", "0.5", "1", "2", "4")]
    promoter = [
        _relative_luminance(PROMOTER_COLORS[key])
        for key in ("Ppro1", "PproA", "PproB", "PproD")
    ]
    assert np.all(np.diff(antc) < 0)
    assert np.all(np.diff(promoter) < 0)


def test_mutants_retain_color_and_marker_redundancy() -> None:
    strains = ["TH5861", "EM16223", "EM4208", "EM4209", "EM16224", "EM16587"]
    styles = [get_strain_style(item) for item in strains]
    assert len({item["color"] for item in styles}) == len(styles)
    assert len({item["marker"] for item in styles}) >= 5
    assert STRAIN_STYLES["EM16224"]["label"] == "motB (D33N)"


def test_revised_panel_mapping_and_blocker_are_explicit() -> None:
    configs = {
        "F3_A": _config("analyses/figure_03_revision/panel_a/config/panel.json"),
        "F3_B": _config("analyses/figure_03_revision/panel_b/config/panel.json"),
        "F3_C": _config("analyses/figure_03_revision/panel_c/config/config.json"),
        "F3_D": _config("analyses/figure_03_revision/panel_d/config/panel.json"),
        "F3_E": _config("analyses/figure_03_revision/panel_e/config/panel.json"),
    }
    assert list(configs) == ["F3_A", "F3_B", "F3_C", "F3_D", "F3_E"]
    assert all(value["figure_number"] == 3 for value in configs.values())
    assert [value["panel_label"] for value in configs.values()] == list("ABCDE")
    assert configs["F3_A"]["status"] == "blocked_asset"
    assert "schematic" in configs["F3_A"]["missing_artifact"]


def test_population_panels_normalize_to_same_day_reference() -> None:
    for relative_config in (
        "analyses/figure_02/panel_a/config/panel.json",
        "analyses/figure_02/panel_b/config/panel.json",
        "analyses/figure_03_revision/panel_b/config/panel.json",
    ):
        config = _config(relative_config)
        _, days = _prepare(ROOT / config["input_table"], config)
        reference = days.loc[days["strain"] == config["reference_strain"]]
        np.testing.assert_allclose(reference["relative_growth_rate"], 1.0, atol=1e-12)
        assert len(reference) == days["experiment_day"].nunique() == 6


def test_ppro_single_cell_reference_is_paired_by_replicate() -> None:
    config = _config("analyses/figure_02/panel_c/config/config.json")
    means = pd.read_csv(ROOT / config["replicate_means_csv"])
    assert config["normalization_reference"] == "EM9662"
    reference = means.loc[means["strain"] == "EM9662"]
    assert set(reference["replicate"]) == set(means["replicate"]) == {"R1", "R2"}


def test_growth_penalty_targets_use_independent_experiment_days() -> None:
    penalties = _experimental_penalties()
    assert penalties.groupby("comparison")["experiment_day"].nunique().eq(6).all()
    means = penalties.groupby("comparison")["growth_penalty_percent"].mean()
    assert np.isclose(means["Rotating flagella"], 12.8992739026, atol=1e-9)
    assert np.isclose(means["Non-rotating flagella"], 9.4840384810, atol=1e-9)


def test_cell_economy_penalty_targets_are_preserved() -> None:
    _, statistics, figure, _, _ = _build_model_curve()
    try:
        values = statistics.set_index("rotation_state")["growth_penalty_percent"]
        assert np.isclose(values["rotating"], 8.39167784687, atol=1e-9)
        assert np.isclose(values["non-rotating"], 7.36256286647, atol=1e-9)
    finally:
        figure.clf()


def test_revised_plotting_code_has_no_stars_inner_boxes_or_replicate_lines() -> None:
    files = [
        ROOT / "analyses/figure_01/plotting.py",
        ROOT / "analyses/figure_02/panel_c/scripts/plot.py",
        ROOT / "src/flagella_repro/population_growth.py",
        ROOT / "analyses/figure_03_revision/scripts/build_revision.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
    assert 'inner="box"' not in combined
    assert "significance_bh_fdr" not in combined
    assert 'return "****"' not in combined
    population = (ROOT / "src/flagella_repro/population_growth.py").read_text(encoding="utf-8")
    assert 'replicate["x"]' not in population


def test_nested_output_contract_is_encoded_in_all_engines() -> None:
    population = (ROOT / "src/flagella_repro/population_growth.py").read_text(encoding="utf-8")
    single_cell = (ROOT / "analyses/figure_02/panel_c/scripts/plot.py").read_text(encoding="utf-8")
    figure_one = (ROOT / "analyses/figure_01/plotting.py").read_text(encoding="utf-8")
    assert '"build" / "panels" / figure_name / panel_label' in population
    assert '"build" / "panels" / figure_name / panel_label' in single_cell
    assert '"build" / "panels" / figure_name / panel_label' in figure_one
